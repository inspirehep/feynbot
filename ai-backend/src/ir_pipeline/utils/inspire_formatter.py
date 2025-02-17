import re
from typing import Dict, List, Tuple


def extract_context(results: Dict, use_highlights: bool = False) -> str:
    """
    Extracts context from search results. If use_highlights is True,
    include highlight snippets instead of abstracts.
    """
    if not use_highlights:
        context_items = [
            f"Result [{i}]\n\n"
            f"Title: {hit['metadata'].get('titles', [{}])[0].get('title', 'N/A')}\n\n"
            f"Abstract: {hit['metadata'].get('abstracts', [{}])[0].get('value', 'N/A')}\n\n"
            for i, hit in enumerate(results["hits"]["hits"])
        ]
    else:
        context_items = []
        for i, hit in enumerate(results["hits"]["hits"]):
            source = hit["_source"]
            snippets = hit.get("highlight", {}).get("documents.attachment.content", [])
            formatted_snippets = (
                "".join(
                    "Snippet "
                    + chr(65 + s_index)
                    + ": "
                    + re.sub(r"\s+", " ", snippet)
                    + "\n\n"
                    for s_index, snippet in enumerate(snippets)
                )
                or "N/A\n\n"
            )
            context_items.append(
                f"Result [{i}]\n\n"
                f"Title: {source.get('titles', [{}])[0].get('title', 'N/A')}\n\n"
                "Snippets:\n" + formatted_snippets
            )
    return "\n".join(context_items)


def format_reference(metadata: Dict) -> str:
    """Formats a single INSPIRE record into a human-readable reference."""
    authors = ", ".join(
        author.get("full_name", "") for author in metadata.get("authors", [])
    )
    year = (
        metadata.get("publication_info", [{}])[0].get("year", "N/A")
        if metadata.get("publication_info")
        else "N/A"
    )
    title = metadata.get("titles", [{}])[0].get("title", "N/A")
    doi = (
        metadata.get("dois", [{}])[0].get("value", "N/A")
        if metadata.get("dois")
        else "N/A"
    )
    inspire_id = metadata["control_number"]

    output = f"{authors} ({year}). *{title}*. DOI: {doi}. [INSPIRE record {inspire_id}](https://inspirehep.net/literature/{inspire_id})\n\n"
    return output


def clean_refs(answer: str, results: Dict) -> Tuple[str, List[str]]:
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
