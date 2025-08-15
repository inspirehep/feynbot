import argparse
import logging
import math
import multiprocessing
import time
from os import getenv

from backend.src.utils.embeddings import VLLMOpenAIEmbeddings
from docling.chunking import HybridChunker
from docling.datamodel.accelerator_options import AcceleratorDevice, AcceleratorOptions
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling_core.transforms.chunker.hierarchical_chunker import (
    ChunkingDocSerializer,
    ChunkingSerializerProvider,
)
from docling_core.transforms.chunker.tokenizer.huggingface import HuggingFaceTokenizer
from docling_core.transforms.serializer.markdown import MarkdownParams
from docling_core.types.doc.document import DocItemLabel
from langchain_core.documents import Document
from langchain_docling import DoclingLoader
from loguru import logger
from opensearchpy.helpers import scan
from tqdm import tqdm
from transformers import AutoTokenizer
from utils import (
    get_indexed_control_numbers,
    get_inspire_os_client,
    get_os_query,
    get_vector_os_client,
)

RECORDS_INDEX_NAME = "records-hep"
HF_EMBEDDING_MODEL_ID = "thellert/accphysbert_cased"
CHUNK_SIZE = 510  # Model supports 512 but docling seems to be off by 1 in a few cases


class SequenceLengthFilter(logging.Filter):
    """Suppress harmless sequence length warning from transformers caused by docling"""

    def filter(self, record):
        return not (
            record.levelno == logging.WARNING
            and (
                "Token indices sequence length is longer than the specified maximum "
                "sequence length for this model"
            )
            in record.getMessage()
        )


transformers_logger = logging.getLogger("transformers")
transformers_logger.addFilter(SequenceLengthFilter())

for handler in transformers_logger.handlers:
    handler.addFilter(SequenceLengthFilter())


class NoContextHybridChunker(HybridChunker):
    """HybridChunker that returns raw text without contextualization. Solves
    the issue of exceeding the final embedding token length due to added headings.
    """

    def serialize(self, chunk):
        return chunk.text


class NoFormulaSerializerProvider(ChunkingSerializerProvider):
    """Serializer provider that removes (<!-- formula-not-decoded --> placeholders)"""

    def get_serializer(self, doc):
        params = MarkdownParams()
        params.labels.remove(DocItemLabel.FORMULA)
        params.image_placeholder = ""

        return ChunkingDocSerializer(
            doc=doc,
            params=params,
        )


def get_control_numbers(es_client, os_query, index):
    control_numbers = []
    batch_size = 10000
    for i, doc in enumerate(
        scan(
            client=es_client,
            query={"query": os_query},
            index=index,
            _source=["control_number"],
            size=batch_size,
            scroll="10m",
        ),
        start=1,
    ):
        cn = doc["_source"].get("control_number")
        if cn is not None:
            control_numbers.append(int(cn))
        if i % batch_size == 0:
            logger.debug(f"Fetched {i} control numbers")
    return sorted(control_numbers)


def process_pdf(pdf_url, tokenizer, chunk_size=CHUNK_SIZE):
    try:
        accphysbert_tokenizer = HuggingFaceTokenizer(
            tokenizer=tokenizer,
            max_tokens=chunk_size,
        )

        chunker = NoContextHybridChunker(
            tokenizer=accphysbert_tokenizer,
            serializer_provider=NoFormulaSerializerProvider(),
        )

        accelerator_options = AcceleratorOptions(
            num_threads=1,
            device=AcceleratorDevice.CPU,
        )

        pipeline_options = PdfPipelineOptions(
            do_ocr=False, accelerator_options=accelerator_options
        )

        converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(
                    pipeline_options=pipeline_options,
                )
            }
        )

        loader = DoclingLoader(
            file_path=pdf_url,
            converter=converter,
            chunker=chunker,
        )

        chunked_docs = loader.load()

        if chunked_docs:
            return chunked_docs
        else:
            logger.debug("No documents loaded from PDF")
            return []

    except Exception as e:
        logger.error(f"Error processing PDF with DoclingLoader: {e}")
        return []


def is_references_section(chunk_metadata):
    """Check if a chunk belongs to a references section based on headings."""
    reference_keywords = {
        "references",
        "bibliography",
        "works cited",
        "citations",
        "literature cited",
        "bibliographic references",
        # TODO: Should be extended for non-english papers
    }

    for heading in chunk_metadata.get("dl_meta", {}).get("headings", []):
        heading_text = "".join(
            c for c in str(heading).lower().strip() if c.isalpha() or c.isspace()
        )

        if heading_text in reference_keywords:
            return True

    return False


