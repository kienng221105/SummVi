import logging
import re
from dataclasses import dataclass, field
from underthesea import sent_tokenize
from ml.utils.similarity_router import DocumentGroup
from ml.utils.preprocessor import ProcessedDocument
logger = logging.getLogger(__name__)

# Multi-style prefixes for instruction-tuned model
STYLE_PREFIX = {
    "ultra_short": "[TIN_SIEU_NGAN]",
    "short": "[TIN_NGAN_GON]",
    "paragraph": "[TIN_DOAN_VAN]",
    "bullet": "[TIN_GACH_DAU_DONG]",
    "howto": "[HUONG_DAN]",
}

HOW_TO_REDUCE_PROMPT_VARIANT = "B"
NEGATION_PATTERN = re.compile(
    r"\b(không|tránh|đừng|ngừng|cấm|chớ)\s+\w+(?:\s+\w+){0,3}",
    re.IGNORECASE,
)
@dataclass
class IndependentSummaryResult:
    group_id: str
    doc_summaries: dict[str, str]    
    meta_summary: str           
    warnings: list[str] = field(default_factory=list)

class IndependentPipeline:
    META_BATCH_SIZE = 5
    def __init__(self, vit5_model):
        self.vit5 = vit5_model

    def run(
        self,
        group: DocumentGroup,
        processed_docs: dict[str, ProcessedDocument],
        style: str = "paragraph",
    ) -> IndependentSummaryResult:
        warnings = []
        doc_summaries = {}
        for doc_id in group.doc_ids:
            doc = processed_docs[doc_id]
            summary, doc_warnings = self._summarize_single_doc(
                doc_id=doc_id,
                chunks=doc.chunks,
                style=style,
            )
            doc_summaries[doc_id] = summary
            warnings.extend(doc_warnings)
        meta_summary = self._build_meta_summary(
            doc_summaries=doc_summaries,
            style=style,
        )
        return IndependentSummaryResult(
            group_id=group.group_id,
            doc_summaries=doc_summaries,
            meta_summary=meta_summary,
            warnings=warnings,
        )

    def _summarize_single_doc(
        self,
        doc_id: str,
        chunks: list[str],
        style: str = "paragraph",
    ) -> tuple[str, list[str]]:
        warnings = []
        if not chunks:
            warnings.append(f"doc_id={doc_id}: no chunks to summarize")
            return "", warnings
        source_text = " ".join(chunks)
        # Increase max_tokens for multi-style model (trained with longer targets)
        max_tokens = 384 if style in ["ultra_short", "short"] else 512
        if len(chunks) == 1:
            if self._detect_doc_type(chunks[0]) == "how_to":
                summary = self._summarize_how_to_extractive(chunks[0], style=style)
            else:
                # Add style prefix and instruction for better control
                prefix = STYLE_PREFIX.get(style, STYLE_PREFIX["bullet"])
                instruction = {
                    "ultra_short": "Tóm tắt cực ngắn trong 1 câu.",
                    "short": "Tóm tắt ngắn gọn trong 2-3 câu.",
                    "paragraph": "Tóm tắt thành đoạn văn đầy đủ.",
                    "bullet": "Tóm tắt thành 3-5 gạch đầu dòng.",
                    "howto": "Liệt kê các bước hướng dẫn."
                }.get(style, "Tóm tắt nội dung chính.")
                
                prompted_text = f"{prefix} {instruction} {chunks[0]}"
                result = self.vit5.summarize(prompted_text, max_new_tokens=max_tokens)
                warnings.extend(result.warnings)
                summary = result.output_text
        else:
            summary = self._hierarchical_summarize(chunks, style=style)
            warnings.append(
                f"doc_id={doc_id}: used token-aware map-reduce summarization "
                f"({len(chunks)} chunks)"
            )
        summary, neg_warnings = self._apply_negation_guard(source_text, summary)
        warnings.extend(neg_warnings)
        summary = self._filter_hallucinations(source_text, summary)
        summary = self.vit5._trim_incomplete_sentence(summary)
        if style == "bullet":
            summary = self._format_as_bullets(summary)
        return summary, warnings

    def _summarize_how_to_extractive(self, text: str, style: str = "bullet") -> str:
        sentences = [s.strip().rstrip('.!?') for s in sent_tokenize(text) if s.strip()]
        action_markers = (
            "đầu tiên", "chọn", "đun", "cho", "dùng", "hít", "xông", "mở", "lặp",
            "lau", "uống", "hỏi", "đi khám", "vệ sinh",
        )
        safety_markers = (
            "không", "tránh", "đừng", "ngừng", "cẩn thận", "bỏng", "ngạt", "hen suyễn",
            "khó thở", "chóng mặt", "bác sĩ", "hô hấp",
        )
        selected = []
        for sent in sentences:
            low = sent.lower()
            if any(m in low for m in action_markers) or any(m in low for m in safety_markers):
                selected.append(sent)
        if not selected:
            selected = sentences[:8]
        selected = self._dedupe_sentences(selected)[:12]
        if style == "paragraph":
            return " ".join(s + "." for s in selected)
        return "\n".join(f"- {s}." for s in selected)

    def _dedupe_sentences(self, sentences: list[str]) -> list[str]:
        kept = []
        seen = set()
        for s in sentences:
            key = re.sub(r'\W+', ' ', s.lower()).strip()
            if key and key not in seen:
                seen.add(key)
                kept.append(s)
        return kept

    def _format_as_bullets(self, text: str) -> str:
        sentences = sent_tokenize(text)
        bullets = []
        for s in self._dedupe_sentences(sentences):
            s = re.sub(r'\s+', ' ', s).strip().rstrip('.!?')
            if not s or len(s.split()) < 3:
                continue
            bullets.append(f"- {s}.")
        return "\n".join(bullets) if bullets else text

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
            to_add = missing[:4]
            safety_note = self._build_safety_note(to_add)
            if safety_note:
                summary = summary.rstrip()
                if summary and not summary.endswith(('.', '!', '?')):
                    summary += '.'
                summary = f"{summary} {safety_note}".strip()
            warnings.append(f"Đã bổ sung {len(to_add)} lưu ý an toàn còn thiếu: {to_add}")
        return summary, warnings

    def _build_safety_note(self, neg_sents: list[str]) -> str:
        cleaned = []
        for sent in neg_sents:
            sent = sent.strip().rstrip('.!?')
            sent = re.sub(r'^(cuối cùng,\s*)', '', sent, flags=re.IGNORECASE)
            if not sent:
                continue
            if len(sent.split()) > 22:
                sent = ' '.join(sent.split()[:22])
            if sent.lower() not in {s.lower() for s in cleaned}:
                cleaned.append(sent)
        if not cleaned:
            return ""
        return "Lưu ý an toàn: " + "; ".join(cleaned) + "."

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

    def _word_overlap_score(self, sent: str, summary: str) -> float:
        words_s = set(re.findall(r'\w+', sent.lower()))
        words_sum = set(re.findall(r'\w+', summary.lower()))
        if not words_s:
            return 1.0
        return len(words_s & words_sum) / len(words_s)
        
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

    def _merge_short_tail(self, chunks: list[str], min_chunk_tokens: int = 200) -> list[str]:
        if len(chunks) < 2:
            return chunks
        last_tokens = self.vit5.count_tokens(chunks[-1])
        if last_tokens < min_chunk_tokens:
            merged_last = chunks[-2] + " " + chunks[-1]
            merged_tokens = self.vit5.count_tokens(merged_last)
            if merged_tokens <= self.vit5.config.max_input_tokens:
                logger.debug(
                    "_merge_short_tail merged: tail=%s, merged=%s, budget=%s",
                    last_tokens,
                    merged_tokens,
                    self.vit5.config.max_input_tokens,
                )
                return chunks[:-2] + [merged_last]
            logger.warning(
                "_merge_short_tail skipped: tail=%s, merged=%s, budget=%s",
                last_tokens,
                merged_tokens,
                self.vit5.config.max_input_tokens,
            )
        else:
            logger.debug(
                "_merge_short_tail not triggered: tail=%s >= %s",
                last_tokens,
                min_chunk_tokens,
            )
        return chunks

    def _hierarchical_summarize(self, chunks: list[str], style: str = "bullet") -> str:
        max_reduce_tokens = 900  
        min_summary_tokens = 30
        max_group_size = 5
        chunks = self._merge_short_tail(chunks)
        safe_budget = max_reduce_tokens // len(chunks)
        if safe_budget < min_summary_tokens:
            grouped = [
                "\n".join(chunks[i:i + max_group_size])
                for i in range(0, len(chunks), max_group_size)
            ]
            return self._hierarchical_summarize(grouped, style=style)
        total_tokens = sum(self.vit5.count_tokens(chunk) for chunk in chunks)
        summaries = []
        prev_summary = ""
        for idx, chunk in enumerate(chunks):
            chunk_tokens = self.vit5.count_tokens(chunk)
            ratio = chunk_tokens / total_tokens if total_tokens > 0 else 0
            budget = max(int(max_reduce_tokens * ratio), 20)
            if idx > 0 and self.vit5.count_tokens(prev_summary) <= 20:
                hint = f"Trước đó: {prev_summary}\n\n"
            else:
                hint = ""
            summary_output = self.vit5.summarize(
                hint + chunk,
                max_new_tokens=budget
            ).output_text
            summaries.append(summary_output)
            prev_summary = summary_output
        logger.debug("Chunk 0 summary: %s", summaries[0])
        if len(summaries) > 1:
            logger.debug("Chunk 1 summary: %s", summaries[1])
        guarded_summaries = []
        for chunk, summary in zip(chunks, summaries):
            if self.vit5.count_tokens(summary) < 20:
                fallback = chunk.split(".")[0] + "."
                guarded_summaries.append(fallback)
            else:
                guarded_summaries.append(summary)
        doc_type = self._detect_doc_type("\n".join(chunks))
        reduce_input = self._build_reduce_input(guarded_summaries, doc_type=doc_type, style=style)
        if self.vit5.count_tokens(reduce_input) <= self.vit5.config.max_input_tokens:
            reduce_tokens = 1024 if style == "paragraph" else 256
            reduce_output = self.vit5.summarize(
                reduce_input,
                max_new_tokens=reduce_tokens,
            ).output_text
            logger.debug("Reduce output (before guard): %s", reduce_output[:200])
            reduce_output = self._prepend_first_sentence_guard(
                reduce_output,
                summaries[0]
            )
            logger.debug("Reduce output (after guard): %s", reduce_output[:200])
            return reduce_output
        grouped = [
            "\n".join(guarded_summaries[i:i + max_group_size])
            for i in range(0, len(guarded_summaries), max_group_size)
        ]
        return self._hierarchical_summarize(grouped, style=style)

    def _build_reduce_input(self, summaries: list[str], doc_type: str = "general", style: str = "bullet") -> str:
        labeled = "\n".join(f"- {s}" for s in summaries)
        if doc_type == "how_to":
            if style == "paragraph":
                instruction = (
                    "Viết lại thành một đoạn văn hướng dẫn duy nhất, mạch lạc. "
                    "Giữ nguyên tất cả các bước và cảnh báo an toàn (không, tránh, đừng, ngừng). "
                    "Sử dụng từ nối để câu văn trôi chảy. Không dùng dấu gạch đầu dòng. "
                    "Sắp xếp các ý theo trình tự hợp lý: chuẩn bị, thực hiện, sau khi làm, lưu ý. "
                    "Viết đúng chính tả, không ghép từ:\n"
                )
            else:
                instruction = "Liệt kê các bước thực hiện (giữ các câu phủ định):\n"
            prefix = instruction
        else:
            if style == "paragraph":
                prefix = "Tóm tắt thành đoạn văn mạch lạc:\n"
            else:
                prefix = "Tóm tắt ý chính:\n"
        return prefix + labeled

    def _detect_doc_type(self, text: str) -> str:
        t = text.lower()
        markers = ["bước", "hãy", "dùng", "chọn", "nhấn", "tránh", "đặt", "cách "]
        score = sum(m in t for m in markers)
        return "how_to" if score >= 2 else "general"

    def _build_meta_summary(
        self,
        doc_summaries: dict[str, str],
        style: str = "paragraph",
    ) -> str:
        summaries = list(doc_summaries.values())
        if not summaries:
            return ""
        if len(summaries) == 1:
            return summaries[0]
        labeled = []
        for i, (doc_id, summary) in enumerate(doc_summaries.items()):
            labeled.append(f"Tài liệu {i + 1}: {summary}")
        prompt = self._build_meta_prompt(labeled, style=style)
        if self.vit5.count_tokens(prompt) <= self.vit5.config.max_input_tokens:
            return self.vit5.summarize(prompt).output_text
        return self._hierarchical_summarize(summaries, style=style)

    def _build_meta_prompt(self, labeled_summaries: list[str], style: str = "bullet") -> str:
        body = "\n".join(labeled_summaries)
        if style == "paragraph":
             prefix = "Tổng hợp nội dung các tài liệu sau thành một đoạn văn duy nhất:"
        else:
             prefix = "Tóm tắt ý chính từng tài liệu:"
        return f"{prefix}\n{body}"
