from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from itertools import combinations

import numpy as np
from sentence_transformers import SentenceTransformer

from store.document_store import RetrievedChunk

logger = logging.getLogger(__name__)

SIMILARITY_THRESHOLD = 0.75

SPECIFIC_CLAIM_PATTERNS = [
    r"\b\d{1,3}(?:,\d{3})*(?:\.\d+)?\s*(?:crore|lakh|million|billion|thousand)\b",
    r"\b\d{4}-\d{2,4}\b",          
    r"\b(?:19|20)\d{2}\b",         
    r"₹\s*\d+",                     
    r"\b\d+(?:\.\d+)?\s*%",         
]


# Data model 

@dataclass
class ContradictionPair:
    chunk_a:        RetrievedChunk
    chunk_b:        RetrievedChunk
    similarity:     float         
    values_a:       list[str]      
    values_b:       list[str]      
    conflict_hint:  str            


# Helpers 

def _extract_specific_values(text: str) -> list[str]:
   
    values = []
    for pattern in SPECIFIC_CLAIM_PATTERNS:
        matches = re.findall(pattern, text, re.IGNORECASE)
        values.extend(matches)
    return list(set(values))


def _values_conflict(values_a: list[str], values_b: list[str]) -> bool:
   
    if not values_a or not values_b:
        return False
    set_a = set(v.lower().strip() for v in values_a)
    set_b = set(v.lower().strip() for v in values_b)

    return len(set_a & set_b) == 0


def _build_conflict_hint(chunk_a: RetrievedChunk,chunk_b: RetrievedChunk,values_a: list[str],values_b: list[str],similarity: float,) -> str:
    return (
        f"Both chunks discuss similar topics (similarity={similarity:.2f}) "
        f"but report different specific values. "
        f"'{chunk_a.title}' (p.{chunk_a.page_start}) mentions: {', '.join(values_a[:3])}. "
        f"'{chunk_b.title}' (p.{chunk_b.page_start}) mentions: {', '.join(values_b[:3])}."
    )


# Detector 

class ContradictionDetector:

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        logger.info("[Contradiction] Loading model '%s'", model_name)
        self._model = SentenceTransformer(model_name)

    def detect(self,chunks: list[RetrievedChunk],similarity_threshold: float = SIMILARITY_THRESHOLD,) -> list[ContradictionPair]:
       
        if len(chunks) < 2:
            return []

        texts = [c.text for c in chunks]
        embeddings = self._model.encode(
            texts,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        embeddings = np.array(embeddings, dtype=np.float32)

        pairs = []
        for (i, chunk_a), (j, chunk_b) in combinations(enumerate(chunks), 2):

            if chunk_a.doc_id == chunk_b.doc_id:
                continue

            similarity = float(np.dot(embeddings[i], embeddings[j]))

            if similarity < similarity_threshold:
                continue   

            values_a = _extract_specific_values(chunk_a.text)
            values_b = _extract_specific_values(chunk_b.text)

            if not _values_conflict(values_a, values_b):
                continue   

            hint = _build_conflict_hint(
                chunk_a, chunk_b, values_a, values_b, similarity
            )

            pairs.append(ContradictionPair(
                chunk_a=chunk_a,
                chunk_b=chunk_b,
                similarity=round(similarity, 4),
                values_a=values_a,
                values_b=values_b,
                conflict_hint=hint,
            ))

            logger.info(
                "[Contradiction] Flagged: '%s' p.%d vs '%s' p.%d (sim=%.2f)",
                chunk_a.title, chunk_a.page_start,
                chunk_b.title, chunk_b.page_start,
                similarity,
            )

        pairs.sort(key=lambda p: p.similarity, reverse=True)

        logger.info(
            "[Contradiction] Found %d potential contradictions in %d chunks",
            len(pairs), len(chunks),
        )
        return pairs