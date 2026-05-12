import json
import os
import platform
from pathlib import Path
import pandas as pd
import torch
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from apps.backend.app.core.database import SessionLocal
from datetime import datetime, timezone as tz
class RetrainPipeline:
    def __init__(
        self,
        feature_store_path: str = "./data/features/feature_store.csv",
        processed_dataset_path: str = "./data/processed/summarization_corpus.jsonl",
        output_dir: str = "./ml/artifacts",
        qwen_model=None,
        data_pipeline=None,
        epochs: int = 3,
        min_text_words: int = 40,
        min_summary_words: int = 8,
    ) -> None:
        self.feature_store_path = Path(feature_store_path)
        self.processed_dataset_path = Path(processed_dataset_path)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.qwen_model = qwen_model
        self.data_pipeline = data_pipeline
        self.epochs = epochs
        self.min_text_words = min_text_words
        self.min_summary_words = min_summary_words

    def run(self) -> str:
        logs             = self._load_logs()
        feature_store    = self._load_feature_store()
        processed_dataset = self._load_processed_dataset()
        training_dataset = self._filter_training_dataset(processed_dataset)
        model_version = f"vit5-retrain-{datetime.now(tz.utc).strftime('%Y%m%d%H%M%S')}"
        target = self.output_dir / model_version
        target.mkdir(parents=True, exist_ok=True)
        self._save_snapshots(target, training_dataset, feature_store, logs)
        trained = False
        train_error = None
        if not training_dataset.empty and self.qwen_model and self.data_pipeline:
            try:
                self._run_kd_training(target, training_dataset)
                trained = True
            except Exception as e:
                train_error = str(e)
        self._write_metadata(
            target=target,
            model_version=model_version,
            training_dataset=training_dataset,
            feature_store=feature_store,
            logs=logs,
            trained=trained,
            train_error=train_error,
        )
        return model_version

    def _load_logs(self) -> pd.DataFrame:
        session = SessionLocal()
        try:
            query = text("""
                SELECT
                    input_length, summary_length,
                    compression_ratio, latency, created_at
                FROM inference_logs
                ORDER BY created_at DESC
            """)
            rows = session.execute(query).fetchall()
        except SQLAlchemyError:
            rows = []
        finally:
            session.close()
        return pd.DataFrame(rows, columns=[
            "input_length", "summary_length",
            "compression_ratio", "latency", "created_at",
        ])

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
        if "text_word_count" in filtered.columns:
            filtered = filtered[
                filtered["text_word_count"] >= self.min_text_words
            ]
        if "summary_word_count" in filtered.columns:
            filtered = filtered[
                filtered["summary_word_count"] >= self.min_summary_words
            ]
            filtered = filtered[
                filtered["summary_word_count"] < filtered["text_word_count"]
            ]
        return filtered.reset_index(drop=True)

    def _save_snapshots(
        self,
        target: Path,
        training_dataset: pd.DataFrame,
        feature_store: pd.DataFrame,
        logs: pd.DataFrame,
    ):
        if not training_dataset.empty:
            training_dataset.to_csv(target / "training_samples.csv", index=False)
        if not feature_store.empty:
            feature_store.to_csv(target / "feature_store_snapshot.csv", index=False)
        if not logs.empty:
            logs.to_csv(target / "inference_logs_snapshot.csv", index=False)

    def _run_kd_training(self, target: Path, training_dataset: pd.DataFrame):
        from ml.training.train import prepare_kd_dataset, train_kd
        kd_dataset_path = str(target / "kd_training_samples.jsonl")
        prepare_kd_dataset(
            corpus_path=str(self.processed_dataset_path),
            qwen_model=self.qwen_model,
            data_pipeline=self.data_pipeline,
            output_path=kd_dataset_path,
        )
        from ml.training.train import TrainingConfig
        train_kd(
            dataset_path=kd_dataset_path,
            output_dir=str(target / "model"),
            config=TrainingConfig(epochs=self.epochs),
        )

    def _write_metadata(
        self,
        target: Path,
        model_version: str,
        training_dataset: pd.DataFrame,
        feature_store: pd.DataFrame,
        logs: pd.DataFrame,
        trained: bool,
        train_error: str | None,
    ):
        metadata = {
            "model_version": model_version,
            "created_at": datetime.now(tz.utc).isoformat(),
            "training_rows": len(training_dataset),
            "feature_rows": len(feature_store),
            "log_rows": len(logs),
            "average_compression_ratio": (
                logs["compression_ratio"].mean() if not logs.empty else 0.0
            ),
            "average_latency": (
                logs["latency"].mean() if not logs.empty else 0.0
            ),
            "kd_training_ran": trained,
            "train_error": train_error,
            "epochs": self.epochs if trained else 0,
            "python_version": platform.python_version(),
            "platform": platform.platform(),
            "cuda_available": torch.cuda.is_available(),
            "gpu_count": torch.cuda.device_count(),
        }
        (target / "metadata.json").write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
