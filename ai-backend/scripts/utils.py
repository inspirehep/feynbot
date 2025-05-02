from os import getenv

from dotenv import load_dotenv
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_community.vectorstores import OpenSearchVectorSearch
from langchain_core.documents import Document
from opensearchpy import OpenSearch

load_dotenv()


def get_inspire_os_client():
    return OpenSearch(
        hosts=[
            {
                "host": getenv("INSPIRE_OPENSEARCH_HOST"),
                "port": 443,
                "http_auth": (
                    getenv("INSPIRE_OPENSEARCH_USERNAME"),
                    getenv("INSPIRE_OPENSEARCH_PASSWORD"),
                ),
                "use_ssl": True,
                "verify_certs": False,
                "ssl_show_warn": False,
                "url_prefix": "/os",
            }
        ],
    )


def get_vector_os_client(embedding_function, index_name="vector_demo_langchain"):
    return OpenSearchVectorSearch(
        index_name=index_name,
        embedding_function=embedding_function,
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


def get_os_query(arXiv_category, full_text_available=True):
    query = {
        "bool": {"must": [{"term": {"arxiv_eprints.categories": f"{arXiv_category}"}}]}
    }
    if full_text_available:
        query["bool"]["must"].append({"term": {"documents.source": "arxiv"}})
    return query


def get_record_metadata(hit):
    hit = hit["_source"]
    control_number = hit["control_number"]
    title = hit.get("titles", [{}])[0].get("title", "")
    abstract = hit.get("abstracts", [{}])[0].get("value", "")
    publication_year = hit.get("publication_info", [{}])[0].get("year")
    categories = list(
        {
            cat
            for eprint in hit.get("arxiv_eprints", [])
            for cat in (eprint.get("categories") or [])
            if isinstance(cat, str)
        }
    )
    documents = hit.get("documents", [])
    return control_number, title, abstract, publication_year, categories, documents


def get_record_documents(hit, title_abstract_only=False, text_splitter=None):
    langchain_documents = []
    control_number, title, abstract, publication_year, categories, documents = (
        get_record_metadata(hit)
    )
    metadata = {
        "control_number": control_number,
        "publication_year": publication_year,
        "categories": categories,
    }
    if title_abstract_only:
        text = title + " <ENDTITLE> " + abstract
        langchain_documents.append(
            Document(
                page_content=text,
                metadata=metadata | {"embedding_type": "title_abstract"},
            )
        )
    else:
        langchain_documents.append(
            Document(
                page_content=title,
                metadata=metadata | {"embedding_type": "title"},
            )
        )
        langchain_documents.append(
            Document(
                page_content=abstract,
                metadata=metadata | {"embedding_type": "abstract"},
            )
        )
        for document in documents:
            if document.get("source") == "arxiv":
                pdf_url = document["url"]
                doc_pages = PyMuPDFLoader(
                    pdf_url,
                    mode="single",
                ).load()
                doc_pages[0].metadata = metadata | {"embedding_type": "fulltext"}
                doc_fragments = text_splitter.split_documents(doc_pages)
                langchain_documents.extend(doc_fragments)
    return langchain_documents


def process_hit(index, hit, vector_store, title_abstract_only, text_splitter):
    try:
        langchain_documents = get_record_documents(
            hit, title_abstract_only=title_abstract_only, text_splitter=text_splitter
        )
        vector_store.add_documents(langchain_documents)
        print(f"[{index}] Successfully processed.")
        return True
    except Exception as e:
        print(f"[{index}] Error processing record: {e}")
        return False


def delete_control_number_from_index(vector_store, control_number):
    try:
        result = vector_store.client.search(
            body={
                "query": {"term": {"metadata.control_number": control_number}},
                "size": 1000,
            },
        )
        ids = [hit["_id"] for hit in result["hits"]["hits"]]
        if not ids:
            print(f"No records found with control number {control_number}.")
            return
        print(
            f"Found {len(ids)} records with control number {control_number}. Deleting.."
        )
        vector_store.delete(ids=ids)
        print(f"Deleted {len(ids)} records with control number {control_number}.")
    except Exception as e:
        print(f"Error deleting documents with control number {control_number}: {e}")
