"""
Timezone Migration Script — UTC+0 → UTC+7 (Vietnam)
====================================================
Cập nhật tất cả timestamps đã lưu ở UTC+0 sang UTC+7
bằng cách cộng thêm 7 giờ vào mỗi cột datetime.

Cách chạy:
  # Xem trước (không thay đổi gì):
  python scripts/migrate_timezone.py --dry-run

  # Thực thi migration:
  python scripts/migrate_timezone.py

  # Với DATABASE_URL tùy chỉnh:
  DATABASE_URL=postgresql+psycopg2://user:pass@host:5432/db python scripts/migrate_timezone.py
"""

import os
import sys
from pathlib import Path

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "apps" / "backend"))

from sqlalchemy import text
from app.core.database import engine


# All tables and their timestamp columns that were stored in UTC+0
MIGRATIONS = [
    ("users",           ["created_at"]),
    ("conversations",   ["created_at", "updated_at"]),
    ("messages",        ["created_at"]),
    ("documents",       ["created_at"]),
    ("ratings",         ["created_at"]),
    ("system_logs",     ["created_at"]),
    ("user_activities", ["created_at"]),
    ("inference_logs",  ["created_at"]),
]

OFFSET_HOURS = 7


def run_migration(dry_run: bool = False):
    with engine.connect() as conn:
        for table, columns in MIGRATIONS:
            # Check if table exists
            result = conn.execute(
                text(
                    "SELECT EXISTS ("
                    "  SELECT 1 FROM information_schema.tables"
                    "  WHERE table_name = :table_name"
                    ")"
                ),
                {"table_name": table},
            )
            if not result.scalar():
                print(f"  ⏭ Bảng '{table}' không tồn tại, bỏ qua.")
                continue

            for col in columns:
                # Count affected rows
                count_result = conn.execute(
                    text(f"SELECT COUNT(*) FROM {table} WHERE {col} IS NOT NULL")
                )
                row_count = count_result.scalar()

                if row_count == 0:
                    print(f"  ⏭ {table}.{col} — không có dữ liệu.")
                    continue

                sql = f"UPDATE {table} SET {col} = {col} + INTERVAL '{OFFSET_HOURS} hours' WHERE {col} IS NOT NULL"

                if dry_run:
                    print(f"  🔍 [DRY-RUN] {table}.{col} — {row_count} dòng sẽ được cập nhật")
                    print(f"     SQL: {sql}")
                else:
                    conn.execute(text(sql))
                    print(f"  ✅ {table}.{col} — đã cập nhật {row_count} dòng (+{OFFSET_HOURS}h)")

        if not dry_run:
            conn.commit()
            print("\n🎉 Migration hoàn tất! Tất cả timestamps đã được chuyển sang UTC+7.")
        else:
            print("\n📋 Dry-run hoàn tất. Không có thay đổi nào được thực hiện.")
            print("   Chạy lại không có --dry-run để thực thi migration.")


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    mode = "DRY-RUN" if dry_run else "THỰC THI"
    print(f"\n{'='*60}")
    print(f"  Timezone Migration: UTC+0 → UTC+7 [{mode}]")
    print(f"  Database: {engine.url}")
    print(f"{'='*60}\n")

    if not dry_run:
        print("⚠️  CẢNH BÁO: Script này sẽ thay đổi dữ liệu trong database!")
        print("   Hãy chắc rằng bạn đã backup dữ liệu trước khi chạy.")
        confirm = input("   Nhập 'YES' để tiếp tục: ")
        if confirm.strip() != "YES":
            print("   Đã hủy.")
            sys.exit(0)
        print()

    run_migration(dry_run=dry_run)
