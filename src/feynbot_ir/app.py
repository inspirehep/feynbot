import requests
import gradio as gr
import time
import re
from os import getenv


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


def llm_expand_query(query, model="llama3.2"):
    """Expands a query to variations of fulltext searches"""
    prompt = f"""
    Expand this query into a the query format used for a fulltext search
    over the INSPIRE HEP database. Propose alternatives of the query to
    maximize the recall and join those variantes using OR operators and
    prepend each variant with the ft prefix. Just provide the expanded
    query, without explanations.

    Example of query:
    how far are black holes?

    Expanded query:
    ft "how far are black holes" OR ft "distance from black holes" OR ft
    "distances to black holes" OR ft "measurement of distance to black
    holes"  OR ft "remoteness of black holes"  OR ft "distance to black
    holes"  OR ft "how far are singularities"  OR ft "distance to
    singularities"  OR ft "distances to event horizon"  OR ft "distance
    from Schwarzschild radius" OR ft "black hole distance"

    Query: {query}

    Expanded query:
  """

    response = requests.post(
        f"{str(getenv('OPENAI_API_BASE'))}/api/generate",
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


def llm_generate_answer(prompt, model="llama3.2"):
    """Generate a response from the LLM"""

    system_desc = """You are part of a Retrieval Augmented Generation system
              (RAG) and are asked with a query and a context of results. Generate an
              answer substantiated by the results provided and citing them using
              their index when used to provide an answer text. Do not put two or more
              references together (ex: use [1][2] instead of [1,2]. Do not generate an answer
              that cannot be entailed from cited abstract, so all paragraphs should cite a
              search result. End the answer with the query and a brief answer as
              summary of the previous discussed results. Do not consider results
              that are not related to the query and, if no specific answer can be
              provided, assert that in the brief answer."""

    response = requests.post(
        f"{str(getenv('OPENAI_API_BASE'))}/api/generate",
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
        },
    )
    return response.json()["response"]


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
    new_results = ""
    for i, hit in enumerate(results["hits"]["hits"]):
        if i not in unique_ordered:
            continue
        metadata = hit["metadata"]
        new_results += f"**[{new_i}]** "
        new_results += format_reference(metadata)
        new_i += 1

    new_i = 1
    for i in unique_ordered:
        answer = answer.replace(f"[{i}]", f" **[__NEW_REF_ID_{new_i}]**")
        new_i += 1
    answer = answer.replace("__NEW_REF_ID_", "")

    return answer, new_results


def search(query, model="llama3.2", progress=gr.Progress()):
    time.sleep(1)
    progress(0, desc="Expanding query...")
    query = llm_expand_query(query, model)
    progress(0.25, desc="Searching INSPIRE HEP...")
    results = search_inspire(query)
    progress(0.50, desc="Generating answer...")
    context = results_context(results)
    prompt = user_prompt(query, context)
    answer = llm_generate_answer(prompt, model)
    new_answer, references = clean_refs(answer, results)
    progress(1, desc="Done!")

    # json_str = json.dumps(results['hits']['hits'][0]['metadata'], indent=4)
    return (
        "**Answer**:\n\n" + new_answer + "\n\n**References**:\n\n" + references
    )  # + "\n\n <pre>\n" + json_str + "</pre>"
