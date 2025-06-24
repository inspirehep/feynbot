import multiprocessing
from os import getenv

from opensearchpy.helpers import scan
from tqdm import tqdm

VECTOR_INDEX_NAME = "embeddings_bge-m3"
RECORDS_INDEX_NAME = "records-hep"


def get_control_number_range(es_client, os_query, index):
    """Get the min and max control_number in the index for filtered query."""
    aggs_query = {
        "size": 0,
        "query": os_query,
        "aggs": {
            "min_cn": {"min": {"field": "control_number"}},
            "max_cn": {"max": {"field": "control_number"}},
        },
    }
    result = es_client.search(index=index, body=aggs_query)
    min_cn = int(result["aggregations"]["min_cn"]["value"])
    max_cn = int(result["aggregations"]["max_cn"]["value"])
    return min_cn, max_cn


def worker_process(
    worker_id, cn_start, cn_end, reprocess, indexed_control_numbers, os_query
):
    from backend.src.ir_pipeline.utils.embeddings import VLLMOpenAIEmbeddings
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    from utils import (
        get_inspire_os_client,
        get_vector_os_client,
        process_hit,
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
    vector_store = get_vector_os_client(embeddings, index_name=VECTOR_INDEX_NAME)
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=512, chunk_overlap=50)
    inspire_os_client = get_inspire_os_client()

    query = {
        "bool": {
            "must": [
                os_query,
                {"range": {"control_number": {"gte": cn_start, "lt": cn_end}}},
            ]
        }
    }
    already_indexed_in_range = {
        cn for cn in indexed_control_numbers if cn_start <= int(cn) < cn_end
    }

    total_hits = inspire_os_client.count(
        index=RECORDS_INDEX_NAME, body={"query": query}
    )["count"]

    remaining_to_process = total_hits - len(already_indexed_in_range)

    hits = scan(
        client=inspire_os_client,
        query={"query": query},
        index=RECORDS_INDEX_NAME,
        size=100,
        scroll="10m",
    )

    count = 0
    with tqdm(
        desc=f"[Worker {worker_id}] cn:{cn_start}-{cn_end}",
        unit="docs",
        total=remaining_to_process,
    ) as pbar:
        for hit in hits:
            cn = hit["_source"].get("control_number") or hit["_source"].get(
                "metadata", {}
            ).get("control_number")
            if not reprocess and cn in indexed_control_numbers:
                pbar.update(1)
                continue

            try:
                print(f"[Worker {worker_id}] Processing {cn}...")
                if process_hit(count, hit, vector_store, False, text_splitter):
                    count += 1
            except Exception as e:
                print(f"[Worker {worker_id}] Error on {cn}: {e}")
            pbar.update(1)

    print(f"[Worker {worker_id}] ✅ Finished — processed {count} new records.")


def main():
    import argparse

    from backend.src.ir_pipeline.utils.embeddings import VLLMOpenAIEmbeddings
    from utils import (
        get_indexed_control_numbers,
        get_inspire_os_client,
        get_os_query,
        get_vector_os_client,
    )

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--workers", type=int, default=4, help="Number of parallel workers"
    )
    parser.add_argument(
        "--reprocess", action="store_true", help="Reprocess all records"
    )
    args = parser.parse_args()

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
    vector_store = get_vector_os_client(embeddings, index_name=VECTOR_INDEX_NAME)
    os_query = get_os_query(full_text_available=True)

    print("📊 Fetching control number range...")
    min_cn, max_cn = get_control_number_range(
        inspire_os_client, os_query, RECORDS_INDEX_NAME
    )
    print(f"Control number range: {min_cn} - {max_cn}")

    total_records = inspire_os_client.count(
        index=RECORDS_INDEX_NAME, body={"query": os_query}
    )["count"]

    if not args.reprocess:
        print("🔎 Loading already embedded control numbers...")
        indexed_control_numbers = get_indexed_control_numbers(vector_store)
        print(f"Found {len(indexed_control_numbers)}/{total_records} already embedded.")
    else:
        indexed_control_numbers = set()

    range_size = (max_cn - min_cn + 1) // args.workers
    processes = []
    for i in range(args.workers):
        cn_start = min_cn + i * range_size
        cn_end = min_cn + (i + 1) * range_size if i < args.workers - 1 else max_cn + 1
        p = multiprocessing.Process(
            target=worker_process,
            args=(
                i,
                cn_start,
                cn_end,
                args.reprocess,
                indexed_control_numbers,
                os_query,
            ),
        )
        p.start()
        processes.append(p)

    for p in processes:
        p.join()

    print("🎉 All workers completed.")


if __name__ == "__main__":
    main()
