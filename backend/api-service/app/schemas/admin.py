from typing import Any

from pydantic import BaseModel, ConfigDict


class DashboardMetric(BaseModel):
    label: str
    value: str | int | float
    unit: str | None = None
    detail: str | None = None


class ChartPoint(BaseModel):
    label: str
    value: int | float


class AdminAnalyticsResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    overview: list[DashboardMetric]
    system_metrics: list[DashboardMetric]
    model_metrics: list[DashboardMetric]
    data_metrics: list[DashboardMetric]
    charts: dict[str, list[ChartPoint]]
    tables: dict[str, list[dict[str, Any]]]
