import uuid
from os import getenv

from backend.src.ir_pipeline.chains import (
    create_answer_generation_chain,
    create_query_expansion_chain,
)
from backend.src.ir_pipeline.schema import LLMResponse, Terms
from backend.src.ir_pipeline.tools.inspire import (
    InspireOSFullTextSearchTool,
    InspireSearchTool,
)
from backend.src.ir_pipeline.utils.inspire_formatter import (
    clean_refs,
    clean_refs_with_snippets,
    extract_context,
)
from langchain_community.llms import VLLMOpenAI
from langfuse.callback import CallbackHandler

LANGFUSE_HANDLER = CallbackHandler(
    public_key=getenv("LANGFUSE_PUBLIC_KEY"),
    secret_key=getenv("LANGFUSE_SECRET_KEY"),
    host=getenv("LANGFUSE_HOST"),
    release=getenv("BACKEND_VERSION"),
)

CHAIN_CACHE = {}


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

    config = {
        "callbacks": [LANGFUSE_HANDLER],
        "metadata": {
            "langfuse_session_id": str(uuid.uuid4()),
            **({"langfuse_user_id": user} if user else {}),
        },
    }

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
