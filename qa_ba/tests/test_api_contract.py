import os
import sys
import unittest
from pathlib import Path

# Ensure we use a test database or mock correctly
os.environ.setdefault("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/summarization_test")
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "apps" / "backend"))

from app.schemas.summarize import SummarizeRequest, SummarizeResponse
from app.api.routes import summarize as summarize_route


class StubSummarizationService:
    def summarize(
        self,
        text: str,
        summary_length: str = "medium",
        output_format: str = "paragraph",
    ) -> SummarizeResponse:
        return SummarizeResponse(
            summary=text[:32],
            metrics={"length_ratio": 0.4, "compression_ratio": 0.6},
        )


import asyncio

class ApiContractTestCase(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        summarize_route.get_service.cache_clear()
        self.original_factory = summarize_route.get_service
        summarize_route.get_service = lambda: StubSummarizationService()

    def tearDown(self) -> None:
        summarize_route.get_service = self.original_factory

    async def test_summarize_contract(self):
        coro = summarize_route.summarize(
            SummarizeRequest(
                text=(
                    "Thành phố Hà Nội thử nghiệm làn đường ưu tiên cho xe buýt điện tại một số tuyến chính. "
                    "Dự án giúp tăng độ đúng giờ, giảm ùn tắc và khuyến khích người dân sử dụng giao thông công cộng."
                )
            )
        )
        payload = (await coro).model_dump()

        self.assertIsInstance(payload["summary"], str)
        self.assertIn("length_ratio", payload["metrics"])
        self.assertIn("compression_ratio", payload["metrics"])


if __name__ == "__main__":
    unittest.main()
