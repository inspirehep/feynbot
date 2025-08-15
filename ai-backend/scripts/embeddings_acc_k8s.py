import logging
import math
import multiprocessing
import os
import sys
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
from transformers import AutoTokenizer
from utils import (
    get_indexed_control_numbers,
    get_inspire_os_client,
    get_os_query,
    get_vector_os_client,
)

RECORDS_INDEX_NAME = os.getenv("RECORDS_INDEX_NAME")
HF_EMBEDDING_MODEL_ID = os.getenv("HF_EMBEDDING_MODEL_ID")
# Model supports 512 but docling seems to be off by 1 in a few cases, set to 510
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE"))


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
            logger.info(f"Fetched {i} control numbers")
    return sorted(control_numbers)


def get_control_number_batch(all_control_numbers, batch_index, total_batches):
    batch_size = math.ceil(len(all_control_numbers) / total_batches)
    start_idx = batch_index * batch_size
    end_idx = min((batch_index + 1) * batch_size, len(all_control_numbers))
    return all_control_numbers[start_idx:end_idx]


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
                        f"[{control_number}] Bulk size exceeded, splitting into "
                        f"{num_batches} batches."
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
    job_completion_index,
    control_numbers,
    reprocess,
    indexed_control_numbers,
    os_query,
    tokenizer,
    debug,
):
    logger.remove()
    logger.add(
        sys.stdout,
        format=(
            f"[Job {job_completion_index} - Worker {worker_id}] "
            f"{{time:MM-DD HH:mm:ss}} | {{level}} | {{message}}"
        ),
        colorize=True,
        level="DEBUG" if debug else "INFO",
    )

    logger.info(
        f"Worker {worker_id} starting with {len(control_numbers)} control numbers"
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

    succesful = 0
    processed = 0
    processing_times = []
    total_to_process = len(control_numbers)

    for hit in hits:
        doc_start_time = time.time()

        cn = hit["_source"].get("control_number") or hit["_source"].get(
            "metadata", {}
        ).get("control_number")

        processed += 1

        if not reprocess and cn in indexed_control_numbers:
            continue

        try:
            logger.debug(f"Processing {cn}")
            if process_hit(hit, vector_store, tokenizer):
                succesful += 1
        except Exception as e:
            logger.error(f"Error on {cn}: {e}")

        doc_time = time.time() - doc_start_time
        processing_times.append(doc_time)
        avg_time = (
            sum(processing_times) / len(processing_times) if processing_times else 0
        )

        if processed % 5 == 0 or processed == total_to_process:
            progress_pct = (processed / total_to_process) * 100
            logger.info(
                f"Progress: {processed}/{total_to_process} "
                f"({progress_pct:.1f}%) - {succesful} successful - "
                f"Avg: {avg_time:.2f}s/doc"
            )

    logger.success(
        f"Worker {worker_id} finished — successfully embedded "
        f"{succesful} documents out of {processed} "
        f"examined. Total time: {sum(processing_times):.1f}s, Avg: {avg_time:.2f}s/doc"
    )
    return succesful


def main():
    reprocess = os.getenv("REPROCESS", "false").lower() == "true"
    debug = os.getenv("DEBUG", "false").lower() == "true"
    inspire_category = os.getenv("INSPIRE_CATEGORY")
    arxiv_category = os.getenv("ARXIV_CATEGORY")

    job_completion_index = int(os.getenv("JOB_COMPLETION_INDEX", "0"))
    total_jobs = int(os.getenv("TOTAL_JOBS", "1"))
    workers_per_job = int(os.getenv("WORKERS_PER_JOB", "1"))

    logger.remove()
    logger.add(
        sys.stdout,
        format=(
            f"[Job {job_completion_index}] "
            f"{{time:MM-DD HH:mm:ss}} | {{level}} | {{message}}"
        ),
        colorize=True,
        level="DEBUG" if debug else "INFO",
    )

    logger.info(
        (
            f"Starting job {job_completion_index} of {total_jobs} "
            f"with {workers_per_job} workers"
        )
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
        inspire_category=inspire_category,
        arxiv_category=arxiv_category,
    )

    tokenizer = AutoTokenizer.from_pretrained(HF_EMBEDDING_MODEL_ID)

    logger.info("📊 Fetching all control numbers...")
    all_control_numbers = get_control_numbers(
        inspire_os_client, os_query, RECORDS_INDEX_NAME
    )
    logger.info(f"Found {len(all_control_numbers)} control numbers total.")

    if not reprocess:
        logger.info("🔎 Loading already embedded control numbers...")
        indexed_control_numbers = set(get_indexed_control_numbers(vector_store))
        logger.info(f"Found {len(indexed_control_numbers)} already embedded globally.")

        all_unprocessed_control_numbers = [
            cn for cn in all_control_numbers if cn not in indexed_control_numbers
        ]
        already_embedded_count = len(all_control_numbers) - len(
            all_unprocessed_control_numbers
        )
        logger.info(
            f"After filtering: {len(all_unprocessed_control_numbers)} control numbers "
            f"need processing ({already_embedded_count} already embedded)"
        )
    else:
        indexed_control_numbers = set()
        all_unprocessed_control_numbers = all_control_numbers
        logger.info("Reprocess mode: will process all control numbers")

    control_numbers = get_control_number_batch(
        all_unprocessed_control_numbers, job_completion_index, total_jobs
    )

    logger.info(
        f"Job {job_completion_index} assigned {len(control_numbers)} control numbers "
        f"to process"
    )

    if not control_numbers:
        logger.success("No control numbers assigned to this job. Exiting.")
        return

    worker_bins = [control_numbers[i::workers_per_job] for i in range(workers_per_job)]

    worker_bins = [bin_cns for bin_cns in worker_bins if bin_cns]
    actual_workers = len(worker_bins)

    logger.info(f"Starting {actual_workers} workers for this job")
    for i, bin_cns in enumerate(worker_bins):
        logger.info(f"Worker {i}: {len(bin_cns)} control numbers")

    # Start worker processes
    processes = []
    for worker_id, worker_control_numbers in enumerate(worker_bins):
        p = multiprocessing.Process(
            target=worker_process,
            args=(
                worker_id,
                job_completion_index,
                worker_control_numbers,
                reprocess,
                indexed_control_numbers,
                os_query,
                tokenizer,
                debug,
            ),
        )
        p.start()
        processes.append(p)

    successful_workers = 0
    finished_processes = set()
    worker_retry_count = {i: 0 for i in range(actual_workers)}
    max_retries = int(os.getenv("MAX_WORKER_RETRIES", "5"))

    logger.debug(
        f"Monitoring {actual_workers} workers (max {max_retries} retries per worker)..."
    )

    while len(finished_processes) < actual_workers:
        for i, p in enumerate(processes):
            if i not in finished_processes and not p.is_alive():
                p.join()
                exit_code = p.exitcode

                if exit_code == 0:
                    successful_workers += 1
                    finished_processes.add(i)
                    logger.info(f"Worker {i} completed successfully")
                else:
                    logger.error(f"Worker {i} failed with exit code: {exit_code}")

                    # Check if we should retry the worker
                    if worker_retry_count[i] < max_retries:
                        worker_retry_count[i] += 1
                        logger.info(
                            f"Restarting worker {i} "
                            f"(attempt {worker_retry_count[i]}/{max_retries})"
                        )

                        logger.debug(
                            f"Checking for newly embedded documents "
                            f"before restarting worker {i}..."
                        )
                        fresh_indexed_control_numbers = set(
                            get_indexed_control_numbers(vector_store)
                        )

                        remaining_control_numbers = [
                            cn
                            for cn in worker_bins[i]
                            if cn not in fresh_indexed_control_numbers
                        ]

                        if remaining_control_numbers:
                            original_count = len(worker_bins[i])
                            remaining_count = len(remaining_control_numbers)
                            filtered_count = original_count - remaining_count
                            logger.info(
                                f"Worker {i} restart: {remaining_count} items "
                                f"remaining (filtered {filtered_count} processed)"
                            )

                            new_process = multiprocessing.Process(
                                target=worker_process,
                                args=(
                                    i,
                                    job_completion_index,
                                    remaining_control_numbers,
                                    reprocess,
                                    fresh_indexed_control_numbers,
                                    os_query,
                                    tokenizer,
                                    debug,
                                ),
                            )
                            new_process.start()
                            processes[i] = new_process
                        else:
                            logger.info(
                                f"Worker {i} restart: all items already processed, "
                                f"marking as complete"
                            )
                            finished_processes.add(i)
                            successful_workers += 1
                    else:
                        logger.error(
                            f"Worker {i} exceeded max retries ({max_retries}), "
                            f"marking as failed"
                        )
                        finished_processes.add(i)

        if len(finished_processes) < actual_workers:
            time.sleep(1)

    failed_workers = actual_workers - successful_workers

    if failed_workers > 0:
        logger.warning(
            f"⚠️ Job {job_completion_index} completed with {successful_workers}"
            f"/{actual_workers} successful workers"
        )
    else:
        logger.success(
            f"🎉 Job {job_completion_index} completed successfully "
            f"with {successful_workers} workers!"
        )


if __name__ == "__main__":
    main()
