from ml.utils.text_utils import safe_ratio


class EvaluationPipeline:
    """
    Pipeline đánh giá chất lượng tóm tắt thông qua các metrics đơn giản.
    """

    def run(self, input_text: str, summary_text: str) -> dict[str, float]:
        """
        Tính toán metrics đánh giá tóm tắt.

        Metrics:
        - length_ratio: tỷ lệ độ dài summary/input (càng nhỏ càng ngắn gọn)
        - compression_ratio: tỷ lệ nén = 1 - length_ratio (càng cao càng nén nhiều)

        Ví dụ: input 1000 chars, summary 200 chars
        -> length_ratio = 0.2, compression_ratio = 0.8
        """
        input_len = max(1, len(input_text))
        length_ratio = safe_ratio(len(summary_text), input_len)
        compression_ratio = 1.0 - length_ratio
        return {
            "length_ratio": float(length_ratio),
            "compression_ratio": float(compression_ratio),
        }
