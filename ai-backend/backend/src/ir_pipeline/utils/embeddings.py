from typing import List

import requests
from langchain_core.embeddings import Embeddings


class VLLMOpenAIEmbeddings(Embeddings):
    def __init__(
        self,
        model_name: str,
        openai_api_base: str,
        openai_api_key: str,
        default_headers: dict = None,
        timeout: float = 5.0,
    ):
        self.model_name = model_name
        self.openai_api_base = openai_api_base.rstrip("/")
        self.openai_api_key = openai_api_key
        self.default_headers = default_headers or {}
        self.timeout = timeout

    def _create_embedding(self, texts: List[str]) -> List[List[float]]:
        url = f"{self.openai_api_base}/embeddings"
        headers = {
            "Authorization": f"Bearer {self.openai_api_key}",
            "Content-Type": "application/json",
            **self.default_headers,
        }
        payload = {
            "model": self.model_name,
            "input": texts,
        }
        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=self.timeout,
        )
        response.raise_for_status()
        data = response.json()
        return [item["embedding"] for item in data["data"]]

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return self._create_embedding(texts)

    def embed_query(self, text: str) -> List[float]:
        return self._create_embedding([text])[0]
