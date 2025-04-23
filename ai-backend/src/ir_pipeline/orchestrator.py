import uuid
from os import getenv

from langchain_openai import ChatOpenAI
from langfuse.callback import CallbackHandler

from src.ir_pipeline.chains import (
    create_answer_generation_chain,
    create_query_expansion_chain,
)
from src.ir_pipeline.schemas import LLMResponse, Terms
from src.ir_pipeline.tools.inspire import InspireOSFullTextSearchTool, InspireSearchTool
from src.ir_pipeline.utils.inspire_formatter import clean_refs, extract_context

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

    llm = ChatOpenAI(
        model=model,
        base_url=f"{getenv('LLM_API_BASE')}/v1",
        default_headers=(
            {"Host": getenv("KUBEFLOW_HOST")} if getenv("KUBEFLOW_HOST") else {}
        ),
        api_key=getenv("LLM_API_KEY"),
        temperature=0,
        top_p=1,
        timeout=20,
    )

    CHAIN_CACHE[model] = {
        "expand_chain": create_query_expansion_chain(llm=llm),
        "answer_chain": create_answer_generation_chain(llm=llm),
    }


async def search(query: str, model: str, user: str, use_highlights: bool = False):
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
            "langfuse_user_id": user,
        },
    }

    expand_chain = CHAIN_CACHE[model]["expand_chain"]
    answer_chain = CHAIN_CACHE[model]["answer_chain"]

    expanded_query: Terms = await expand_chain.ainvoke({"query": query}, config=config)
    raw_results = inspire_search_tool.run(expanded_query)

    context = extract_context(raw_results, use_highlights=use_highlights)

    answer: LLMResponse = await answer_chain.ainvoke(
        {"query": query, "context": context}, config=config
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
