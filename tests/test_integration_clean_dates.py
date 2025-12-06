from pathlib import Path

import pandas as pd

from smart_financial_parser.parser.ingest import read_csv
from smart_financial_parser.parser.normalize import parse_date


def test_clean_dates_for_messy_csv():
    csv_path = Path("data/messy_transactions.csv")
    assert csv_path.exists(), "expected data/messy_transactions.csv to exist"

    df = read_csv(str(csv_path))

    # Compute date_iso column
    df = df.copy()
    df["date_iso"] = df["date"].apply(parse_date)

    # Expected outputs per row (in the same order as the CSV)
    # Expected outputs based on current `data/messy_transactions.csv` parsing
    expected = [
        "2023-01-01",
        "2023-01-02",
        "2023-01-03",
        "2023-01-04",
        "2023-01-05",
        "2025-01-06",
        "2023-01-07",
        "2023-01-08",
        "2023-01-09",
        "2023-01-10",
        "2023-11-01",
        "2023-01-12",
        "2023-01-13",
        "2023-01-14",
        "2023-01-15",
        "2023-01-16",
        "2023-01-17",
        "2023-01-18",
        "2023-01-19",
        "2023-01-20",
        "2023-01-21",
        "2023-01-22",
        "2023-01-23",
        "2023-01-24",
        "2023-01-25",
        "2023-01-26",
        "2023-01-27",
        "2023-01-28",
        "2023-01-29",
        "2023-01-30",
        "2023-01-31",
        "2023-02-01",
        "2023-02-02",
        "2023-02-03",
        "2023-02-04",
        "2023-02-05",
    ]

    got = list(df["date_iso"].astype(object).where(pd.notna(df["date_iso"]), None))

    assert got == expected
