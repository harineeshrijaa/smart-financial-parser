import re
import warnings
import unicodedata
from decimal import Decimal, InvalidOperation
from typing import Optional, Tuple

warnings.filterwarnings("ignore", category=DeprecationWarning, module="dateparser")

from dateparser import parse as dp_parse
from dateutil.parser import parse as du_parse
import json
import os
try:
    # rapidfuzz is an optional dependency; prefer it if available
    from rapidfuzz import process as rf_process
    from rapidfuzz import fuzz as rf_fuzz
    _HAS_RAPIDFUZZ = True
except Exception:
    _HAS_RAPIDFUZZ = False
try:
    # sentence-transformers optional embedding fallback
    from sentence_transformers import SentenceTransformer
    from sentence_transformers import util as _st_util
    _HAS_EMBEDDINGS = True
except Exception:
    _HAS_EMBEDDINGS = False

# caches for embeddings to avoid reloading model repeatedly
_EMBED_MODEL = None
_CHOICE_EMBED_CACHE = None


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

    symbol = None
    # Ordered list to prefer multi-char symbols before single-char '$'
    symbol_candidates = [
        "US$",
        "USD$",
        "C$",
        "A$",
        "CA$",
        "AU$",
        # single-char symbols
        "$",
        "£",
        "€",
        "¥",
        "￥",
        "₹",
        "Ξ",
        "₽",
        "₩",
        "₺",
        "฿",
        "₦",
        "₫",
        "₴",
        "₪",
    ]
    found_sym = None
    t_work = t
    # search for any candidate present in the string (case-insensitive for ASCII prefixes)
    for cand in symbol_candidates:
        # For ASCII multi-char candidates, check case-insensitively
        if any(ch.isascii() for ch in cand):
            if re.search(re.escape(cand), t_work, flags=re.IGNORECASE):
                found_sym = cand
                break
        else:
            if cand in t_work:
                found_sym = cand
                break
    if found_sym:
        symbol = found_sym
        t = t.replace(found_sym, "").strip()

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
            "US$": "USD",
            "USD$": "USD",
            "£": "GBP",
            "€": "EUR",
            "¥": "JPY",
            "￥": "JPY",
            "₹": "INR",
            "C$": "CAD",
            "CA$": "CAD",
            "A$": "AUD",
            "AU$": "AUD",
            "Ξ": "ETH",
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


def convert_amount_to_usd(amount: Optional[Decimal], currency: Optional[str], rates: Optional[dict] = None, assume_missing_usd: bool = True) -> Optional[Decimal]:
    """Convert a Decimal `amount` in `currency` to USD using provided `rates`.
    This function does not fetch live rates.
    """
    if amount is None:
        return None

    # Default example rates (USD per unit of currency)
    default_rates = {
        "USD": "1",
        "EUR": "1.08",
        "GBP": "1.25",
        "JPY": "0.007",
        "INR": "0.012",
        "CAD": "0.74",
        "AUD": "0.66",
        "ETH": "1800",
    }

    use_rates = {}
    if rates:
        # normalize incoming rates to strings for Decimal
        for k, v in rates.items():
            try:
                use_rates[k.upper()] = Decimal(str(v))
            except Exception:
                pass
    # merge defaults for any missing values
    for k, v in default_rates.items():
        if k not in use_rates:
            use_rates[k] = Decimal(v)

    if not currency:
        if assume_missing_usd:
            return amount
        return None

    cur = currency.upper()
    # Some inputs may include symbol-like codes (e.g. "$" or "US$") - normalize common forms
    cur = {
        "$": "USD",
        "US$": "USD",
        "USD$": "USD",
        "C$": "CAD",
        "CA$": "CAD",
        "A$": "AUD",
        "AU$": "AUD",
        "Ξ": "ETH",
    }.get(cur, cur)

    rate = use_rates.get(cur)
    if rate is None:
        return None

    try:
        return (amount * rate).normalize()
    except Exception:
        return None


