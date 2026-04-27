"""
Google Sheets sync service.

Appends analytics rows to a configured Google Sheet after each summarisation.
Uses a service-account JSON key file pointed to by the GSHEET_CREDENTIALS_FILE
environment variable.

Required env vars:
  GSHEET_CREDENTIALS_FILE  – path to the service-account JSON key
  GSHEET_SPREADSHEET_ID    – the spreadsheet ID from the Google Sheet URL
  GSHEET_WORKSHEET_NAME    – (optional) worksheet/tab name, defaults to "Analytics"
"""

import logging
import os
from datetime import datetime
from typing import List

logger = logging.getLogger(__name__)

# Lazy-loaded client (one per process)
_sheet_client = None


def _get_worksheet():
    """
    Lazy-load và cache Google Sheets worksheet.

    Logic:
    - Kiểm tra env vars: GSHEET_CREDENTIALS_FILE, GSHEET_SPREADSHEET_ID
    - Nếu không config: return None (sync disabled)
    - Nếu đã init: return cached worksheet
    - Nếu chưa init: authenticate với service account và cache worksheet

    Auto-create worksheet nếu chưa tồn tại và thêm header row.

    Returns:
        Worksheet object hoặc None nếu không config
    """
    global _sheet_client

    creds_file = os.getenv("GSHEET_CREDENTIALS_FILE", "")
    spreadsheet_id = os.getenv("GSHEET_SPREADSHEET_ID", "")

    if not creds_file or not spreadsheet_id or not os.path.isfile(creds_file):
        return None  # Google Sheets sync disabled (not configured or file missing)

    if _sheet_client is not None:
        return _sheet_client

    try:
        import gspread
        from google.oauth2.service_account import Credentials

        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]
        credentials = Credentials.from_service_account_file(creds_file, scopes=scopes)
        gc = gspread.authorize(credentials)

        spreadsheet = gc.open_by_key(spreadsheet_id)
        worksheet_name = os.getenv("GSHEET_WORKSHEET_NAME", "Analytics")

        try:
            worksheet = spreadsheet.worksheet(worksheet_name)
        except gspread.WorksheetNotFound:
            worksheet = spreadsheet.add_worksheet(
                title=worksheet_name, rows=1000, cols=10,
            )
            # Write header row
            worksheet.append_row(
                ["timestamp", "topic", "keywords", "summary_length", "compression_ratio"],
                value_input_option="RAW",
            )

        _sheet_client = worksheet
        logger.info("Google Sheets sync enabled → spreadsheet %s", spreadsheet_id)
        return _sheet_client

    except Exception as exc:
        logger.warning("Google Sheets init failed (sync disabled): %s", exc)
        return None


def append_analytics_row(
    topic: str,
    keywords: List[str],
    summary_length: int,
    compression_ratio: float,
) -> bool:
    """
    Append một row analytics vào Google Sheets.

    Use case: Real-time BI sync - mỗi lần tạo summary sẽ append vào sheet
    để stakeholders có thể xem analytics trực tiếp trên Google Sheets.

    Returns:
        True nếu sync thành công, False nếu disabled hoặc lỗi
    """
    worksheet = _get_worksheet()
    if worksheet is None:
        return False

    try:
        row = [
            datetime.now().isoformat(timespec="seconds"),
            topic,
            ", ".join(keywords),
            summary_length,
            round(compression_ratio, 4),
        ]
        worksheet.append_row(row, value_input_option="RAW")
        return True
    except Exception as exc:
        logger.warning("Google Sheets append failed: %s", exc)
        return False
