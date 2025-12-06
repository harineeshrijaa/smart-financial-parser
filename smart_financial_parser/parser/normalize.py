import re
import warnings
from decimal import Decimal, InvalidOperation
from typing import Optional, Tuple

# dateparser emits a DeprecationWarning when parsing ambiguous day-of-month
# strings without an explicit year. Suppress that specific warning here so
# it doesn't surface during test runs; we'll still let other warnings through.
warnings.filterwarnings("ignore", category=DeprecationWarning, module="dateparser")

from dateparser import parse as dp_parse
from dateutil.parser import parse as du_parse


def _strip_ordinal(s: str) -> str:
    return re.sub(r"(\d)(st|nd|rd|th)", r"\1", s, flags=re.IGNORECASE)


def parse_date(s: Optional[str]) -> Optional[str]:
    """Try to parse many human date formats to ISO YYYY-MM-DD.

    Returns ISO date string or None if parsing fails.
    """
    if not s:
        return None
    if not isinstance(s, str):
        s = str(s)
    s2 = s.strip()
    s2 = _strip_ordinal(s2)

    # Policy decisions:
    # - Ambiguous numeric dates (e.g. 01/02/03 or 01-02-2020) will be
    #   interpreted using MDY (month-day-year) order to match common
    #   US-style statements and the project's chosen convention.
    # - Two-digit years will be expanded using a pivot year to map to a
    #   4-digit year. We use a pivot of 50: 00-49 -> 2000-2049, 50-99 -> 1950-1999.
    #   This is explicit and avoids surprising interpretations.
    # - Output format is ISO `YYYY-MM-DD` (or `None` when unparseable).

    # Expand two-digit years in simple numeric dates before parsing.
    # Match patterns like M/D/YY or MM-DD-YY, etc.
    def _expand_2digit_year(match: re.Match) -> str:
        m = match.group(1)
        d = match.group(2)
        y = match.group(3)
        try:
            yy = int(y)
        except Exception:
            return match.group(0)
        # pivot at 26: 00-25 -> 2000-2025, 26-99 -> 1900-1999
        # This maps recent two-digit years (<=25) to 2000s because the
        # project is being developed in 2025; adjust the pivot later if needed.
        if yy <= 25:
            full = 2000 + yy
        else:
            full = 1900 + yy
        return f"{m}/{d}/{full}"

    # Pattern: month/day/yy or day/month/yy depending on order; we assume MDY
    two_digit_pattern = re.compile(r"\b(\d{1,2})[\/-](\d{1,2})[\/-](\d{2})\b")
    s3 = two_digit_pattern.sub(_expand_2digit_year, s2)

    # First try dateparser with explicit MDY ordering to resolve numeric ambiguity.
    try:
        dt = dp_parse(s3, settings={"DATE_ORDER": "MDY", "RETURN_AS_TIMEZONE_AWARE": False})
        if dt:
            return dt.date().isoformat()
    except Exception:
        pass

    # Fallback to dateutil parser; prefer MDY (dayfirst=False) to match project policy.
    try:
        dt2 = du_parse(s3, fuzzy=True, dayfirst=False)
        return dt2.date().isoformat()
    except Exception:
        return None


_amount_re = re.compile(r"^\s*\(?\s*([\-–−]?)\s*([\$£€])?\s*([\d,]+(?:\.\d+)?)\s*\)?\s*(?:([A-Za-z]{3}))?\s*$")


def parse_amount(s: Optional[str]) -> Tuple[Optional[Decimal], Optional[str]]:
    """Parse amount-like strings into (Decimal(amount), currency)

    Supports symbols ($, £, €), optional 3-letter currency codes, parentheses for negatives,
    commas in thousands, and leading minus signs.
    Returns (None, None) if parsing fails.
    """
    if s is None:
        return None, None
    if not isinstance(s, str):
        s = str(s)
    t = s.strip()
    if t == "":
        return None, None

    # Normalize common currency words like 'USD' appearing after amount
    if t.upper().endswith(" USD"):
        t = t[:-4].strip() + " USD"

    m = _amount_re.match(t)
    if not m:
        # try simpler fallback: remove commas, remove currency symbols, detect parentheses
        negative = False
        if t.startswith("(") and t.endswith(")"):
            negative = True
            t2 = t[1:-1]
        else:
            t2 = t
        t2 = re.sub(r"[\$£€,]", "", t2)
        parts = t2.split()
        amt_part = parts[0] if parts else ""
        cur_part = parts[1] if len(parts) > 1 else None
        try:
            val = Decimal(amt_part)
            if negative:
                val = -val
            return val, (cur_part.upper() if cur_part else None)
        except (InvalidOperation, ValueError):
            return None, None

    sign, sym, amt_str, code = m.groups()
    amt_clean = amt_str.replace(",", "")
    try:
        val = Decimal(amt_clean)
    except InvalidOperation:
        return None, None
    # handle sign or parentheses
    if sign and sign.strip() in ("-", "–", "−"):
        val = -val
    if t.startswith("(") and t.endswith(")"):
        val = -val

    currency = None
    if code:
        currency = code.upper()
    elif sym:
        currency = {"$": "USD", "£": "GBP", "€": "EUR"}.get(sym)

    return val, currency
