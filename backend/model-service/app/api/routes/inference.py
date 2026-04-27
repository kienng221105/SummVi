from fastapi import APIRouter

from app.schemas.inference import SummarizeRequest, SummarizeResponse
from app.services.inference_service import get_inference_service

router = APIRouter()


@router.post("/summarize", response_model=SummarizeResponse)
def summarize(request: SummarizeRequest) -> SummarizeResponse:
    service = get_inference_service()
    return service.summarize(
        request.text,
        summary_length=request.summary_length,
        output_format=request.output_format,
    )
