from __future__ import annotations

import logging
from dataclasses import dataclass

from store.document_store import DocumentStore, RetrievedChunk

logger = logging.getLogger(__name__)

MIN_RELEVANCE_SCORE = 0.2


@dataclass
class RetrievalResult:
    query:          str
    chunks:         list[RetrievedChunk]
    total_searched: int    
    was_filtered:   bool   


class Retriever:
   
    def __init__(self, store: DocumentStore):
        self._store = store

    def retrieve(self,query: str,top_k: int = 5,min_score: float = MIN_RELEVANCE_SCORE,deduplicate: bool = True,) -> RetrievalResult:
        
        raw = self._store.search(query, top_k=top_k * 3)
        total_searched = len(raw)

        filtered = [c for c in raw if c.score >= min_score]

        if deduplicate:
            seen: dict[str, RetrievedChunk] = {}
            for chunk in filtered:
                key = f"{chunk.doc_id}_{chunk.page_start}"
                if key not in seen or chunk.score > seen[key].score:
                    seen[key] = chunk
            filtered = list(seen.values())
            filtered.sort(key=lambda c: c.score, reverse=True)

        final = filtered[:top_k]
        was_filtered = len(final) < total_searched

        if not final:
            logger.info(
                "[Retriever] No relevant chunks found for '%s' "
                "(searched %d, min_score=%.2f)",
                query, total_searched, min_score,
            )
        else:
            logger.info(
                "[Retriever] '%s' → %d chunks from %d unique sources",
                query, len(final),
                len({c.source_url for c in final}),
            )

        return RetrievalResult(
            query=query,
            chunks=final,
            total_searched=total_searched,
            was_filtered=was_filtered,
        )