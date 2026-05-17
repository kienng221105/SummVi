import pytest
from fastapi import status
from unittest.mock import patch, MagicMock
from uuid import uuid4
from datetime import datetime

def test_summarize_text(authenticated_client):
    conv_id = uuid4()
    msg_id = uuid4()
    mock_response = {
        "id": msg_id,
        "conversation_id": conv_id,
        "content": "Gốc",
        "summary": "Tóm tắt giả lập",
        "metrics": {"latency": 0.5},
        "created_at": datetime.now()
    }
    
    with patch("app.services.ai_service.summarize_text") as mock_summarize:
        mock_summarize.return_value = mock_response
        response = authenticated_client.post(
            "/ai/",
            json={"text": "Đoạn văn bản cần tóm tắt", "summary_length": "medium"}
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["summary"] == "Tóm tắt giả lập"

def test_summarize_file_invalid_ext(authenticated_client):
    response = authenticated_client.post(
        "/ai/summarize-file",
        files={"file": ("test.exe", b"invalid content", "application/octet-stream")}
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST

def test_model_health_success(authenticated_client):
    with patch("app.services.model_client.model_client.health_check") as mock_health:
        mock_health.return_value = {"status": "ok"}
        response = authenticated_client.get("/ai/model-health")
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["status"] == "ok"

def test_model_health_fail(authenticated_client):
    from app.services.model_client import ModelServiceError
    with patch("app.services.model_client.model_client.health_check") as mock_health:
        mock_health.side_effect = ModelServiceError("Down")
        response = authenticated_client.get("/ai/model-health")
        assert response.status_code == status.HTTP_502_BAD_GATEWAY
