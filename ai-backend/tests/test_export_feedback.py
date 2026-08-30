import unittest
from datetime import datetime
from unittest.mock import MagicMock
from uuid import UUID

from backend.src.api.v1 import authenticate
from backend.src.database import get_db
from backend.src.main import app
from backend.src.models import SearchFeedback
from fastapi.testclient import TestClient


class ExportFeedbackTest(unittest.TestCase):
    def setUp(self):
        feedback = SearchFeedback(
            id=UUID("00000000-0000-0000-0000-000000000001"),
            question="How can search improve?",
            additional=None,
            matomo_client_id=None,
            timestamp=datetime(2025, 1, 15, 12, 0),
        )
        self.db = MagicMock()
        self.db.query.return_value.filter.return_value.all.return_value = [feedback]
        app.dependency_overrides[get_db] = lambda: self.db
        app.dependency_overrides[authenticate] = lambda: "test-user"
        self.client = TestClient(app)
        self.params = {
            "start_date": "2025-01-01T00:00:00",
            "end_date": "2025-01-31T00:00:00",
        }

    def tearDown(self):
        app.dependency_overrides.clear()

    def test_returns_json_by_default(self):
        response = self.client.get(
            "/v1/export-search-feedback",
            params=self.params,
        )

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"
        assert response.json() == [
            {
                "id": "00000000-0000-0000-0000-000000000001",
                "question": "How can search improve?",
                "additional": None,
                "matomo_client_id": None,
                "timestamp": "2025-01-15T12:00:00",
            }
        ]

    def test_returns_json_when_csv_is_explicitly_false(self):
        response = self.client.get(
            "/v1/export-search-feedback",
            params={**self.params, "export_csv": "false"},
        )

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"

    def test_returns_csv_when_csv_is_true(self):
        response = self.client.get(
            "/v1/export-search-feedback",
            params={**self.params, "export_csv": "true"},
        )

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/csv")
        assert "attachment;" in response.headers["content-disposition"]
        assert (
            response.text.splitlines()[0]
            == "id,question,additional,matomo_client_id,timestamp"
        )

    def test_openapi_advertises_json_and_csv(self):
        response_content = app.openapi()["paths"]["/v1/export-search-feedback"]["get"][
            "responses"
        ]["200"]["content"]

        assert set(response_content) == {"application/json", "text/csv"}


if __name__ == "__main__":
    unittest.main()
