from typing import Optional
from decimal import Decimal
import re
import pandas as pd

# Seed mapping: canonical merchant -> category
# Keep this mapping small but cover common merchants used in the dataset.
merchant_to_category = {
    "Uber": "Transport",
    "Lyft": "Transport",
    "Starbucks": "Food",
    "Chipotle": "Food",
    "Swiss Bakery": "Food",
    "Whole Foods": "Groceries",
    "Walmart": "Groceries",
    "Neighborhood Grocery": "Groceries",
    "Corner Store": "Groceries",
    "Target": "Shopping",
    "Amazon": "Shopping",
    "Office Supplies": "Office",
    "Electro Depot": "Shopping",
    "Asia Imports": "Shopping",
    "Netflix": "Entertainment",
    "Spotify": "Entertainment",
    "Starz": "Entertainment",
    "Chipotle": "Food",
    "Shell": "Fuel",
    "ExxonMobil": "Fuel",
    "RentCo": "Housing",
    "Health Clinic": "Healthcare",
    "Pharmacy": "Healthcare",
    "Credit Card": "Debt",
    "LoanService": "Debt",
}


def categorize_row(merchant_canonical: Optional[str], raw_merchant: Optional[str]) -> Optional[str]:
    """Return a category string for a transaction using either the canonical merchant
    or heuristics on the raw merchant string.

    - Prefer `merchant_canonical` mapping when available.
    - Fall back to substring/regex heuristics on `raw_merchant` when canonical not present.
    - Returns None when no category could be determined.
    """
    # Prefer canonical mapping
    if merchant_canonical:
        cat = merchant_to_category.get(merchant_canonical)
        if cat:
            return cat

    if not raw_merchant:
        return None

    s = raw_merchant.lower()

    # Common heuristics (ordered by expected specificity)
    if re.search(r"\b(rent|landlord|lease)\b", s):
        return "Housing"
    if re.search(r"\b(atm|withdrawal)\b", s):
        return "Cash"
    if re.search(r"\b(uber|lyft|taxi|cab|ride)\b", s):
        return "Transport"
    if re.search(r"\b(starbuck|coffee|cafe)\b", s):
        return "Food"
    if re.search(r"\b(chipotl|chipotle)\b", s):
        return "Food"
    if re.search(r"\b(whole ?foods|wholefoods|grocery|market|grocer)\b", s):
        return "Groceries"
    if re.search(r"\b(wal-?mart|walmart|supercenter|super ctr|mart)\b", s):
        return "Groceries"
    if re.search(r"\b(target|tgt)\b", s):
        return "Shopping"
    if re.search(r"\b(amzn|amazon|mktp|marketplace)\b", s):
        return "Shopping"
    if re.search(r"\b(shell|exxon|mobil|petrol|gasoline|gas)\b", s):
        return "Fuel"
    if re.search(r"\b(pharmacy|cv s|walgreens|drug)\b", s):
        return "Healthcare"
    if re.search(r"\b(clinic|hospital|health)\b", s):
        return "Healthcare"
    if re.search(r"\b(netflix|spotify|hulu|prime video|itunes|amazon prime)\b", s):
        return "Entertainment"
    if re.search(r"\b(subscription|subscr|membership|prime)\b", s):
        return "Subscription"
    if re.search(r"\b(loan|payment to|loanservice|student loan|cc payment|credit card)\b", s):
        return "Debt"
    if re.search(r"\b(office|supplies|stationery|staples)\b", s):
        return "Office"
    if re.search(r"\b(bakery|boulangerie|bakery)\b", s):
        return "Food"
    if re.search(r"\b(cinema|movie|cineplex|theatre|theater)\b", s):
        return "Entertainment"

    # Last resort: try to match any canonical key contained in raw_merchant
    for canon in merchant_to_category:
        if canon.lower() in s:
            return merchant_to_category[canon]

    return None


def categorize_dataframe(df: pd.DataFrame, merchant_col: str = "merchant", canonical_col: str = "merchant_canonical") -> pd.DataFrame:
    """Return a copy of the DataFrame with a `category` column added.

    Logic:
    - If `canonical_col` exists and is non-null, use it to map categories.
    - Otherwise use heuristics on `merchant_col`.
    """
    out = df.copy()

    def _cat_row(r):
        canonical = None
        raw = None
        if canonical_col in r and pd.notna(r[canonical_col]):
            canonical = r[canonical_col]
        if merchant_col in r and pd.notna(r[merchant_col]):
            raw = r[merchant_col]
        return categorize_row(canonical, raw)

    out["category"] = out.apply(_cat_row, axis=1)
    return out

