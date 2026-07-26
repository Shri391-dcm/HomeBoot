"""
Stage 1: Scrape.

Crawls Whirlpool and GE Appliances support pages for the three target
categories (washer, refrigerator, dishwasher), staying inside robots.txt
rules and a strict rate limit. Saves every raw HTML page and PDF exactly
as received -- nothing is cleaned or parsed here -- so later stages can
be re-run against these raw files without ever hitting the network again.

Run: python scrape.py
"""
import ssl
import time
import urllib.robotparser as robotparser
from urllib.parse import urljoin, urlparse
import urllib.request
import certifi
import requests
from bs4 import BeautifulSoup

# Some Python installs (most commonly python.org's macOS installer) don't
# wire up the OS certificate store, so any HTTPS request -- including the
# one robotparser makes internally via urllib -- fails with
# "CERTIFICATE_VERIFY_FAILED: unable to get local issuer certificate".
# Pointing urllib explicitly at certifi's bundle fixes this regardless of
# whether a teammate has run their OS's cert-install step.
_ssl_context = ssl.create_default_context(cafile=certifi.where())
urllib.request.install_opener(
    urllib.request.build_opener(urllib.request.HTTPSHandler(context=_ssl_context))
)

from config import (
    SEEDS, RAW_DIR, LOG_DIR, USER_AGENT, REQUEST_DELAY_SECONDS,
    REQUEST_TIMEOUT, MAX_PAGES_PER_CATEGORY,
)
from utils import url_hash, content_hash, get_logger, append_jsonl, already_processed

logger = get_logger("scrape", LOG_DIR)
MANIFEST = RAW_DIR / "manifest.jsonl"

_robots_cache = {}
_last_request_time = {}


def _allowed(url: str) -> bool:
    domain = urlparse(url).netloc
    if domain not in _robots_cache:
        rp = robotparser.RobotFileParser()
        robots_url = f"https://{domain}/robots.txt"
        rp.set_url(robots_url)
        try:
            # Fetch robots.txt with requests (honours certifi CA bundle)
            # instead of rp.read() which uses urllib and may fail behind
            # corporate proxies that inject self-signed certificates.
            r = requests.get(robots_url, headers={"User-Agent": USER_AGENT},
                             timeout=REQUEST_TIMEOUT)
            if r.status_code == 404:
                # No robots.txt means no restrictions per the standard
                rp.parse([])  # empty rules = allow all
            else:
                r.raise_for_status()
                rp.parse(r.text.splitlines())
        except Exception as e:
            logger.warning(f"Could not read robots.txt for {domain}: {e}. Skipping domain.")
            _robots_cache[domain] = None
        else:
            _robots_cache[domain] = rp
    rp = _robots_cache[domain]
    if rp is None:
        return False  # fail closed: no robots.txt read, no crawl
    return rp.can_fetch(USER_AGENT, url)


def _rate_limit(domain: str):
    last = _last_request_time.get(domain, 0)
    wait = REQUEST_DELAY_SECONDS - (time.time() - last)
    if wait > 0:
        time.sleep(wait)
    _last_request_time[domain] = time.time()


def _fetch(url: str) -> requests.Response | None:
    domain = urlparse(url).netloc
    if not _allowed(url):
        logger.info(f"Blocked by robots.txt, skipping: {url}")
        return None
    _rate_limit(domain)
    try:
        resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        return resp
    except requests.RequestException as e:
        logger.warning(f"Fetch failed for {url}: {e}")
        return None


def _save_raw(url: str, content: bytes, is_pdf: bool, brand: str, category: str) -> str:
    ext = "pdf" if is_pdf else "html"
    out_dir = RAW_DIR / brand / category
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{url_hash(url)}.{ext}"
    path.write_bytes(content)
    return str(path)


def infer_category_from_url(url: str) -> str:
    """Infer the appliance category from a URL when possible."""
    path = urlparse(url).path.lower()
    if any(k in path for k in ["dishwasher", "dishwashers"]):
        return "dishwasher"
    if any(k in path for k in ["refrigerator", "refrigerators", "freezer", "freezers"]):
        return "refrigerator"
    if any(k in path for k in ["washer", "laundry", "washers", "dryer", "dryers"]):
        return "washer"
    return ""


def _in_category_links(base_url: str, html: str, category: str) -> list[str]:
    """Follow only links that look like troubleshooting/support pages on
    the same domain and likely belong to the target category."""
    soup = BeautifulSoup(html, "html.parser")
    domain = urlparse(base_url).netloc
    links = []
    for a in soup.find_all("a", href=True):
        href = urljoin(base_url, a["href"])
        parsed = urlparse(href)
        if parsed.netloc != domain:
            continue
        path_lower = parsed.path.lower()
        inferred_category = infer_category_from_url(href)
        if inferred_category and inferred_category != category:
            continue
        if any(k in path_lower for k in ["troubleshoot", "support", "error", "manual", "guide",
                                            "laundry", "washer", "kitchen", "dishwasher",
                                            "refrigerat", "service-and-support",
                                            "front_load", "top_load", "compact",
                                            "product_info", "faq",
                                            "gea-support"]):
            links.append(href.split("#")[0])
    return list(dict.fromkeys(links))  # de-dupe, keep order


def crawl_category(brand: str, category: str, seeds: list[str]):
    visited = set()
    queue = list(seeds)

    while queue and len(visited) < MAX_PAGES_PER_CATEGORY:
        url = queue.pop(0)
        if url in visited or already_processed(MANIFEST, url):
            continue
        visited.add(url)

        resp = _fetch(url)
        if resp is None:
            append_jsonl(MANIFEST, {"url": url, "brand": brand, "category": category, "status": "failed"})
            continue

        is_pdf = "application/pdf" in resp.headers.get("Content-Type", "") or url.lower().endswith(".pdf")
        local_path = _save_raw(url, resp.content, is_pdf, brand, category)

        append_jsonl(MANIFEST, {
            "url": url, "brand": brand, "category": category,
            "local_path": local_path, "is_pdf": is_pdf,
            "content_hash": content_hash(resp.content),
            "scraped_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "status": "ok",
        })
        logger.info(f"Saved [{brand}/{category}] {url} -> {local_path}")

        if not is_pdf:
            for link in _in_category_links(url, resp.text, category):
                if link not in visited:
                    queue.append(link)


def main():
    for brand, categories in SEEDS.items():
        for category, seeds in categories.items():
            logger.info(f"Starting crawl: {brand}/{category}")
            crawl_category(brand, category, seeds)


if __name__ == "__main__":
    main()
