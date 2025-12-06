import os
import json

import pytest

from smart_financial_parser.parser.normalize import normalize_merchant, _HAS_RAPIDFUZZ


def _load_merchant_map():
    here = os.path.abspath(os.path.dirname(__file__))
    # data directory is sibling to tests
    merchant_file = os.path.normpath(os.path.join(here, "..", "data", "merchants.json"))
    if not os.path.exists(merchant_file):
        # fallback to repo-root-relative path
        merchant_file = os.path.normpath(os.path.join(here, "..", "..", "data", "merchants.json"))
    with open(merchant_file, "r", encoding="utf-8") as fh:
        return json.load(fh)


@pytest.fixture(scope="module")
def merchant_map():
    return _load_merchant_map()


def test_exact_alias_uber(merchant_map):
    canonical, score = normalize_merchant("UBER *TRIP", merchant_map)
    assert canonical == "Uber"
    assert score == 100


def test_alias_variants_uber(merchant_map):
    canonical, score = normalize_merchant("Uber*Eats", merchant_map)
    assert canonical == "Uber"
    assert score == 100


def test_canonical_name(merchant_map):
    canonical, score = normalize_merchant("Uber", merchant_map)
    assert canonical == "Uber"
    assert score == 100


def test_walmart_store_number(merchant_map):
    canonical, score = normalize_merchant("WALMART #1234", merchant_map)
    assert canonical == "Walmart"
    assert score == 100


def test_shell_variants(merchant_map):
    canonical, score = normalize_merchant("SHELL OIL CO.", merchant_map)
    assert canonical == "Shell"
    assert score == 100


def test_corner_store_punctuation(merchant_map):
    canonical, score = normalize_merchant("Corner.Store", merchant_map)
    assert canonical == "Corner Store"
    assert score == 100


def test_neighborhood_grocery_with_number(merchant_map):
    canonical, score = normalize_merchant("Neighborhood Grocery #22", merchant_map)
    assert canonical == "Neighborhood Grocery"
    assert score == 100


def test_unknown_merchant_returns_none(merchant_map):
    canonical, score, issues = normalize_merchant("Some Random Vendor 999", merchant_map, return_issues=True)
    assert canonical is None
    # Depending on fuzzy-matching availability and accidental low-similarity hits,
    # we accept either a true 'no_match' (score==0) or a low-confidence fuzzy result
    # (score>0 but below threshold). Ensure the reported issue reflects that.
    if score == 0:
        assert "no_match" in issues
    else:
        assert score < 85
        assert "low_confidence" in issues


def test_fuzzy_typo_matches_amazon_when_available(merchant_map):
    # a slightly different string that should fuzzy-match to Amazon
    raw = "AMZN Mkt US"
    canonical, score, issues = normalize_merchant(raw, merchant_map, threshold=70, return_issues=True)
    if _HAS_RAPIDFUZZ:
        assert canonical == "Amazon"
        assert score >= 70
        assert "fuzzy_matched" in issues
    else:
        # without rapidfuzz we may not fuzzy-match; accept either a match or no match
        assert (canonical == "Amazon" and score >= 70) or canonical is None
