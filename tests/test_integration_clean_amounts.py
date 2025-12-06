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

    expected = [
        ("12.50", "USD"),
        ("12.50", "USD"),
        ("8.00", "GBP"),
        ("123.45", "USD"),
        ("45.00", "USD"),
        ("-200.00", None),
        ("4500.00", "USD"),
        ("12.00", "USD"),
        ("15.99", "USD"),
        ("-32.00", "USD"),
        ("9.99", "EUR"),
        ("12.50", "USD"),
        (None, None),
        ("10.00", "USD"),
        ("1200", "JPY"),
        (None, None),
        ("5.00", "USD"),
        ("12.99", "USD"),
    ]
    # Additional rows appended to the CSV (new messy rows):
    expected.extend([
        ("1234.56", None),
        ("1234.56", None),
        ("1234.56", "CHF"),
        ("1234.56", "USD"),
        ("1234.56", None),
        ("1234.56", None),
        ("12", "USD"),
    ])

    got = []
    for v, c in zip(df["amount_decimal"].tolist(), df["currency"].tolist()):
        if v is None or (isinstance(v, float) and pd.isna(v)):
            got.append((None, None))
        else:
            # Convert Decimal to string to compare easily
            got.append((str(v), c))

    assert got == expected
