from __future__ import annotations

import logging
import os
from dataclasses import dataclass

from rag.retriever import RetrievalResult

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an analyst for Unredacted, a platform that helps \
citizens understand Indian government documents.

You are given excerpts from official government documents — CAG audit reports, \
parliamentary bills, and public datasets. Answer the user's question using \
ONLY the provided document excerpts.

Rules:
- Answer only from the provided context. Do not use outside knowledge.
- Cite your sources: after each claim, note the document title and page number.
- If the context does not contain enough information to answer, say so clearly.
- Be concise and factual. This is a research tool, not a chatbot.
- Flag any figures, amounts, or statistics you cite — these matter for accountability.
"""


# Data model 

@dataclass
class Answer:
    query:       str
    answer:      str
    sources:     list[dict]   
    chunk_count: int          
    mocked:      bool         


# Context formatting 

def _format_context(result: RetrievalResult) -> str:
   
    parts = []
    for i, chunk in enumerate(result.chunks, start=1):
        parts.append(
            f"[{i}] Source: {chunk.title} (Page {chunk.page_start}, "
            f"{chunk.source_site})\n"
            f"{chunk.text}\n"
        )
    return "\n---\n".join(parts)


def _extract_sources(result: RetrievalResult) -> list[dict]:
    seen = set()
    sources = []
    for chunk in result.chunks:
        key = (chunk.source_url, chunk.page_start)
        if key not in seen:
            seen.add(key)
            sources.append({
                "title":      chunk.title,
                "url":        chunk.source_url,
                "page":       chunk.page_start,
                "site":       chunk.source_site,
            })
    return sources


# LLM calls 

def _call_claude(context: str, query: str) -> str:
 
    import anthropic

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    message = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": (
                    f"Document excerpts:\n\n{context}\n\n"
                    f"Question: {query}"
                ),
            }
        ],
    )
    return message.content[0].text


def _mock_answer(context: str, query: str) -> str:
   
    chunk_count = context.count("[") 
    return (
        f"[MOCK RESPONSE — Add ANTHROPIC_API_KEY to .env for real answers]\n\n"
        f"Query: {query}\n\n"
        f"I found {chunk_count} relevant excerpts from government documents. "
        f"With a real API key, I would analyze these excerpts and provide "
        f"a grounded answer with citations to specific pages and documents.\n\n"
        f"Context preview:\n{context[:300]}..."
    )


#  Public interface 

class Answerer:

    def __init__(self):
        self._has_api_key = bool(os.environ.get("ANTHROPIC_API_KEY"))
        if not self._has_api_key:
            logger.warning(
                "[Answerer] ANTHROPIC_API_KEY not set — using mock responses. "
                "Add key to backend/.env for real answers."
            )

    def answer(self, result: RetrievalResult) -> Answer:
      
        if not result.chunks:
            return Answer(
                query=result.query,
                answer=(
                    "No relevant documents found for this query. "
                    "Try scraping more documents first, or rephrase your question."
                ),
                sources=[],
                chunk_count=0,
                mocked=False,
            )

        context = _format_context(result)
        sources = _extract_sources(result)

        if self._has_api_key:
            try:
                logger.info(
                    "[Answerer] Calling Claude API for '%s' (%d chunks)",
                    result.query, len(result.chunks),
                )
                answer_text = _call_claude(context, result.query)
                mocked = False
            except Exception as e:
                logger.error("[Answerer] API call failed: %s", e)
                answer_text = f"API error: {e}"
                mocked = True
        else:
            answer_text = _mock_answer(context, result.query)
            mocked = True

        return Answer(
            query=result.query,
            answer=answer_text,
            sources=sources,
            chunk_count=len(result.chunks),
            mocked=mocked,
        )