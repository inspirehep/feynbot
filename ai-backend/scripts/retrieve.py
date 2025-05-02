from os import getenv

from dotenv import load_dotenv
from langchain_community.vectorstores import OpenSearchVectorSearch
from langchain_ollama import OllamaEmbeddings

load_dotenv()

embeddings = OllamaEmbeddings(model="nomic-embed-text")
vector_store = OpenSearchVectorSearch(
    index_name="vector_demo_langchain",
    embedding_function=embeddings,
    opensearch_url=getenv("VECTOR_DB_HOST"),
    http_auth=(
        getenv("VECTOR_DB_USERNAME"),
        getenv("VECTOR_DB_PASSWORD"),
    ),
    use_ssl=True,
    verify_certs=False,
    ssl_show_warn=False,
    url_prefix="/os",
)

search_filter = [
    {
        "bool": {
            "should": [
                {"term": {"metadata.embedding_type": "title"}},
                {"term": {"metadata.embedding_type": "abstract"}},
            ],
            "minimum_should_match": 1,
        }
    }
]
docs = vector_store.similarity_search_with_score(
    "What is a star?", k=100, filter=search_filter
)
for doc, score in docs:
    print(f"Score: {score}")
    print(f"Metadata: {doc.metadata}")
    print("\n")
print(len(docs))
