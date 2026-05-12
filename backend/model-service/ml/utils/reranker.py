import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from ml.utils.retriever import RetrievedChunk
class CrossEncoderReranker:
    MODEL_NAME = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    def __init__(self, device: str | None = None):
        self.device = device or (
            "cuda" if torch.cuda.is_available() else "cpu"
        )
        self.tokenizer = AutoTokenizer.from_pretrained(self.MODEL_NAME)
        self.model = AutoModelForSequenceClassification.from_pretrained(
            self.MODEL_NAME
        )
        self.model.eval()
        self.model.to(self.device)

    def rerank(
        self,
        query: str,
        candidates: list[RetrievedChunk],
        top_n: int = 5,
    ) -> list[RetrievedChunk]:
        if not candidates:
            return []
        scores = self._score_batch(
            query=query,
            chunks=[c.chunk for c in candidates],
        )
        for candidate, score in zip(candidates, scores):
            candidate.rerank_score = score
        reranked = sorted(
            candidates,
            key=lambda x: x.rerank_score,
            reverse=True,
        )
        return reranked[:top_n]

    def _score_batch(
        self,
        query: str,
        chunks: list[str],
        batch_size: int = 16,
    ) -> list[float]:
        all_scores = []
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i : i + batch_size]
            batch_scores = self._score_pairs(query, batch)
            all_scores.extend(batch_scores)
        return all_scores

    def _score_pairs(
        self,
        query: str,
        chunks: list[str],
    ) -> list[float]:
        pairs = [[query, chunk] for chunk in chunks]
        assert callable(self.tokenizer)
        encoded = self.tokenizer(
            pairs,
            padding=True,
            truncation=True,
            max_length=512,
            return_tensors="pt",
        ).to(self.device)
        with torch.no_grad():
            logits = self.model(**encoded).logits
        scores = logits.squeeze(-1).cpu().tolist()
        if isinstance(scores, float):
            scores = [scores]
        return scores
