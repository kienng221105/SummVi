import json
from datetime import datetime
from pathlib import Path

import pandas as pd

from ml.utils.text_utils import clean_text, split_sentences


class DataPipeline:
    def __init__(
        self,
        raw_dir: str = "./data/raw",
        processed_dir: str = "./data/processed",
        features_dir: str = "./data/features",
        metadata_dir: str = "./data/metadata",
    ) -> None:
        self.raw_dir = Path(raw_dir)
        self.processed_dir = Path(processed_dir)
        self.features_dir = Path(features_dir)
        self.metadata_dir = Path(metadata_dir)

        for path in (self.raw_dir, self.processed_dir, self.features_dir, self.metadata_dir):
            path.mkdir(parents=True, exist_ok=True)

    def _bootstrap_dataset_if_empty(self) -> None:
        has_raw_files = any(path.is_file() and path.suffix in {".jsonl", ".csv", ".txt"} for path in self.raw_dir.rglob("*"))
        if has_raw_files:
            return

        bootstrap_dir = self.raw_dir / str(datetime.utcnow().year)
        bootstrap_dir.mkdir(parents=True, exist_ok=True)
        bootstrap_path = bootstrap_dir / "bootstrap_summarization_samples.jsonl"
        samples = [
            {
                "id": "sample-001",
                "source": "bootstrap",
                "text": "Thành phố Hà Nội triển khai kế hoạch mở rộng mạng lưới xe buýt điện nhằm giảm khí thải và ùn tắc giao thông. Dự án tập trung vào việc tăng số tuyến kết nối khu dân cư với trung tâm, nâng cấp bến chờ và áp dụng hệ thống theo dõi lịch trình thời gian thực cho người dân.",
                "summary": "Hà Nội mở rộng mạng lưới xe buýt điện để giảm ùn tắc và khí thải, đồng thời nâng cấp hạ tầng và hệ thống theo dõi lịch trình.",
            },
            {
                "id": "sample-002",
                "source": "bootstrap",
                "text": "Bộ Giáo dục và Đào tạo công bố chương trình tăng cường kỹ năng số cho sinh viên đại học. Chương trình bao gồm các học phần về phân tích dữ liệu, trí tuệ nhân tạo ứng dụng, an toàn thông tin và quản trị dự án công nghệ, triển khai theo mô hình kết hợp giữa doanh nghiệp và nhà trường.",
                "summary": "Chương trình kỹ năng số mới bổ sung học phần dữ liệu, AI, an toàn thông tin và phối hợp đào tạo với doanh nghiệp.",
            },
            {
                "id": "sample-003",
                "source": "bootstrap",
                "text": "Nhiều doanh nghiệp logistics Việt Nam đang đầu tư vào kho thông minh và hệ thống tối ưu tuyến đường để rút ngắn thời gian giao hàng. Việc đồng bộ dữ liệu đơn hàng, vị trí tài xế và năng lực kho bãi giúp giảm chi phí vận hành và nâng cao trải nghiệm khách hàng trong giai đoạn cao điểm.",
                "summary": "Doanh nghiệp logistics đầu tư kho thông minh và tối ưu tuyến đường để giảm chi phí vận hành và giao hàng nhanh hơn.",
            },
        ]
        with bootstrap_path.open("w", encoding="utf-8") as file:
            for sample in samples:
                file.write(json.dumps(sample, ensure_ascii=False) + "\n")

    def _read_jsonl(self, path: Path) -> list[dict]:
        records: list[dict] = []
        with path.open("r", encoding="utf-8") as file:
            for line in file:
                line = line.strip()
                if not line:
                    continue
                payload = json.loads(line)
                records.append(payload)
        return records

    def _read_csv(self, path: Path) -> list[dict]:
        dataframe = pd.read_csv(path)
        return dataframe.to_dict(orient="records")

    def _read_txt(self, path: Path) -> list[dict]:
        text = path.read_text(encoding="utf-8")
        return [
            {
                "id": path.stem,
                "source": path.name,
                "text": text,
                "summary": "",
            }
        ]

    def _load_raw_records(self) -> list[dict]:
        records: list[dict] = []
        for path in sorted(self.raw_dir.rglob("*")):
            if not path.is_file():
                continue
            if path.suffix == ".jsonl":
                records.extend(self._read_jsonl(path))
            elif path.suffix == ".csv":
                records.extend(self._read_csv(path))
            elif path.suffix == ".txt":
                records.extend(self._read_txt(path))
        return records

    def _build_processed_dataframe(self, records: list[dict]) -> pd.DataFrame:
        rows: list[dict] = []
        seen_texts: set[str] = set()

        for index, record in enumerate(records):
            text = clean_text(str(record.get("text", "")))
            summary = clean_text(str(record.get("summary", "")))
            if not text or text in seen_texts:
                continue

            seen_texts.add(text)
            summary = summary or " ".join(split_sentences(text)[:2]).strip()
            rows.append(
                {
                    "id": record.get("id", f"record-{index:04d}"),
                    "source": record.get("source", "unknown"),
                    "text": text,
                    "summary": summary,
                    "text_char_count": len(text),
                    "summary_char_count": len(summary),
                    "text_word_count": len(text.split()),
                    "summary_word_count": len(summary.split()),
                    "sentence_count": len(split_sentences(text)),
                    "processed_at": datetime.utcnow().isoformat(),
                }
            )

        return pd.DataFrame(rows)

    def _build_feature_store(self, processed_df: pd.DataFrame) -> pd.DataFrame:
        if processed_df.empty:
            return processed_df

        features = processed_df.copy()
        features["compression_ratio_target"] = 1.0 - (
            features["summary_char_count"] / features["text_char_count"].clip(lower=1)
        )
        features["avg_word_length"] = features["text"].apply(
            lambda value: round(sum(len(word) for word in value.split()) / max(1, len(value.split())), 4)
        )
        return features

    def run(self) -> dict:
        self._bootstrap_dataset_if_empty()
        raw_records = self._load_raw_records()
        processed_df = self._build_processed_dataframe(raw_records)
        feature_df = self._build_feature_store(processed_df)

        processed_path = self.processed_dir / "summarization_corpus.jsonl"
        feature_path = self.features_dir / "feature_store.csv"
        manifest_path = self.metadata_dir / "dataset_manifest.json"

        if not processed_df.empty:
            processed_df.to_json(processed_path, orient="records", lines=True, force_ascii=False)
            feature_df.to_csv(feature_path, index=False)

        report = {
            "raw_records": int(len(raw_records)),
            "processed_records": int(len(processed_df)),
            "feature_rows": int(len(feature_df)),
            "processed_path": str(processed_path.resolve()),
            "feature_store_path": str(feature_path.resolve()),
            "generated_at": datetime.utcnow().isoformat(),
        }
        manifest_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        return report


if __name__ == "__main__":
    print(json.dumps(DataPipeline().run(), ensure_ascii=False, indent=2))
