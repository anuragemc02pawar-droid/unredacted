from __future__ import annotations

import hashlib
import json
import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_cors import CORS

load_dotenv()

from scraper.gov_scraper import GovScraper
from ingestion.extractor import extract_all
from ingestion.chunker import chunk_all
from store.document_store import DocumentStore
from rag.retriever import Retriever
from rag.answerer import Answerer
from analysis.contradiction import ContradictionDetector

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("unredacted.app")

# App setup 

app = Flask(__name__)
CORS(app)   

# Paths
BASE_DIR  = Path(__file__).parent
PDF_DIR   = BASE_DIR / "data" / "pdfs"
DB_DIR    = BASE_DIR / "data" / "db"
META_DIR  = PDF_DIR   

# Shared instances
_store     = DocumentStore(db_dir=DB_DIR)
_retriever = Retriever(_store)
_answerer  = Answerer()
_detector  = ContradictionDetector()
_scraper   = GovScraper(pdf_dir=PDF_DIR)


# Routes 

@app.get("/api/health")
def health():
    return jsonify({
        "status":      "ok",
        "chunks":      _store.chunk_count,
        "has_api_key": bool(os.environ.get("ANTHROPIC_API_KEY")),
    })


@app.post("/api/scrape")
def scrape():
    
    data    = request.get_json(silent=True) or {}
    query   = data.get("query", "").strip()
    sources = data.get("sources", None)

    if not query:
        return jsonify({"error": "Missing required field 'query'."}), 400

    logger.info("[API] Scrape request: '%s'", query)
    docs = _scraper.scrape(query, sources=sources)

    return jsonify({
        "query":          query,
        "documents_found": len(docs),
        "documents": [
            {
                "title":       d.title,
                "source_site": d.source_site,
                "source_url":  d.source_url,
                "file_size_kb": d.file_size_kb,
            }
            for d in docs
        ],
    })


@app.post("/api/ingest")
def ingest():
    
    logger.info("[API] Starting ingestion of PDFs in %s", PDF_DIR)

    extracted = extract_all(PDF_DIR)
    if not extracted:
        return jsonify({
            "message": "No PDFs found. Run /api/scrape first.",
            "chunks_added": 0,
        })

    metadata_list = []
    for doc in extracted:
        pdf_path  = Path(doc.file_path)
        meta_path = pdf_path.with_suffix(".json")
        if meta_path.exists():
            meta = json.loads(meta_path.read_text())
        else:
            meta = {"title": pdf_path.stem, "source_url": "", "source_site": "unknown"}

        url_hash = hashlib.md5(meta.get("source_url", pdf_path.stem).encode()).hexdigest()[:12]
        meta["doc_id"] = url_hash
        metadata_list.append(meta)

    chunks = chunk_all(extracted, metadata_list)

    added = _store.add_chunks(chunks)

    return jsonify({
        "pdfs_processed": len(extracted),
        "chunks_created": len(chunks),
        "chunks_added":   added,
        "total_chunks":   _store.chunk_count,
    })


@app.post("/api/query")
def query():
    
    data     = request.get_json(silent=True) or {}
    question = data.get("question", "").strip()
    top_k    = data.get("top_k", 5)

    if not question:
        return jsonify({"error": "Missing required field 'question'."}), 400

    logger.info("[API] Query: '%s'", question)

    result = _retriever.retrieve(question, top_k=top_k)

    answer = _answerer.answer(result)

    return jsonify({
        "question":    question,
        "answer":      answer.answer,
        "mocked":      answer.mocked,
        "chunk_count": answer.chunk_count,
        "sources": [
            {
                "title": s["title"],
                "url":   s["url"],
                "page":  s["page"],
                "site":  s["site"],
            }
            for s in answer.sources
        ],
        "chunks": [
            {
                "text":       c.text[:300] + "..." if len(c.text) > 300 else c.text,
                "score":      c.score,
                "title":      c.title,
                "page":       c.page_start,
                "source_url": c.source_url,
            }
            for c in result.chunks
        ],
    })


@app.post("/api/contradictions")
def contradictions():
   
    data     = request.get_json(silent=True) or {}
    question = data.get("question", "").strip()

    if not question:
        return jsonify({"error": "Missing required field 'question'."}), 400

    logger.info("[API] Contradiction check: '%s'", question)

    result = _retriever.retrieve(question, top_k=10)
    pairs  = _detector.detect(result.chunks)

    return jsonify({
        "question":          question,
        "chunks_analyzed":   len(result.chunks),
        "contradictions_found": len(pairs),
        "contradictions": [
            {
                "similarity":    p.similarity,
                "conflict_hint": p.conflict_hint,
                "document_a": {
                    "title":  p.chunk_a.title,
                    "page":   p.chunk_a.page_start,
                    "site":   p.chunk_a.source_site,
                    "url":    p.chunk_a.source_url,
                    "excerpt": p.chunk_a.text[:200] + "...",
                },
                "document_b": {
                    "title":  p.chunk_b.title,
                    "page":   p.chunk_b.page_start,
                    "site":   p.chunk_b.source_site,
                    "url":    p.chunk_b.source_url,
                    "excerpt": p.chunk_b.text[:200] + "...",
                },
                "values_a": p.values_a,
                "values_b": p.values_b,
            }
            for p in pairs
        ],
    })


# Entry point 

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=False)