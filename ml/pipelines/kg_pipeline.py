from ml.utils.ner_extractor import NERExtractor
from ml.utils.entity_resolver import EntityResolver
from ml.utils.kg_builder import KGBuilder, Community
from ml.utils.similarity_router import DocumentGroup
from ml.utils.preprocessor import ProcessedDocument
import logging
logger = logging.getLogger(__name__)
import re
NEGATION_PATTERN = re.compile(
    r"\b(không|tránh|đừng|ngừng|cấm|chớ)\s+\w+(?:\s+\w+){0,3}",
    re.IGNORECASE,
)
class KGPipeline:
    def __init__(self, vit5_model):
        self.ner = NERExtractor()
        self.resolver = EntityResolver()
        self.builder = KGBuilder()
        self.vit5 = vit5_model

    def run(
        self,
        group: DocumentGroup,
        processed_docs: dict[str, ProcessedDocument],
    ) -> str:
        all_entities, all_relations = [], []
        for doc_id in group.doc_ids:
            doc = processed_docs[doc_id]
            entities, relations = self.ner.extract(
                doc_id=doc_id,
                sentences=doc.sentences,
            )
            all_entities.extend(entities)
            all_relations.extend(relations)
        resolved_entities, alias_map = self.resolver.resolve(all_entities)
        resolved_relations = self.resolver.apply_aliases(
            all_relations, alias_map
        )
        G = self.builder.build(resolved_entities, resolved_relations)
        communities = self.builder.detect_communities(
            G, resolved_relations, resolved_entities
        )
        if not communities:
            final_summary = self._fallback_summary(group, processed_docs)
        else:
            community_summaries = self._summarize_communities(communities)
            final_summary = self._hierarchical_summary(community_summaries)
        source_parts = []
        for doc_id in group.doc_ids:
            doc = processed_docs[doc_id]
            source_parts.extend(doc.sentences)  
        source_text = " ".join(source_parts)
        final_summary, _ = self._apply_negation_guard(source_text, final_summary)
        final_summary = self._filter_hallucinations(source_text, final_summary)
        final_summary = self.vit5._trim_incomplete_sentence(final_summary)
        return final_summary

    def _summarize_communities(
        self,
        communities: list[Community],
    ) -> list[str]:
        summaries = []
        for community in communities:
            text = self.builder.community_to_text(community)
            result = self.vit5.summarize(text, max_new_tokens=256)
            community.summary = result.output_text
            summaries.append(result.output_text)
        return summaries
      
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
            warnings.append(f"Đã thêm {len(to_add)} câu phủ định còn thiếu: {to_add}")
        return summary, warnings

    def _prepend_first_sentence_guard(self, summary: str, chunk0_summary: str) -> str:
        if not chunk0_summary:
            return summary
        chunk0_sents = re.split(r'(?<=[.!?])\s+', chunk0_summary.strip())
        if not chunk0_sents:
            return summary
        first_chunk_sent = chunk0_sents[0].rstrip('.!?')
        def _norm(s):
            return re.sub(r'\s+', ' ', s.lower().strip())
        if _norm(first_chunk_sent) in _norm(summary):
            return summary
        summary_sents = re.split(r'(?<=[.!?])\s+', summary.strip())
        if summary_sents:
            first_reduce_sent = summary_sents[0].rstrip('.!?')
            if first_reduce_sent and _norm(first_reduce_sent) in _norm(first_chunk_sent):
                return summary
            if first_reduce_sent and self._word_overlap_score(first_chunk_sent, first_reduce_sent) >= 0.7:
                return summary
        if not first_chunk_sent.endswith(('.', '!', '?')):
            first_chunk_sent += '.'
        return first_chunk_sent + ' ' + summary.lstrip()

    def _hierarchical_summary(self, community_summaries: list[str]) -> str:
        if not community_summaries:
            return ""
        max_group_size = 5
        doc_type = self._detect_doc_type("\n".join(community_summaries))
        reduce_input = self._build_reduce_input(community_summaries, doc_type=doc_type)
        if self.vit5.count_tokens(reduce_input) <= self.vit5.config.max_input_tokens:
            reduce_output = self.vit5.summarize(reduce_input, max_new_tokens=256).output_text
            if community_summaries:
                reduce_output = self._prepend_first_sentence_guard(reduce_output, community_summaries[0])
            return reduce_output
        grouped = [
            "\n".join(community_summaries[i:i + max_group_size])
            for i in range(0, len(community_summaries), max_group_size)
        ]
        return self._hierarchical_summary(grouped)

    def _build_reduce_input(self, summaries: list[str], doc_type: str = "general") -> str:
        labeled = "\n".join(f"[Phần {i+1}]: {s}" for i, s in enumerate(summaries))
        if doc_type == "how_to":
            prefix = "Tổng hợp các bước (giữ phủ định):\n"
        else:
            prefix = "Tổng hợp nội dung chính:\n"
        return prefix + labeled

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

    def _detect_doc_type(self, text: str) -> str:
        t = text.lower()
        markers = ["bước", "hãy", "dùng", "chọn", "nhấn", "tránh", "đặt", "cách "]
        score = sum(m in t for m in markers)
        return "how_to" if score >= 2 else "general"

    def _fallback_summary(
        self,
        group: DocumentGroup,
        processed_docs: dict[str, ProcessedDocument],
    ) -> str:
        all_chunks = []
        for doc_id in group.doc_ids:
            all_chunks.extend(processed_docs[doc_id].chunks)
        if not all_chunks:
            return ""
        if len(all_chunks) == 1:
            return self.vit5.summarize(all_chunks[0]).output_text
        return self._hierarchical_summary(all_chunks)
