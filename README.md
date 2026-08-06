# Unredacted

A document intelligence platform that automatically scrapes Indian government 
documents, indexes them using semantic search, and lets you ask questions 
grounded in source text — with contradiction detection across documents.

---

## Why this exists

Government documents are public but inaccessible. A CAG audit report exposing 
financial irregularities exists as a 200-page scanned PDF that nobody reads. 
Unredacted makes these documents searchable, queryable, and comparable — so 
contradictions between what different government bodies report can be surfaced 
automatically.

---

## How it works

Government websites (RBI, Budget, Sansad, NITI Aayog, FinMin)
↓
Scraper layer ← fetches PDFs automatically
↓
OCR + extraction ← pulls text from both text and scanned PDFs
↓
Chunking ← splits into 500-char overlapping passages
↓
FAISS vector store ← embeds chunks with sentence-transformers
↓
RAG query layer ← retrieves relevant chunks for a question
↓
LLM answer ← Claude generates grounded answer with citations
↓
Contradiction detector ← finds conflicting claims across documents

---

## Features

- **Automatic scraping** — fetches PDFs from RBI, India Budget, Sansad,
  NITI Aayog, and Ministry of Finance
- **OCR support** — handles both text-based and scanned PDFs
- **Semantic search** — finds relevant passages by meaning, not keyword
- **Grounded answers** — every claim cites a specific document and page
- **Contradiction detection** — flags when different documents report
  different figures for the same topic

---

## Setup

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate    # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Create `backend/.env`: