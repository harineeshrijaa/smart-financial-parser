# Smart Financial Parser

A small, test-driven Python CLI that ingests a messy CSV of transactions, normalizes dates/amounts/merchants, categorizes merchants, converts amounts to USD (using deterministic demo FX rates) and produces a top-spending-category report.

This repository is structured for clarity and reproducibility: parsing and canonicalization logic are separated from reporting/FX conversion, and a compact set of unit and integration tests exercise edge cases.

## Quick Start

Clone, create a virtual environment, install dependencies, run tests and the CLI:

```bash
cd "/Users/harineesaravanakumar/personal projects/Smart Financial Parser"
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Run tests
pytest -q

# Produce the top-spending report (reads data/messy_transactions.csv)
python -m smart_financial_parser.cli --input data/messy_transactions.csv --report report/top_spending.json

# Preview cleaned rows (show parsed date and amount columns)
python -m smart_financial_parser.cli --input data/messy_transactions.csv --clean-preview --preview 20
```

## Overview

- Ingests a CSV (flexible quoting and encoding handling).
- Normalizes dates to ISO `YYYY-MM-DD` (`parse_date`).
- Parses amounts into `Decimal` and detects currency where explicit (symbols, 3-letter codes, words).
- Canonicalizes merchants using an alias map + fuzzy matching with `rapidfuzz` and an optional embedding fallback (`sentence-transformers`).
- Categorizes merchants using a small deterministic map and heuristics.
- Aggregates amounts (converted to USD using deterministic demo FX rates) and writes a JSON report with the top spending category.

## Design Decisions

- `pandas` for robust CSV ingestion and small-data convenience (preview, sample, reading different encodings).
- `dateparser` + `dateutil` for flexible date parsing; we enforce an MDY policy for determinism and add preprocessing (ordinal stripping, two-digit-year pivot) for edge cases.
- `decimal.Decimal` for monetary math to avoid floating-point rounding errors.
- `rapidfuzz` for fast, deterministic fuzzy matching against an alias dictionary.
- Optional `sentence-transformers` embedding fallback for low-confidence merchant matches (disabled by default to keep tests and installs lightweight).

Why these choices: the goal prioritizes correctness and reproducibility (deterministic unit tests) over exotic ML models. Libraries were chosen for their stability, testability, and suitability for text/date/number processing.

## Methodology (mandatory)

### AI Disclosure

I used AI assistance (ChatGPT) to prototype and suggest regexes and parsing heuristics (for example, ordinal stripping and two-digit-year handling) and to brainstorm edge cases and test inputs. All code, tests, and modifications were implemented and reviewed by me; I verified behaviors with unit and integration tests and adjusted logic where AI suggestions needed correction.

### Verification

- Test-driven approach: core parsing functions (`parse_date`, `parse_amount`, `normalize_merchant`) have unit tests (`tests/`).
- Integration tests exercise the full pipeline on `data/messy_transactions.csv` and assert the cleaned CSV and `report/top_spending.json` outputs.
- I ran `pytest -q` and spot-checked cleaned rows and the generated report. The demo FX table is intentionally fixed so test outputs are reproducible.

### Responsible use of AI

AI was used as an assistant to speed iteration and produce considered options; I accepted, modified, and rejected suggestions as needed. I take full responsibility for all code included in this repository and for verifying correctness.

## Files of interest

- `data/messy_transactions.csv` — sample messy dataset used for integration tests.
- `data/merchants.json` — compact canonical merchant → aliases mapping used for deterministic normalization.
- `smart_financial_parser/cli.py` — Command-Line Interface (flags described below).
- `smart_financial_parser/parser/normalize.py` — date & amount parsing, merchant cleaning helpers, `convert_amount_to_usd`.
- `smart_financial_parser/parser/categorize.py` — merchant → category mapping and heuristics.
- `smart_financial_parser/parser/report.py` — report aggregation, formatting, and JSON writer.
- `tests/` — unit and integration tests (important ones: `test_normalize_date.py`, `test_normalize_amount*.py`, `test_normalize_merchant.py`, `test_report.py`, `test_cli.py`).

## CLI Usage (important flags)

- `--input <path>`: input CSV (required for most actions). If the path doesn't exist, the CLI attempts `data/<basename>` as a convenience fallback.
- `--report <path>`: build and write the top-spending JSON report to the given path.
- `--output <path>`: write cleaned CSV to the given path.
- `--clean-preview`: show a preview including parsed `date_iso`, `amount_decimal`, and `currency` (uses `--preview N` to control rows shown).
- `--preview N`: show N rows (default small number).
- `--sample N`: process only the first N rows (fast iteration).
- `--default-currency CODE`: preview-only helper; when present, missing currencies in the preview are shown as this code (does not mutate data).
- `--verbose`: enables debug logs (stderr) while keeping user-facing messages on stdout for reliable test assertions.

