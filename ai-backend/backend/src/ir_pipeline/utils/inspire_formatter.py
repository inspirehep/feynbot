import re
from typing import Dict, List, Tuple

from backend.src.schemas.query import Citation


def extract_context(results: Dict, use_highlights: bool = False) -> str:
    """
    Extracts context from search results. If use_highlights is True,
    include highlight snippets instead of abstracts.
    """
    if not use_highlights:
        context_items = []
        for i, hit in enumerate(results["hits"]["hits"]):
            title = hit["metadata"].get("titles", [{}])[0].get("title", "N/A")
            abstract = hit["metadata"].get("abstracts", [{}])[0].get("value", "N/A")
            context_items.append(
                f"Result [{i}]\n\nTitle: {title}\n\nAbstract: {abstract}\n\n"
            )
    else:
        context_items = []
        for i, hit in enumerate(results["hits"]["hits"]):
            source = hit["_source"]
            snippets = hit.get("highlight", {}).get("documents.attachment.content", [])
            formatted_snippets = (
                "".join(
                    "Snippet "
                    + f"[{s_index}]"
                    + ": "
                    + re.sub(r"\s+|</?em>", " ", snippet)
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


def clean_refs(
    answer: str, results: Dict, use_highlights: bool = False
) -> Tuple[str, List[str]]:
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
        formatted_references.append(
            format_reference(hit["_source" if use_highlights else "metadata"])
        )

    new_i = 1
    for i in unique_ordered:
        answer = answer.replace(f"[{i}]", f" **[__NEW_REF_ID_{new_i}]**")
        new_i += 1
    answer = answer.replace("__NEW_REF_ID_", "")

    return answer, formatted_references


def clean_refs_with_snippets(
    answer: str,
    results: Dict,
) -> Tuple[str, List[str]]:
    """Returns an object with [paper:snippet] references as keys and paperId, snippet
    and display (citation numbers to display starting from 1) as values"""
    count = 1
    paper_order = {}

    citations = {}

    for match in re.finditer(r"\[(\d+):(\d+)\]", answer):
        full_match = match.group(0)
        paper = int(match.group(1))
        snippet = int(match.group(2))

        if paper not in paper_order:
            paper_order[paper] = count
            count += 1

        hit = results["hits"]["hits"][paper]

        snippets = hit.get("highlight", {}).get("documents.attachment.content", [])

        citations[full_match] = {
            "paperId": hit["_source"]["control_number"],
            "snippet": snippets[snippet] if len(snippets) > snippet else "",
            "display": paper_order[paper],
        }

    return answer, citations


def format_docs(docs):
    res = f"\n{'-' * 10}\n".join(
        [f"Document {i + 1}: \n" + str(d.page_content) for i, d in enumerate(docs)]
    )
    return res


def format_refs(answer, docs):
    unique_ordered = []
    for match in re.finditer(r"\[(\d+)\]", answer):
        ref_num = int(match.group(1))
        if ref_num not in unique_ordered:
            unique_ordered.append(ref_num)

    doc_id_map = {}
    new_i = 1
    citations = []

    for i in unique_ordered:
        doc = docs[i - 1]
        control_number = doc.metadata.get("control_number")

        if control_number in doc_id_map:
            doc_id = doc_id_map[control_number]
        else:
            doc_id = new_i
            doc_id_map[control_number] = new_i
            new_i += 1

        answer = answer.replace(f"[{i}]", f"[__NEW_REF_ID_{doc_id}]")

        citations.append(
            Citation(
                doc_id=doc_id,
                control_number=control_number,
                snippet=doc.page_content,
            )
        )

    formatted_answer = answer.replace("__NEW_REF_ID_", "")

    return formatted_answer, citations
