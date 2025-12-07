import json
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Optional, Dict, Any

import pandas as pd

from .ingest import read_csv
from .normalize import parse_amount, convert_amount_to_usd
from .categorize import categorize_dataframe


def _to_number_for_json(d: Decimal) -> Any:
    """Convert Decimal to a JSON-serializable number (float when safe, else string)."""
    try:
        # avoid losing precision for very large numbers
        f = float(d)
        return f
    except Exception:
        return str(d)


def build_report_from_dataframe(df: pd.DataFrame, rates: Optional[Dict[str, Decimal]] = None, group_by: str = "category", round_digits: Optional[int] = 2) -> Dict[str, Any]:
    """Given a cleaned DataFrame with an `amount` column (raw), produce a USD-aggregated report.
    """
    if "amount_decimal" not in df.columns or "currency" not in df.columns:
        parsed = df["amount"].apply(lambda s: pd.Series(parse_amount(s)))
        parsed.columns = ["amount_decimal", "currency"]
        df = pd.concat([df.reset_index(drop=True), parsed.reset_index(drop=True)], axis=1)

    # Convert currency to USD
    usd_amounts = []
    for a, c in zip(df["amount_decimal"].tolist(), df["currency"].tolist()):
        usd = convert_amount_to_usd(a, c, rates=rates)
        usd_amounts.append(usd)
    df = df.copy()
    df["amount_usd"] = usd_amounts

    # Ensure categories via categorize_dataframe
    df_cat = categorize_dataframe(df)

    # Grouping column
    if group_by not in df_cat.columns:
        group_by = "category"

    group = df_cat.groupby(group_by, dropna=False)["amount_usd"].sum()

    # Convert group to list sorted by amount desc
    items = []
    total = Decimal(0)
    for k, v in group.items():
        if v is None:
            continue
        # pandas may return numpy types - coerce to Decimal
        try:
            dec = Decimal(str(v))
        except Exception:
            try:
                dec = Decimal(v)
            except Exception:
                continue
        items.append((k if pd.notna(k) else None, dec))
        total += dec

    # sort
    items.sort(key=lambda x: x[1], reverse=True)

    # Apply rounding (quantize) if requested
    if round_digits is not None:
        quant = Decimal(1).scaleb(-int(round_digits))
        rounded_items = []
        rounded_total = Decimal(0)
        for k, dec in items:
            try:
                dec_q = dec.quantize(quant, rounding=ROUND_HALF_UP)
            except Exception:
                dec_q = dec
            rounded_items.append((k, dec_q))
            rounded_total += dec_q
        items = rounded_items
        total = rounded_total

    by_category = []
    for k, dec in items:
        pct = float((dec / total)) if total != 0 else 0.0
        by_category.append({"category": k, "amount": _to_number_for_json(dec), "pct": pct})

    # Choose a top category. If multiple categories tie for the same top amount,
    # pick one deterministically using alphabetical order so the report is reproducible.
    if by_category:
        # items is sorted desc by amount; the top amount is items[0][1]
        top_amount = items[0][1]
        tied_categories = [k for k, dec in items if dec == top_amount]
        if tied_categories:
            # sort None safely by converting to empty string
            chosen = sorted(tied_categories, key=lambda x: "" if x is None else str(x))[0]
        else:
            chosen = by_category[0]["category"]
        top = next((b for b in by_category if b["category"] == chosen), by_category[0])
    else:
        top = {"category": None, "amount": 0, "pct": 0.0}

    report = {
        "top_category": top["category"],
        # `amount` kept for backward compatibility.
        "amount": top["amount"],
        # `top_amount` is a numeric value suitable for programmatic consumption.
        "top_amount": _to_number_for_json(top_amount),
        "by_category": by_category,
        "total_usd": _to_number_for_json(total),
    }
    return report


def build_report_from_csv(path: str, rates: Optional[Dict[str, Decimal]] = None, group_by: str = "category") -> Dict[str, Any]:
    p = Path(path)
    if not p.exists():
        raise ValueError(f"CSV path not found: {path}")
    df = read_csv(path)
    return build_report_from_dataframe(df, rates=rates, group_by=group_by)


def write_report_json(report: Dict[str, Any], out_path: str) -> None:
    p = Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)

    def _format_usd_value(v, use_symbol: bool = True, decimals: int = 2):
        # Convert numeric types to Decimal then format with commas and symbol
        if v is None:
            return None
        try:
            dec = Decimal(str(v))
        except Exception:
            return v
        quant = Decimal(1).scaleb(-int(decimals))
        try:
            dec_q = dec.quantize(quant, rounding=ROUND_HALF_UP)
        except Exception:
            dec_q = dec
        # Format with thousands separators
        try:
            s = f"{dec_q:,.{decimals}f}"
        except Exception:
            s = format(float(dec_q), f",.{decimals}f")
        if use_symbol:
            return f"${s}"
        else:
            return f"{s} USD"

    # Ensure all Decimal -> serializable; optionally format amounts for readability
    # shallow copy with formatted amount fields so the original report stays numeric.
    formatted_report = dict(report)
    # Format top amount and total
    if "amount" in formatted_report:
        formatted_report["amount"] = _format_usd_value(formatted_report["amount"]) if formatted_report["amount"] is not None else None
    if "total_usd" in formatted_report:
        formatted_report["total_usd"] = _format_usd_value(formatted_report["total_usd"]) if formatted_report["total_usd"] is not None else None

    # Format by_category amounts
    if "by_category" in formatted_report and isinstance(formatted_report["by_category"], list):
        b = []
        for entry in formatted_report["by_category"]:
            e = dict(entry)
            if "amount" in e:
                e["amount"] = _format_usd_value(e["amount"]) if e["amount"] is not None else None
            b.append(e)
        formatted_report["by_category"] = b

    with p.open("w", encoding="utf-8") as fh:
        json.dump(formatted_report, fh, indent=2)


def format_usd(value, use_symbol: bool = True, decimals: int = 2) -> str:
    """Format a numeric value as USD with thousands separators and a symbol or code.

    Returns a string like "$1,234.56" or "1,234.56 USD".
    """
    if value is None:
        return "None"
    try:
        dec = Decimal(str(value))
    except Exception:
        return str(value)
    quant = Decimal(1).scaleb(-int(decimals))
    try:
        dec_q = dec.quantize(quant, rounding=ROUND_HALF_UP)
    except Exception:
        dec_q = dec
    try:
        s = f"{dec_q:,.{decimals}f}"
    except Exception:
        s = format(float(dec_q), f",.{decimals}f")
    return f"${s}" if use_symbol else f"{s} USD"
import json
from decimal import Decimal
from typing import Any, Dict


def write_top_spending(summary: Dict[str, Any], path: str):
    # Convert Decimal to float for JSON
    def _default(o):
        if isinstance(o, Decimal):
            return float(o)
        raise TypeError

    with open(path, "w", encoding="utf-8") as f:
        json.dump(summary, f, default=_default, indent=2)
