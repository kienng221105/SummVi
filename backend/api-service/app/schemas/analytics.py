from typing import Dict, List

from pydantic import BaseModel


class KeywordCount(BaseModel):
    keyword: str
    count: int


class KeywordTrendPoint(BaseModel):
    date: str
    keyword: str
    count: int


class SummaryStats(BaseModel):
    total_summaries: int
    avg_summary_length: float
    avg_compression_ratio: float
    min_summary_length: int
    max_summary_length: int


class TopicDistributionResponse(BaseModel):
    topics: Dict[str, int]


class TopKeywordsResponse(BaseModel):
    keywords: List[KeywordCount]


class KeywordTrendsResponse(BaseModel):
    trends: List[KeywordTrendPoint]


class SummaryStatsResponse(BaseModel):
    stats: SummaryStats
