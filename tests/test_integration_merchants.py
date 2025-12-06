import os
import csv
import json

from smart_financial_parser.parser.normalize import normalize_merchant


def _load_merchant_map():
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    candidate = os.path.join(repo_root, "data", "merchants.json")
    if not os.path.exists(candidate):
        candidate = os.path.join(repo_root, "..", "data", "merchants.json")
    with open(candidate, "r", encoding="utf-8") as fh:
        return json.load(fh)


def test_normalize_against_messy_csv():
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    csv_path = os.path.join(repo_root, "data", "messy_transactions.csv")
    merchant_map = _load_merchant_map()

    expected = {
        # Uber variants
        "UBER *TRIP": "Uber",
        "Uber Technologies": "Uber",
        "UBER EATS": "Uber",
        "Uber*Eats": "Uber",
        "UBER TRIP ": "Uber",
        "Uber Eats": "Uber",
        # Target variants
        "TARGET #112": "Target",
        "TGT 445": "Target",
        "Target Store #112 ": "Target",
        # Walmart variants
        "WAL-MART SUPERCENTER 3301 ": "Walmart",
        "WALMART ": "Walmart",
        "Walmart Super Ctr": "Walmart",
        "Wal-Mart ": "Walmart",
        # Amazon / AMZN
        "Aｍａｚｏｎ MKTPLACE PMTS": "Amazon",
        "Amazon.Com ": "Amazon",
        "AMZN PRIME ": "Amazon",
        "AMAZON Mktp US": "Amazon",
        "A M A Z O N": "Amazon",
        # Spotify
        "SPOTIFY  USA": "Spotify",
        "Spotify ": "Spotify",
        "SPOTIFY": "Spotify",
        # Chipotle
        "CHIPOTLE #221": "Chipotle",
        "Chipotle Mexican Grill ": "Chipotle",
        "CHIPOTLE ": "Chipotle",
        "Chipotle": "Chipotle",
        # Exxon
        "EXXONMOBIL 44543354": "ExxonMobil",
        "Exxon ": "ExxonMobil",
        "EXXON MOBIL ": "ExxonMobil",
        "ExxonMobil": "ExxonMobil",
        # Whole Foods
        "WHOLEFDS MRKT 10203": "Whole Foods",
        "Whole Foods Market ": "Whole Foods",
        "WHOLE FOODS ": "Whole Foods",
        "Whole Foods": "Whole Foods",
        # Starbucks
        "Starbucks Coffee": "Starbucks",
        "STARBUCKS #4421": "Starbucks",
    }

    # Use a permissive threshold for integration checks (handles store numbers, fullwidth chars, short typos)
    check_threshold = 70
    with open(csv_path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            raw = row.get("merchant")
            canonical, score, issues = normalize_merchant(raw, merchant_map, threshold=check_threshold, return_issues=True)
            if raw in expected:
                assert canonical == expected[raw], f"Expected {expected[raw]} for {raw}, got {canonical} (score={score}, issues={issues})"
            else:
                # For other rows, ensure we don't falsely map known canonical names (conservative)
                if canonical is not None:
                    # allow mapping only if score >= check_threshold
                    assert score >= check_threshold, f"Unexpected mapping of {raw} -> {canonical} with low score {score}"
