import logging
import re
import time
from os import getenv

from backend.src.rag_pipeline.schemas import Citation, QueryResponse
from backend.src.rag_pipeline.utils import format_docs
from backend.src.utils.embeddings import VLLMOpenAIEmbeddings
from backend.src.utils.langfuse import get_prompt
from backend.src.utils.reranker import CustomJinaRerank
from langchain_community.llms import VLLMOpenAI
from langchain_community.vectorstores import OpenSearchVectorSearch
from langchain_core.output_parsers import JsonOutputParser

logger = logging.getLogger(__name__)

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
output_parser = JsonOutputParser(pydantic_object=QueryResponse)
prompt_template, _ = get_prompt("rag-query")

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


def search_rag(search_query: str, model: str):
    start_embedding = time.time()
    query_embedding = embedding_class.embed_query(search_query)
    end_embedding = time.time()
    logger.info("[search_rag] Embedding time: %.2fs", end_embedding - start_embedding)

    start_retrieval = time.time()
    docs = vector_store.similarity_search_by_vector(
        embedding=query_embedding,
        k=25,
    )
    end_retrieval = time.time()
    logger.info("[search_rag] Retrieval time: %.2fs", end_retrieval - start_retrieval)

    start_reranking = time.time()
    ranked_docs = reranker_class.compress_documents(
        documents=docs,
        query=search_query,
    )
    end_reranking = time.time()
    logger.info("[search_rag] Reranking time: %.2fs", end_reranking - start_reranking)

    context = format_docs(ranked_docs)

    prompt_template.input_variables = ["question", "context"]
    chain = prompt_template | llm_class | output_parser
    start_llm = time.time()
    response = chain.invoke({"question": search_query, "context": context})
    end_llm = time.time()
    brief_answer = response["brief"]
    long_answer = response["response"]

    logger.info("[search_rag] LLM time: %.2fs", end_llm - start_llm)

    cited_indices = set(
        int(match) for match in re.findall(r"\[(\d+)\]", brief_answer + long_answer)
    )

    filtered_docs = [
        (i + 1, doc) for i, doc in enumerate(ranked_docs) if (i + 1) in cited_indices
    ]

    old_to_new_idx = {
        old_idx: new_idx + 1 for new_idx, (old_idx, _) in enumerate(filtered_docs)
    }

    def replace_citation(match):
        old_idx = int(match.group(1))
        if old_idx in old_to_new_idx:
            return f"[{old_to_new_idx[old_idx]}]"
        else:
            return match.group(0)

    def replace_all_citations(text):
        return re.sub(r"\[(\d+)\]", replace_citation, text)

    brief_answer = replace_all_citations(brief_answer.strip())

    long_answer = replace_all_citations(long_answer.strip())

    citations = [
        Citation(
            doc_id=new_idx + 1,
            control_number=doc.metadata.get("control_number"),
            snippet=doc.page_content,
        )
        for new_idx, (_, doc) in enumerate(filtered_docs)
    ]

    return QueryResponse(
        brief_answer=brief_answer, long_answer=long_answer, citations=citations
    )
