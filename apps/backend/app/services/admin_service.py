from collections import Counter, defaultdict
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.core.database import InferenceLog
from app.models.conversation import Conversation
from app.models.document import Document
from app.models.message import Message
from app.models.rating import Rating
from app.models.system_log import SystemLog
from app.models.user import AppUser
from app.models.user_activity import UserActivity


def list_users(db: Session) -> list[AppUser]:
    return db.query(AppUser).order_by(AppUser.created_at.desc()).all()


def get_logs(db: Session, limit: int = 200) -> list[SystemLog]:
    return db.query(SystemLog).order_by(SystemLog.created_at.desc()).limit(limit).all()


def get_admin_analytics(db: Session) -> dict[str, Any]:
    users = list_users(db)
    logs = get_logs(db, limit=1000)
    inference_logs = db.query(InferenceLog).order_by(InferenceLog.created_at.desc()).limit(1000).all()
    activities = db.query(UserActivity).order_by(UserActivity.created_at.desc()).limit(1000).all()
    ratings = db.query(Rating).all()
    documents = db.query(Document).all()
    conversations = db.query(Conversation).all()
    messages = db.query(Message).all()

    total_users = len(users)
    active_users = sum(1 for user in users if user.is_active)
    admin_users = sum(1 for user in users if user.role == "admin")
    total_logs = len(logs)
    error_logs = [log for log in logs if log.status_code >= 400]
    success_rate = ((total_logs - len(error_logs)) / total_logs * 100) if total_logs else 100.0

    overview = [
        _metric("Tong users", total_users, detail=f"{active_users} active / {admin_users} admin"),
        _metric("Conversations", len(conversations), detail=f"{len(messages)} messages"),
        _metric("Documents", len(documents), detail=f"{sum(doc.chunk_count or 0 for doc in documents)} total chunks"),
        _metric("Requests", total_logs, detail=f"{len(error_logs)} loi gan day"),
    ]

    system_metrics = [
        _metric("Success rate", round(success_rate, 2), unit="%"),
        _metric("Avg latency", round(_avg([log.response_time for log in logs]), 2), unit="ms"),
        _metric("Error logs", len(error_logs), detail="HTTP >= 400"),
        _metric("Unique endpoints", len({log.endpoint for log in logs}), detail="Tu system logs"),
    ]

    model_metrics = [
        _metric("Inference requests", len(inference_logs), detail="So lan model duoc goi"),
        _metric("Avg model latency", round(_avg([log.latency for log in inference_logs]), 3), unit="s"),
        _metric("Avg generation", round(_avg([log.generation_latency for log in inference_logs]), 3), unit="s"),
        _metric("Fallback rate", round(_ratio(sum(1 for log in inference_logs if log.used_model_fallback), len(inference_logs)), 2), unit="%"),
        _metric("Avg compression", round(_avg([log.compression_ratio for log in inference_logs]), 4)),
        _metric("Avg retrieved chunks", round(_avg([log.retrieved_chunk_count for log in inference_logs]), 2)),
    ]

    avg_rating = _avg([rating.rating for rating in ratings])
    data_metrics = [
        _metric("Avg input words", round(_avg([log.input_word_count for log in inference_logs]), 2)),
        _metric("Avg summary words", round(_avg([log.summary_word_count for log in inference_logs]), 2)),
        _metric("Avg rating", round(avg_rating, 2), detail=f"{len(ratings)} feedbacks"),
        _metric("User activities", len(activities), detail="Hanh dong gan day"),
        _metric("Avg chunk count", round(_avg([doc.chunk_count for doc in documents]), 2)),
        _metric("Distinct embedding", len({doc.embedding_model for doc in documents if doc.embedding_model})),
    ]

    charts = {
        "request_volume": _count_series(logs, lambda item: item.created_at),
        "error_volume": _count_series(error_logs, lambda item: item.created_at),
        "latency_trend": _average_series(logs, lambda item: item.created_at, lambda item: item.response_time),
        "user_growth": _count_series(users, lambda item: item.created_at),
        "endpoint_distribution": _counter_to_points(Counter(log.endpoint for log in logs), top_k=8),
        "status_distribution": _counter_to_points(Counter(_status_bucket(log.status_code) for log in logs), top_k=5),
        "activity_distribution": _counter_to_points(Counter(activity.action for activity in activities), top_k=8),
        "inference_volume": _count_series(inference_logs, lambda item: item.created_at),
        "compression_trend": _average_series(
            inference_logs,
            lambda item: item.created_at,
            lambda item: item.compression_ratio,
        ),
        "stage_latency_breakdown": [
            {"label": "RAG", "value": round(_avg([log.rag_latency for log in inference_logs]), 3)},
            {"label": "Retrieve", "value": round(_avg([log.retrieval_latency for log in inference_logs]), 3)},
            {"label": "Generate", "value": round(_avg([log.generation_latency for log in inference_logs]), 3)},
        ],
        "backend_distribution": _counter_to_points(
            Counter(log.generation_backend or "unknown" for log in inference_logs),
            top_k=6,
        ),
        "device_distribution": _counter_to_points(
            Counter(log.model_device or "unknown" for log in inference_logs),
            top_k=4,
        ),
        "rating_distribution": _counter_to_points(
            Counter(f"{rating.rating} sao" for rating in ratings),
            top_k=5,
        ),
        "chunk_trend": _average_series(
            inference_logs,
            lambda item: item.created_at,
            lambda item: item.retrieved_chunk_count,
        ),
    }

    user_lookup = {str(user.id): user.email for user in users}
    endpoint_groups: dict[str, list[SystemLog]] = defaultdict(list)
    for log in logs:
        endpoint_groups[log.endpoint].append(log)

    tables = {
        "top_endpoints": [
            {
                "label": endpoint,
                "value": len(items),
                "secondary": f"{round(_avg([item.response_time for item in items]), 2)} ms avg",
                "status": _status_bucket(max(item.status_code for item in items)),
            }
            for endpoint, items in sorted(endpoint_groups.items(), key=lambda pair: len(pair[1]), reverse=True)[:8]
        ],
        "recent_errors": [
            {
                "label": log.endpoint,
                "value": log.status_code,
                "secondary": log.error_type or log.method,
                "tertiary": log.error_message or log.request_id,
                "created_at": log.created_at.isoformat(),
            }
            for log in error_logs[:12]
        ],
        "recent_inference": [
            {
                "label": log.model_name or log.generation_backend or "unknown",
                "value": round(log.latency or 0, 3),
                "secondary": f"compression={round(log.compression_ratio or 0, 4)}",
                "tertiary": log.model_device or "unknown",
                "created_at": log.created_at.isoformat(),
            }
            for log in inference_logs[:12]
        ],
        "activity_leaders": [
            {
                "label": user_lookup.get(user_id, user_id),
                "value": count,
                "secondary": "actions",
            }
            for user_id, count in Counter(str(activity.user_id) for activity in activities).most_common(8)
        ],
    }

    return {
        "overview": overview,
        "system_metrics": system_metrics,
        "model_metrics": model_metrics,
        "data_metrics": data_metrics,
        "charts": charts,
        "tables": tables,
    }


