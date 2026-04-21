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
    return word_tokenize(sentence, format="text")

def segment_sentences(sentences: list[str]) -> list[str]:
    return [segment_words(s) for s in sentences]

MAX_TOKENS = 800 
def chunk_sentences(
    sentences: list[str],
    tokenizer,       
    max_tokens: int = MAX_TOKENS,
) -> tuple[list[str], list[int]]:
    chunks = []
    token_counts = []
    current_chunk = []
    current_count = 0
    for sentence in sentences:
        token_len = len(tokenizer.encode(sentence, add_special_tokens=False))
        if current_count + token_len > max_tokens:
            if current_chunk:
                chunk_text = " ".join(current_chunk)
                chunks.append(chunk_text)
                token_counts.append(current_count)
            current_chunk = [sentence]
            current_count = token_len
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
) -> ProcessedDocument:
    warnings = []
    sentences = split_sentences(full_text)
    segmented = segment_sentences(sentences)
    chunks, token_counts = chunk_sentences(segmented, tokenizer)
    if any(tc > MAX_TOKENS for tc in token_counts):
        warnings.append(f"doc_id={doc_id}: some chunks exceed token budget")
    return ProcessedDocument(
        doc_id=doc_id,
        sentences=sentences,      
        segmented_sentences=segmented,
        chunks=chunks,
        token_counts=token_counts,
        warnings=warnings,
    )