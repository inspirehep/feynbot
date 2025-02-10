import logging
import re
import time
from os import getenv

import gradio as gr
import requests
from feynbot_ir.schemas import LLMResponse, Terms
from opensearchpy import OpenSearch

logger = logging.getLogger(__name__)


def get_prompt(prompts, prompt_type, model):
    """Get prompt for specific model or fall back to default"""
    model_specific = prompts.get(prompt_type, {}).get(model)
    if model_specific:
        return model_specific
    return prompts.get(prompt_type, {}).get("default", "")


def build_nested_bool_query(terms, is_root=True):
    """Build a nested bool query from array of terms"""
    if not terms:
        return None

    if len(terms) == 1:
        query = {
            "bool": {
                "must": [{"match_phrase": {"documents.attachment.content": terms[0]}}],
                "minimum_should_match": "0<1",
            }
        }
    else:
        query = {
            "bool": {
                "should": [
                    {"match_phrase": {"documents.attachment.content": terms[0]}},
                    build_nested_bool_query(terms[1:], is_root=False)
                    if len(terms) > 2
                    else {"match_phrase": {"documents.attachment.content": terms[1]}},
                ],
            }
        }

    if is_root:
        query["bool"]["filter"] = [
            {"match_all": {}},
            {"terms": {"_collections": ["Literature"]}},
            # Only fetch records with arXiv eprints while we evaluate publisher agreements regarding fulltext utilization
            {"exists": {"field": "arxiv_eprints"}},
        ]
        if len(terms) > 1:
            query["bool"]["minimum_should_match"] = 1

    return query


def search_inspire(terms, size=5):
    """Search INSPIRE HEP database using Elasticsearch"""
    client = OpenSearch(
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

    query = build_nested_bool_query(terms, is_root=True)

    body = {
        "query": query,
        "size": size,
        "highlight": {
            "fields": {
                "documents.attachment.content": {
                    "fragment_size": 1000,
                    "number_of_fragments": 3,
                    "order": "score",
                    "type": "fvh",
                    "pre_tags": ["<em>"],
                    "post_tags": ["</em>"],
                    "boundary_scanner": "sentence",
                    "boundary_scanner_locale": "en-US",
                }
            }
        },
    }

    response = client.search(body=body, index="records-hep")

    try:
        return {"hits": {"hits": response["hits"]["hits"]}}
    except Exception as e:
        logger.error(f"OpenSearch error: {str(e)}")


def format_reference(source):
    output = f"{', '.join(author.get('full_name', '') for author in source.get('authors', []))} "
    output += f"({source.get('publication_info', [{}])[0].get('year', 'N/A')}). "
    output += f"*{source.get('titles', [{}])[0].get('title', 'N/A')}*. "
    output += f"DOI: {source.get('dois', [{}])[0].get('value', 'N/A') if source.get('dois') else 'N/A'}. "
    output += f"[INSPIRE record {source['control_number']}](https://inspirehep.net/literature/{source['control_number']})"
    output += "\n\n"
    return output


def results_context(results):
    """Prepare a context from the results for the LLM"""
    context = ""
    for i, hit in enumerate(results["hits"]["hits"]):
        source = hit["_source"]
        context += f"# Result [{i}]\n\n"
        context += (
            f"## Title: \n {source.get('titles', [{}])[0].get('title', 'N/A')}\n\n"
        )
        context += "## Snippets: \n"
        for s_index, snippet in enumerate(
            hit.get("highlight").get("documents.attachment.content", [])
        ):
            clean_snippet = re.sub(r"\s+", " ", snippet)
            context += f"### Snippet {chr(65 + s_index)}: \n {clean_snippet}\n\n"
    return context


def user_prompt(query, context):
    """Generate a prompt for the LLM"""
    prompt = f"""
  <QUERY>{query}</QUERY>

  <CONTEXT>
  {context}
  </CONTEXT>
  """
    return prompt


def llm_expand_query(query, model):
    """Expands a query to variations of fulltext searches"""
    system_prompt = """
    Expand this search query and propose 5 alternatives of the query to
    maximize the recall. These queries will later be used by the application
    to perform a fulltext search on InspireHEP literature records.
    Provide only a JSON object with a terms item that will contain the
    array of queries, without any explanation, introduction or comment.

    Example of query:
    how far are black holes?

    Example of expanded query:
    {
      "terms": [
        "how far are black holes",
        "distance to black holes",
        "distance to singularities",
        "distances to event horizon",
        "distance from Schwarzschild radius",
      ]
    }
  """

    response = requests.post(
        f"{str(getenv('OPENAI_API_BASE'))}/api/generate",
        json={
            "model": model,
            "system": system_prompt,
            "prompt": query,
            "stream": False,
            "options": {
                "num_ctx": 30000,
                "temperature": 0,
                "num_predict": 2048,
                "top_p": 1,
                # "repeat_penalty": 0,
            },
            "format": Terms.model_json_schema(),
        },
    )

    return Terms.model_validate_json(response.json()["response"]).terms


def llm_generate_answer(prompt, model):
    """Generate a response from the LLM"""
    system_prompt = """
    You are part of a Retrieval Augmented Generation system
    (RAG) and you are provided with a query and a context of results. Your task 
    is to generate an answer which must be substantiated by the results provided. 
    You must cite these results using their index when used to provide an answer 
    text. Do not put two or more references together (ex: use [1][2] instead of 
    [1,2]) and do not reference the snippets, only the result they belong to. 
    Also, do not include citations present in the retrieved context in your response 
    and do not mention the notion of snippet in your response. Do not generate an 
    answer that cannot be extracted from the provided context. All paragraphs must 
    be separated by new line characters and cite a search result. Your response 
    should ideally be a few paragraphs long. End the answer with the original 
    query and a brief summary of you response. Do not consider results that are 
    not related to the query and, if no specific answer can be provided, assert 
    that in the brief answer. Format your response as JSON with the fields `brief`, 
    `response` and `query`.
    """

    response = requests.post(
        f"{str(getenv('OPENAI_API_BASE'))}/api/generate",
        json={
            "model": model,
            "system": system_prompt,
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_ctx": 50000,
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
    new_i = 1
    formatted_references = []
    for i, hit in enumerate(results["hits"]["hits"]):
        if i not in unique_ordered:
            continue
        formatted_references.append(f"**[{new_i}]** {format_reference(hit['_source'])}")
        new_i += 1

    new_i = 1
    for i in unique_ordered:
        answer = answer.replace(f"[{i}]", f" **[__NEW_REF_ID_{new_i}]**")
        new_i += 1
    answer = answer.replace("__NEW_REF_ID_", "")

    return answer, formatted_references


def search(query, model="llama3.2", progress=gr.Progress()):
    time.sleep(1)
    progress(0, desc="Expanding query...")
    expanded_query = llm_expand_query(query, model)
    progress(0.25, desc="Searching INSPIRE ElasticSearch...")
    results = search_inspire(expanded_query)
    progress(0.50, desc="Generating answer...")
    context = results_context(results)
    prompt = user_prompt(query, context)
    answer = llm_generate_answer(prompt, model)
    new_answer, references = clean_refs(answer.response, results)
    progress(1, desc="Done!")

    return (
        "**Brief answer**:\n\n"
        + answer.brief
        + "\n\n**Answer**:\n\n"
        + new_answer
        + "\n\n**Expanded query**:\n\n"
        + ", ".join(expanded_query)
        + "\n\n**References**:\n\n"
        + "\n".join(references)
    )
