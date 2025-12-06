import re
import warnings
import unicodedata
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


def parse_amount(s: Optional[str], return_issues: bool = False) -> Tuple[Optional[Decimal], Optional[str]]:
    """Parse amount-like strings into (Decimal(amount), currency)

    Supports symbols ($, £, €), optional 3-letter currency codes, parentheses for negatives,
    commas in thousands, and leading minus signs.
    Returns (None, None) if parsing fails.
    """
    # Backwards-compatible: callers can pass a kwarg `return_issues=True`
    # to receive a third return value (list of issue tags).
    if s is None:
        if return_issues:
            return None, None, []
        return None, None
    if not isinstance(s, str):
        s = str(s)
    t = s.strip()
    if t == "":
        if return_issues:
            return None, None, []
        return None, None

    # Normalize a variety of non-breaking / thin spaces to plain spaces
    # and convert Unicode digits (e.g. fullwidth) to ASCII digits.
    issues = []
    # map of space characters to normalize
    for sp in ("\u00A0", "\u2009", "\u202F", "\u200A"):
        if sp in t:
            t = t.replace(sp, " ")
            issues.append("normalized_space")

    # Convert Unicode digits (e.g. '１２３４' or Arabic-Indic digits) to ASCII
    def _convert_unicode_digits(text: str) -> str:
        out = []
        changed = False
        for ch in text:
            try:
                d = unicodedata.digit(ch)
                out.append(str(d))
                if ch != str(d):
                    changed = True
            except (TypeError, ValueError):
                out.append(ch)
        return ("".join(out), changed)

    t_conv, conv_changed = _convert_unicode_digits(t)
    if conv_changed:
        t = t_conv
        issues.append("unicode_digits_converted")

    # Normalize common non-ASCII decimal/thousands separators to ASCII form
    # Fullwidth dot (．) -> '.' ; Arabic decimal (٫, U+066B) -> '.' ; Arabic thousands (٬, U+066C) -> removed
    dec_replacements = {
        "．": ".",
        "\u066B": ".",
        "\u066C": "",
        "٬": "",
        "٫": ".",
    }
    replaced_any = False
    for k, v in dec_replacements.items():
        if k in t:
            t = t.replace(k, v)
            replaced_any = True
    if replaced_any:
        issues.append("normalized_decimal_separators")

    # Track negativity from parentheses or leading minus
    negative = False
    if t.startswith("(") and t.endswith(")"):
        negative = True
        t = t[1:-1].strip()
    if t and t[0] in ("-", "–", "−"):
        negative = True
        t = t[1:].strip()

    # Detect currency code (USD, JPY, etc.) either trailing or leading
    code = None
    m_code_trail = re.search(r"\b([A-Za-z]{3})\b\s*$", t)
    if m_code_trail:
        code = m_code_trail.group(1).upper()
        t = t[: m_code_trail.start()].strip()
    else:
        # match leading 3-letter currency code even when directly followed by digits (e.g. 'USD12.50')
        m_code_lead = re.match(r"^([A-Za-z]{3})", t)
        if m_code_lead:
            code = m_code_lead.group(1).upper()
            t = t[m_code_lead.end() :].strip()

    # Detect symbol
    symbol = None
    m_sym = re.search(r"([\$£€¥₹₽₩₺฿₦₫₴₪])", t)
    if m_sym:
        symbol = m_sym.group(1)
        # remove symbol for numeric parsing
        t = t.replace(symbol, "").strip()

    # Now t should be the numeric-ish part, possibly with commas/dots
    # Heuristics for comma/dot as thousand/decimal separators:
    num = t
    # Remove spaces
    num = num.replace(" ", "")
    # Remove common grouping apostrophes (e.g. Swiss 1'234.56) and similar quotes
    if "'" in num or "’" in num:
        num = num.replace("'", "").replace("’", "")
        issues.append("removed_apostrophe_grouping")

    # If both comma and dot present, decide by last separator position
    if "," in num and "." in num:
        if num.rfind(",") > num.rfind("."):
            # comma is decimal separator: 1.234,56 -> 1234.56
            num_norm = num.replace(".", "").replace(",", ".")
        else:
            # dot is decimal separator: 4,500.00 -> 4500.00
            num_norm = num.replace(",", "")
    elif "," in num and "." not in num:
        # only comma present: could be decimal or thousands
        parts = num.split(",")
        if len(parts[-1]) <= 2:
            # treat comma as decimal separator
            if len(parts) == 1:
                num_norm = parts[0]
            else:
                num_norm = "".join(parts[:-1]) + "." + parts[-1]
            issues.append("comma_as_decimal")
        else:
            # likely thousands separator
            num_norm = num.replace(",", "")
    else:
        # only dot or plain digits
        num_norm = num

    # final clean: remove any characters except digits and dot and minus
    num_norm = re.sub(r"[^0-9.\-]", "", num_norm)
    if num_norm == "":
        if return_issues:
            return None, None, []
        return None, None

    try:
        val = Decimal(num_norm)
    except (InvalidOperation, ValueError):
        # Attempt a conservative repair: if multiple dots present, keep last as decimal
        # but avoid repairing when there are adjacent dots like '..' which indicate a malformed input.
        if num_norm.count(".") > 1:
            if ".." in num_norm:
                if return_issues:
                    return None, None, []
                return None, None
            last = num_norm.rfind(".")
            repaired = num_norm[:last].replace(".", "") + num_norm[last:]
            try:
                val = Decimal(repaired)
                issues.append("repaired_multiple_dots")
            except Exception:
                if return_issues:
                    return None, None, []
                return None, None
        else:
            if return_issues:
                return None, None, []
            return None, None

    if negative:
        val = -val

    # Determine currency: prefer explicit code, then symbol mapping
    currency = None
    if code:
        currency = code.upper()
    elif symbol:
        currency = {
            "$": "USD",
            "£": "GBP",
            "€": "EUR",
            "¥": "JPY",
            "₹": "INR",
            "₽": "RUB",
            "₩": "KRW",
            "₺": "TRY",
            "฿": "THB",
            "₦": "NGN",
            "₫": "VND",
            "₴": "UAH",
            "₪": "ILS",
        }.get(symbol)

    # If still no currency, try to detect currency words in the original string
    if not currency:
        word_map = {
            "usd": "USD",
            "dollar": "USD",
            "dollars": "USD",
            "eur": "EUR",
            "euro": "EUR",
            "euros": "EUR",
            "gbp": "GBP",
            "pound": "GBP",
            "pounds": "GBP",
            "inr": "INR",
            "rupee": "INR",
            "rupees": "INR",
            "jpy": "JPY",
            "yen": "JPY",
            "aud": "AUD",
            "cad": "CAD",
            "chf": "CHF",
            "cny": "CNY",
            "rmb": "CNY",
            "yuan": "CNY",
        }
        s_low = s.lower()
        for k, v in word_map.items():
            if re.search(r"\b" + re.escape(k) + r"\b", s_low):
                currency = v
                break

    if return_issues:
        return val, currency, issues
    return val, currency
