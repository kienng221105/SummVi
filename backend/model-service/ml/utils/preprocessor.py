from dataclasses import dataclass, field
from underthesea import sent_tokenize, word_tokenize
@dataclass
class ProcessedDocument:
    doc_id: str
    sentences: list[str]       
    segmented_sentences: list[str] 
    chunks: list[str]            
    token_counts: list[int]     
    warnings: list[str] = field(default_factory=list)

def split_sentences(text: str) -> list[str]:
    sentences = sent_tokenize(text)
    return [s.strip() for s in sentences if len(s.strip()) > 10]

def segment_words(sentence: str) -> str:
    segmented = word_tokenize(sentence, format="text")
    if isinstance(segmented, str):
        return segmented
    return " ".join(str(s) for s in segmented)

def segment_sentences(sentences: list[str]) -> list[str]:
    return [segment_words(s) for s in sentences]

def prepare_sentences_for_chunking(sentences: list[str], use_segmentation: bool = False) -> list[str]:
    if use_segmentation:
        return segment_sentences(sentences)
    return sentences

MAX_TOKENS = 800 
def chunk_sentences(
    sentences: list[str],
    tokenizer,
    max_tokens: int = MAX_TOKENS,
    overlap_sentences: int = 1,
) -> tuple[list[str], list[int]]:
    chunks = []
    token_counts = []
    current_chunk = []
    current_count = 0
    buffer = []
    for sentence in sentences:
        token_len = len(tokenizer.encode(sentence, add_special_tokens=False))
        if current_count + token_len > max_tokens and current_chunk:
            chunks.append(" ".join(current_chunk))
            token_counts.append(current_count)
            overlap_buffer = current_chunk[-overlap_sentences:] if overlap_sentences > 0 else []
            current_chunk = overlap_buffer + [sentence]
            current_count = sum(len(tokenizer.encode(s, add_special_tokens=False)) for s in current_chunk)
        else:
            current_chunk.append(sentence)
            current_count += token_len
    if current_chunk:
        chunks.append(" ".join(current_chunk))
        token_counts.append(current_count)
    return chunks, token_counts

def preprocess(
    doc_id: str,
    full_text: str,
    tokenizer,
    use_segmentation: bool = False,
) -> ProcessedDocument:
    warnings = []
    sentences = split_sentences(full_text)
    
    # Fallback: if no sentences extracted, use full text as single chunk
    if not sentences and full_text.strip():
        sentences = [full_text.strip()]
        warnings.append(f"doc_id={doc_id}: fallback to full text (no sentences extracted)")
    
    chunk_sent_inputs = prepare_sentences_for_chunking(
        sentences,
        use_segmentation=use_segmentation,
    )
    chunks, token_counts = chunk_sentences(chunk_sent_inputs, tokenizer)
    if any(tc > MAX_TOKENS for tc in token_counts):
        warnings.append(f"doc_id={doc_id}: some chunks exceed token budget")
    segmented = chunk_sent_inputs if use_segmentation else []
    return ProcessedDocument(
        doc_id=doc_id,
        sentences=sentences,
        segmented_sentences=segmented,
        chunks=chunks,
        token_counts=token_counts,
        warnings=warnings,
    )
