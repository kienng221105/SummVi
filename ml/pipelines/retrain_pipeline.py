import json
from app.core.timezone import get_now
from pathlib import Path

import pandas as pd
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.database import SessionLocal


class RetrainPipeline:
    def __init__(
        self,
        feature_store_path: str = "./data/features/feature_store.csv",
        processed_dataset_path: str = "./data/processed/summarization_corpus.jsonl",
        output_dir: str = "./ml/artifacts",
    ) -> None:
        self.feature_store_path = Path(feature_store_path)
        self.processed_dataset_path = Path(processed_dataset_path)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _load_logs(self) -> pd.DataFrame:
        session = SessionLocal()
        try:
            query = text(
                """
                SELECT input_length, summary_length, compression_ratio, latency, created_at
                FROM inference_logs
                ORDER BY created_at DESC
                """
            )
            rows = session.execute(query).fetchall()
        except SQLAlchemyError:
            rows = []
        finally:
            session.close()

        return pd.DataFrame(
            rows,
            columns=["input_length", "summary_length", "compression_ratio", "latency", "created_at"],
        )

    def _load_feature_store(self) -> pd.DataFrame:
        if not self.feature_store_path.exists():
            return pd.DataFrame()
        return pd.read_csv(self.feature_store_path)

    def _load_processed_dataset(self) -> pd.DataFrame:
        if not self.processed_dataset_path.exists():
            return pd.DataFrame()
        return pd.read_json(self.processed_dataset_path, lines=True)

    def _filter_training_dataset(self, dataset: pd.DataFrame) -> pd.DataFrame:
        if dataset.empty:
            return dataset

        filtered = dataset.copy()
        filtered = filtered[filtered["text_word_count"] >= 40]
        filtered = filtered[filtered["summary_word_count"] >= 8]
        filtered = filtered[filtered["summary_word_count"] < filtered["text_word_count"]]
        return filtered.reset_index(drop=True)

    def run(self) -> str:
        feature_store = self._load_feature_store()
        processed_dataset = self._load_processed_dataset()
        logs = self._load_logs()

        training_dataset = self._filter_training_dataset(processed_dataset)
        model_version = f"vit5-retrain-{get_now().strftime('%Y%m%d%H%M%S')}"
        target = self.output_dir / model_version
        target.mkdir(parents=True, exist_ok=True)

        if not training_dataset.empty:
            training_dataset.to_csv(target / "training_samples.csv", index=False)
        if not feature_store.empty:
            feature_store.to_csv(target / "feature_store_snapshot.csv", index=False)
        if not logs.empty:
            logs.to_csv(target / "inference_logs_snapshot.csv", index=False)

        retrain_report = {
            "model_version": model_version,
            "created_at": get_now().isoformat(),
            "training_rows": int(len(training_dataset)),
            "feature_rows": int(len(feature_store)),
            "log_rows": int(len(logs)),
            "average_compression_ratio": float(logs["compression_ratio"].mean()) if not logs.empty else 0.0,
            "average_latency": float(logs["latency"].mean()) if not logs.empty else 0.0,
        }
        (target / "metadata.json").write_text(
            json.dumps(retrain_report, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return model_version
