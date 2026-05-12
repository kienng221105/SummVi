from _typeshed import wsgi
import time
from dataclasses import dataclass, field
import torch
from ml.models.embedding_model import EmbeddingModel
from ml.models.vit5_model import ViT5Model
from ml.utils.bm25_store import BM25Store
from ml.utils.retriever import HybridRetriever, RetrievedChunk
from ml.utils.reranker import CrossEncoderReranker
from ml.utils.vector_store import VectorStore
import re
import logging
logger = logging.getLogger(__name__)
NEGATION_PATTERN = re.compile(
    r"\b(không|tránh|đừng|ngừng|cấm|chớ)\s+\w+(?:\s+\w+){0,3}",
    re.IGNORECASE,
)
@dataclass
class RAGResult:
    query: str
    retrieved_chunks: list[RetrievedChunk]
    context: str
    warnings: list[str] = field(default_factory=list)


class RAGPipeline:
    RETRIEVAL_TOP_K = 10
    RERANK_TOP_N = 5

    def __init__(
        self,
        bm25_store: BM25Store | None = None,
        vector_store: VectorStore | None = None,
        embed_model: EmbeddingModel | None = None,
        model: ViT5Model | None = None,
        embedding_model: EmbeddingModel | None = None,
        persist_dir: str | None = None,
        collection_name: str | None = None,
        top_k: int | None = None,
        chunk_size: int | None = None,
        chunk_overlap: int | None = None,
    ):
        self.model = model
        self.embed_model = embed_model or embedding_model
        self.bm25 = bm25_store or BM25Store()
        self.vector = vector_store or VectorStore(
            persist_dir=persist_dir or "data/vector_store",
            collection_name=collection_name or "documents",
        )
        self.retriever = HybridRetriever(
            bm25_store=self.bm25,
            vector_store=self.vector,
            embed_model=self.embed_model,
        )
        self.reranker = CrossEncoderReranker()
        self.top_k = top_k or self.RETRIEVAL_TOP_K
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def run(
        self,
        query: str,
        filter_doc_id: str | None = None,
    ) -> RAGResult:
        warnings = []
        candidates = self.retriever.retrieve(
            query=query,
            top_k=self.top_k,
            filter_doc_id=filter_doc_id,
        )
        if not candidates:
            warnings.append("No chunks retrieved for query")
            return RAGResult(
                query=query,
                retrieved_chunks=[],
                context="",
                warnings=warnings,
            )
        reranked = self.reranker.rerank(
            query=query,
            candidates=candidates,
            top_n=self.RERANK_TOP_N,
        )
        context, fit_warnings = self._build_context(reranked)
        warnings.extend(fit_warnings)
        return RAGResult(
            query=query,
            retrieved_chunks=reranked,
            context=context,
            warnings=warnings,
        )

    def run_with_diagnostics(
        self,
        query: str,
        summary_length: str = "medium",
        output_format: str = "paragraph",
        filter_doc_id: str | None = None,
    ) -> dict:
        if self.model is None:
            raise ValueError("RAGPipeline requires model=ViT5Model for run_with_diagnostics")
        rag_start = time.perf_counter()
        retrieval_start = time.perf_counter()
        rag_result = self.run(query=query, filter_doc_id=filter_doc_id)
        retrieval_latency = time.perf_counter() - retrieval_start
        generation_start = time.perf_counter()
        warnings = list(rag_result.warnings)
        if rag_result.context:
            context_tokens = self.model.count_tokens(rag_result.context)
            if context_tokens > self.model.config.max_input_tokens:
                warnings.append(
                    f"RAG context {context_tokens} tokens > "
                    f"{self.model.config.max_input_tokens}, may be truncated"
                )
            if context_tokens > self.model.config.max_input_tokens:
                summary = self._summarize_long_context(rag_result.context)
                result_warnings = []
            else:
                result = self.model.summarize(rag_result.context, max_new_tokens=256)
                summary = result.output_text
                result_warnings = result.warnings
            warnings.extend(result_warnings)
        else:
            summary = ""
        if summary and rag_result.context:
            summary, negation_warnings = self._apply_negation_guard(rag_result.context, summary)
            warnings.extend(negation_warnings)
            summary = self._filter_hallucinations(rag_result.context, summary)
        summary = self.model._trim_incomplete_sentence(summary)
        generation_latency = time.perf_counter() - generation_start
        rag_latency = time.perf_counter() - rag_start
        return {
            "summary": summary,
            "warnings": warnings,
            "rag_latency": rag_latency,
            "retrieval_latency": retrieval_latency,
            "generation_latency": generation_latency,
            "chunk_count": None,
            "retrieved_chunk_count": len(rag_result.retrieved_chunks),
            "context_char_length": len(rag_result.context),
            "model_name": getattr(self.model, "MODEL_NAME", None),
            "embedding_model_name": getattr(self.embed_model, "model_name", getattr(self.embed_model, "MODEL_NAME", None)),
            "model_device": getattr(self.model, "device", None),
            "generation_backend": "vit5",
            "embedding_backend": "phobert",
            "used_model_fallback": False,
            "model_load_error": None,
            "embedding_load_error": None,
            "rag_top_k": self.top_k,
            "chunk_size": self.chunk_size,
            "chunk_overlap": self.chunk_overlap,
            "cuda_available": torch.cuda.is_available(),
            "gpu_memory_mb": round(torch.cuda.get_device_properties(0).total_memory / (1024 * 1024), 2) if torch.cuda.is_available() else None,
        }

    def _extract_negation_sentences(self, text: str) -> list[str]:
        raw = re.split(r'(?<=[.!?])\s+|\n+', text)
        neg_sents = []
        for s in raw:
            s = s.strip()
            if not s:
                continue
            if not re.match(r'^(không|tránh|đừng|ngừng|cấm|chớ)\b', s, re.IGNORECASE):
                continue
            if len(s.split()) > 25:
                continue
            neg_sents.append(s.rstrip('.!?'))
        return neg_sents

    def _word_overlap_score(self, sent: str, summary: str) -> float:
        words_s = set(re.findall(r'\w+', sent.lower()))
        words_sum = set(re.findall(r'\w+', summary.lower()))
        if not words_s:
            return 1.0
        return len(words_s & words_sum) / len(words_s)

    def _apply_negation_guard(self, source_text: str, summary: str) -> tuple[str, list[str]]:
        warnings = []
        neg_sents = self._extract_negation_sentences(source_text)
        if not neg_sents:
            return summary, warnings
        summary_lower = summary.lower()
        missing = []
        for sent in neg_sents:
            if sent.lower() in summary_lower:
                continue
            keyword_match = NEGATION_PATTERN.search(sent)
            if keyword_match and keyword_match.group().lower() in summary_lower:
                continue
            if self._word_overlap_score(sent, summary) > 0.7:
                continue
            missing.append(sent)
        if missing:
            to_add = missing[:5]
            additions = [s if s.endswith(('.', '!', '?')) else s + '.' for s in to_add]
            summary = summary.rstrip() + ' ' + ' '.join(additions)
            warnings.append(f"[RAG] Đã thêm {len(to_add)} câu phủ định còn thiếu: {to_add}")
        return summary, warnings

    VIET_STOPWORDS = {
        "và", "của", "có", "là", "được", "cho", "với", "một", "những", "này",
        "không", "nhưng", "tuy", "nhiên", "đó", "này", "kia", "ấy", "đây",
        "mọi", "tất cả", "các", "đều", "chỉ", "sự", "việc", "thì", "mà",
        "hay", "hoặc", "nếu", "bởi", "vì", "để", "đến", "từ", "ra", "vào",
        "lên", "xuống", "lại", "qua", "về", "trước", "sau", "trong", "ngoài",
        "trên", "dưới", "giữa", "cùng", "hơn", "nữa", "cũng", "còn", "đang",
        "sẽ", "đã", "mới", "vừa", "rất", "quá", "lắm", "nhiều", "ít",
        "người", "ta", "tôi", "bạn", "anh", "chị", "em", "chúng", "họ",
        "nó", "chàng", "nàng",
    }

    def _get_token_overlap(self, sentence: str, source: str) -> float:
        tokens_s = [t for t in re.findall(r'\w+', sentence.lower()) if t not in self.VIET_STOPWORDS]
        tokens_src = set(t for t in re.findall(r'\w+', source.lower()) if t not in self.VIET_STOPWORDS)
        if not tokens_s:
            return 0.0
        common = [t for t in tokens_s if t in tokens_src]
        return len(common) / len(tokens_s)

    def _filter_hallucinations(self, source: str, summary: str) -> str:
        sents = re.split(r'(?<=[.!?])\s+', summary)
        filtered = []
        for s in sents:
            s = s.strip()
            if not s:
                continue
            if s.endswith('?') and not NEGATION_PATTERN.search(s):
                continue
            if re.search(r'\b(có phải|liệu có phải|hay không|đúng không|phải không)\b', s, re.IGNORECASE):
                continue
            if NEGATION_PATTERN.search(s):
                filtered.append(s)
                continue
            overlap = self._get_token_overlap(s, source)
            if overlap >= 0.3:
                filtered.append(s)
            else:
                logger.debug("Loại bỏ câu nghi ngờ ảo giác: %s", s[:100])
        return ' '.join(filtered) if filtered else summary

    def _summarize_long_context(self, context: str) -> str:
        if self.model is None:
            raise ValueError("_summarize_long_context requires a ViT5Model")
        words = context.split()
        window = 700
        stride = 650
        parts = []
        for i in range(0, len(words), stride):
            part = " ".join(words[i:i+window]).strip()
            if not part:
                continue
            parts.append(self.model.summarize(part, max_new_tokens=256).output_text)
            if i + window >= len(words):
                break
        merged = "\n".join(parts)
        return self.model.summarize(merged, max_new_tokens=256).output_text

    def _build_context(self, chunks: list[RetrievedChunk]) -> tuple[str, list[str]]:
        warnings = []
        if self.model is None:
            parts = [f"[{i + 1}] {chunk.chunk}" for i, chunk in enumerate(chunks)]
            return "\n\n".join(parts), warnings
        parts = []
        for i, chunk in enumerate(chunks):
            candidate = parts + [f"[{i + 1}] {chunk.chunk}"]
            candidate_text = "\n\n".join(candidate)
            if self.model.count_tokens(candidate_text) > self.model.config.max_input_tokens:
                warnings.append(f"Context capped at {i} chunks to fit token budget")
                break
            parts = candidate
        return "\n\n".join(parts), warnings
