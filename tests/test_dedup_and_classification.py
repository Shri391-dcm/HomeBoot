"""
Tests for content-hash deduplication and support type classification.
"""

import json
import tempfile
from pathlib import Path

import pytest

# Add parent to path so imports work
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils import content_hash, already_processed, append_jsonl, read_jsonl
from extract import _detect_support_type
from scrape import infer_category_from_url


# ─── Deduplication Tests ────────────────────────────────────────────────────

class TestContentHash:
    def test_same_bytes_same_hash(self):
        data = b"Hello, appliance world!"
        assert content_hash(data) == content_hash(data)

    def test_different_bytes_different_hash(self):
        assert content_hash(b"page A") != content_hash(b"page B")

    def test_encoding_matters(self):
        # Same string, different encoding -> different bytes -> different hash
        text = "café"
        assert content_hash(text.encode("utf-8")) != content_hash(text.encode("latin-1"))


class TestAlreadyProcessed:
    def test_returns_false_for_missing_file(self, tmp_path):
        assert already_processed(tmp_path / "nope.jsonl", "http://x.com") is False

    def test_returns_true_when_url_present_and_ok(self, tmp_path):
        manifest = tmp_path / "manifest.jsonl"
        append_jsonl(manifest, {"url": "http://example.com/page", "status": "ok"})
        assert already_processed(manifest, "http://example.com/page") is True

    def test_returns_false_when_status_not_ok(self, tmp_path):
        manifest = tmp_path / "manifest.jsonl"
        append_jsonl(manifest, {"url": "http://example.com/page", "status": "error"})
        assert already_processed(manifest, "http://example.com/page") is False

    def test_returns_false_for_unseen_url(self, tmp_path):
        manifest = tmp_path / "manifest.jsonl"
        append_jsonl(manifest, {"url": "http://example.com/other", "status": "ok"})
        assert already_processed(manifest, "http://example.com/page") is False


# ─── Category inference tests ─────────────────────────────────────────────

class TestCategoryInference:
    def test_ge_refrigerator_url_infers_refrigerator(self):
        url = "https://www.geappliances.com/ge-appliances/kitchen/refrigerators/french-door-refrigerators/"
        assert infer_category_from_url(url) == "refrigerator"

    def test_ge_dishwasher_url_infers_dishwasher(self):
        url = "https://www.geappliances.com/ge/service-and-support/faq-dishwasher.htm"
        assert infer_category_from_url(url) == "dishwasher"

    def test_whirlpool_washer_url_infers_washer(self):
        url = "https://producthelp.whirlpool.com/Laundry/Washers"
        assert infer_category_from_url(url) == "washer"


# ─── Support Type Classification Tests ──────────────────────────────────────

class TestDetectSupportType:
    """Each test sends a minimal record + body and checks the label."""

    def _classify(self, url="", title="", body=""):
        record = {"url": url, "title": title}
        return _detect_support_type(record, body)

    # Error codes (highest priority)
    def test_error_code_from_body(self):
        assert self._classify(body="If you see error code F1 E2, unplug") == "error_code"

    def test_error_code_from_url(self):
        assert self._classify(url="https://whirlpool.com/error_code/f5.html") == "error_code"

    # Installation
    def test_installation_keyword(self):
        assert self._classify(body="How to install your new dishwasher") == "installation"

    def test_installation_setup(self):
        assert self._classify(title="Setup guide for washer") == "installation"

    # Troubleshooting
    def test_troubleshooting(self):
        assert self._classify(body="Washer not working? Try these steps") == "troubleshooting"

    def test_troubleshooting_wont(self):
        assert self._classify(body="Door won't close properly") == "troubleshooting"

    # Maintenance
    def test_maintenance_clean(self):
        assert self._classify(body="Clean the lint filter monthly") == "maintenance"

    def test_maintenance_affresh(self):
        assert self._classify(body="Use affresh tablets to deodorize") == "maintenance"

    # Warranty
    def test_warranty(self):
        assert self._classify(body="Your warranty coverage lasts 1 year") == "warranty"

    # Parts
    def test_parts(self):
        assert self._classify(body="Order replacement parts online") == "parts"

    # Safety
    def test_safety(self):
        assert self._classify(body="Safety hazard: keep children away") == "safety"

    # Specifications
    def test_specifications(self):
        assert self._classify(body="Dimensions: 27in wide, capacity 5.0 cu ft") == "specifications"

    # Manual (keyword)
    def test_manual_keyword(self):
        assert self._classify(body="Download the owner manual here") == "manual"

    # Manual (PDF fallback)
    def test_manual_pdf_fallback(self):
        record = {"url": "https://example.com/doc.pdf", "title": "Doc", "is_pdf": True}
        assert _detect_support_type(record, "some generic content") == "manual"

    # Usage
    def test_usage(self):
        assert self._classify(body="How to use the delicate cycle setting") == "usage"

    # FAQ
    def test_faq(self):
        assert self._classify(body="FAQ: frequently asked questions about your appliance") == "faq"

    # General fallback
    def test_general_support_fallback(self):
        assert self._classify(body="Welcome to our appliance brand page") == "general_support"

    # Priority: error_code beats troubleshooting
    def test_priority_error_over_troubleshooting(self):
        assert self._classify(body="Troubleshoot error code E1") == "error_code"

    # Priority: installation beats usage (setup keyword)
    def test_priority_install_over_usage(self):
        assert self._classify(body="Set up the cycle options during install") == "installation"
