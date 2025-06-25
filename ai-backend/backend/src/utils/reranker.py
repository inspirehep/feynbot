from __future__ import annotations

import json
from copy import deepcopy
from typing import Any, Dict, List, Optional, Sequence, Union

import requests
from langchain_core.callbacks import Callbacks
from langchain_core.documents import BaseDocumentCompressor, Document
from pydantic import Field


class CustomJinaRerank(BaseDocumentCompressor):
    """Document compressor that uses a custom-hosted Jina Rerank API."""

    model_name: str = Field(default="jina-reranker-v2-base-multilingual")
    openai_api_base: str = Field(..., description="Custom Jina Rerank base URL")
    openai_api_key: str = Field(..., description="API key for authentication")
    top_n: int = Field(default=3)
    default_headers: Optional[Dict[str, str]] = Field(default_factory=dict)
    timeout: float = Field(default=5.0)

    def rerank(
        self,
        documents: Sequence[Union[str, Document, dict]],
        query: str,
        *,
        model: Optional[str] = None,
        top_n: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        if not documents:
            return []

        url = f"{self.openai_api_base.rstrip('/')}/rerank"
        headers = {
            "Authorization": f"Bearer {self.openai_api_key}",
            "Content-Type": "application/json",
            **self.default_headers,
        }

        docs = [
            doc.page_content if isinstance(doc, Document) else doc for doc in documents
        ]

        data = {
            "query": query,
            "documents": docs,
            "model": model or self.model_name,
            "top_n": top_n if (top_n is not None and top_n > 0) else self.top_n,
        }

        try:
            resp = requests.post(url, headers=headers, json=data, timeout=self.timeout)
            resp.raise_for_status()
            fixed_response = resp.text.replace("\\u", "\\\\u")
            resp_json = json.loads(fixed_response)
        except requests.RequestException as e:
            raise RuntimeError(f"Request to rerank API failed: {str(e)}") from e
        except ValueError:
            raise RuntimeError(f"Non-JSON response: {resp.text}") from resp

        if "results" not in resp_json:
            raise RuntimeError(resp_json.get("detail", "Unknown error"))
        return [
            {
                "index": res["index"],
                "document": res["document"],
                "relevance_score": res["relevance_score"],
            }
            for res in resp_json["results"]
        ]

    def compress_documents(
        self,
        documents: Sequence[Document],
        query: str,
        callbacks: Optional[Callbacks] = None,
    ) -> Sequence[Document]:
        reranked = self.rerank(documents, query)
        compressed = []
        for res in reranked:
            doc = documents[res["index"]]
            doc_copy = Document(
                page_content=doc.page_content, metadata=deepcopy(doc.metadata)
            )
            doc_copy.metadata["relevance_score"] = res["relevance_score"]
            compressed.append(doc_copy)
        return compressed
