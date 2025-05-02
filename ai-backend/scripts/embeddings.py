from langchain_ollama import OllamaEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from opensearchpy.helpers import scan
from utils import (
    get_inspire_os_client,
    get_os_query,
    get_vector_os_client,
    process_hit,
)

embeddings = OllamaEmbeddings(model="nomic-embed-text")
text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)


inspire_os_client = get_inspire_os_client()
vector_store = get_vector_os_client(embeddings, index_name="embeddings_nucl-ex")


os_query = get_os_query(arXiv_category="nucl-ex", full_text_available=True)

record_count = inspire_os_client.search(
    body={"query": os_query, "size": 0, "track_total_hits": True}, index="records-hep"
)["hits"]["total"]["value"]
print(f"Found {record_count} records")

results = scan(
    inspire_os_client,
    query={"query": os_query},
    index="records-hep",
    size=1000,
    scroll="2m",
)

count = 0
for idx, hit in enumerate(results):
    try:
        if process_hit(idx, hit, vector_store, True, text_splitter):
            count += 1
    except Exception as e:
        print(f"[{idx}] Unexpected error: {e}")
print(f"Processed {count}/{record_count} records.")

# with ThreadPoolExecutor(max_workers=None) as executor:
#     futures = {
#         executor.submit(process_hit, idx, hit, vector_store, True, text_splitter): idx
#         for idx, hit in enumerate(results)
#     }

#     for future in as_completed(futures):
#         idx = futures[future]
#         try:
#             if future.result():
#                 count += 1
#         except Exception as e:
#             print(f"[{idx}] Unexpected error: {e}")

# print(f"Finished processing. Successfully processed {count}/{record_count} records.")