def process_hit(hit, vector_store, tokenizer):
    try:
        hit_source = hit["_source"]
        control_number = hit_source.get("control_number")
        publication_year = hit_source.get("publication_info", [{}])[0].get("year")
        categories = list(
            {
                cat
                for eprint in hit_source.get("arxiv_eprints", [])
                for cat in (eprint.get("categories") or [])
                if isinstance(cat, str)
            }
        )

        base_metadata = {
            "control_number": control_number,
            "publication_year": publication_year,
            "categories": categories,
        }

        # Try to get PDF URL from metadata.documents
        pdf_url = None
        metadata = hit_source.get("metadata", {})
        documents = metadata.get("documents", [])
        for doc in documents:
            if doc.get("source") == "arxiv" and doc.get("url"):
                pdf_url = doc.get("url")
                break

        # Get arXiv ID from arxiv_eprints as fallback
        arxiv_eprints = hit_source.get("arxiv_eprints", [])
        arxiv_id = None
        if arxiv_eprints:
            arxiv_id = arxiv_eprints[0].get("value")

        if pdf_url:
            logger.debug(f"Processing paper from INSPIRE: {pdf_url}")
        elif arxiv_id:
            pdf_url = f"https://browse-export.arxiv.org/pdf/{arxiv_id}"
            logger.debug(f"Processing paper from arXiv: {arxiv_id}")
        else:
            logger.error(
                f"Could not determine Inspire URL or arXiv ID for "
                f"control_number {control_number}"
            )
            return False

        chunked_docs = process_pdf(pdf_url, tokenizer)

        if chunked_docs:
            # Create final documents with full metadata
            langchain_documents = []
            chunks_skipped = 0
            chunks_processed = 0
            for i, doc in enumerate(chunked_docs):
                if is_references_section(doc.metadata):
                    chunks_skipped += 1
                    continue

                chunks_processed += 1

                # binary_hash is unnecessary and exceeds long type range
                if "dl_meta" in doc.metadata and "origin" in doc.metadata["dl_meta"]:
                    doc.metadata["dl_meta"]["origin"].pop("binary_hash", None)

                full_metadata = (
                    base_metadata
                    | doc.metadata
                    | {
                        "embedding_type": "docling-accphysbert",
                        "chunk_index": i,
                        "arxiv_id": arxiv_id,
                    }
                )

                langchain_documents.append(
                    Document(page_content=doc.page_content, metadata=full_metadata)
                )

            logger.debug(
                f"Processed {chunks_processed} chunks, skipped "
                f"{chunks_skipped} reference chunks"
            )

            # Add documents to vector store
            if langchain_documents:
                start_time = time.time()
                bulk_size = 500  # OpenSearch default
                num_docs = len(langchain_documents)
                if num_docs > bulk_size:
                    num_batches = math.ceil(num_docs / bulk_size)
                    logger.warning(
                        f"[{control_number}] Bulk size exceeded, splitting into ",
                        f"{num_batches} batches.",
                    )
                for i in range(0, num_docs, bulk_size):
                    batch = langchain_documents[i : i + bulk_size]
                    vector_store.add_documents(batch)
                elapsed = time.time() - start_time
                logger.debug(
                    f"Added {num_docs} documents to vector store "
                    f"in {elapsed:.2f} seconds."
                )
                return True
            else:
                logger.debug(f"No chunks created for {arxiv_id}")
                return False
        else:
            logger.error(f"Failed to process PDF with DoclingLoader for {arxiv_id}")
            return False

    except Exception as e:
        logger.error(f"[{control_number}] Error processing record: {e}")
        return False


