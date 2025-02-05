import re
from os import getenv

import requests
import yaml

from src.ir_pipeline.llm_response import LLMResponse


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


def search_inspire(query, size=10):
    """
    Search INSPIRE HEP database using fulltext search

    Args:
        query (str): Search query
        size (int): Number of results to return
    """
    base_url = "https://inspirehep.net/api/literature"
    params = {"q": query, "size": size, "format": "json"}

    response = requests.get(base_url, params=params)
    return response.json()


def format_reference(metadata):
    output = f"{', '.join(author.get('full_name', '') for author in metadata.get('authors', []))} "
    output += f"({metadata.get('publication_info', [{}])[0].get('year', 'N/A')}). "
    output += f"*{metadata.get('titles', [{}])[0].get('title', 'N/A')}*. "
    output += f"DOI: {metadata.get('dois', [{}])[0].get('value', 'N/A') if metadata.get('dois') else 'N/A'}. "
    output += f"[INSPIRE record {metadata['control_number']}](https://inspirehep.net/literature/{metadata['control_number']})"
    output += "\n\n"
    return output


def format_results(results):
    """Print formatted search results"""
    output = ""
    for i, hit in enumerate(results["hits"]["hits"]):
        metadata = hit["metadata"]
        output += f"**[{i}]** "
        output += format_reference(metadata)
    return output


def results_context(results):
    """Prepare a context from the results for the LLM"""
    context = ""
    for i, hit in enumerate(results["hits"]["hits"]):
        metadata = hit["metadata"]
        context += f"Result [{i}]\n\n"
        context += f"Title: {metadata.get('titles', [{}])[0].get('title', 'N/A')}\n\n"
        context += (
            f"Abstract: {metadata.get('abstracts', [{}])[0].get('value', 'N/A')}\n\n"
        )
    return context


def user_prompt(query, context):
    """Generate a prompt for the LLM"""
    prompt = f"""
  QUERY: {query}

  CONTEXT:

  {context}

  ANSWER:

  """
    return prompt


def llm_expand_query(query, model):
    """Expands a query to variations of fulltext searches"""
    prompt = get_prompt(PROMPTS, "expand_query", model).format(query=query)

    response = requests.post(
        f"{str(getenv('LLM_API_BASE'))}/api/generate",
        json={
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_ctx": 30000,
                "temperature": 0,
                "num_predict": 2048,
                "top_p": 1,
                # "repeat_penalty": 0,
            },
        },
    )
    return response.json()["response"]


def llm_generate_answer(prompt, model):
    """Generate a response from the LLM"""
    system_desc = get_prompt(PROMPTS, "generate_answer", model)

    response = requests.post(
        f"{str(getenv('LLM_API_BASE'))}/api/generate",
        json={
            "model": model,
            "prompt": system_desc + "\n\n" + prompt,
            "stream": False,
            "options": {
                "num_ctx": 30000,
                "temperature": 0,
                "num_predict": 2048,
                "top_p": 1,
                # "repeat_penalty": 0,
            },
            "format": LLMResponse.model_json_schema(),
        },
    )
    return LLMResponse.model_validate_json(response.json()["response"])


def clean_refs(answer, results):
    """Clean the references from the answer"""

    # Find references
    unique_ordered = []
    for match in re.finditer(r"\[(\d+)\]", answer):
        ref_num = int(match.group(1))
        if ref_num not in unique_ordered:
            unique_ordered.append(ref_num)

    # Filter references
    formatted_references = []
    for i, hit in enumerate(results["hits"]["hits"]):
        if i not in unique_ordered:
            continue
        formatted_references.append(format_reference(hit["metadata"]))

    new_i = 1
    for i in unique_ordered:
        answer = answer.replace(f"[{i}]", f" **[__NEW_REF_ID_{new_i}]**")
        new_i += 1
    answer = answer.replace("__NEW_REF_ID_", "")

    return answer, formatted_references


def search(query, model="llama3.2"):
    query = llm_expand_query(query, model)
    results = search_inspire(query)
    context = results_context(results)
    prompt = user_prompt(query, context)
    answer = llm_generate_answer(prompt, model)
    new_answer, references = clean_refs(answer.response, results)

    res = {
        "brief": answer.brief,
        "response": new_answer,
        "references": references,
        "expanded_query": query,
    }

    return res
