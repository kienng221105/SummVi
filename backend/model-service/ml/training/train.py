import json

from ml.pipelines.data_pipeline import DataPipeline
from ml.pipelines.retrain_pipeline import RetrainPipeline


def main() -> None:
    data_report = DataPipeline().run()
    retrain_pipeline = RetrainPipeline()
    version = retrain_pipeline.run()
    print(json.dumps({"data_report": data_report, "model_version": version}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
