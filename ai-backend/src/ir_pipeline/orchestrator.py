from os import getenv

import yaml
from langchain_openai import ChatOpenAI

from src.ir_pipeline.chains import (
    create_answer_generation_chain,
    create_query_expansion_chain,
)
from src.ir_pipeline.schemas import LLMResponse, Terms
from src.ir_pipeline.tools.inspire import InspireOSFullTextSearchTool, InspireSearchTool
from src.ir_pipeline.utils.inspire_formatter import clean_refs, extract_context

CHAIN_CACHE = {}


def load_prompts():
    """Note: this file will be overridden in kubernetes-inspire"""
    with open("src/config/prompts.yml") as f:
        return yaml.safe_load(f)


PROMPTS = load_prompts()


def get_prompt(prompts, prompt_type, model):
    """Get prompt for specific model or fall back to default"""
    model_specific = prompts.get(prompt_type, {}).get(model)
    if model_specific:
        return model_specific
    return prompts.get(prompt_type, {}).get("default", "")


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

    expand_chain = create_query_expansion_chain(
        llm=llm, system_prompt=get_prompt(PROMPTS, "expand_query", model)
    )
    answer_chain = create_answer_generation_chain(
        llm=llm, system_prompt=get_prompt(PROMPTS, "generate_answer", model)
    )

    CHAIN_CACHE[model] = {
        "expand_chain": expand_chain,
        "answer_chain": answer_chain,
    }


async def search(query, model, use_highlights=False):
    """Search INSPIRE HEP database with query expansion and answer generation"""

    if model not in CHAIN_CACHE:
        initialize_chains(model)

    if use_highlights:
        inspire_search_tool = InspireOSFullTextSearchTool()
    else:
        inspire_search_tool = InspireSearchTool()

    expand_chain = CHAIN_CACHE[model]["expand_chain"]
    answer_chain = CHAIN_CACHE[model]["answer_chain"]

    expanded_query: Terms = await expand_chain.ainvoke({"query": query})
    raw_results = inspire_search_tool.run(expanded_query)

    context = extract_context(raw_results, use_highlights=use_highlights)

    answer: LLMResponse = await answer_chain.ainvoke(
        {"query": query, "context": context}
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
