from functools import lru_cache

from fastapi import APIRouter, HTTPException

from app.schemas.summarize import SummarizeRequest, SummarizeResponse
from app.services.summarization_service import SummarizationService, build_summarization_service


from starlette.concurrency import run_in_threadpool

router = APIRouter()


@lru_cache(maxsize=1)
def get_service() -> SummarizationService:
    return build_summarization_service()


@router.post("/summarize", response_model=SummarizeResponse)
async def summarize(request: SummarizeRequest) -> SummarizeResponse:
    try:
        service = get_service()
        return await run_in_threadpool(
            service.summarize,
            request.text,
            summary_length=request.summary_length,
            output_format=request.output_format,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Summarization failed: {exc}") from exc
