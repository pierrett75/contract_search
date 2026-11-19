from pathlib import Path

import pymupdf
import pytesseract
from PIL import Image

IMAGE_EXT = {".png", ".jpg", ".jpeg", ".tif", ".tiff"}


def read_pdf_text(path: Path) -> str:
    """Vytáhne textovou vrstvu z PDF. U naskenovaného PDF vrátí (skoro) prázdný řetězec."""
    from pypdf import PdfReader
    reader = PdfReader(str(path))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def ocr_image(path: Path) -> str:
    """OCR jedné fotky / obrázku."""
    with Image.open(path) as img:
        return pytesseract.image_to_string(img, lang="ces")


def load_document(path: Path) -> str:
    """Vrátí text dokumentu bez ohledu na formát."""
    suffix = path.suffix.lower()
    if suffix == ".txt":
        return path.read_text(encoding="utf-8")
    if suffix in IMAGE_EXT:
        return ocr_image(path)
    if suffix == ".pdf":
        text = read_pdf_text(path)
       
        if len("".join(text.split())) >= 50:
            return text
        with pymupdf.open(path) as doc:
            pages = []
            for page in doc:
                pix = page.get_pixmap(dpi=300)
                img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
                pages.append(pytesseract.image_to_string(img, lang="ces"))
        return "\n".join(pages)

    raise ValueError(f"Nepodporovaný formát: {path}")