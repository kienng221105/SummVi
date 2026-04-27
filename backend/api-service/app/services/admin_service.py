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

def _percentile(values: list[float], p: float) -> float:
    """
    Tính percentile của một danh sách giá trị.
    Ví dụ: p=95 sẽ trả về giá trị mà 95% các giá trị nhỏ hơn hoặc bằng nó.
    """
    cleaned = sorted([float(val) for val in values if val is not None])
    if not cleaned: return 0.0
    idx = int((p / 100.0) * len(cleaned))
    return cleaned[min(idx, len(cleaned) - 1)]



def get_logs(db: Session, limit: int = 200) -> list[SystemLog]:
    return db.query(SystemLog).order_by(SystemLog.created_at.desc()).limit(limit).all()


def get_admin_analytics(db: Session) -> dict[str, Any]:
    """
    Tổng hợp toàn bộ analytics data cho admin dashboard.

    Chức năng:
    - Thu thập data từ nhiều bảng: users, logs, inference_logs, activities, ratings, documents, conversations
    - Tính toán metrics tổng hợp: success rate, latency percentiles, compression ratio, retention rate
    - Tạo charts: time series (request volume, latency trend), distributions (endpoints, status codes)
    - Tạo tables: top endpoints, recent errors, activity leaders, ratings detail

    Returns:
        dict với các section: overview, system_metrics, model_metrics, data_metrics, charts, tables
    """
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
        _metric("Tổng người dùng", total_users, detail=f"{active_users} hoạt động / {admin_users} quản trị"),
        _metric("K. Khách (WAU)", len({act.user_id for act in activities}), detail="Khách truy cập gần đây"),
        _metric("Hội thoại", len(conversations), detail=f"{len(messages)} tin nhắn"),
        _metric("Tài liệu", len(documents), detail=f"{sum(doc.chunk_count or 0 for doc in documents)} chunks trích xuất"),
        _metric("Yêu cầu (Requests)", total_logs, detail=f"{len(error_logs)} lỗi gần đây"),
    ]

    system_metrics = [
        _metric("Tỷ lệ thành công", round(success_rate, 2), unit="%"),
        _metric("Độ trễ trung bình", round(_avg([log.response_time for log in logs]), 2), unit="ms"),
        _metric("Nhật ký lỗi", len(error_logs), detail="HTTP >= 400"),
        _metric("Điểm cuối (Endpoints)", len({log.endpoint for log in logs}), detail="Từ nhật ký hệ thống"),
    ]

    latencies = [log.latency for log in inference_logs if log.latency]
    model_metrics = [
        _metric("Yêu cầu Inference", len(inference_logs), detail="Số lần gọi model AI"),
        _metric("Độ trễ trung bình", round(_avg(latencies), 3), unit="s"),
        _metric("Độ trễ (p50)", round(_percentile(latencies, 50), 3), unit="s"),
        _metric("Độ trễ (p95)", round(_percentile(latencies, 95), 3), unit="s"),
        _metric("Độ trễ (p99)", round(_percentile(latencies, 99), 3), unit="s"),
        _metric("Tỷ lệ Fallback", round(_ratio(sum(1 for log in inference_logs if log.used_model_fallback), len(inference_logs)), 2), unit="%"),
        _metric("Tỷ lệ nén trung bình", round(_avg([log.compression_ratio for log in inference_logs]), 4)),
        _metric("Token trung bình ước tính", int(_avg([log.input_word_count for log in inference_logs]) * 1.3), detail="Input tokens"),
    ]

    avg_rating = _avg([rating.rating for rating in ratings])
    input_lens = [log.input_word_count for log in inference_logs if log.input_word_count]
    data_metrics = [
        _metric("Số từ đầu vào avg", round(_avg(input_lens), 2)),
        _metric("Đầu vào Max", max(input_lens) if input_lens else 0, detail="từ (word count)"),
        _metric("Đầu vào Min", min(input_lens) if input_lens else 0, detail="từ (word count)"),
        _metric("Số từ tóm tắt avg", round(_avg([log.summary_word_count for log in inference_logs]), 2)),
        _metric("Đánh giá trung bình", round(avg_rating, 2), detail=f"{len(ratings)} phản hồi"),
        _metric("Hoạt động người dùng", len(activities), detail="Hành động ghi nhận"),
        _metric("Số chunk trung bình", round(_avg([doc.chunk_count for doc in documents]), 2)),
        _metric("Model Embedding", len({doc.embedding_model for doc in documents if doc.embedding_model})),
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
            {"label": "Truy vấn", "value": round(_avg([log.retrieval_latency for log in inference_logs]), 3)},
            {"label": "Sinh văn bản", "value": round(_avg([log.generation_latency for log in inference_logs]), 3)},
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
        "length_histogram": _build_histogram([log.input_word_count for log in inference_logs]),
        "hourly_volume": _hourly_series(logs, lambda item: item.created_at, hours=24),
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
            for endpoint, items in sorted(endpoint_groups.items(), key=lambda pair: len(pair[1]), reverse=True)[:20]
        ],
        "recent_errors": [
            {
                "label": log.endpoint,
                "value": log.status_code,
                "secondary": log.error_type or log.method,
                "tertiary": log.error_message or log.request_id,
                "created_at": log.created_at.isoformat(),
            }
            for log in error_logs[:20]
        ],
        "recent_inference": [
            {
                "label": log.model_name or log.generation_backend or "unknown",
                "value": round(log.latency or 0, 3),
                "secondary": f"compression={round(log.compression_ratio or 0, 4)}",
                "tertiary": log.model_device or "unknown",
                "created_at": log.created_at.isoformat(),
            }
            for log in inference_logs[:20]
        ],
        "activity_leaders": [
            {
                "label": user_lookup.get(user_id, user_id),
                "value": count,
                "secondary": "hành động",
            }
            for user_id, count in Counter(str(activity.user_id) for activity in activities).most_common(20)
        ],
        "ratings_detail": [
            {
                "email": user_lookup.get(str(r.user_id), str(r.user_id)),
                "rating": r.rating,
                "feedback": r.feedback or "--",
                "created_at": r.created_at.isoformat() if r.created_at else "--",
            }
            for r in sorted(ratings, key=lambda x: x.created_at or datetime.min, reverse=True)[:20]
        ],
        "top_inputs": _top_inputs(messages),
        "retention": _retention_table(activities),
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