def _metric(label: str, value: str | int | float, unit: str | None = None, detail: str | None = None) -> dict[str, Any]:
    return {"label": label, "value": value, "unit": unit, "detail": detail}


def _avg(values: list[float | int | None]) -> float:
    cleaned = [float(value) for value in values if value is not None]
    if not cleaned:
        return 0.0
    return sum(cleaned) / len(cleaned)


def _ratio(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 0.0
    return numerator / denominator * 100


def _status_bucket(status_code: int) -> str:
    lead = int(status_code) // 100
    if lead in {2, 3, 4, 5}:
        return f"{lead}xx"
    return str(status_code)


def _counter_to_points(counter: Counter, top_k: int = 8) -> list[dict[str, Any]]:
    if not counter:
        return []
    return [{"label": label, "value": value} for label, value in counter.most_common(top_k)]


def _count_series(items: list[Any], date_getter, days: int = 7) -> list[dict[str, Any]]:
    slots = _date_slots(days)
    values = {slot: 0 for slot in slots}
    for item in items:
        item_date = date_getter(item)
        if item_date is None:
            continue
        normalized = item_date.date() if isinstance(item_date, datetime) else item_date
        if normalized in values:
            values[normalized] += 1
    return [{"label": slot.strftime("%d/%m"), "value": values[slot]} for slot in slots]


def _average_series(items: list[Any], date_getter, value_getter, days: int = 7) -> list[dict[str, Any]]:
    slots = _date_slots(days)
    grouped: dict[Any, list[float]] = {slot: [] for slot in slots}
    for item in items:
        item_date = date_getter(item)
        value = value_getter(item)
        if item_date is None or value is None:
            continue
        normalized = item_date.date() if isinstance(item_date, datetime) else item_date
        if normalized in grouped:
            grouped[normalized].append(float(value))
    return [
        {"label": slot.strftime("%d/%m"), "value": round(_avg(grouped[slot]), 3) if grouped[slot] else 0}
        for slot in slots
    ]


def _date_slots(days: int) -> list[Any]:
    today = datetime.utcnow().date()
    return [today - timedelta(days=offset) for offset in reversed(range(days))]
