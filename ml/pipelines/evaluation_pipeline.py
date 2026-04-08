from ml.utils.text_utils import safe_ratio


class EvaluationPipeline:
    def run(self, input_text: str, summary_text: str) -> dict[str, float]:
        input_len = max(1, len(input_text))
        length_ratio = safe_ratio(len(summary_text), input_len)
        compression_ratio = 1.0 - length_ratio
        return {
            "length_ratio": float(length_ratio),
            "compression_ratio": float(compression_ratio),
        }
