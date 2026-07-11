from __future__ import annotations

import logging
import re
from dataclasses import dataclass

from ingestion.extractor import ExtractedDocument

logger = logging.getLogger(__name__)

DEFAULT_CHUNK_SIZE    = 500    
DEFAULT_CHUNK_OVERLAP = 100    


# Data model 

@dataclass
class Chunk:
    
    chunk_id:    str    
    doc_id:      str     
    text:        str     
    page_start:  int     
    page_end:    int     
    char_offset: int     
    source_url:  str     
    source_site: str     
    title:       str    


# Chunking logic 

def _clean_text(text: str) -> str:
   
    text = re.sub(r"-\n(\w)", r"\1", text)

    text = re.sub(r"\n{3,}", "\n\n", text)

    text = re.sub(r" {2,}", " ", text)

    text = re.sub(r"\n--- Page \d+ ---\n", "\n", text)

    return text.strip()


def _split_into_chunks(text: str,chunk_size: int,overlap: int,) -> list[tuple[str, int]]:
   
    chunks = []
    start  = 0
    text_len = len(text)

    while start < text_len:
        end = min(start + chunk_size, text_len)

        if end < text_len:
            boundary = text.rfind(". ", start, end)
            if boundary != -1 and boundary > start + (chunk_size // 2):
                end = boundary + 1   # include the period

        chunk_text = text[start:end].strip()
        if chunk_text:
            chunks.append((chunk_text, start))

        start += chunk_size - overlap

    return chunks


def chunk_document(
    doc: ExtractedDocument,
    metadata: dict,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> list[Chunk]:
   
    full_text = _clean_text(doc.full_text)

    if not full_text.strip():
        logger.warning(
            "[Chunker] Document %s has no text after cleaning",
            metadata.get("doc_id"),
        )
        return []

    raw_chunks = _split_into_chunks(full_text, chunk_size, overlap)

    page_offsets = []
    running = 0
    for page in doc.pages:
        page_offsets.append((running, page.page_number))
        running += page.char_count + 20   

    def char_to_page(offset: int) -> int:
        page_num = 1
        for po, pn in page_offsets:
            if offset >= po:
                page_num = pn
        return page_num

    doc_id = metadata.get("doc_id", "unknown")
    chunks = []

    for i, (text, offset) in enumerate(raw_chunks):
        page = char_to_page(offset)
        chunk = Chunk(
            chunk_id=f"{doc_id}_{i:04d}",
            doc_id=doc_id,
            text=text,
            page_start=page,
            page_end=page,
            char_offset=offset,
            source_url=metadata.get("source_url", ""),
            source_site=metadata.get("source_site", ""),
            title=metadata.get("title", ""),
        )
        chunks.append(chunk)

    logger.info(
        "[Chunker] %s → %d chunks (size=%d, overlap=%d)",
        doc_id, len(chunks), chunk_size, overlap,
    )
    return chunks


def chunk_all(
    documents: list[ExtractedDocument],
    metadata_list: list[dict],
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> list[Chunk]:
   
    all_chunks = []
    for doc, meta in zip(documents, metadata_list):
        chunks = chunk_document(doc, meta, chunk_size, overlap)
        all_chunks.extend(chunks)

    logger.info("[Chunker] Total chunks across all documents: %d", len(all_chunks))
    return all_chunks