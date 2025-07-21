import uuid
from os import getenv

from backend.src.ir_pipeline.chains import (
    create_answer_generation_chain,
    create_query_expansion_chain,
    create_rag_answer_generation_chain,
    create_rag_paper_answer_generation_chain,
)
from backend.src.ir_pipeline.schema import LLMPaperResponse, LLMResponse, Terms
from backend.src.ir_pipeline.tools.inspire import (
    InspireOSFullTextSearchTool,
    InspireSearchTool,
)
from backend.src.ir_pipeline.utils.inspire_formatter import (
    clean_refs,
    clean_refs_with_snippets,
    extract_context,
    format_docs,
    format_refs,
)
from backend.src.ir_pipeline.utils.utils import timer
from backend.src.schemas.query import QueryPaperResponse, QueryResponse
from backend.src.utils.embeddings import VLLMOpenAIEmbeddings
from backend.src.utils.reranker import CustomJinaRerank
from langchain.schema import Document
from langchain_community.llms import VLLMOpenAI
from langchain_community.vectorstores import OpenSearchVectorSearch
from langfuse.callback import CallbackHandler

LANGFUSE_HANDLER = CallbackHandler(
    public_key=getenv("LANGFUSE_PUBLIC_KEY"),
    secret_key=getenv("LANGFUSE_SECRET_KEY"),
    host=getenv("LANGFUSE_HOST"),
    release=getenv("BACKEND_VERSION"),
)

CHAIN_CACHE = {}
RESOURCE_CACHE = {}


def create_langfuse_config(user: str = None):
    return {
        "callbacks": [LANGFUSE_HANDLER],
        "metadata": {
            "langfuse_session_id": str(uuid.uuid4()),
            **({"langfuse_user_id": user} if user else {}),
        },
        "run_id": str(uuid.uuid4()),  # Manual trace ID for feedback
    }


