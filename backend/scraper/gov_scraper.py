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

# ── Config ────────────────────────────────────────────────────────────────────

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

REQUEST_TIMEOUT  = 15   
DOWNLOAD_DELAY   = 1.5   
MAX_PDFS_PER_SOURCE = 5  


# Data model 

@dataclass
class ScrapedDocument:
    title:        str
    source_url:   str
    source_site:  str
    file_path:    str
    downloaded_at:str
    file_size_kb: float


# Individual scrapers 

def _scrape_cag(query: str, pdf_dir: Path) -> list[ScrapedDocument]:
    
    docs = []
    search_url = f"https://cag.gov.in/en/search?query={query.replace(' ', '+')}"

    try:
        logger.info("[CAG] Searching: %s", search_url)
        resp = requests.get(search_url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")

        pdf_links = []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if href.lower().endswith(".pdf"):
                if not href.startswith("http"):
                    href = "https://cag.gov.in" + href
                title = a.get_text(strip=True) or Path(href).stem
                pdf_links.append((title, href))

        logger.info("[CAG] Found %d PDF links", len(pdf_links))

        for title, url in pdf_links[:MAX_PDFS_PER_SOURCE]:
            doc = _download_pdf(
                title=title,
                url=url,
                source_site="cag.gov.in",
                pdf_dir=pdf_dir,
            )
            if doc:
                docs.append(doc)
            time.sleep(DOWNLOAD_DELAY)

    except requests.RequestException as e:
        logger.warning("[CAG] Request failed: %s", e)

    return docs


def _scrape_prs(query: str, pdf_dir: Path) -> list[ScrapedDocument]:
    
    docs = []
    search_url = f"https://prsindia.org/search?query={query.replace(' ', '+')}"

    try:
        logger.info("[PRS] Searching: %s", search_url)
        resp = requests.get(search_url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")

        pdf_links = []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if href.lower().endswith(".pdf"):
                if not href.startswith("http"):
                    href = "https://prsindia.org" + href
                title = a.get_text(strip=True) or Path(href).stem
                pdf_links.append((title, href))

        logger.info("[PRS] Found %d PDF links", len(pdf_links))

        for title, url in pdf_links[:MAX_PDFS_PER_SOURCE]:
            doc = _download_pdf(
                title=title,
                url=url,
                source_site="prsindia.org",
                pdf_dir=pdf_dir,
            )
            if doc:
                docs.append(doc)
            time.sleep(DOWNLOAD_DELAY)

    except requests.RequestException as e:
        logger.warning("[PRS] Request failed: %s", e)

    return docs


def _scrape_data_gov(query: str, pdf_dir: Path) -> list[ScrapedDocument]:
    
    docs = []
    api_url = "https://data.gov.in/api/datastore/resource.json"

    try:
        logger.info("[data.gov.in] Searching: %s", query)
        resp = requests.get(
            api_url,
            params={"q": query, "limit": MAX_PDFS_PER_SOURCE},
            headers=HEADERS,
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()

        records = data.get("records", [])
        logger.info("[data.gov.in] Found %d records", len(records))

        for record in records[:MAX_PDFS_PER_SOURCE]:
            # Records may contain direct PDF URLs in various fields
            for key, value in record.items():
                if isinstance(value, str) and value.lower().endswith(".pdf"):
                    doc = _download_pdf(
                        title=record.get("title", key),
                        url=value,
                        source_site="data.gov.in",
                        pdf_dir=pdf_dir,
                    )
                    if doc:
                        docs.append(doc)
                    time.sleep(DOWNLOAD_DELAY)
                    break

    except requests.RequestException as e:
        logger.warning("[data.gov.in] Request failed: %s", e)

    return docs


# Download helper 

def _download_pdf(title: str, url: str, source_site: str, pdf_dir: Path,) -> ScrapedDocument | None:
    
    url_hash  = hashlib.md5(url.encode()).hexdigest()[:12]
    pdf_path  = pdf_dir / f"{url_hash}.pdf"
    meta_path = pdf_dir / f"{url_hash}.json"

    if pdf_path.exists():
        logger.info("[Scraper] Already have %s — skipping", url_hash)
        meta = json.loads(meta_path.read_text())
        return ScrapedDocument(**meta)

    try:
        logger.info("[Scraper] Downloading: %s", url)
        resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT, stream=True)
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

        logger.info(
            "[Scraper] Saved %s (%.1f KB) from %s",
            pdf_path.name, size_kb, source_site,
        )
        return doc

    except requests.RequestException as e:
        logger.warning("[Scraper] Failed to download %s: %s", url, e)
        return None


# Public interface 

class GovScraper:
    
    def __init__(self, pdf_dir: Path):
        self.pdf_dir = pdf_dir
        self.pdf_dir.mkdir(parents=True, exist_ok=True)

    def scrape(self, query: str, sources: list[str] | None = None,) -> list[ScrapedDocument]:
        
        sources = sources or ["cag", "prs", "data.gov.in"]
        all_docs = []

        source_map = {
            "cag":        lambda: _scrape_cag(query, self.pdf_dir),
            "prs":        lambda: _scrape_prs(query, self.pdf_dir),
            "data.gov.in": lambda: _scrape_data_gov(query, self.pdf_dir),
        }

        for source in sources:
            if source not in source_map:
                logger.warning("[Scraper] Unknown source '%s' — skipping", source)
                continue

            logger.info("[Scraper] Scraping %s for '%s'", source, query)
            docs = source_map[source]()
            all_docs.extend(docs)
            logger.info("[Scraper] Got %d docs from %s", len(docs), source)

        logger.info(
            "[Scraper] Total: %d documents downloaded for query '%s'",
            len(all_docs), query,
        )
        return all_docs