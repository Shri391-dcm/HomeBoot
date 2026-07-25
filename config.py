"""
Central configuration for the appliance support scraper/extractor/chunker.
Keeping every tunable in one file means the whole pipeline can be adjusted
(rate limit, chunk size, target brands) without touching the actual logic.
"""

from pathlib import Path

# --- Project paths -----------------------------------------------------
ROOT = Path(__file__).parent
RAW_DIR = ROOT / "data" / "raw"
EXTRACTED_DIR = ROOT / "data" / "extracted"
NORMALIZED_DIR = ROOT / "data" / "normalized"
CHUNKS_DIR = ROOT / "data" / "chunks"
LOG_DIR = ROOT / "logs"

for d in [RAW_DIR, EXTRACTED_DIR, NORMALIZED_DIR, CHUNKS_DIR, LOG_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# --- Crawl targets ------------------------------------------------------
# One seed URL per brand + category. Add more seeds here as you find them;
# the crawler will follow in-category links from each seed automatically.
SEEDS = {
    "whirlpool": {
        "washer": [
            "https://producthelp.whirlpool.com/Laundry/Washers",
        ],
        "refrigerator": [
            "https://producthelp.whirlpool.com/Refrigeration",
        ],
        "dishwasher": [
            "https://producthelp.whirlpool.com/Dishwashers",
        ],
    },
    "ge": {
        "washer": [
            "https://www.geappliances.com/ge/service-and-support/washers-dryers.htm",
            "https://www.geappliances.com/content/pdfs/GEA_CommLaundry_Launderday.pdf",
            "https://www.geappliances.com/content/pdfs/GEA_CommLaundry_SmartHQ.pdf",
            "https://www.geappliances.com/content/pdfs/GE_CL_PDP_VFW310SSRWW.pdf",
            "https://www.geappliances.com/content/pdfs/GE-Profile-PFQ97HSPVDS-Quick-Specs.pdf",
        ],
        "refrigerator": [
            "https://www.geappliances.com/ge/service-and-support/refrigerators-freezers.htm",
            "https://www.geappliances.com/content/migrated-assets/downloads/GEA-Refrigeration-R600a-Models.pdf",
        ],
        "dishwasher": [
            "https://www.geappliances.com/ge/service-and-support/dishwashers.htm",
            "https://www.geappliances.com/ge/service-and-support/faq-dishwasher.htm",
            "https://products.geappliances.com/appliance/gea-support-search-content?contentId=16240",
            "https://products.geappliances.com/appliance/gea-support-search-content?contentId=18921",
            "https://products.geappliances.com/appliance/gea-support-search-content?contentId=17452",
            "https://products.geappliances.com/appliance/gea-support-search-content?contentId=17380",
        ],
    },
}

# --- Crawl politeness ----------------------------------------------------
REQUEST_DELAY_SECONDS = 1.0        # minimum gap between requests to the same domain
USER_AGENT = "MSAI633-ApplianceSupportBot/1.0 (contact: mkolluru48935@ucumberlands.edu)"
REQUEST_TIMEOUT = 30
MAX_PAGES_PER_CATEGORY = 60        # crawl ceiling, keeps a bug from crawling the whole site

# --- Chunking -------------------------------------------------------------
FIXED_CHUNK_TOKENS = 400
FIXED_CHUNK_OVERLAP = 60
# Rough words-per-token ratio for English text, used since we chunk before
# tying the pipeline to any one tokenizer. Swap in a real tokenizer
# (e.g. tiktoken) later without changing anything upstream of chunk.py.
WORDS_PER_TOKEN = 0.75
