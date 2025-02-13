from typing import Dict, Optional

import requests
from langchain_core.callbacks import CallbackManagerForToolRun
from langchain_core.tools import BaseTool
from pydantic import Field


class InspireSearchTool(BaseTool):
    """Tool for searching on the INSPIRE HEP API."""

    name: str = "inspire_search"
    description: str = "Search INSPIRE HEP database using fulltext search"
    size: int = Field(default=10, description="Number of results to return")

    def _run(
        self,
        query: str,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> Dict:
        """Executes the search and returns the raw JSON response."""
        base_url = "https://inspirehep.net/api/literature"
        params = {"q": query, "size": self.size, "format": "json"}
        response = requests.get(base_url, params=params)
        response.raise_for_status()
        results = response.json()
        if run_manager:
            run_manager.on_text(f"Returned {len(results['hits']['hits'])} results.")
        return results
