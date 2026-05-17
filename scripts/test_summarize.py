import pytest
from fastapi import status
from unittest.mock import patch
from app.core.config import settings

PREFIX = settings.api_prefix

def test_legacy_summarize_success(client):
    with patch("app.services.model_client.model_client.summarize") as mock_summ:
        mock_summ.return_value = {"summary": "Legacy Tóm tắt", "metrics": {}}
        response = client.post(
            f"{PREFIX}/summarize",
            json={"text": "Nội dung", "summary_length": "medium"}
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["summary"] == "Legacy Tóm tắt"

def test_legacy_summarize_fail(client):
    from app.services.model_client import ModelServiceError
    with patch("app.services.model_client.model_client.summarize") as mock_summ:
        mock_summ.side_effect = ModelServiceError("Error")
        response = client.post(
            f"{PREFIX}/summarize",
            json={"text": "Nội dung"}
        )
        assert response.status_code == status.HTTP_502_BAD_GATEWAY

def test_legacy_multi_summarize_success(client):
    with patch("app.services.model_client.model_client.multi_summarize") as mock_summ:
        mock_summ.return_value = {"summary": "Legacy Multi Tóm tắt", "metrics": {}}
        response = client.post(
            f"{PREFIX}/multi-summarize",
            json=["Đoạn 1", "Đoạn 2"]
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["summary"] == "Legacy Multi Tóm tắt"
