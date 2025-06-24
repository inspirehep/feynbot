import time
from os import getenv

from backend.src.ir_pipeline.utils.embeddings import VLLMOpenAIEmbeddings
from backend.src.ir_pipeline.utils.reranker import CustomJinaRerank
from dotenv import load_dotenv
from langchain_community.llms import VLLMOpenAI
from langchain_community.vectorstores import OpenSearchVectorSearch
from langchain_core.prompts import PromptTemplate

load_dotenv()


def pretty_print_docs(docs):
    print(
        f"\n{'-' * 100}\n".join(
            [
                f"Document {i + 1}:\n\n"
                + str(d.metadata["control_number"])
                + " "
                + str(d.page_content)
                for i, d in enumerate(docs)
            ]
        )
    )


def pretty_print_sources(docs):
    print(
        "\n".join(
            [
                f"Document {i + 1}: "
                + "https://inspirehep.net/literature/"
                + str(d.metadata["control_number"])
                for i, d in enumerate(docs)
            ]
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
    timeout=10,
)

reranker = CustomJinaRerank(
    model_name=getenv("RERANKING_MODEL"),
    openai_api_base=f"{getenv('API_BASE')}/v1",
    openai_api_key=getenv("KUBEFLOW_API_KEY"),
    default_headers=(
        {"Host": getenv("KUBEFLOW_RERANKING_HOST")}
        if getenv("KUBEFLOW_RERANKING_HOST")
        else {}
    ),
    top_n=15,
    timeout=40,
)

llm = VLLMOpenAI(
    model_name=getenv("LLM_MODEL"),
    openai_api_base=f"{getenv('API_BASE')}/v1",
    default_headers=(
        {"Host": getenv("KUBEFLOW_LLM_HOST")} if getenv("KUBEFLOW_LLM_HOST") else {}
    ),
    openai_api_key=getenv("KUBEFLOW_API_KEY"),
    temperature=0,
    top_p=1,
    timeout=20,
)

vector_store = OpenSearchVectorSearch(
    index_name="embeddings_nucl-ex",
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
                {"term": {"metadata.embedding_type": "fulltext"}},
                {"term": {"metadata.embedding_type": "abstract"}},
            ],
            "minimum_should_match": 1,
        }
    }
]

search_query = """
Whats being discussed in the Collider constraints?
"""

prompt = PromptTemplate.from_template("""
    You are an assistant for question-answering tasks in High Enegery Physics.
    Only use the information provided in the context to answer the question.
    Do not make up any information or provide any personal opinions.
    If you do not know the answer, dont hesitate to say "I don't know".
    Question: {question}
    Context: {context}
    Answer:
    """)

start_retireval = time.time()
docs = vector_store.similarity_search(
    query=search_query,
    k=25,
    # filter=search_filter,
)
end_retireval = time.time()

start_reranking = time.time()
reranked_docs = reranker.compress_documents(
    documents=docs,
    query=search_query,
)
end_reranking = time.time()

message = prompt.invoke({"question": search_query, "context": reranked_docs})

start_llm = time.time()
response = llm.invoke(message)
end_llm = time.time()

print(response)


print("The response is based on the following documents:")
pretty_print_sources(reranked_docs)


print("Retrieval time: ", end_retireval - start_retireval)
print("Reranking time: ", end_reranking - start_reranking)
print("LLM time: ", end_llm - start_llm)
print("Total time: ", end_llm - start_retireval)
