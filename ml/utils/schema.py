from dataclasses import dataclass, field
from typing import Optional
from .preprocessor import ProcessedDocument

@dataclass
class PageData:
    page_num: int
    text: str
    char_count: int
    has_images: bool = False
    ocr_applied: bool = False

@dataclass
class IngestedDocument:
    doc_id: str
    source_path: str
    format: str                          
    pages: list[PageData]
    full_text: str                 
    extraction_method: str           
    ocr_confidence: Optional[float] = None
    warnings: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)