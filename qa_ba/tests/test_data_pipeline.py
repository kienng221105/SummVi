from pathlib import Path
import unittest

from ml.pipelines.data_pipeline import DataPipeline


class DataPipelineTestCase(unittest.TestCase):
    def test_data_pipeline_generates_processed_and_feature_outputs(self):
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            raw_dir = tmp_path / "raw"
            processed_dir = tmp_path / "processed"
            features_dir = tmp_path / "features"
            metadata_dir = tmp_path / "metadata"
            raw_dir.mkdir(parents=True)

            sample_path = raw_dir / "samples.jsonl"
            sample_path.write_text(
                "\n".join(
                    [
                        '{"id":"1","source":"test","text":"Doanh nghiep tang toc chuyen doi so de nang cao nang suat va giam chi phi van hanh.","summary":"Doanh nghiep day manh chuyen doi so de tang nang suat."}',
                        '{"id":"2","source":"test","text":"Nganh giao duc bo sung hoc phan du lieu va AI ung dung vao chuong trinh dao tao dai hoc.","summary":"Chuong trinh dao tao bo sung hoc phan du lieu va AI."}'
                    ]
                ),
                encoding="utf-8",
            )

            report = DataPipeline(
                raw_dir=str(raw_dir),
                processed_dir=str(processed_dir),
                features_dir=str(features_dir),
                metadata_dir=str(metadata_dir),
            ).run()

            self.assertEqual(report["processed_records"], 2)
            self.assertTrue((processed_dir / "summarization_corpus.jsonl").exists())
            self.assertTrue((features_dir / "feature_store.csv").exists())
            self.assertTrue((metadata_dir / "dataset_manifest.json").exists())


if __name__ == "__main__":
    unittest.main()
