from __future__ import annotations

import json
import logging
import sqlite3
from dataclasses import dataclass
from pathlib import Path

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

from ingestion.chunker import Chunk

logger = logging.getLogger(__name__)

EMBEDDING_MODEL = "all-MiniLM-L6-v2"


# Retrieved result 

@dataclass
class RetrievedChunk:
    chunk_id:    str
    doc_id:      str
    text:        str
    score:       float
    title:       str
    source_url:  str
    source_site: str
    page_start:  int


# Document store 

class DocumentStore:

    def __init__(self, db_dir: Path, model_name: str = EMBEDDING_MODEL):
        self.db_dir     = db_dir
        self.db_dir.mkdir(parents=True, exist_ok=True)

        self.index_path = db_dir / "chunks.faiss"
        self.db_path    = db_dir / "chunks.db"

        logger.info("[Store] Loading embedding model '%s'", model_name)
        self._model = SentenceTransformer(model_name)

        self._index: faiss.IndexFlatIP | None = None
        self._chunk_ids: list[str] = []  

        self._init_db()
        self._load_index()

    # Database setup 

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS chunks (
                    chunk_id    TEXT PRIMARY KEY,
                    doc_id      TEXT NOT NULL,
                    text        TEXT NOT NULL,
                    title       TEXT,
                    source_url  TEXT,
                    source_site TEXT,
                    page_start  INTEGER,
                    page_end    INTEGER,
                    char_offset INTEGER
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_doc_id
                ON chunks(doc_id)
            """)
            conn.commit()
        logger.info("[Store] Database ready at %s", self.db_path)

    # Index loading/saving 

    def _load_index(self) -> None:
       
        ids_path = self.db_dir / "chunk_ids.json"

        if self.index_path.exists() and ids_path.exists():
            self._index = faiss.read_index(str(self.index_path))
            self._chunk_ids = json.loads(ids_path.read_text())
            logger.info(
                "[Store] Loaded index with %d vectors", self._index.ntotal
            )
        else:
            dim = self._model.get_sentence_embedding_dimension()
            self._index = faiss.IndexFlatIP(dim)
            self._chunk_ids = []
            logger.info("[Store] Created new index (dim=%d)", dim)

    def _save_index(self) -> None:
        """Persist FAISS index and chunk_ids mapping to disk."""
        faiss.write_index(self._index, str(self.index_path))
        ids_path = self.db_dir / "chunk_ids.json"
        ids_path.write_text(json.dumps(self._chunk_ids))

    # Adding chunks 

    def add_chunks(self, chunks: list[Chunk]) -> int:
       
        existing = self._get_existing_chunk_ids(
            {c.chunk_id for c in chunks}
        )
        new_chunks = [c for c in chunks if c.chunk_id not in existing]

        if not new_chunks:
            logger.info("[Store] All chunks already indexed — nothing to add")
            return 0

        logger.info("[Store] Embedding %d new chunks...", len(new_chunks))

        texts = [c.text for c in new_chunks]
        embeddings = self._model.encode(
            texts,
            normalize_embeddings=True,
            show_progress_bar=True,
        )
        embeddings = np.array(embeddings, dtype=np.float32)

        # Add to FAISS
        self._index.add(embeddings)
        self._chunk_ids.extend([c.chunk_id for c in new_chunks])

        # Add metadata to SQLite
        with sqlite3.connect(self.db_path) as conn:
            conn.executemany(
                """
                INSERT OR IGNORE INTO chunks
                (chunk_id, doc_id, text, title, source_url,
                 source_site, page_start, page_end, char_offset)
                VALUES (?,?,?,?,?,?,?,?,?)
                """,
                [
                    (
                        c.chunk_id, c.doc_id, c.text, c.title,
                        c.source_url, c.source_site,
                        c.page_start, c.page_end, c.char_offset,
                    )
                    for c in new_chunks
                ],
            )
            conn.commit()

        self._save_index()
        logger.info("[Store] Added %d chunks. Total: %d", len(new_chunks), self._index.ntotal)
        return len(new_chunks)

    # Searching 

    def search(self, query: str, top_k: int = 5) -> list[RetrievedChunk]:
        
        if self._index.ntotal == 0:
            logger.warning("[Store] Index is empty — run ingestion first")
            return []

        query_vec = self._model.encode(
            [query],
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        query_vec = np.array(query_vec, dtype=np.float32)

        top_k     = min(top_k, self._index.ntotal)
        scores, indices = self._index.search(query_vec, top_k)

        chunk_ids = [
            self._chunk_ids[i]
            for i in indices[0]
            if i >= 0
        ]
        score_map = {
            self._chunk_ids[idx]: float(score)
            for idx, score in zip(indices[0], scores[0])
            if idx >= 0
        }

        rows = self._fetch_chunks(chunk_ids)

        results = []
        for row in rows:
            results.append(RetrievedChunk(
                chunk_id=row["chunk_id"],
                doc_id=row["doc_id"],
                text=row["text"],
                score=round(score_map.get(row["chunk_id"], 0.0), 4),
                title=row["title"] or "",
                source_url=row["source_url"] or "",
                source_site=row["source_site"] or "",
                page_start=row["page_start"] or 0,
            ))

        results.sort(key=lambda r: r.score, reverse=True)
        return results

    # Helpers 

    def _get_existing_chunk_ids(self, chunk_ids: set[str]) -> set[str]:
        with sqlite3.connect(self.db_path) as conn:
            placeholders = ",".join("?" * len(chunk_ids))
            rows = conn.execute(
                f"SELECT chunk_id FROM chunks WHERE chunk_id IN ({placeholders})",
                list(chunk_ids),
            ).fetchall()
        return {row[0] for row in rows}

    def _fetch_chunks(self, chunk_ids: list[str]) -> list[dict]:
        if not chunk_ids:
            return []
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            placeholders = ",".join("?" * len(chunk_ids))
            rows = conn.execute(
                f"SELECT * FROM chunks WHERE chunk_id IN ({placeholders})",
                chunk_ids,
            ).fetchall()
        return [dict(row) for row in rows]

    @property
    def chunk_count(self) -> int:
        return self._index.ntotal