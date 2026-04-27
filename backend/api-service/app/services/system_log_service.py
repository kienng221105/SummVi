import json
from typing import Any

from app.core.database import SessionLocal
from app.models.system_log import SystemLog


def determine_log_level(status_code: int, error_message: str | None) -> str:
    """
    Xác định log level dựa trên status code và error message.

    Logic:
    - ERROR: status >= 500 hoặc có error message
    - WARNING: status >= 400 (client errors)
    - INFO: các trường hợp còn lại (2xx, 3xx)
    """
    if error_message or status_code >= 500:
        return "ERROR"
    if status_code >= 400:
        return "WARNING"
    return "INFO"


def serialize_log_details(details: dict[str, Any] | None) -> str | None:
    """
    Serialize dict details thành JSON string để lưu vào database.
    default=str để handle các object không serialize được (datetime, UUID, etc.)
    """
    if not details:
        return None
    return json.dumps(details, ensure_ascii=False, default=str)


def safe_create_system_log(**payload: Any) -> None:
    """
    Tạo system log một cách an toàn (không crash nếu lỗi).

    Pattern:
    - Tạo session riêng cho mỗi log write
    - Rollback nếu có lỗi
    - Always close session để tránh leak

    Logging không được làm crash application flow.
    """
    session = SessionLocal()
    try:
        session.add(SystemLog(**payload))
        session.commit()
    except Exception:
        session.rollback()
    finally:
        session.close()
