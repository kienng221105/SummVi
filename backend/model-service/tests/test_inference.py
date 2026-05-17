import pytest
from fastapi import status
from unittest.mock import patch

def test_summarize_success(client):
    with patch("app.services.inference_service.get_inference_service") as mock_get_service:
        mock_service = mock_get_service.return_value
        # Mocking the response of service.summarize
        # Note: SummarizeResponse is expected, so the mock should return a dict or object 
        # that matches the schema.
        mock_service.summarize.return_value = {
            "summary": "Tóm tắt từ model service",
            "metrics": {"latency": 0.1},
            "diagnostics": {}
        }
        
        response = client.post(
            "/v1/summarize",
            json={"text": "Văn bản cần tóm tắt", "summary_length": "medium"}
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["summary"] == "Tóm tắt từ model service"

def test_summarize_empty_text(client):
    response = client.post(
        "/v1/summarize",
        json={"text": "   ", "summary_length": "medium"}
    )
    # Pydantic validator will raise ValueError which translates to 422
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"status": "ok"}
