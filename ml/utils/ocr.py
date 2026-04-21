import io
from PIL import Image
from .schema import PageData
OCR_THRESHOLD = 100   
OCR_CONFIDENCE_WARN = 0.6 
def needs_ocr(pages: list[PageData]) -> bool:
    if not pages:
        return False
    avg = sum(p.char_count for p in pages) / len(pages)
    return avg < OCR_THRESHOLD

def _load_vietocr():
    from vietocr.tool.predictor import Predictor
    from vietocr.tool.config import Cfg
    config = Cfg.load_config_from_name("vgg_transformer")
    config["device"] = "cuda:0"
    config["cnn"]["pretrained"] = False
    return Predictor(config)

_detector = None
def get_detector():
    global _detector
    if _detector is None:
        _detector = _load_vietocr()
    return _detector

def ocr_image_bytes(img_bytes: bytes) -> tuple[str, float]:
    detector = get_detector()
    image = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    text, confidence = detector.predict(image, return_prob=True)
    return text, confidence

def ocr_full_page(page_image_bytes: bytes) -> tuple[str, float]:
    return ocr_image_bytes(page_image_bytes)

def apply_ocr_to_pages(
    pages: list[PageData],
    file_path: str,
    extract_page_fn, 
    extract_images_fn,
) -> tuple[list[PageData], float, list[str]]:
    updated = []
    confidences = []
    warnings = []
    for page in pages:
        if page.char_count >= OCR_THRESHOLD:
            updated.append(page)
            continue
        if page.has_images and page.char_count > 0:
            img_bytes_list = extract_images_fn(file_path, page.page_num)
            ocr_texts = []
            for img_bytes in img_bytes_list:
                text, conf = ocr_image_bytes(img_bytes)
                ocr_texts.append(text)
                confidences.append(conf)
                if conf < OCR_CONFIDENCE_WARN:
                    warnings.append(
                        f"Low OCR confidence ({conf:.2f}) on page "
                        f"{page.page_num} image region"
                    )
            page.text += "\n" + "\n".join(ocr_texts)
            page.char_count = len(page.text.strip())
            page.ocr_applied = True
        else:
            page_img = extract_page_fn(file_path, page.page_num)
            text, conf = ocr_full_page(page_img)
            confidences.append(conf)
            if conf < OCR_CONFIDENCE_WARN:
                warnings.append(
                    f"Low OCR confidence ({conf:.2f}) on page {page.page_num}"
                )
            page.text = text
            page.char_count = len(text.strip())
            page.ocr_applied = True
        updated.append(page)
    avg_conf = sum(confidences) / len(confidences) if confidences else None
    return updated, avg_conf, warnings