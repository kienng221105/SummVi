"""
Service layer for the BI Analytics module.
Handles writing analytics records and querying aggregated data.
"""

from collections import Counter
from typing import Dict, List

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db_session
from app.models.analytics import Analytics
from app.utils.analytics_utils import (
    assign_topic,
    extract_keywords,
    keywords_from_json,
    keywords_to_json,
)


# ── Write ──────────────────────────────────────────────────────────────────

def record_analytics(
    summary: str,
    input_text: str,
) -> None:
    """
    Trích xuất và lưu analytics từ một lần tóm tắt hoàn thành.

    Flow:
    1. Extract keywords từ summary (top 10 từ phổ biến nhất)
    2. Assign topic dựa trên keyword matching
    3. Tính compression ratio
    4. Persist vào database
    5. Sync sang Google Sheets nếu được config

    Called at the end of summarization pipeline.
    Silent fail - không crash nếu analytics lỗi.
    """
    import logging
    logger = logging.getLogger(__name__)

    summary_length = len(summary)
    input_length = len(input_text) if input_text else 1
    compression_ratio = summary_length / input_length if input_length else 0.0

    keywords = extract_keywords(summary, top_k=10)
    topic = assign_topic(summary)

    # ── DB persist ─────────────────────────────────────────────────
    session = get_db_session()
    try:
        record = Analytics(
            topic=topic,
            keywords=keywords_to_json(keywords),
            summary_length=summary_length,
            compression_ratio=compression_ratio,
        )
        session.add(record)
        session.commit()
        logger.info("Analytics saved to DB: topic=%s, keywords=%d", topic, len(keywords))
    except Exception as exc:
        session.rollback()
        logger.warning("Analytics DB save failed: %s", exc)
    finally:
        session.close()

    # ── Google Sheets sync ─────────────────────────────────────────
    try:
        from app.services.gsheets_service import append_analytics_row

        ok = append_analytics_row(
            topic=topic,
            keywords=keywords,
            summary_length=summary_length,
            compression_ratio=compression_ratio,
        )
        if ok:
            logger.info("Analytics synced to Google Sheets")
        else:
            logger.info("Google Sheets sync skipped (not configured)")
    except Exception as exc:
        logger.warning("Google Sheets sync failed: %s", exc)


# ── Read (aggregations for the dashboard) ──────────────────────────────────

def get_topic_distribution(db: Session) -> Dict[str, int]:
    """
    Trả về phân bố topics: {topic_name: count}.
    Dùng cho pie chart hoặc bar chart trong dashboard.
    """
    rows = (
        db.query(Analytics.topic, func.count(Analytics.id))
        .group_by(Analytics.topic)
        .all()
    )
    return {topic: count for topic, count in rows}


def get_top_keywords(db: Session, limit: int = 20) -> List[Dict]:
    """
    Aggregate keyword frequencies across tất cả analytics rows.

    Logic:
    - Load tất cả keywords từ DB
    - Deserialize JSON và count frequency
    - Trả về top N keywords phổ biến nhất

    Dùng cho word cloud hoặc keyword trends chart.
    """
    rows = db.query(Analytics.keywords).all()
    counter: Counter = Counter()
    for (raw,) in rows:
        for kw in keywords_from_json(raw):
            counter[kw] += 1
    return [{"keyword": kw, "count": c} for kw, c in counter.most_common(limit)]


def get_keyword_trends(db: Session, limit: int = 30) -> List[Dict]:
    """
    Trả về keyword counts grouped by date (last N days).

    Output format: [{date, keyword, count}, ...]
    Dùng cho time series chart showing keyword trends over time.
    """
    rows = (
        db.query(
            func.date(Analytics.created_at).label("day"),
            Analytics.keywords,
        )
        .order_by(func.date(Analytics.created_at).desc())
        .all()
    )

    # aggregate per (day, keyword)
    agg: Dict[tuple, int] = {}
    seen_days: set = set()
    for day, raw in rows:
        day_str = str(day)
        seen_days.add(day_str)
        if len(seen_days) > limit:
            break
        for kw in keywords_from_json(raw):
            key = (day_str, kw)
            agg[key] = agg.get(key, 0) + 1

    return [
        {"date": d, "keyword": kw, "count": c}
        for (d, kw), c in sorted(agg.items())
    ]


def get_summary_stats(db: Session) -> Dict:
    """
    Trả về aggregate statistics về summaries.

    Metrics:
    - total_summaries: tổng số lần tóm tắt
    - avg_summary_length: độ dài trung bình của summary
    - avg_compression_ratio: tỷ lệ nén trung bình
    - min/max_summary_length: độ dài ngắn nhất/dài nhất

    Dùng cho overview metrics trong dashboard.
    """
    row = db.query(
        func.count(Analytics.id),
        func.avg(Analytics.summary_length),
        func.avg(Analytics.compression_ratio),
        func.min(Analytics.summary_length),
        func.max(Analytics.summary_length),
    ).first()

    total, avg_len, avg_ratio, min_len, max_len = row  # type: ignore[misc]
    return {
        "total_summaries": total or 0,
        "avg_summary_length": round(float(avg_len or 0), 2),
        "avg_compression_ratio": round(float(avg_ratio or 0), 4),
        "min_summary_length": min_len or 0,
        "max_summary_length": max_len or 0,
    }
