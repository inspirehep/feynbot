from os import getenv
from typing import Dict, Optional

import requests
from backend.src.ir_pipeline.schema import Terms
from langchain_core.callbacks import CallbackManagerForToolRun
from langchain_core.tools import BaseTool
from opensearchpy import OpenSearch
from pydantic import Field


class InspireSearchTool(BaseTool):
    """Tool for searching on the INSPIRE HEP API."""

    name: str = "inspire_search"
    description: str = "Search INSPIRE HEP database using fulltext search"
    size: int = Field(default=10, description="Number of results to return")

    def _run(
        self,
        terms: list[str],
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> Dict:
        """Executes the search and returns the raw JSON response."""
        query = " OR ".join([f'ft "{term}"' for term in terms])
        base_url = "https://inspirehep.net/api/literature"
        params = {"q": query, "size": self.size, "format": "json"}
        response = requests.get(base_url, params=params)
        response.raise_for_status()
        results = response.json()
        if run_manager:
            run_manager.on_text(f"Returned {len(results['hits']['hits'])} results.")
        return results

    def run(
        self,
        terms: Terms,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> Dict:
        """Override run to handle Terms parameter"""
        return self._run(terms.terms, run_manager=run_manager)


class InspireOSFullTextSearchTool(BaseTool):
    """Tool for searching on the INSPIRE HEP OpenSearch database."""

    name: str = "inspire_elastic_search"
    description: str = "Search INSPIRE HEP OpenSearch database"
    size: int = Field(default=5, description="Number of results to return")

    class Config:
        extra = "allow"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.client = OpenSearch(
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

    def build_nested_bool_query(self, terms):
        """Build a nested bool query iteratively to avoid recursion limits"""
        if not terms:
            return None
        should_clauses = [
            {"match_phrase": {"documents.attachment.content": term}} for term in terms
        ]
        query = {
            "bool": {
                "should": should_clauses,
                "minimum_should_match": 1,
            }
        }
        query["bool"]["filter"] = [
            {"match_all": {}},
            {"terms": {"_collections": ["Literature"]}},
            {"exists": {"field": "arxiv_eprints"}},
        ]
        return query

    def _run(
        self,
        terms: list[str],
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> Dict:
        """Executes the search and returns the raw JSON response."""
        query = self.build_nested_bool_query(terms)
        body = {
            "query": query,
            "size": self.size,
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

        response = self.client.search(body=body, index="records-hep")

        if run_manager:
            run_manager.on_text(f"Returned {len(response['hits']['hits'])} results.")
        return response

    def run(
        self,
        terms: Terms,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> Dict:
        """Override run to handle Terms parameter"""
        return self._run(terms.terms, run_manager=run_manager)
