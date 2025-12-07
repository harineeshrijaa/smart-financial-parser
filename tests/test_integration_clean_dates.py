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
        "1998-02-03",
        "1989-01-03",
        "2014-07-04",
        "1999-01-05",
        "2002-01-06",
        "1987-01-07",
        "2015-02-08",
        "2001-12-09",
        "2012-01-10",
        "1930-11-01",
        "1994-01-12",
        "2024-01-13",
        "1997-03-14",
        "2003-01-15",
        "2014-06-16",
        "2011-11-17",
        "1927-01-18",
        "1990-01-19",
        "1999-01-20",
        "2004-01-21",
        "1988-01-22",
        "1975-01-23",
        "2003-01-24",
        "1989-01-25",
        "2005-01-26",
        "1999-01-27",
        "2019-01-28",
        "2014-01-29",
        "2012-01-30",
        "2010-01-31",
        "2022-02-01",
        "1996-02-02",
        "1985-02-03",
        "2009-02-04",
        "1983-02-05",
    ]

    got = list(df["date_iso"].astype(object).where(pd.notna(df["date_iso"]), None))

    assert got == expected
