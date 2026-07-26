#!/usr/bin/env python3
"""
Validate the 40-item golden evaluation set and report human-verification status.

Run from the HomeBoot repository root:
    python evaluation/check_golden_set.py

Optional:
    python evaluation/check_golden_set.py --show-all
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any


EXPECTED_CATEGORY_COUNTS = {
    "single_hop_factual": 15,
    "multi_hop": 6,
    "comparative": 4,
    "temporal": 4,
    "unanswerable": 8,
    "ambiguous_adversarial": 3,
}

EXPECTED_SPLIT_COUNTS = {
    "dev": 24,
    "test": 16,
}


def load_items(path: Path) -> list[dict[str, Any]]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise SystemExit(f"ERROR: File not found: {path}")
    except json.JSONDecodeError as exc:
        raise SystemExit(
            f"ERROR: Invalid JSON in {path} at line {exc.lineno}, "
            f"column {exc.colno}: {exc.msg}"
        )

    if not isinstance(data, list):
        raise SystemExit("ERROR: golden_queries.json must contain a JSON array.")

    return data


def quote_word_count(quote: str) -> int:
    return len(quote.split())


def validate_item(item: dict[str, Any], index: int) -> list[str]:
    errors: list[str] = []
    item_id = item.get("id", f"item #{index}")

    required_fields = {
        "id",
        "query",
        "category",
        "expected_category",
        "gold_answer",
        "source_urls",
        "evidence_quotes",
        "searched_terms",
        "split",
        "human_verified",
    }

    missing = sorted(required_fields - item.keys())
    if missing:
        errors.append(f"{item_id}: missing fields: {', '.join(missing)}")
        return errors

    if not isinstance(item["human_verified"], bool):
        errors.append(f"{item_id}: human_verified must be true or false.")

    if item["split"] not in EXPECTED_SPLIT_COUNTS:
        errors.append(f"{item_id}: invalid split '{item['split']}'.")

    if item["category"] not in EXPECTED_CATEGORY_COUNTS:
        errors.append(f"{item_id}: invalid category '{item['category']}'.")

    if not isinstance(item["source_urls"], list):
        errors.append(f"{item_id}: source_urls must be a list.")

    if not isinstance(item["evidence_quotes"], list):
        errors.append(f"{item_id}: evidence_quotes must be a list.")
    else:
        for quote_number, quote in enumerate(item["evidence_quotes"], start=1):
            if not isinstance(quote, str):
                errors.append(
                    f"{item_id}: evidence quote {quote_number} must be text."
                )
                continue

            words = quote_word_count(quote)
            if words > 25:
                errors.append(
                    f"{item_id}: evidence quote {quote_number} has "
                    f"{words} words; maximum is 25."
                )

    if not isinstance(item["searched_terms"], list):
        errors.append(f"{item_id}: searched_terms must be a list.")

    category = item["category"]

    if category == "unanswerable":
        if item["source_urls"]:
            errors.append(
                f"{item_id}: unanswerable item should not contain source URLs."
            )
        if item["evidence_quotes"]:
            errors.append(
                f"{item_id}: unanswerable item should not contain evidence quotes."
            )
        if not item["searched_terms"]:
            errors.append(
                f"{item_id}: unanswerable item must record searched_terms."
            )

    elif category == "ambiguous_adversarial":
        # These questions test clarification, safe refusal, near-miss terminology,
        # or prompt-injection handling. Sources are optional.
        pass

    else:
        if not item["source_urls"]:
            errors.append(
                f"{item_id}: answerable item must contain at least one source URL."
            )
        if not item["evidence_quotes"]:
            errors.append(
                f"{item_id}: answerable item must contain evidence."
            )

    if category == "multi_hop":
        if len(item["source_urls"]) < 2:
            errors.append(
                f"{item_id}: multi-hop item must use at least two source URLs."
            )
        if len(item["evidence_quotes"]) < 2:
            errors.append(
                f"{item_id}: multi-hop item must include at least two evidence quotes."
            )

    return errors


def print_count_check(
    title: str,
    actual: Counter[str],
    expected: dict[str, int],
) -> bool:
    passed = True
    print(f"\n{title}")
    print("-" * len(title))

    for name, expected_count in expected.items():
        actual_count = actual.get(name, 0)
        marker = "PASS" if actual_count == expected_count else "FAIL"
        print(
            f"{marker:4}  {name:24} "
            f"{actual_count:2}/{expected_count:2}"
        )
        if actual_count != expected_count:
            passed = False

    return passed


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate golden_queries.json and display verification status."
    )
    parser.add_argument(
        "--file",
        type=Path,
        default=Path(__file__).with_name("golden_queries.json"),
        help="Path to golden_queries.json",
    )
    parser.add_argument(
        "--show-all",
        action="store_true",
        help="Show both verified and unverified item IDs.",
    )
    args = parser.parse_args()

    items = load_items(args.file)

    print("=" * 64)
    print("GOLDEN EVALUATION SET CHECK")
    print("=" * 64)
    print(f"File: {args.file}")
    print(f"Total items: {len(items)}")

    category_counts = Counter(item.get("category") for item in items)
    split_counts = Counter(item.get("split") for item in items)

    total_ok = len(items) == 40
    print(f"{'PASS' if total_ok else 'FAIL'}  Required total: {len(items)}/40")

    category_ok = print_count_check(
        "Category counts",
        category_counts,
        EXPECTED_CATEGORY_COUNTS,
    )

    split_ok = print_count_check(
        "Dev/test split",
        split_counts,
        EXPECTED_SPLIT_COUNTS,
    )

    validation_errors: list[str] = []
    ids: list[str] = []

    for index, item in enumerate(items, start=1):
        item_id = str(item.get("id", f"item-{index}"))
        ids.append(item_id)
        validation_errors.extend(validate_item(item, index))

    duplicate_ids = sorted(
        item_id for item_id, count in Counter(ids).items() if count > 1
    )

    for duplicate_id in duplicate_ids:
        validation_errors.append(f"Duplicate ID: {duplicate_id}")

    verified = [
        item for item in items if item.get("human_verified") is True
    ]

    unverified = [
        item for item in items if item.get("human_verified") is not True
    ]

    print("\nHuman verification")
    print("------------------")
    print(f"Verified:     {len(verified)}/{len(items)}")
    print(f"Not verified: {len(unverified)}/{len(items)}")

    if args.show_all and verified:
        print("\nVerified items:")
        for item in verified:
            print(
                f"  YES  {item.get('id')} | "
                f"{item.get('category')} | {item.get('query')}"
            )

    if unverified:
        print("\nItems still requiring human verification:")
        for item in unverified:
            print(
                f"  NO   {item.get('id')} | "
                f"{item.get('category')} | {item.get('query')}"
            )

    print("\nSchema and evidence validation")
    print("------------------------------")

    if validation_errors:
        for error in validation_errors:
            print(f"FAIL  {error}")
    else:
        print("PASS  All required fields and evidence rules are valid.")

    all_verified = not unverified

    structural_ok = (
        total_ok
        and category_ok
        and split_ok
        and not validation_errors
    )

    print("\nFinal status")
    print("------------")
    print("STRUCTURE: " + ("READY" if structural_ok else "NOT READY"))
    print("HUMAN REVIEW: " + ("COMPLETE" if all_verified else "INCOMPLETE"))

    if structural_ok and all_verified:
        print("RESULT: Golden set is ready for final evaluation.")
        return 0

    if structural_ok:
        print(
            "RESULT: The set is structurally valid, but final testing must wait "
            "until every item is manually verified."
        )
        return 2

    print("RESULT: Fix the reported validation failures before evaluation.")
    return 1


if __name__ == "__main__":
    sys.exit(main())