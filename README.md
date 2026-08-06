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

Without the API key, the query tab returns mock responses but everything
else works — scraping, indexing, contradiction detection.

Start the backend:

```bash
python app.py
```

Backend runs on `http://localhost:8000`.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend runs on `http://localhost:5173`.

---

## Usage

### 1. Scrape documents

Go to the **Scrape** tab. Enter a topic like `monetary policy inflation`
or `budget 2024`. The scraper searches RBI, India Budget, Sansad, NITI
Aayog, and Ministry of Finance and downloads relevant PDFs.

### 2. Index documents

After scraping, click **Index documents into vector store**. This extracts
text from all downloaded PDFs, splits into chunks, embeds them, and adds
to the FAISS index.

### 3. Ask questions

Go to the **Query** tab. Ask anything about the indexed documents:

- "What was the fiscal deficit in 2023-24?"
- "What are the key provisions of the Finance Bill?"
- "What did RBI say about inflation targets?"

Answers are grounded in source text with page citations.

### 4. Detect contradictions

Go to the **Contradictions** tab. Enter a topic. The system retrieves
relevant chunks from multiple documents and flags pairs that discuss
the same topic but report different figures.

---

## Tech stack

| Component | Technology |
|---|---|
| Scraping | requests + BeautifulSoup |
| PDF extraction | pdfplumber + pytesseract (OCR) |
| Chunking | Custom sliding window with sentence boundary detection |
| Embeddings | sentence-transformers (all-MiniLM-L6-v2) |
| Vector store | FAISS + SQLite |
| RAG retrieval | Cosine similarity with deduplication |
| LLM answers | Anthropic Claude (claude-haiku-4-5) |
| Contradiction detection | Embedding similarity + specific value extraction |
| Backend | Flask |
| Frontend | React + Tailwind CSS |

---

## Project structure