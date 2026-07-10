from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import pdfplumber

logger = logging.getLogger(__name__)


MIN_TEXT_CHARS = 50


# Data model 

@dataclass
class ExtractedPage:
    """Text content of a single PDF page."""
    page_number: int
    text:        str
    method:      str    # "pdfplumber" or "ocr"
    char_count:  int


@dataclass
class ExtractedDocument:
    """Full text extraction result for one PDF."""
    file_path:   str
    pages:       list[ExtractedPage]
    total_chars: int
    ocr_pages:   int    

    @property
    def full_text(self) -> str:
        """All pages joined into one string with page markers."""
        parts = []
        for page in self.pages:
            parts.append(f"\n\n--- Page {page.page_number} ---\n")
            parts.append(page.text)
        return "".join(parts)


# Extraction 

def _extract_page_text(page) -> tuple[str, str]:
    
    text = page.extract_text() or ""

    if len(text.strip()) >= MIN_TEXT_CHARS:
        return text.strip(), "pdfplumber"

    try:
        import pytesseract
        from PIL import Image

        img = page.to_image(resolution=300).original
        text = pytesseract.image_to_string(img, lang="eng")
        return text.strip(), "ocr"

    except ImportError:
        logger.debug(
            "pytesseract not installed — skipping OCR for page %s. "
            "Install with: pip install pytesseract pillow",
            page.page_number,
        )
        return text.strip(), "pdfplumber"

    except Exception as e:
        logger.warning("OCR failed on page: %s", e)
        return text.strip(), "pdfplumber"


def extract_pdf(file_path: Path) -> ExtractedDocument | None:
    
    if not file_path.exists():
        logger.error("[Extractor] File not found: %s", file_path)
        return None

    logger.info("[Extractor] Processing %s", file_path.name)

    pages       = []
    ocr_count   = 0
    total_chars = 0

    try:
        with pdfplumber.open(file_path) as pdf:
            total_pages = len(pdf.pages)
            logger.info("[Extractor] %d pages in %s", total_pages, file_path.name)

            for i, page in enumerate(pdf.pages, start=1):
                text, method = _extract_page_text(page)

                if method == "ocr":
                    ocr_count += 1

                extracted = ExtractedPage(
                    page_number=i,
                    text=text,
                    method=method,
                    char_count=len(text),
                )
                pages.append(extracted)
                total_chars += len(text)

                logger.debug(
                    "[Extractor] Page %d/%d — %s — %d chars",
                    i, total_pages, method, len(text),
                )

    except Exception as e:
        logger.error("[Extractor] Failed to process %s: %s", file_path.name, e)
        return None

    logger.info(
        "[Extractor] Done — %d chars, %d/%d pages via OCR",
        total_chars, ocr_count, len(pages),
    )

    return ExtractedDocument(
        file_path=str(file_path),
        pages=pages,
        total_chars=total_chars,
        ocr_pages=ocr_count,
    )


def extract_all(pdf_dir: Path) -> list[ExtractedDocument]:
   
    pdf_files = list(pdf_dir.glob("*.pdf"))
    logger.info("[Extractor] Found %d PDFs in %s", len(pdf_files), pdf_dir)

    results = []
    for pdf_path in pdf_files:
        doc = extract_pdf(pdf_path)
        if doc and doc.total_chars > 0:
            results.append(doc)
        else:
            logger.warning("[Extractor] Skipping %s — no text extracted", pdf_path.name)

    logger.info("[Extractor] Successfully extracted %d/%d PDFs", len(results), len(pdf_files))
    return results