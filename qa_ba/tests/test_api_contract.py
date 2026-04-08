import os
import sys
import unittest
from pathlib import Path

os.environ.setdefault("SQLITE_PATH", "./data/test_summarization.db")
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "apps" / "backend"))

from app.schemas.summarize import SummarizeRequest, SummarizeResponse
from app.api.routes import summarize as summarize_route


class StubSummarizationService:
    def summarize(self, text: str) -> SummarizeResponse:
        return SummarizeResponse(
            summary=text[:32],
            metrics={"length_ratio": 0.4, "compression_ratio": 0.6},
        )


class ApiContractTestCase(unittest.TestCase):
    def setUp(self) -> None:
        summarize_route.get_service.cache_clear()
        self.original_factory = summarize_route.get_service
        summarize_route.get_service = lambda: StubSummarizationService()

    def tearDown(self) -> None:
        summarize_route.get_service = self.original_factory

    def test_summarize_contract(self):
        payload = summarize_route.summarize(
            SummarizeRequest(
                text=(
                    "Thành phố Hà Nội thử nghiệm làn đường ưu tiên cho xe buýt điện tại một số tuyến chính. "
                    "Dự án giúp tăng độ đúng giờ, giảm ùn tắc và khuyến khích người dân sử dụng giao thông công cộng."
                )
            )
        ).model_dump()

        self.assertIsInstance(payload["summary"], str)
        self.assertIn("length_ratio", payload["metrics"])
        self.assertIn("compression_ratio", payload["metrics"])


if __name__ == "__main__":
    unittest.main()