def _clean_merchant(raw: Optional[str]) -> str:
    """
    Returns a cleaned string suitable for exact or fuzzy matching.
    """
    if not raw:
        return ""
    if not isinstance(raw, str):
        raw = str(raw)
    s = unicodedata.normalize("NFKC", raw)
    s = s.lower()
    # Replace common punctuation/symbols with space
    s = re.sub(r"[\u2000-\u206F\u2E00-\u2E7F'\"·•*\/\\(),@!?:;_\[\]#\$%\^&=+<>`~]+", " ", s)
    # Remove store numbers like '#1234' or trailing numbers
    s = re.sub(r"#\d+", " ", s)
    s = re.sub(r"\b(store|store\s*#|atm|pos|terminal)\b", " ", s)
    # Remove long numeric sequences (likely transaction ids)
    s = re.sub(r"\b\d{4,}\b", " ", s)
    # remove spaces between single-letter tokens so spaced acronyms/words normalize
    s = re.sub(r"\b([a-zA-Z])(?:\s+)(?=[a-zA-Z]\b)", r"\1", s)
    # Collapse whitespace
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _aggressive_clean(s: str) -> str:
    """A stronger cleaning pass for low-confidence inputs.
    This is applied only when initial fuzzy score is below threshold.
    """
    if not s:
        return s
    t = s
    # remove ordinal markers and punctuation, already normalized by _clean_merchant
    # remove tokens that usually add noise
    t = re.sub(r"\b(supercenter|super ctr|super ctr\.|super ctr|store|store\b|branch|branch\b|center|ctr|centre)\b", " ", t)
    # remove trailing small numeric groups often used as store ids
    t = re.sub(r"\b\d{2,}\b", " ", t)
    # collapse repeated whitespace
    t = re.sub(r"\s+", " ", t).strip()
    return t


