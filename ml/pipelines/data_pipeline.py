import uuid
from ml.utils.schema import IngestedDocument, PageData
from ml.utils.extractor import (
    extract_pdf,
    extract_pdf_images,
    extract_pdf_page_as_image,
    extract_pdf_metadata,
    extract_docx,
    extract_docx_metadata,
)
from ml.utils.ocr import needs_ocr, apply_ocr_to_pages
from ml.utils.cleaner import clean_text, merge_pages
from ml.utils.preprocessor import preprocess, ProcessedDocument
import magic
class DataPipeline:
    def __init__(self, tokenizer):
        self.tokenizer = tokenizer

    def run(self, file_path: str) -> tuple[IngestedDocument, ProcessedDocument]:
        fmt = self._detect_format(file_path)
        if fmt == "unsupported":
            raise ValueError(f"Unsupported file format: {file_path}")
        pages, metadata = self._extract(file_path, fmt)
        pages, ocr_confidence, ocr_warnings = self._ocr_if_needed(
            pages, file_path
        )
        merged = merge_pages(pages)
        clean = clean_text(merged)
        extraction_method = self._resolve_extraction_method(pages)
        ingested = IngestedDocument(
            doc_id=str(uuid.uuid4()),
            source_path=file_path,
            format=fmt,
            pages=pages,
            full_text=clean,
            extraction_method=extraction_method,
            ocr_confidence=ocr_confidence,
            warnings=ocr_warnings,
            metadata=metadata,
        )
        processed = preprocess(
            doc_id=ingested.doc_id,
            full_text=ingested.full_text,
            tokenizer=self.tokenizer,
        )
        ingested.warnings.extend(processed.warnings)
        return ingested, processed

    def _detect_format(self, file_path: str) -> str:
        mime = magic.from_file(file_path, mime=True)
        mapping = {
            "application/pdf": "pdf",
            "application/vnd.openxmlformats-officedocument"
            ".wordprocessingml.document": "docx",
            "image/jpeg": "image",
            "image/png": "image",
        }
        return mapping.get(mime, "unsupported")

    def _extract(self, file_path: str, fmt: str) -> tuple[list[PageData], dict]:
        if fmt == "pdf":
            pages = extract_pdf(file_path)
            metadata = extract_pdf_metadata(file_path)
        elif fmt == "docx":
            pages = extract_docx(file_path)
            metadata = extract_docx_metadata(file_path)
        else:
            raise ValueError(f"No extractor for format: {fmt}")
        return pages, metadata

    def _ocr_if_needed(
        self, pages: list[PageData], file_path: str
    ) -> tuple[list[PageData], float | None, list[str]]:
        if not needs_ocr(pages):
            return pages, None, []
        return apply_ocr_to_pages(
            pages=pages,
            file_path=file_path,
            extract_page_fn=extract_pdf_page_as_image,
            extract_images_fn=extract_pdf_images,
        )

    def _resolve_extraction_method(self, pages: list[PageData]) -> str:
        ocr_pages = [p for p in pages if p.ocr_applied]
        if not ocr_pages:
            return "pymupdf"
        elif len(ocr_pages) == len(pages):
            return "ocr"
        else:
            return "hybrid"