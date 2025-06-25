import logging
import re
import time
from os import getenv

from backend.src.rag_pipeline.schemas import Citation, QueryResponse
from backend.src.rag_pipeline.utils import format_docs
from backend.src.utils.embeddings import VLLMOpenAIEmbeddings
from backend.src.utils.reranker import CustomJinaRerank
from langchain.prompts import PromptTemplate
from langchain_community.llms import VLLMOpenAI
from langchain_community.vectorstores import OpenSearchVectorSearch

logger = logging.getLogger("uvicorn")

embedding_class = VLLMOpenAIEmbeddings(
    model_name=getenv("EMBEDDING_MODEL"),
    openai_api_base=f"{getenv('API_BASE')}/v1",
    openai_api_key=getenv("KUBEFLOW_API_KEY"),
    default_headers=(
        {"Host": getenv("KUBEFLOW_EMBEDDING_HOST")}
        if getenv("KUBEFLOW_EMBEDDING_HOST")
        else {}
    ),
    timeout=15,
)

llm_class = VLLMOpenAI(
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

reranker_class = CustomJinaRerank(
    model_name=getenv("RERANKING_MODEL"),
    openai_api_base=f"{getenv('API_BASE')}/v1",
    openai_api_key=getenv("KUBEFLOW_API_KEY"),
    default_headers=(
        {"Host": getenv("KUBEFLOW_RERANKING_HOST")}
        if getenv("KUBEFLOW_RERANKING_HOST")
        else {}
    ),
    top_n=10,
    timeout=40,
)

vector_store = OpenSearchVectorSearch(
    index_name=getenv("VECTOR_DB_INDEX"),
    embedding_function=embedding_class,
    opensearch_url=getenv("VECTOR_DB_HOST"),
    http_auth=(
        getenv("VECTOR_DB_USERNAME"),
        getenv("VECTOR_DB_PASSWORD"),
    ),
    use_ssl=True,
    verify_certs=False,
    ssl_show_warn=False,
    url_prefix="/os",
    timeout=30,
)

prompt = PromptTemplate.from_template("""
     You are an expert research assistant on InspireHEP for High Energy Physics.
     Use the numbered context documents to answer the user question.
     Respond in two parts:\n\n
     1. **Brief Answer:** A short and direct answer to the question (3-5 sentences).\n
     2. **Detailed Explanation:** A longer explanation that includes references to the
     numbered context documents using square brackets like [1], [2], etc.\n\n
     Only use information from the context.
     If the answer is not in the context, say you don't know.

     Question: {question}\n\n
     Context:\n{context}
     Answer:
     """)


def search_rag(search_query: str, model: str):
    start_embedding = time.time()
    query_embedding = embedding_class.embed_query(search_query)
    end_embedding = time.time()
    logger.info("[search_rag] Embedding time: %.2fs", end_embedding - start_embedding)

    start_retireval = time.time()
    docs = vector_store.similarity_search_by_vector(
        embedding=query_embedding,
        k=25,
        # filter=search_filter,
    )
    end_retireval = time.time()
    logger.info("[search_rag] Retrieval time: %.2fs", end_retireval - start_retireval)

    start_reranking = time.time()
    ranked_docs = reranker_class.compress_documents(
        documents=docs,
        query=search_query,
    )
    end_reranking = time.time()
    logger.info("[search_rag] Reranking time: %.2fs", end_reranking - start_reranking)

    context = format_docs(ranked_docs)
    formatted_prompt = prompt.invoke({"question": search_query, "context": context})
    start_llm = time.time()
    response = llm_class.invoke(formatted_prompt)
    end_llm = time.time()
    logger.info("[search_rag] LLM time: %.2fs", end_llm - start_llm)
    logger.info("[search_rag] Total time: %.2fs", end_llm - start_retireval)
    full_answer = response.strip()

    brief_match = re.search(
        r"Brief Answer:\s*(.+?)(?:\n\n|Detailed Explanation:|$)",
        full_answer,
        re.DOTALL | re.IGNORECASE,
    )
    brief_answer = brief_match.group(1).strip() if brief_match else "N/A"
    long_match = re.search(
        r"Detailed Explanation:\s*(.+)", full_answer, re.DOTALL | re.IGNORECASE
    )
    long_answer = long_match.group(1).strip() if long_match else "N/A"

    citations = [
        Citation(
            doc_id=i + 1,
            control_number=doc.metadata.get("control_number"),
            snippet=doc.page_content,
        )
        for i, doc in enumerate(ranked_docs)
    ]
    return QueryResponse(
        brief_answer=brief_answer, long_answer=long_answer, citations=citations
    )
