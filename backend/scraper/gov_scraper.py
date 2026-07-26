from __future__ import annotations

import hashlib
import json
import logging
import time
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

REQUEST_TIMEOUT     = 15
DOWNLOAD_DELAY      = 1.5
MAX_PDFS_PER_SOURCE = 5


@dataclass
class ScrapedDocument:
    title:         str
    source_url:    str
    source_site:   str
    file_path:     str
    downloaded_at: str
    file_size_kb:  float


def _scrape_rbi(query: str, pdf_dir: Path) -> list[ScrapedDocument]:
    docs = []
    listing_url = "https://www.rbi.org.in/Scripts/AnnualReportPublications.aspx"
    search_url = f"https://www.rbi.org.in/Scripts/SearchAggregator.aspx?searchtext={query.replace(' ', '+')}&searchin=RBI"

    try:
        logger.info("[RBI] Searching: %s", search_url)
        resp = requests.get(search_url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        pdf_links = []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if href.lower().endswith(".pdf"):
                if not href.startswith("http"):
                    href = urljoin(resp.url, href)
                title = a.get_text(strip=True) or Path(href).stem
                if query.lower().split()[0] in title.lower() or query.lower().split()[0] in href.lower():
                    pdf_links.append((title, href))

        if not pdf_links:
            resp2 = requests.get(listing_url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
            resp2.raise_for_status()
            soup2 = BeautifulSoup(resp2.text, "html.parser")
            for a in soup2.find_all("a", href=True):
                href = a["href"]
                if href.lower().endswith(".pdf"):
                    if not href.startswith("http"):
                        href = urljoin(resp2.url, href)
                    title = a.get_text(strip=True) or Path(href).stem
                    pdf_links.append((title, href))

        logger.info("[RBI] Found %d PDF links", len(pdf_links))

        for title, url in pdf_links[:MAX_PDFS_PER_SOURCE]:
            doc = _download_pdf(title, url, "rbi.org.in", pdf_dir)
            if doc:
                docs.append(doc)
            time.sleep(DOWNLOAD_DELAY)

    except requests.RequestException as e:
        logger.warning("[RBI] Request failed: %s", e)

    return docs


def _scrape_budget(query: str, pdf_dir: Path) -> list[ScrapedDocument]:
    docs = []
    main_page = "https://www.indiabudget.gov.in/"

    known_docs = [
        ("Union Budget Speech", "https://www.indiabudget.gov.in/doc/budget_speech.pdf"),
        ("Economic Survey Chapter 1", "https://www.indiabudget.gov.in/economicsurvey/doc/eschapter/echap01.pdf"),
    ]

    try:
        logger.info("[Budget] Fetching budget documents listing")
        resp = requests.get(main_page, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        pdf_links = []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if href.lower().endswith(".pdf"):
                if not href.startswith("http"):
                    href = urljoin(resp.url, href)
                title = a.get_text(strip=True) or Path(href).stem
                pdf_links.append((title, href))

        for title, url in known_docs:
            if url not in [l[1] for l in pdf_links]:
                pdf_links.append((title, url))

        logger.info("[Budget] Found %d PDF links", len(pdf_links))

        query_words = query.lower().split()
        filtered = [
            (t, u) for t, u in pdf_links
            if any(w in t.lower() or w in u.lower() for w in query_words)
        ] or pdf_links

        for title, url in filtered[:MAX_PDFS_PER_SOURCE]:
            doc = _download_pdf(title, url, "indiabudget.gov.in", pdf_dir)
            if doc:
                docs.append(doc)
            time.sleep(DOWNLOAD_DELAY)

    except requests.RequestException as e:
        logger.warning("[Budget] Request failed: %s", e)

    return docs


def _scrape_sansad(query: str, pdf_dir: Path) -> list[ScrapedDocument]:
    
    docs = []
    bills_url = "https://sansad.in/ls/legislation/bills"

    try:
        logger.info("[Sansad] Fetching bills listing")
        resp = requests.get(bills_url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        pdf_links = []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if href.lower().endswith(".pdf"):
                if not href.startswith("http"):
                    href = urljoin(resp.url, href)
                title = a.get_text(strip=True) or Path(href).stem
                pdf_links.append((title, href))

        logger.info("[Sansad] Found %d PDF links", len(pdf_links))

        query_words = query.lower().split()
        filtered = [
            (t, u) for t, u in pdf_links
            if any(w in t.lower() for w in query_words)
        ] or pdf_links[:MAX_PDFS_PER_SOURCE]

        for title, url in filtered[:MAX_PDFS_PER_SOURCE]:
            doc = _download_pdf(title, url, "sansad.in", pdf_dir)
            if doc:
                docs.append(doc)
            time.sleep(DOWNLOAD_DELAY)

    except requests.RequestException as e:
        logger.warning("[Sansad] Request failed: %s", e)

    return docs

def _scrape_niti(query: str, pdf_dir: Path) -> list[ScrapedDocument]:
    
    docs = []
    listing_url = "https://www.niti.gov.in/publications/division-reports"
    MAX_ARTICLES_TO_CHECK = 15  

    try:
        logger.info("[NITI] Fetching listing: %s", listing_url)
        resp = requests.get(listing_url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        article_links = []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            text = a.get_text(strip=True)
            if href.lower().endswith(".pdf") or href.startswith(("mailto:", "#")):
                continue
            full_url = href if href.startswith("http") else urljoin(resp.url, href)
            if "/publications/" in full_url or "read more" in text.lower():
                article_links.append((text or full_url, full_url))

        seen = set()
        unique_articles = []
        for title, url in article_links:
            if url not in seen:
                seen.add(url)
                unique_articles.append((title, url))

        logger.info("[NITI] Found %d article links, checking up to %d",
                    len(unique_articles), MAX_ARTICLES_TO_CHECK)

        query_words = query.lower().split()
        relevant = [
            (t, u) for t, u in unique_articles
            if any(w in t.lower() or w in u.lower() for w in query_words)
        ] or unique_articles  # fall back to all if nothing matches

        pdf_links = []
        for title, article_url in relevant[:MAX_ARTICLES_TO_CHECK]:
            try:
                a_resp = requests.get(article_url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
                a_resp.raise_for_status()
                a_soup = BeautifulSoup(a_resp.text, "html.parser")

                for a in a_soup.find_all("a", href=True):
                    href = a["href"]
                    if href.lower().endswith(".pdf"):
                        pdf_url = href if href.startswith("http") else urljoin(a_resp.url, href)
                        pdf_title = a.get_text(strip=True) or title
                        pdf_links.append((pdf_title, pdf_url))
                        break  

                time.sleep(0.5)  

            except requests.RequestException as e:
                logger.warning("[NITI] Failed to fetch article %s: %s", article_url, e)
                continue

        logger.info("[NITI] Found %d PDF links after crawling articles", len(pdf_links))

        for title, url in pdf_links[:MAX_PDFS_PER_SOURCE]:
            doc = _download_pdf(title, url, "niti.gov.in", pdf_dir)
            if doc:
                docs.append(doc)
            time.sleep(DOWNLOAD_DELAY)

    except requests.RequestException as e:
        logger.warning("[NITI] Request failed: %s", e)

    return docs


def _scrape_finmin(query: str, pdf_dir: Path) -> list[ScrapedDocument]:
    docs = []

    known_docs = [
        (
            "Economic Survey Chapter 1",
            "https://www.indiabudget.gov.in/economicsurvey/doc/eschapter/echap01.pdf",
        ),
        (
            "Union Budget Speech",
            "https://www.indiabudget.gov.in/doc/budget_speech.pdf",
        ),
    ]

    try:
        logger.info("[FinMin] Fetching known Finance Ministry documents")
        for title, url in known_docs:
            doc = _download_pdf(title, url, "finmin.nic.in", pdf_dir)
            if doc:
                docs.append(doc)
            time.sleep(DOWNLOAD_DELAY)

    except Exception as e:
        logger.warning("[FinMin] Failed: %s", e)

    return docs

def _scrape_cic(query: str, pdf_dir: Path) -> list[ScrapedDocument]:
   
    docs = []
    pages_to_check = [
        "https://cic.gov.in/circular-reports-conventions",  
        "https://cic.gov.in/cic_landmark",                  
        "https://cic.gov.in/rti-study-reports",             
    ]

    try:
        pdf_links = []
        for page_url in pages_to_check:
            try:
                resp = requests.get(page_url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
                resp.raise_for_status()
                soup = BeautifulSoup(resp.text, "html.parser")

                for a in soup.find_all("a", href=True):
                    href = a["href"]
                    if href.lower().endswith(".pdf"):
                        pdf_url = href if href.startswith("http") else urljoin(resp.url, href)
                        title = a.get_text(strip=True) or Path(pdf_url).stem
                        if pdf_url.lower().endswith("h.pdf") or "h_0.pdf" in pdf_url.lower():
                            continue
                        pdf_links.append((title, pdf_url))

                time.sleep(0.5)

            except requests.RequestException as e:
                logger.warning("[CIC] Failed to fetch %s: %s", page_url, e)
                continue

        seen = set()
        unique_links = []
        for title, url in pdf_links:
            if url not in seen:
                seen.add(url)
                unique_links.append((title, url))

        logger.info("[CIC] Found %d PDF links across %d pages", len(unique_links), len(pages_to_check))

        query_words = query.lower().split()
        filtered = [
            (t, u) for t, u in unique_links
            if any(w in t.lower() or w in u.lower() for w in query_words)
        ] or unique_links

        for title, url in filtered[:MAX_PDFS_PER_SOURCE]:
            doc = _download_pdf(title, url, "cic.gov.in", pdf_dir)
            if doc:
                docs.append(doc)
            time.sleep(DOWNLOAD_DELAY)

    except Exception as e:
        logger.warning("[CIC] Scrape failed: %s", e)

    return docs


def _download_pdf(
    title: str,
    url: str,
    source_site: str,
    pdf_dir: Path,
) -> ScrapedDocument | None:
    url_hash  = hashlib.md5(url.encode()).hexdigest()[:12]
    pdf_path  = pdf_dir / f"{url_hash}.pdf"
    meta_path = pdf_dir / f"{url_hash}.json"

    if pdf_path.exists():
        logger.info("[Scraper] Already have %s — skipping", url_hash)
        meta = json.loads(meta_path.read_text())
        return ScrapedDocument(**meta)

    try:
        logger.info("[Scraper] Downloading: %s", url)
        resp = requests.get(
            url, headers=HEADERS, timeout=REQUEST_TIMEOUT, stream=True
        )
        resp.raise_for_status()

        content_type = resp.headers.get("content-type", "")
        if "pdf" not in content_type.lower() and not url.lower().endswith(".pdf"):
            logger.warning("[Scraper] Not a PDF (%s) — skipping %s", content_type, url)
            return None

        pdf_path.write_bytes(resp.content)
        size_kb = pdf_path.stat().st_size / 1024

        doc = ScrapedDocument(
            title=title[:200],
            source_url=url,
            source_site=source_site,
            file_path=str(pdf_path),
            downloaded_at=datetime.utcnow().isoformat(),
            file_size_kb=round(size_kb, 2),
        )

        meta_path.write_text(json.dumps(asdict(doc), indent=2))
        logger.info("[Scraper] Saved %s (%.1f KB)", pdf_path.name, size_kb)
        return doc

    except requests.RequestException as e:
        logger.warning("[Scraper] Failed to download %s: %s", url, e)
        return None


class GovScraper:
    def __init__(self, pdf_dir: Path):
        self.pdf_dir = pdf_dir
        self.pdf_dir.mkdir(parents=True, exist_ok=True)

    def scrape(
        self,
        query: str,
        sources: list[str] | None = None,
    ) -> list[ScrapedDocument]:
        sources = sources or ["rbi", "budget", "sansad", "niti", "finmin", "cic"]

        source_map = {
            "rbi":    lambda: _scrape_rbi(query, self.pdf_dir),
            "budget": lambda: _scrape_budget(query, self.pdf_dir),
            "sansad": lambda: _scrape_sansad(query, self.pdf_dir),
            "niti":   lambda: _scrape_niti(query, self.pdf_dir),
            "finmin": lambda: _scrape_finmin(query, self.pdf_dir),
            "cic":    lambda: _scrape_cic(query, self.pdf_dir),
        }

        all_docs = []
        for source in sources:
            if source not in source_map:
                continue
            logger.info("[Scraper] Scraping %s for '%s'", source, query)
            docs = source_map[source]()
            all_docs.extend(docs)
            logger.info("[Scraper] Got %d docs from %s", len(docs), source)

        logger.info("[Scraper] Total: %d documents", len(all_docs))
        return all_docs