def worker_process(
    worker_id,
    control_numbers,
    reprocess,
    indexed_control_numbers,
    os_query,
    tokenizer,
    debug,
):
    logger.remove()
    logger.add(
        lambda msg: tqdm.write(msg, end=""),
        format=f"[Worker {worker_id}] {{time}} | {{level}} | {{message}}",
        colorize=True,
        level="DEBUG" if debug else "INFO",
    )

    embeddings = VLLMOpenAIEmbeddings(
        model_name=getenv("EMBEDDING_MODEL"),
        openai_api_base=f"{getenv('API_BASE')}/v1",
        openai_api_key=getenv("KUBEFLOW_API_KEY"),
        default_headers=(
            {"Host": getenv("KUBEFLOW_EMBEDDING_HOST")}
            if getenv("KUBEFLOW_EMBEDDING_HOST")
            else {}
        ),
        timeout=60,
    )
    vector_store = get_vector_os_client(
        embeddings, index_name=getenv("VECTOR_DB_INDEX")
    )
    inspire_os_client = get_inspire_os_client()

    # Fetch documents with the control_numbers assigned to this worker
    query = {
        "bool": {
            "must": [
                os_query,
                {"terms": {"control_number": control_numbers}},
            ]
        }
    }

    hits = scan(
        client=inspire_os_client,
        query={"query": query},
        index=RECORDS_INDEX_NAME,
        size=100,
        scroll="10h",  # Needs to be high to avoid timeouts between batches
    )

    count = 0
    with tqdm(
        desc=f"[Worker {worker_id}]",
        unit="doc",
        total=len(control_numbers),
        position=worker_id,
    ) as pbar:
        for hit in hits:
            cn = hit["_source"].get("control_number") or hit["_source"].get(
                "metadata", {}
            ).get("control_number")
            if not reprocess and cn in indexed_control_numbers:
                pbar.update(1)
                continue

            try:
                logger.debug(f"[Worker {worker_id}] Processing {cn}")
                if process_hit(hit, vector_store, tokenizer):
                    count += 1
            except Exception as e:
                logger.error(f"[Worker {worker_id}] Error on {cn}: {e}")
            pbar.update(1)

    logger.success(f"[Worker {worker_id}] ✅ Finished — processed {count} new records.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--workers", type=int, default=4, help="Number of parallel workers"
    )
    parser.add_argument(
        "--reprocess", action="store_true", help="Reprocess all records"
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    parser.add_argument(
        "--inspire-category", type=str, help="INSPIRE category to filter"
    )
    parser.add_argument("--arxiv-category", type=str, help="arXiv category to filter")
    args = parser.parse_args()

    logger.remove()
    logger.add(
        lambda msg: tqdm.write(msg, end=""),
        colorize=True,
        level="DEBUG" if args.debug else "INFO",
    )

    embeddings = VLLMOpenAIEmbeddings(
        model_name=getenv("EMBEDDING_MODEL"),
        openai_api_base=f"{getenv('API_BASE')}/v1",
        openai_api_key=getenv("KUBEFLOW_API_KEY"),
        default_headers=(
            {"Host": getenv("KUBEFLOW_EMBEDDING_HOST")}
            if getenv("KUBEFLOW_EMBEDDING_HOST")
            else {}
        ),
        timeout=60,
    )

    inspire_os_client = get_inspire_os_client()
    vector_store = get_vector_os_client(
        embeddings, index_name=getenv("VECTOR_DB_INDEX")
    )

    os_query = get_os_query(
        full_text_available=True,
        inspire_category=args.inspire_category,
        arxiv_category=args.arxiv_category,
    )

    tokenizer = AutoTokenizer.from_pretrained(HF_EMBEDDING_MODEL_ID)

    logger.info("📊 Fetching all control numbers...")
    control_numbers = get_control_numbers(
        inspire_os_client, os_query, RECORDS_INDEX_NAME
    )
    total_records = len(control_numbers)
    logger.info(f"Found {total_records} control numbers.")

    if not args.reprocess:
        logger.info("🔎 Loading already embedded control numbers...")
        indexed_control_numbers = get_indexed_control_numbers(vector_store)
        logger.info(
            f"Found {len(indexed_control_numbers)}/{total_records} already embedded."
        )
    else:
        indexed_control_numbers = set()

    to_process_control_numbers = [
        cn for cn in control_numbers if cn not in indexed_control_numbers
    ]
    bins = [to_process_control_numbers[i :: args.workers] for i in range(args.workers)]
    processes = []
    for i, bin_control_numbers in enumerate(bins):
        p = multiprocessing.Process(
            target=worker_process,
            args=(
                i,
                bin_control_numbers,
                args.reprocess,
                indexed_control_numbers,
                os_query,
                tokenizer,
                args.debug,
            ),
        )
        p.start()
        processes.append(p)

    for p in processes:
        p.join()

    logger.success("🎉 All workers completed!")


if __name__ == "__main__":
    main()