Example:

```bash
python -m smart_financial_parser.cli --input data/messy_transactions.csv --report report/top_spending.json
```

This prints a short summary like `Top spending category: Shopping — $223,417.04` and writes `report/top_spending.json`.

## Report JSON schema

The generated report (`report/top_spending.json`) contains:

- `top_category`: string or `null` — the category with the largest USD total.
- `amount`: formatted top amount (string, e.g., `$1,234.56`) — kept for backward compatibility and human-readability.
- `top_amount`: numeric top amount (float) — programmatic, recommended for downstream processing.
- `by_category`: array of `{ category, amount, pct }` where `amount` is formatted (string) and `pct` is the fraction of total (float).
- `total_usd`: formatted total USD string.

Notes: the writer preserves human-readable formatted strings for easy inspection. If you need machine-friendly numeric fields for each `by_category` entry (e.g., `amount_usd`), consider adding that small extension (it's straightforward and I can add it on request).

## Normalization & Parsing Notes (important implementation details)

- parse_date(s):
  - Strips ordinal suffixes (`1st`, `2nd`, `3rd`, `4th`).
  - Uses `dateparser` with `DATE_ORDER=MDY`, falls back to `dateutil.parser.parse`.
  - Two-digit-year pivot: current policy maps `00-25` → 2000-2025 and `26-99` → 1900-1999 to reflect the current test pivot behavior (this was tuned during testing). This is configurable in code if you prefer a different rule.

- parse_amount(s):
  - Uses `decimal.Decimal` for amounts.
  - Detects and maps currency symbols to codes (expanded to include: `₹, ₽, ₩, ₺, ฿, ₦, ₫, ₴, ₪` and others).
  - Performs word/code detection (e.g., `USD`, `dollars`, `eur`, `pounds`) but only sets a currency when detection is explicit; avoids guessing a currency when input is ambiguous (so `2.00` without a symbol/code will parse numeric amount but leave `currency` as `None`).
  - Handles parentheses and leading-minus for negatives, thousands separators, and malformed numeric strings return `None` for the amount to avoid incorrect assumptions.

- Merchant normalization:
  - Exact alias match → canonical. Otherwise, `rapidfuzz` fuzzy match against canonical aliases.
  - Aggressive cleaning (strip punctuation, collapse whitespace) is applied before fuzzy scoring to improve match confidence.
  - Low-confidence matches are flagged in an `issues` column and an optional embedding-based fallback (using `sentence-transformers`) can be enabled to re-score ambiguous cases.

## Tests & Acceptance

- Run the full test suite:
```bash
pytest -q
```

- Key tests:
  - `tests/test_normalize_date.py` — date parsing edge cases (ordinals, two-digit years, empty/None inputs, MDY policy).
  - `tests/test_normalize_amount*.py` — amount parsing, currency detection, separators, negatives.
  - `tests/test_normalize_merchant.py` — canonicalization and fuzzy match behavior.
  - `tests/test_report.py` & integration tests — end-to-end report generation and CLI behavior.

Current test status: the repository's test suite passes; the demo FX rates and deterministic matching keep tests reproducible.

## Limitations & Future Improvements

- FX rates: the project currently ships with deterministic demo conversion rates for reproducible tests (`convert_amount_to_usd`). For production you'd supply live exchange rates (via a `--rates-file` CLI option or a small adapter to a trusted FX API).
- Merchant canonicalization: the alias map is compact; fuzzy matching works well for the sample data, but a production system would benefit from LLM or embedding-assisted expansion of canonical names and active review workflows for low-confidence rows.
- Reporting JSON: currently top amounts are included both as formatted strings and as a numeric `top_amount`. I can add machine-ready `amount_usd` values to each `by_category` entry in the report JSON on request.
- Internationalization & timezones: dates are normalized to local date (no timezone offset preservation). If you need per-transaction timezone-aware reporting we should carry the full ISO timestamp and the original timezone.

## Final notes / Developer rationale

This project was built under a tight, test-driven constraint: prioritize correctness and reproducibility. I used small, deterministic datasets and fixed demo FX rates so that behavior is repeatable in tests. AI-assisted suggestions helped speed iteration on regexes and edge-case thinking but I validated and adapted those suggestions; I accept responsibility for the final implementation and tests.


