import numpy as np
from dataclasses import dataclass, field
from ml.utils.bm25_store import BM25Store
from ml.utils.vector_store import VectorStore
from ml.models.embedding_model import EmbeddingModel
@dataclass
class RetrievedChunk:
    chunk: str
    doc_id: str
    bm25_rank: int | None
    dense_rank: int | None
    rrf_score: float
    rerank_score: float = 0.0

class HybridRetriever:
    RRF_K = 60
    def __init__(
        self,
        bm25_store: BM25Store,
        vector_store: VectorStore,
        embed_model: EmbeddingModel | None,
    ):
        self.bm25 = bm25_store
        self.vector = vector_store
        self.embed = embed_model

    def retrieve(
        self,
        query: str,
        top_k: int = 10,
        filter_doc_id: str | None = None,
    ) -> list[RetrievedChunk]:
        bm25_results = self.bm25.search(
            query=query,
            top_k=top_k,
            filter_doc_id=filter_doc_id,
        )
        dense_results = []
        if self.embed is not None:
            query_vec = self.embed.embed_query(query)
            dense_results = self.vector.search(
                query_embedding=query_vec,
                top_k=top_k,
                filter_doc_id=filter_doc_id,
            )
        fused = self._rrf_fusion(bm25_results, dense_results)
        return fused[:top_k]

    def _rrf_fusion(
        self,
        bm25_results: list[dict],
        dense_results: list[dict],
    ) -> list[RetrievedChunk]:
        bm25_ranks = {
            r["chunk"]: i + 1     
            for i, r in enumerate(bm25_results)
        }
        dense_ranks = {
            r["chunk"]: i + 1
            for i, r in enumerate(dense_results)
        }
        all_chunks = {}
        for r in bm25_results:
            all_chunks[r["chunk"]] = r["doc_id"]
        for r in dense_results:
            all_chunks[r["chunk"]] = r["doc_id"]
        fused = []
        for chunk_text, doc_id in all_chunks.items():
            bm25_rank = bm25_ranks.get(chunk_text)
            dense_rank = dense_ranks.get(chunk_text)
            rrf_score = 0.0
            if bm25_rank:
                rrf_score += 1 / (self.RRF_K + bm25_rank)
            if dense_rank:
                rrf_score += 1 / (self.RRF_K + dense_rank)
            fused.append(RetrievedChunk(
                chunk=chunk_text,
                doc_id=doc_id,
                bm25_rank=bm25_rank,
                dense_rank=dense_rank,
                rrf_score=rrf_score,
            ))
        fused.sort(key=lambda x: x.rrf_score, reverse=True)
        return fused
