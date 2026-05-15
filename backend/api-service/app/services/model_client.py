from typing import Any, List

import httpx

from app.core.config import settings


class ModelServiceError(RuntimeError):
    pass


class ModelClient:
    def __init__(self) -> None:
        self._client = httpx.Client(
            base_url=settings.model_service_url.rstrip("/"),
            timeout=settings.model_service_timeout_seconds,
        )

    # ── Single-text summarization ───────────────────────────────
    def summarize(self, text: str, summary_length: str, output_format: str) -> dict[str, Any]:
        try:
            response = self._client.post(
                "/v1/summarize",
                json={
                    "text": text,
                    "summary_length": summary_length,
                    "output_format": output_format,
                },
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise ModelServiceError("Model service request failed") from exc

        payload = response.json()
        if not isinstance(payload, dict):
            raise ModelServiceError("Model service returned an invalid response")
        return payload

    # ── Multi-document summarization ────────────────────────────
    def multi_summarize(self, texts: List[str], summary_length: str, output_format: str) -> dict[str, Any]:
        try:
            response = self._client.post(
                "/v1/multi-summarize",
                json={
                    "texts": texts,
                    "summary_length": summary_length,
                    "output_format": output_format,
                },
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise ModelServiceError("Model service request failed") from exc

        payload = response.json()
        if not isinstance(payload, dict):
            raise ModelServiceError("Model service returned an invalid response")
        return payload

    # ── File summarization ──────────────────────────────────────
    def summarize_file(self, file_bytes: bytes, filename: str, summary_length: str, output_format: str) -> dict[str, Any]:
        try:
            response = self._client.post(
                "/v1/summarize-file",
                files={"file": (filename, file_bytes)},
                params={
                    "summary_length": summary_length,
                    "output_format": output_format,
                },
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise ModelServiceError("Model service request failed") from exc

        payload = response.json()
        if not isinstance(payload, dict):
            raise ModelServiceError("Model service returned an invalid response")
        return payload

    # ── Health check ────────────────────────────────────────────
    def health_check(self) -> dict[str, Any]:
        try:
            response = self._client.get("/health")
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise ModelServiceError("Model service health check failed") from exc
        return response.json()


model_client = ModelClient()