def initialize_rag_resources():
    global RESOURCE_CACHE

    if "embedding_model" not in RESOURCE_CACHE:
        RESOURCE_CACHE["embedding_model"] = VLLMOpenAIEmbeddings(
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

    if "vector_store" not in RESOURCE_CACHE:
        RESOURCE_CACHE["vector_store"] = OpenSearchVectorSearch(
            index_name=getenv("VECTOR_DB_INDEX"),
            embedding_function=RESOURCE_CACHE["embedding_model"],
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

    if "reranker" not in RESOURCE_CACHE:
        RESOURCE_CACHE["reranker"] = CustomJinaRerank(
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


def initialize_chains(model):
    global CHAIN_CACHE

    if model in CHAIN_CACHE:
        return

    llm = VLLMOpenAI(
        model_name=model,
        openai_api_base=f"{getenv('API_BASE')}/v1",
        default_headers=(
            {"Host": getenv("KUBEFLOW_LLM_HOST")} if getenv("KUBEFLOW_LLM_HOST") else {}
        ),
        openai_api_key=getenv("KUBEFLOW_API_KEY"),
        temperature=0,
        top_p=1,
        timeout=20,
    )

    CHAIN_CACHE[model] = {
        "expand_chain": create_query_expansion_chain(llm=llm),
        "answer_chain": create_answer_generation_chain(
            llm=llm, prompt_name="generate-answer"
        ),
        "answer_chain_playground": create_answer_generation_chain(
            llm=llm, prompt_name="generate-answer-playground"
        ),
        "answer_chain_rag": create_rag_answer_generation_chain(llm=llm),
        "answer_chain_rag_paper": create_rag_paper_answer_generation_chain(llm=llm),
    }


async def search_common(
    query: str,
    model: str,
    user: str = None,
    use_highlights: bool = False,
    is_playground: bool = False,
):
    """Search INSPIRE HEP database with query expansion and answer generation"""
    if model not in CHAIN_CACHE:
        initialize_chains(model)

    if use_highlights:
        inspire_search_tool = InspireOSFullTextSearchTool()
    else:
        inspire_search_tool = InspireSearchTool()

    config = create_langfuse_config(user)

    expand_chain = CHAIN_CACHE[model]["expand_chain"]
    answer_chain = (
        CHAIN_CACHE[model]["answer_chain_playground"]
        if is_playground
        else CHAIN_CACHE[model]["answer_chain"]
    )

    expanded_query: Terms = await expand_chain.ainvoke({"query": query}, config=config)
    raw_results = inspire_search_tool.run(expanded_query)

    context = extract_context(raw_results, use_highlights=use_highlights)

    answer: LLMResponse = await answer_chain.ainvoke(
        {"query": query, "context": context}, config=config
    )

    return answer, raw_results, expanded_query


async def search(query, model, user, use_highlights=False):
    answer, raw_results, expanded_query = await search_common(
        query, model, user, use_highlights=use_highlights
    )

    clean_response, references = clean_refs(
        answer.response, raw_results, use_highlights=use_highlights
    )

    return {
        "brief": answer.brief,
        "response": clean_response,
        "references": references,
        "expanded_query": " OR ".join(
            [f'ft "{term}"' for term in expanded_query.terms]
        ),
    }


async def search_playground(query, model):
    answer, raw_results, _ = await search_common(
        query, model, use_highlights=True, is_playground=True
    )

    clean_response, citations = clean_refs_with_snippets(answer.response, raw_results)

    return {
        "brief": answer.brief,
        "response": clean_response,
        "citations": citations,
    }


async def _rag_common(
    query: str, model: str, user: str = None, control_number: int = None
):
    initialize_rag_resources()
    initialize_chains(model)

    embedding_model = RESOURCE_CACHE["embedding_model"]
    vector_store = RESOURCE_CACHE["vector_store"]
    reranker = RESOURCE_CACHE["reranker"]

    config = create_langfuse_config(user)

    with timer("RAG Embedding"):
        query_embedding = embedding_model.embed_query(query)

    with timer("RAG Retrieval"):
        if control_number:
            os_client = vector_store.client
            index_name = vector_store.index_name

            # We need a direct OpenSearch query as LangChain methods don't support
            # filtering with empty queries
            search_body = {
                "query": {"term": {"metadata.control_number": control_number}},
                "size": 25,
                "_source": ["text", "metadata"],
            }

            try:
                response = os_client.search(index=index_name, body=search_body)

                docs = [
                    Document(
                        page_content=hit["_source"]["text"],
                        metadata=hit["_source"]["metadata"],
                    )
                    for hit in response["hits"]["hits"]
                ]

            except Exception as e:
                print(f"OpenSearch query failed: {e}")
                docs = []
        else:
            docs = vector_store.similarity_search_by_vector(
                embedding=query_embedding,
                k=25,
            )

    with timer("RAG Reranking"):
        ranked_docs = reranker.compress_documents(
            documents=docs,
            query=query,
        )

    context = format_docs(ranked_docs)

    return ranked_docs, context, config


async def search_rag(query: str, model: str, user: str = None):
    ranked_docs, context, config = await _rag_common(query, model, user)

    answer_chain = CHAIN_CACHE[model]["answer_chain_rag"]

    with timer("RAG LLM"):
        response: LLMResponse = await answer_chain.ainvoke(
            {"question": query, "context": context}, config=config
        )

    formatted_response, citations = format_refs(response.response, ranked_docs)

    return QueryResponse(
        brief_answer=response.brief,
        long_answer=formatted_response,
        citations=citations,
        trace_id=config.get("run_id"),
    )


async def search_rag_paper(
    query: str,
    model: str,
    control_number: int,
    user: str = None,
    chat_history: list = None,
):
    ranked_docs, context, config = await _rag_common(query, model, user, control_number)

    answer_chain = CHAIN_CACHE[model]["answer_chain_rag_paper"]

    chat_messages = []
    if chat_history:
        for msg in chat_history:
            role = "user" if msg["type"] == "user" else "assistant"
            chat_messages.append({"role": role, "content": msg["content"]})

    with timer("RAG LLM"):
        response: LLMPaperResponse = await answer_chain.ainvoke(
            {
                "question": query,
                "context": context,
                "history": chat_messages,
            },
            config=config,
        )

    formatted_response, _ = format_refs(response.response, ranked_docs)

    return QueryPaperResponse(
        long_answer=formatted_response, trace_id=config.get("run_id")
    )
