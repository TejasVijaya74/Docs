import logging
from pathlib import Path

import pytesseract
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

logger = logging.getLogger(__name__)


def extract_text_from_image(path: Path) -> str:
    try:
        from PIL import Image, ImageFilter, ImageOps

        img = Image.open(str(path)).convert("L")
        img = ImageOps.autocontrast(img)
        img = img.filter(ImageFilter.SHARPEN)

        custom_config = r"--oem 3 --psm 6"
        text = pytesseract.image_to_string(img, config=custom_config)

        if not text.strip():
            logger.warning("Tesseract returned empty text, retrying with original image")
            img_original = Image.open(str(path))
            text = pytesseract.image_to_string(img_original, config=custom_config)

        return _clean_ocr_text(text)

    except ImportError:
        raise RuntimeError("pytesseract is not installed.")
    except Exception as e:
        logger.error(f"OCR failed for {path.name}: {e}")
        raise RuntimeError(f"OCR extraction failed: {e}")


def _clean_ocr_text(text: str) -> str:
    import re
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    lines = [line.strip() for line in text.splitlines()]
    lines = [line for line in lines if len(line) > 1]
    return "\n".join(lines).strip()