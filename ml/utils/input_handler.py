import uuid
import tempfile
import os
from dataclasses import dataclass, field
from enum import Enum
class SourceType(str, Enum):
    FILE = "file"
    TEXT = "text"
MAX_DOCUMENT_UNITS = 10
MAX_CHARS_PER_UNIT = 50_000
HARD_REJECT_CHARS  = 100_000
@dataclass
class DocumentUnit:
    unit_id: str
    source_type: SourceType
    content: str              
    file_path: str | None    
    char_count: int
    warnings: list[str] = field(default_factory=list)

class InputSession:
    def __init__(self):
        self.units: list[DocumentUnit] = []

    @property
    def count(self) -> int:
        return len(self.units)

    @property
    def is_full(self) -> bool:
        return self.count >= MAX_DOCUMENT_UNITS

    def add_file(self, file_path: str) -> DocumentUnit:
        if self.is_full:
            raise ValueError(
                f"Reached maximum of {MAX_DOCUMENT_UNITS} documents. "
                f"Remove one before adding more."
            )
        unit = DocumentUnit(
            unit_id=str(uuid.uuid4()),
            source_type=SourceType.FILE,
            content="",          
            file_path=file_path,
            char_count=0,        
        )
        self.units.append(unit)
        return unit

    def add_text(self, text: str, label: str | None = None) -> DocumentUnit:
        if self.is_full:
            raise ValueError(
                f"Reached maximum of {MAX_DOCUMENT_UNITS} documents."
            )
        warnings = []
        char_count = len(text)
        if char_count > HARD_REJECT_CHARS:
            raise ValueError(
                f"Text exceeds {HARD_REJECT_CHARS:,} character limit "
                f"({char_count:,} chars). Please split into smaller documents."
            )
        if char_count > MAX_CHARS_PER_UNIT:
            text = text[:MAX_CHARS_PER_UNIT]
            warnings.append(
                f"Text truncated to {MAX_CHARS_PER_UNIT:,} characters."
            )
        tmp_path = self._text_to_tempfile(text, label)
        unit = DocumentUnit(
            unit_id=str(uuid.uuid4()),
            source_type=SourceType.TEXT,
            content=text,
            file_path=tmp_path,
            char_count=len(text),
            warnings=warnings,
        )
        self.units.append(unit)
        return unit

    def remove(self, unit_id: str):
        self.units = [u for u in self.units if u.unit_id != unit_id]

    def clear(self):
        self.units = []

    def _text_to_tempfile(self, text: str, label: str | None = None) -> str:
        suffix = f"_{label}.txt" if label else ".txt"
        tmp = tempfile.NamedTemporaryFile(
            mode="w",
            suffix=suffix,
            delete=False,
            encoding="utf-8",
        )
        tmp.write(text)
        tmp.close()
        return tmp.name
