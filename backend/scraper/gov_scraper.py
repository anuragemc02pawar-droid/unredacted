from __future__ import annotations

import hashlib
import json
import logging
import time
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path

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


# Source scrapers 

def _scrape_rbi(query: str, pdf_dir: Path) -> list[ScrapedDocument]:
   
    docs = []
    urls_to_try = [
        "https://www.rbi.org.in/Scripts/AnnualReportPublications.aspx",
        "https://www.rbi.org.in/Scripts/PublicationsView.aspx?id=21803",
        "https://rbidocs.rbi.org.in/rdocs/Publications/PDFs/",
    ]

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
                    href = "https://www.rbi.org.in" + href
                title = a.get_text(strip=True) or Path(href).stem
                if query.lower().split()[0] in title.lower() or query.lower().split()[0] in href.lower():
                    pdf_links.append((title, href))

        
        if not pdf_links:
            resp2 = requests.get(urls_to_try[0], headers=HEADERS, timeout=REQUEST_TIMEOUT)
            soup2 = BeautifulSoup(resp2.text, "html.parser")
            for a in soup2.find_all("a", href=True):
                href = a["href"]
                if href.lower().endswith(".pdf"):
                    if not href.startswith("http"):
                        href = "https://www.rbi.org.in" + href
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
    """
    Scrape India Budget documents from indiabudget.gov.in.
    Budget documents are always publicly listed with direct PDF links.
    """
    docs = []

    # Known direct URLs for recent budget documents
    budget_pages = [
        "https://www.indiabudget.gov.in/doc/Budget_Speech.pdf",
        "https://www.indiabudget.gov.in/doc/rec/allsbe.pdf",
        "https://www.indiabudget.gov.in/economicsurvey.php",
        "https://www.indiabudget.gov.in/",
    ]

    try:
        # Try the main budget page first
        logger.info("[Budget] Fetching budget documents listing")
        resp = requests.get(budget_pages[3], headers=HEADERS, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        pdf_links = []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if href.lower().endswith(".pdf"):
                if not href.startswith("http"):
                    href = "https://www.indiabudget.gov.in" + href
                title = a.get_text(strip=True) or Path(href).stem
                pdf_links.append((title, href))

        # Also try known direct PDFs
        known_docs = [
            ("Union Budget Speech", "https://www.indiabudget.gov.in/doc/Budget_Speech.pdf"),
            ("Budget at a Glance", "https://www.indiabudget.gov.in/doc/rec/allsbe.pdf"),
        ]

        for title, url in known_docs:
            if url not in [l[1] for l in pdf_links]:
                pdf_links.append((title, url))

        logger.info("[Budget] Found %d PDF links", len(pdf_links))

        # Filter by query if possible
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
    bills_url = "https://sansad.in/ls/bills"

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
                    href = "https://sansad.in" + href
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
    search_url = f"https://www.niti.gov.in/search/node/{query.replace(' ', '%20')}"

    try:
        logger.info("[NITI] Searching: %s", search_url)
        resp = requests.get(search_url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        pdf_links = []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if href.lower().endswith(".pdf"):
                if not href.startswith("http"):
                    href = "https://www.niti.gov.in" + href
                title = a.get_text(strip=True) or Path(href).stem
                pdf_links.append((title, href))

        logger.info("[NITI] Found %d PDF links", len(pdf_links))

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
            "Economic Survey 2023-24 Volume 1",
            "https://www.indiabudget.gov.in/economicsurvey/doc/eschapter/echap01.pdf",
        ),
        (
            "Medium Term Fiscal Policy Statement",
            "https://www.indiabudget.gov.in/doc/rec/MTFPS.pdf",
        ),
        (
            "Macro Economic Framework Statement",
            "https://www.indiabudget.gov.in/doc/rec/mefs.pdf",
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


# Download helper 

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


# Public interface 

class GovScraper:
    
    def __init__(self, pdf_dir: Path):
        self.pdf_dir = pdf_dir
        self.pdf_dir.mkdir(parents=True, exist_ok=True)

    def scrape(
        self,
        query: str,
        sources: list[str] | None = None,
    ) -> list[ScrapedDocument]:
        sources = sources or ["rbi", "budget", "sansad", "niti", "finmin"]

        source_map = {
            "rbi":    lambda: _scrape_rbi(query, self.pdf_dir),
            "budget": lambda: _scrape_budget(query, self.pdf_dir),
            "sansad": lambda: _scrape_sansad(query, self.pdf_dir),
            "niti":   lambda: _scrape_niti(query, self.pdf_dir),
            "finmin": lambda: _scrape_finmin(query, self.pdf_dir),
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