from pathlib import Path

import pandas as pd

from smart_financial_parser.parser.ingest import read_csv
from smart_financial_parser.parser.normalize import parse_amount


def test_clean_amounts_for_messy_csv():
    csv_path = Path("data/messy_transactions.csv")
    assert csv_path.exists(), "expected data/messy_transactions.csv to exist"

    df = read_csv(str(csv_path))
    df = df.copy()
    df[["amount_decimal", "currency"]] = df["amount"].apply(lambda s: pd.Series(parse_amount(s)))

    # Expected outputs based on the current `data/messy_transactions.csv` parsing.
    expected = [
        ("-12.50", "EUR"),
        ("13.00", "USD"),
        ("25.4", "GBP"),
        ("25.40", "EUR"),
        ("12", "USD"),
        ("-54.20", "INR"),
        ("19.99", "EUR"),
        ("23.10", "CAD"),
        ("-102.33", "USD"),
        ("98.1", "JPY"),
        ("-101.05", "GBP"),
        ("14.22", "EUR"),
        ("-120.00", "USD"),
        ("14.99", None),
        ("-9.99", "EUR"),
        ("-9.99", "GBP"),
        ("11.30", "USD"),
        ("12.00", "AUD"),
        ("-10.5", "EUR"),
        ("45.00", "USD"),
        ("46.20", "JPY"),
        ("44.10", None),
        ("-73.90", "USD"),
        ("75.00", "JPY"),
        ("-80.45", "GBP"),
        ("1234.56", "EUR"),
        ("123.4", "ETH"),
        ("15.00", "USD"),
        ("45.000", "CAD"),
        ("1234.5", "EUR"),
        ("10.00", "USD"),
        ("-9.99", "INR"),
        ("14.2", "EUR"),
        ("40", "GBP"),
        ("475", "GBP"),
        ("-4.75", "AUD"),
    ]

    got = []
    for v, c in zip(df["amount_decimal"].tolist(), df["currency"].tolist()):
        if v is None or (isinstance(v, float) and pd.isna(v)):
            got.append((None, None))
        else:
            # Convert Decimal to string to compare easily
            got.append((str(v), c))

    assert got == expected
