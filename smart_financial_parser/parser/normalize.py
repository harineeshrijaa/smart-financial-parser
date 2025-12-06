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

    # First try dateparser which handles many casual formats
    try:
        dt = dp_parse(s2, settings={"RETURN_AS_TIMEZONE_AWARE": False})
        if dt:
            return dt.date().isoformat()
    except Exception:
        pass

    # Fallback to dateutil
    try:
        dt2 = du_parse(s2, fuzzy=True, dayfirst=False)
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
