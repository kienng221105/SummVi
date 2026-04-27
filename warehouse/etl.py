import os
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine


def _build_database_uri() -> str:
    """
    Xây dựng URI kết nối database từ biến môi trường.
    Ưu tiên sử dụng DATABASE_URL nếu có, nếu không sẽ build từ các biến riêng lẻ.
    """
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return database_url

    if os.getenv("POSTGRES_HOST"):
        return (
            f"postgresql+psycopg2://{os.getenv('POSTGRES_USER', 'postgres')}:"
            f"{os.getenv('POSTGRES_PASSWORD', 'postgres')}@"
            f"{os.getenv('POSTGRES_HOST', 'localhost')}:"
            f"{os.getenv('POSTGRES_PORT', '5432')}/"
            f"{os.getenv('POSTGRES_DB', 'summarization')}"
        )

    raise RuntimeError("No PostgreSQL configuration found (DATABASE_URL or POSTGRES_HOST). ETL depends on PostgreSQL.")


def export_inference_logs(output_dir: str = "./warehouse/exports") -> dict:
    """
    Xuất dữ liệu inference logs từ database ra file CSV để phân tích.

    Chức năng:
    - Trích xuất toàn bộ logs từ bảng inference_logs
    - Tính toán các metrics tổng hợp theo ngày (avg latency, compression ratio, etc.)
    - Xuất ra 2 file CSV: logs chi tiết và metrics tổng hợp

    Returns:
        dict: Thông tin về số dòng đã xuất và đường dẫn file
    """
    db_uri = _build_database_uri()
    target_dir = Path(output_dir).resolve()
    target_dir.mkdir(parents=True, exist_ok=True)

    engine = create_engine(db_uri)
    # Query 1: Lấy toàn bộ logs chi tiết
    logs_query = "SELECT * FROM inference_logs ORDER BY created_at DESC"
    # Query 2: Tính metrics tổng hợp theo ngày (latency, compression, fallback count, etc.)
    metrics_query = """
        SELECT
            DATE(created_at) AS metric_date,
            COUNT(*) AS total_requests,
            AVG(input_length) AS avg_input_length,
            AVG(summary_length) AS avg_summary_length,
            AVG(input_word_count) AS avg_input_word_count,
            AVG(summary_word_count) AS avg_summary_word_count,
            AVG(length_ratio) AS avg_length_ratio,
            AVG(compression_ratio) AS avg_compression_ratio,
            AVG(latency) AS avg_latency,
            AVG(rag_latency) AS avg_rag_latency,
            AVG(retrieval_latency) AS avg_retrieval_latency,
            AVG(generation_latency) AS avg_generation_latency,
            AVG(chunk_count) AS avg_chunk_count,
            AVG(retrieved_chunk_count) AS avg_retrieved_chunk_count,
            SUM(CASE WHEN used_model_fallback = TRUE THEN 1 ELSE 0 END) AS fallback_requests
        FROM inference_logs
        GROUP BY DATE(created_at)
        ORDER BY metric_date DESC
    """

    logs_df = pd.read_sql(logs_query, engine)
    metrics_df = pd.read_sql(metrics_query, engine)

    logs_path = target_dir / "inference_logs.csv"
    metrics_path = target_dir / "daily_metrics.csv"
    logs_df.to_csv(logs_path, index=False)
    metrics_df.to_csv(metrics_path, index=False)

    return {
        "logs_rows": int(len(logs_df)),
        "metrics_rows": int(len(metrics_df)),
        "logs_path": str(logs_path),
        "metrics_path": str(metrics_path),
    }


if __name__ == "__main__":
    print(export_inference_logs())