from app.core.timezone import get_now


def _date_slots(days: int) -> list[Any]:
    today = get_now().date()
    return [today - timedelta(days=offset) for offset in reversed(range(days))]

def _build_histogram(values: list[int | None]) -> list[dict[str, Any]]:
    buckets = [
        {"label": "0-200", "min": 0, "max": 200, "value": 0},
        {"label": "200-500", "min": 200, "max": 500, "value": 0},
        {"label": "500-1000", "min": 500, "max": 1000, "value": 0},
        {"label": ">1000", "min": 1000, "max": float("inf"), "value": 0},
    ]
    for v in values:
        if v is None: continue
        for b in buckets:
            if b["min"] <= v < b["max"]:
                b["value"] += 1
                break
    return buckets

def _hourly_series(items: list[Any], date_getter, hours: int = 24) -> list[dict[str, Any]]:
    now = get_now()
    # Ensure comparison works by normalizing to naive datetime if database items are naive
    now_naive = now.replace(tzinfo=None)
    slots = [now - timedelta(hours=offset) for offset in reversed(range(hours))]
    values = {slot.strftime("%H:00"): 0 for slot in slots}
    for item in items:
        item_date = date_getter(item)
        if item_date is None:
            continue
        # Support both aware and naive comparison by normalizing to naive
        item_date_naive = item_date.replace(tzinfo=None) if item_date.tzinfo else item_date
        if item_date_naive < now_naive - timedelta(hours=hours):
            continue
        key = item_date.strftime("%H:00")
        if key in values:
            values[key] += 1
    return [{"label": k, "value": v} for k, v in values.items()]

def _retention_table(activities: list[Any]) -> list[dict[str, Any]]:
    """
    Tính retention rate: tỷ lệ user quay lại sau 1 ngày và 7 ngày.

    Logic:
    - Nhóm activities theo user_id và ngày
    - Tính số user active hôm nay, hôm qua, tuần trước
    - Retention = (users active cả 2 kỳ) / (users active kỳ trước) * 100%
    """
    now = get_now().date()
    yesterday = now - timedelta(days=1)
    last_week = now - timedelta(days=7)
    user_pool = {}
    for act in activities:
        uid = act.user_id
        d = act.created_at.date()
        if uid not in user_pool: user_pool[uid] = set()
        user_pool[uid].add(d)
    
    active_now = {u for u, days in user_pool.items() if now in days}
    active_yesterday = {u for u, days in user_pool.items() if yesterday in days}
    active_last_week = {u for u, days in user_pool.items() if last_week in days}
    
    ret_1d = (len(active_now.intersection(active_yesterday)) / len(active_yesterday) * 100) if active_yesterday else 0
    ret_7d = (len(active_now.intersection(active_last_week)) / len(active_last_week) * 100) if active_last_week else 0
    return [
        {"label": "Hôm qua (1d)", "value": round(ret_1d, 1), "secondary": "% trở lại", "tertiary": f"{len(active_yesterday)} user"},
        {"label": "Tuần trước (7d)", "value": round(ret_7d, 1), "secondary": "% trở lại", "tertiary": f"{len(active_last_week)} user"},
    ]

def _top_inputs(messages: list[Any], limit: int = 10) -> list[dict[str, Any]]:
    contents = [m.content for m in messages if m.is_user and m.content]
    counts = Counter(contents)
    return [
        {"label": (content[:40] + "...") if len(content) > 40 else content, "value": count, "secondary": "lượt", "tertiary": content}
        for content, count in counts.most_common(limit)
    ]
