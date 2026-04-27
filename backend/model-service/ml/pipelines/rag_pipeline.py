import os
import time
import uuid
from typing import List

import chromadb
from chromadb.config import Settings as ChromaSettings

from ml.models.embedding_model import EmbeddingModel
from ml.models.vit5_model import ViT5Model
from ml.utils.text_utils import clean_text, recursive_chunk_text


def _cosine_top_k(chunk_embeddings: List[List[float]], query_embedding: List[float], k: int) -> List[int]:
    """Return indices of the top-k most similar chunks using cosine similarity (pure Python, no numpy)."""
    q_norm = sum(v * v for v in query_embedding) ** 0.5 or 1e-9
    scores: list[tuple[float, int]] = []
    for idx, emb in enumerate(chunk_embeddings):
        dot = sum(a * b for a, b in zip(emb, query_embedding))
        c_norm = sum(v * v for v in emb) ** 0.5 or 1e-9
        scores.append((dot / (c_norm * q_norm), idx))
    scores.sort(key=lambda x: x[0], reverse=True)
    return [idx for _, idx in scores[:k]]


class RAGPipeline:
    def __init__(
        self,
        model: ViT5Model,
        embedding_model: EmbeddingModel,
        persist_dir: str | None = None,
        collection_name: str = "summarization_chunks",
        top_k: int = 4,
        chunk_size: int = 160,
        chunk_overlap: int = 32,
    ) -> None:
        self.model = model
        self.embedding_model = embedding_model
        self.persist_dir = persist_dir or os.getenv("CHROMA_PERSIST_DIR", "./chroma_data")
        self.collection_name = collection_name
        self.top_k = top_k
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        os.makedirs(self.persist_dir, exist_ok=True)

        self.client = self._build_client()
        self.collection = self.client.get_or_create_collection(name=self.collection_name)

    def _build_client(self):
        """
        Khởi tạo ChromaDB client - ưu tiên HTTP client nếu có config, fallback về PersistentClient.

        Logic:
        - Nếu có CHROMA_HTTP_HOST: tạo HTTP client để kết nối remote ChromaDB server
        - Nếu không: tạo PersistentClient lưu local vào persist_dir
        """
        http_host = os.getenv("CHROMA_HTTP_HOST")
        if http_host:
            http_port = int(os.getenv("CHROMA_HTTP_PORT", "8000"))
            http_ssl = os.getenv("CHROMA_HTTP_SSL", "false").lower() in {"1", "true", "yes", "on"}
            http_tenant = os.getenv("CHROMA_TENANT", "default_tenant")
            http_database = os.getenv("CHROMA_DATABASE", "default_database")
            try:
                return chromadb.HttpClient(
                    host=http_host,
                    port=http_port,
                    ssl=http_ssl,
                    settings=ChromaSettings(allow_reset=True),
                    tenant=http_tenant,
                    database=http_database,
                )
            except Exception:
                pass

        return chromadb.PersistentClient(
            path=self.persist_dir,
            settings=ChromaSettings(is_persistent=True, persist_directory=self.persist_dir),
            tenant=os.getenv("CHROMA_TENANT", "default_tenant"),
            database=os.getenv("CHROMA_DATABASE", "default_database"),
        )

    def _clean_text(self, text: str) -> str:
        return clean_text(text)

    def _chunk_text(self, text: str, chunk_size: int = 256, overlap: int = 48) -> List[str]:
        return recursive_chunk_text(text, chunk_size=chunk_size, overlap=overlap)

    def _store_chunks(self, request_id: str, chunks: List[str], embeddings: List[List[float]]) -> None:
        ids = [str(uuid.uuid4()) for _ in chunks]
        metadatas = [{"request_id": request_id, "chunk_index": index} for index, _ in enumerate(chunks)]
        self.collection.upsert(documents=chunks, embeddings=embeddings, ids=ids, metadatas=metadatas)

    def _retrieve_chunks(
        self,
        request_id: str,
        query_embedding: List[float],
        fallback_chunks: List[str],
    ) -> List[str]:
        """
        Truy vấn vector database để lấy các chunk liên quan nhất dựa trên similarity.

        Args:
            request_id: ID để filter chunks của request hiện tại
            query_embedding: Vector embedding của query (toàn bộ văn bản gốc)
            fallback_chunks: Danh sách chunks dự phòng nếu query thất bại

        Returns:
            Top-k chunks có độ tương đồng cao nhất với query
        """
        try:
            result = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=min(self.top_k, max(1, len(fallback_chunks))),
                where={"request_id": request_id},
            )
            documents = result.get("documents", [[]])[0]
            if documents:
                return [document for document in documents if document]
        except Exception:
            pass

        return fallback_chunks[: self.top_k]

    def _build_context(self, chunks: List[str], full_text: str) -> str:
        context = " ".join(chunk.strip() for chunk in chunks if chunk.strip()).strip()
        return context or full_text

    def run(self, text: str) -> str:
        return self.run_with_diagnostics(text)["summary"]

    def _base_diagnostics(self) -> dict:
        """Diagnostics chung cho mọi code path."""
        d: dict = {
            "rag_top_k": self.top_k,
            "chunk_size": self.chunk_size,
            "chunk_overlap": self.chunk_overlap,
        }
        d.update(self.model.diagnostics())
        d.update(self.embedding_model.diagnostics())
        return d

    def run_with_diagnostics(
        self,
        text: str,
        summary_length: str = "medium",
        output_format: str = "paragraph",
    ) -> dict:
        """
        Chạy RAG pipeline với đầy đủ diagnostics để tracking performance.

        Quy trình tối ưu:
        - Văn bản ngắn (≤1 chunk): đưa thẳng vào model, bỏ qua RAG
        - Văn bản dài: embed chunks → in-memory cosine similarity → top-k → model
        - Không dùng ChromaDB cho per-request chunks (tiết kiệm I/O)
        """
        cleaned_text = self._clean_text(text)
        chunks = self._chunk_text(cleaned_text, chunk_size=self.chunk_size, overlap=self.chunk_overlap)

        # Empty text
        if not chunks:
            diagnostics = {
                "summary": "", "chunk_count": 0, "retrieved_chunk_count": 0,
                "context_char_length": 0, "retrieval_latency": 0.0,
                "generation_latency": 0.0, "rag_latency": 0.0,
            }
            diagnostics.update(self._base_diagnostics())
            return diagnostics

        # ── Fast path: short text (single chunk) → skip RAG overhead ──
        if len(chunks) <= 1:
            gen_start = time.perf_counter()
            summary = self.model.summarize_with_options(
                cleaned_text, summary_length=summary_length, output_format=output_format,
            )
            gen_latency = time.perf_counter() - gen_start
            diagnostics = {
                "summary": summary, "chunk_count": 1, "retrieved_chunk_count": 0,
                "context_char_length": len(cleaned_text),
                "retrieval_latency": 0.0, "generation_latency": gen_latency,
                "rag_latency": gen_latency,
            }
            diagnostics.update(self._base_diagnostics())
            return diagnostics

        # ── Normal path: in-memory similarity (no ChromaDB I/O) ──
        rag_start = time.perf_counter()
        embeddings = self.embedding_model.embed(chunks)

        retrieval_start = time.perf_counter()
        query_embedding = self.embedding_model.embed([cleaned_text])[0]
        top_indices = _cosine_top_k(embeddings, query_embedding, self.top_k)
        relevant_chunks = [chunks[i] for i in top_indices]
        retrieval_latency = time.perf_counter() - retrieval_start

        context = self._build_context(relevant_chunks, cleaned_text)
        generation_start = time.perf_counter()
        summary = self.model.summarize_with_options(
            context, summary_length=summary_length, output_format=output_format,
        )
        generation_latency = time.perf_counter() - generation_start
        rag_latency = time.perf_counter() - rag_start

        diagnostics = {
            "summary": summary,
            "chunk_count": len(chunks),
            "retrieved_chunk_count": len(relevant_chunks),
            "context_char_length": len(context),
            "retrieval_latency": retrieval_latency,
            "generation_latency": generation_latency,
            "rag_latency": rag_latency,
        }
        diagnostics.update(self._base_diagnostics())
        return diagnostics