def normalize_merchant(raw: Optional[str], merchant_map: dict, threshold: int = 85, return_issues: bool = False):
    """Normalize a raw merchant string to a canonical merchant.

    Parameters:
    - raw: raw merchant string from the CSV/transaction
    - merchant_map: mapping of canonical_name -> list_of_aliases (as in `data/merchants.json`)
    - threshold: rapidfuzz score threshold for accepting fuzzy matches (0-100)
    - return_issues: if True, returns (canonical_or_None, score_int, issues_list)

    Returns either `(canonical_name, score)` or `(canonical_name, score, issues)` when
    `return_issues=True`. Score is 0-100 (int). When an exact alias match is found score=100.
    """
    issues = []
    if raw is None or str(raw).strip() == "":
        if return_issues:
            issues.append("empty_merchant")
            return None, 0, issues
        return None, 0

    cleaned = _clean_merchant(raw)

    # Build alias -> canonical mapping and choices list for fuzzy matching
    alias_map = {}
    choices = []
    for canonical, aliases in (merchant_map or {}).items():
        # include canonical name itself
        c_clean = _clean_merchant(canonical)
        if c_clean:
            alias_map[c_clean] = canonical
            choices.append(c_clean)
        # aliases may be a list or single string
        if isinstance(aliases, (list, tuple)):
            for a in aliases:
                a_clean = _clean_merchant(a)
                if a_clean:
                    alias_map[a_clean] = canonical
                    choices.append(a_clean)
        elif isinstance(aliases, str):
            a_clean = _clean_merchant(aliases)
            if a_clean:
                alias_map[a_clean] = canonical
                choices.append(a_clean)

    # Exact match short-circuit
    if cleaned in alias_map:
        canonical = alias_map[cleaned]
        if return_issues:
            return canonical, 100, issues
        return canonical, 100

    # If there are no choices, nothing to match against
    if not choices:
        if return_issues:
            issues.append("no_merchant_map")
            return None, 0, issues
        return None, 0

    # Try fuzzy matching using rapidfuzz if available
    if _HAS_RAPIDFUZZ:
        try:
            # Prefer token_set_ratio for robustness against token reordering and duplicates.
            best = rf_process.extractOne(cleaned, choices, scorer=rf_fuzz.token_set_ratio)
            if best:
                match_str, score, _ = best
                # also compute complementary scores and take the max to handle different noise
                extra_partial = rf_fuzz.partial_ratio(cleaned, match_str)
                extra_sort = rf_fuzz.token_sort_ratio(cleaned, match_str)
                score = int(round(max(score, extra_partial, extra_sort)))
                canonical = alias_map.get(match_str)
                if score >= threshold:
                    if return_issues:
                        issues.append("fuzzy_matched")
                        return canonical, score, issues
                    return canonical, score
                else:
                    # Attempt an aggressive-clean retry before giving up
                    cleaned_aggr = _aggressive_clean(cleaned)
                    if cleaned_aggr and cleaned_aggr != cleaned:
                        try:
                            best2 = rf_process.extractOne(cleaned_aggr, choices, scorer=rf_fuzz.token_set_ratio)
                            if best2:
                                match2, score2, _ = best2
                                extra_partial2 = rf_fuzz.partial_ratio(cleaned_aggr, match2)
                                extra_sort2 = rf_fuzz.token_sort_ratio(cleaned_aggr, match2)
                                score2 = int(round(max(score2, extra_partial2, extra_sort2)))
                                if score2 >= threshold:
                                    canonical2 = alias_map.get(match2)
                                    if return_issues:
                                        issues.append("aggressive_fuzzy_matched")
                                        return canonical2, score2, issues
                                    return canonical2, score2
                                # otherwise fall through and report low_confidence with higher of the two
                                score = max(score, score2)
                        except Exception:
                            pass
                    # Embedding fallback (optional): try sentence-transformers if available
                    if _HAS_EMBEDDINGS:
                        try:
                            global _EMBED_MODEL, _CHOICE_EMBED_CACHE
                            if _EMBED_MODEL is None:
                                # small, fast model; requires sentence-transformers and model download
                                _EMBED_MODEL = SentenceTransformer("all-MiniLM-L6-v2")
                            if _CHOICE_EMBED_CACHE is None:
                                # store (choices_list, tensor_embeddings)
                                emb = _EMBED_MODEL.encode(choices, convert_to_tensor=True, show_progress_bar=False)
                                _CHOICE_EMBED_CACHE = (choices, emb)
                            choices_list, choices_emb = _CHOICE_EMBED_CACHE
                            query = cleaned_aggr or cleaned
                            q_emb = _EMBED_MODEL.encode(query, convert_to_tensor=True)
                            try:
                                sims = _st_util.cos_sim(q_emb, choices_emb)
                            except Exception:
                                # fallback naming
                                sims = _st_util.pytorch_cos_sim(q_emb, choices_emb)
                            # sims could be a 1-d or 2-d tensor/array
                            # pick best index
                            best_idx = int(sims.argmax())
                            best_sim = float(sims[0][best_idx]) if hasattr(sims, '__len__') and sims.ndim > 1 else float(sims[best_idx])
                            # map similarity to 0-100 score
                            emb_score = int(round(best_sim * 100))
                            # embedding threshold (0.0-1.0) -> default 0.72
                            emb_thresh = 0.72
                            if best_sim >= emb_thresh:
                                matched = choices_list[best_idx]
                                canonical3 = alias_map.get(matched)
                                if return_issues:
                                    issues.append("embedding_matched")
                                    return canonical3, emb_score, issues
                                return canonical3, emb_score
                        except Exception:
                            # embedding fallback failure is non-fatal
                            pass
                    if return_issues:
                        issues.append("low_confidence")
                        return None, score, issues
                    return None, score
        except Exception:
            # fall through to conservative substring matching
            pass

    # Fallback
    for choice in choices:
        if cleaned in choice or choice in cleaned:
            canonical = alias_map.get(choice)
            if return_issues:
                issues.append("substring_matched")
                return canonical, 75, issues
            return canonical, 75

    if return_issues:
        issues.append("no_match")
        return None, 0, issues
    return None, 0
