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
    expected = [
        "2023-01-01",
        "2023-01-01",
        "2023-01-02",
        "2023-03-03",
        "2023-04-05",
        "2023-05-06",
        "2023-06-07",
        "2023-08-01",
        "2023-08-05",
        "2023-09-10",
        "2023-12-31",
        "2023-11-01",
        "2023-10-10",
        None,
        "2023-12-01",
        "2023-04-01",
        "2023-12-31",
        "1949-01-02",
    ]
    # Expected dates for appended messy rows
    expected.extend([
        "2024-01-15",
        "2024-02-20",
        "2024-03-10",
        "2024-04-18",
        "2024-05-22",
        "2024-06-30",
        "2024-07-07",
    ])

    got = list(df["date_iso"].astype(object).where(pd.notna(df["date_iso"]), None))

    assert got == expected
