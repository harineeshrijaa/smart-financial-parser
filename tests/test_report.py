from pathlib import Path
import json
from decimal import Decimal

import pandas as pd

from smart_financial_parser.parser.report import build_report_from_dataframe, write_report_json


def test_build_report_from_dataframe_simple(tmp_path):
    df = pd.DataFrame([
        {"merchant": "Uber", "amount": "$10.00", "merchant_canonical": "Uber"},
        {"merchant": "Starbucks", "amount": "€5.00", "merchant_canonical": "Starbucks"},
        {"merchant": "Amazon", "amount": "USD20.00", "merchant_canonical": "Amazon"},
    ])

    report = build_report_from_dataframe(df)
    assert "top_category" in report
    assert "by_category" in report
    # write to file
    out = tmp_path / "report.json"
    write_report_json(report, str(out))
    assert out.exists()
    data = json.loads(out.read_text())
    assert "total_usd" in data


def test_build_report_tie_break_alphabetical():
    import pandas as pd

    # Two categories with equal USD totals; alphabetical tiebreak should choose 'Alpha'
    df = pd.DataFrame([
        {"merchant": "A", "amount": "$10.00", "merchant_canonical": "Alpha"},
        {"merchant": "B", "amount": "$10.00", "merchant_canonical": "Beta"},
    ])
    report = build_report_from_dataframe(df, group_by="merchant_canonical", round_digits=2)
    assert report["top_category"] == "Alpha"
