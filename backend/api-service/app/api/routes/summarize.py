from fastapi import APIRouter, HTTPException, status

from app.schemas.summarize import SummarizeRequest, SummarizeResponse
from app.services.model_client import ModelServiceError, model_client

router = APIRouter()


@router.post("/summarize", response_model=SummarizeResponse)
def summarize(request: SummarizeRequest) -> SummarizeResponse:
    try:
        result = model_client.summarize(
            request.text,
            summary_length=request.summary_length,
            output_format=request.output_format,
        )
    except ModelServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Model service is unavailable",
        ) from exc

    return SummarizeResponse(
        summary=str(result.get("summary") or ""),
        metrics=result.get("metrics") or {},
    )
