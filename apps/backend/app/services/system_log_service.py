import json
from typing import Any

from app.core.database import SessionLocal
from app.models.system_log import SystemLog


def determine_log_level(status_code: int, error_message: str | None) -> str:
    if error_message or status_code >= 500:
        return "ERROR"
    if status_code >= 400:
        return "WARNING"
    return "INFO"


def serialize_log_details(details: dict[str, Any] | None) -> str | None:
    if not details:
        return None
    return json.dumps(details, ensure_ascii=False, default=str)


def safe_create_system_log(**payload: Any) -> None:
    session = SessionLocal()
    try:
        session.add(SystemLog(**payload))
        session.commit()
    except Exception:
        session.rollback()
    finally:
        session.close()
