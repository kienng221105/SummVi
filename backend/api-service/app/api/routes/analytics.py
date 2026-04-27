from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.dependencies.deps import get_db
from app.schemas.analytics import (
    KeywordTrendsResponse,
    SummaryStatsResponse,
    TopicDistributionResponse,
    TopKeywordsResponse,
)
from app.services import analytics_service


router = APIRouter()


@router.get("/topics", response_model=TopicDistributionResponse)
def get_topics(db: Session = Depends(get_db)):
    """Distribution of topics across all generated summaries."""
    return TopicDistributionResponse(
        topics=analytics_service.get_topic_distribution(db),
    )


@router.get("/top-keywords", response_model=TopKeywordsResponse)
def get_top_keywords(
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Most frequent keywords extracted from summaries."""
    return TopKeywordsResponse(
        keywords=analytics_service.get_top_keywords(db, limit=limit),
    )


@router.get("/trends", response_model=KeywordTrendsResponse)
def get_keyword_trends(
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
):
    """Keyword frequencies grouped by date for trend visualisation."""
    return KeywordTrendsResponse(
        trends=analytics_service.get_keyword_trends(db, limit=days),
    )


@router.get("/summary-stats", response_model=SummaryStatsResponse)
def get_summary_stats(db: Session = Depends(get_db)):
    """Aggregate statistics about generated summaries."""
    return SummaryStatsResponse(
        stats=analytics_service.get_summary_stats(db),
    )
