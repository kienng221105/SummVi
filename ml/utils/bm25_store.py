from dataclasses import dataclass, field
from rank_bm25 import BM25Okapi 
from underthesea import word_tokenize
import numpy as np
@dataclass
class BM25Store:
    corpus_tokens: list[list[str]] = field(default_factory=list)
    corpus_texts: list[str] = field(default_factory=list)
    corpus_doc_ids: list[str] = field(default_factory=list)
    bm25: BM25Okapi | None = field(init=False, default=None)
    def add(
        self,
        doc_id: str,
        chunks: list[str],
    ):
        for chunk in chunks:
            tokens = self._tokenize(chunk)
            self.corpus_tokens.append(tokens)
            self.corpus_texts.append(chunk)
            self.corpus_doc_ids.append(doc_id)
        self._rebuild()

    def search(
        self,
        query: str,
        top_k: int = 10,
        filter_doc_id: str | None = None,
    ) -> list[dict]:
        if self.bm25 is None or not self.corpus_texts:
            return []
        query_tokens = self._tokenize(query)
        scores = self.bm25.get_scores(query_tokens)
        indexed = [
            {
                "index": i,
                "doc_id": self.corpus_doc_ids[i],
                "chunk": self.corpus_texts[i],
                "score": float(scores[i]),
            }
            for i in range(len(self.corpus_texts))
        ]
        if filter_doc_id:
            indexed = [r for r in indexed if r["doc_id"] == filter_doc_id]
        indexed.sort(key=lambda x: x["score"], reverse=True)
        return indexed[:top_k]

    def delete_document(self, doc_id: str):
        keep = [
            i for i, d in enumerate(self.corpus_doc_ids)
            if d != doc_id
        ]
        self.corpus_tokens = [self.corpus_tokens[i] for i in keep]
        self.corpus_texts = [self.corpus_texts[i] for i in keep]
        self.corpus_doc_ids = [self.corpus_doc_ids[i] for i in keep]
        self._rebuild()

    def _tokenize(self, text: str) -> list[str]:
        segmented = word_tokenize(text, format="text")
        if isinstance(segmented, str):
            return segmented.split()
        return list(segmented)

    def _rebuild(self):
        if self.corpus_tokens:
            self.bm25 = BM25Okapi(self.corpus_tokens)
