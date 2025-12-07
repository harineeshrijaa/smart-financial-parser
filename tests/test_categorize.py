import pandas as pd

from smart_financial_parser.parser.categorize import categorize_row, categorize_dataframe


def test_categorize_row_with_canonical():
    assert categorize_row("Uber", None) == "Transport"
    assert categorize_row("Starbucks", None) == "Food"


def test_categorize_row_from_raw_heuristics():
    assert categorize_row(None, "UBER *TRIP") == "Transport"
    assert categorize_row(None, "Amazon.com Marketplace") == "Shopping"
    assert categorize_row(None, "Starbucks #4421") == "Food"
    assert categorize_row(None, "ATM Withdrawal") == "Cash"
    assert categorize_row(None, "Monthly Rent - Landlord") == "Housing"
    # ExxonMobil combined token should be found via canonical fallback
    assert categorize_row(None, "EXXONMOBIL 44543354") == "Fuel"


def test_categorize_row_returns_none_when_unknown():
    assert categorize_row(None, "Some Weird Unknown Merchant") is None


def test_categorize_dataframe_adds_category_column():
    df = pd.DataFrame([
        {"merchant": "UBER *TRIP", "merchant_canonical": None},
        {"merchant": "Starbucks #4421", "merchant_canonical": None},
        {"merchant": "EXXONMOBIL 44543354", "merchant_canonical": None},
        {"merchant": "Rent - Landlord", "merchant_canonical": None},
        {"merchant": "Unknown Co", "merchant_canonical": None},
    ])

    out = categorize_dataframe(df)
    assert "category" in out.columns
    assert out.loc[0, "category"] == "Transport"
    assert out.loc[1, "category"] == "Food"
    assert out.loc[2, "category"] == "Fuel"
    assert out.loc[3, "category"] == "Housing"
    assert out.loc[4, "category"] is None


def test_canonical_priority_and_fallback():
    # When canonical maps exist, they take priority over raw
    assert categorize_row("Uber", "Starbucks #1") == "Transport"

    # If canonical is provided but not in the mapping, fall back to heuristics on raw
    assert categorize_row("UnknownBrand", "Starbucks #1") == "Food"


def test_whitespace_punctuation_and_case_insensitivity():
    assert categorize_row(None, "  starBUCKS-COFFEE/STM  ") == "Food"
    assert categorize_row(None, "cVs/pharmacy #123") == "Healthcare"


def test_subscription_and_entertainment_edgecases():
    # 'netflix' should map to Entertainment via explicit regex
    assert categorize_row(None, "Netflix.com subscription") == "Entertainment"
    # 'subscription' without brand should map to Subscription
    assert categorize_row(None, "Monthly subscription fee") == "Subscription"


def test_office_supplies_and_bakery():
    assert categorize_row(None, "Staples - Office Supplies") == "Office"
    assert categorize_row(None, "La Boulangerie Bakery") == "Food"


def test_canonical_case_variants_and_missing_raw():
    # canonical lookup is case-sensitive (keys are title-cased). If canonical is lowercase and raw absent, returns None
    assert categorize_row("uber", None) is None


def test_dataframe_respects_canonical_over_raw():
    df = pd.DataFrame([
        {"merchant": "Starbucks Reserve", "merchant_canonical": "Whole Foods"},
        {"merchant": "WAL-MART SUPERCENTER 3301", "merchant_canonical": None},
    ])
    out = categorize_dataframe(df)
    # canonical provided -> Groceries
    assert out.loc[0, "category"] == "Groceries"
    # raw heuristic -> Groceries
    assert out.loc[1, "category"] == "Groceries"
