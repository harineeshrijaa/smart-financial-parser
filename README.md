# Smart Financial Parser - Harinee Saravanakumar 

A small, test-driven Python CLI project that ingests unstructured, messy CSV transactions containing columns such as `date`, `amount`, `merchant`, and `notes`. The project cleans and fixes noisy inputs by normalizing dates to ISO, parsing amounts into `Decimal` with explicit currency detection, canonicalizing merchant names (alias maps + fuzzy matching with an optional embedding fallback), categorizing merchants, converting currencies to USD using deterministic demo FX rates, and producing a top-spending-category JSON report.

The codebase separates data-cleaning (parsing and merchant canonicalization) from reporting and FX-conversion logic, and provides a focused suite of unit and integration tests that validate edge cases and ensure reproducible behavior.

## Quick Start

Clone, create a virtual environment, install dependencies, run tests and the CLI:

```bash
# Clone the repo (creates folder `smart-financial-parser`) and change into it:
git clone https://github.com/harineeshrijaa/smart-financial-parser.git
cd smart-financial-parser

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# This writes package metadata into the venv so `import smart_financial_parser` works.
python -m pip install -e .

# This is OPTIONAL — only needed if you enable embedding-based merchant matching.
pip install sentence-transformers 

# Run tests
python -m pytest -q

# Produce the top-spending report (reads data/messy_transactions.csv)
python -m smart_financial_parser.cli --input data/messy_transactions.csv --report report/top_spending.json

# Preview cleaned rows (show parsed date and amount columns)
python -m smart_financial_parser.cli --input data/messy_transactions.csv --clean-preview --preview 20
```

## Overview

- Ingests a messy CSV.
- Normalizes dates to ISO `YYYY-MM-DD` (`parse_date`).
- Parses amounts into `Decimal` and detects currency where explicit (symbols, 3-letter codes, words).
- Canonicalizes merchants using an alias map + fuzzy matching with `rapidfuzz` and an optional embedding fallback (`sentence-transformers`).
- Categorizes merchants using a small deterministic map and heuristics.
- Aggregates amounts (converted to USD using deterministic demo FX rates) and writes a JSON report with the top spending category.

## Methodology

### AI Usage Disclosure

I used Microsoft Copilot as an assistant while I developed this project. Copilot helped me quickly clarify Python syntax, suggested prototype code snippets and regexes (for example, ordinal stripping and two-digit-year handling), and provided ideas for parsing heuristics and fuzzy-search tuning.

Concretely, Copilot accelerated these parts of the workflow:
- Identifying the best-suited python libraries for the project.
- Adding various edge cases to the messy CSV file. 
- Bootstrapping the project with structure
- implementing date normalization, amount parsing, and merchant canonicalization. 
    - Prototyping regexes and small parsing helpers that I then turned into unit tests.
    - Exploring `pandas`/`dateparser` usage patterns when I wasn’t certain about the exact API surface.
    - Helping reason about fuzzy-match thresholds and cleaning steps for merchant canonicalization.
- Creating unit and integration tests for all methods. 
- Documentation

I used Copilot's suggestions as starting points — I accepted, adapted, and rejected suggestions as appropriate. I take full responsibility for every line of code and verified all behavior through tests and manual checks.

### Verification

- Test-first validation: every essential parsing function (`parse_date`, `parse_amount`, `normalize_merchant`) has unit tests that exercise normal cases and edge cases.
    - Date edge cases: Two‑digit year pivot handling (e.g., 01/03/89 → 1989 vs 01/13/24 → 2024 policy), Slashed, dashed, dot, and textual separators: 2014/07/04, 11-01-30, 1987.01.07, Missing or unusual year placements, Mixed human formats, Ordinal day suffixes, etc
    - Amount edge cases: Parentheses for negatives, Leading/trailing minus signs and spaces, currency symbols, thousands place punctuation, etc 
    - Merchant edge cases: store numbers and noisy suffixes/prefix, fullwidth/strange unicode merchant names (ai debugging), aggresive cleaning (strip punctuation, collapse whitespace)
- End-to-end checks: the integration tests run the full pipeline on `data/messy_transactions.csv` to validate cleaned output and the produced `report/top_spending.json`.
- Manual verification: I also inspected results on real sample rows by printing cleaned outputs for several representative examples. For example, I outputted the raw dates data from `messy_transactions.csv` against the normalized dates to see if it was translated accurately. I repeated the manual verification for normalized merchants, amounts, and categories. 

Using Copilot saved iteration time, but all parsing heuristics, thresholds, and mappings were validated by tests and manual inspection before being committed.

## Procedure I Took

Below is the development procedure I followed to build the project incrementally and testably:

- Research: utilized co-pilot to identify the best-suited libraries for this project by comparing and contrasting all available python modules.  
- Environment & scaffold: created a Python virtualenv, installed all necessary packed, added a minimal `requirements.txt`, and scaffolded the package (`smart_financial_parser/`), `data/`, and `tests/` directories.
- Create messy file: authored `data/messy_transactions.csv` with many realistic, messy examples (mixed date formats, quoted fields, currency symbols, and noisy merchant strings) to drive parsing edge cases. I updated this file throughout the development to account for new edge cases I came up with. 
- Ingest & CLI: implemented `parser/ingest.py` and a small `cli.py` that reads CSV files, supports many flags, and prints user-facing messages for deterministic tests.
- Date & amount normalization: implemented `parse_date` and `parse_amount` in `parser/normalize.py`, adding ordinal stripping, various date format configurations, currency symbol/word detection, and Decimal-based parsing. I extended the functionality by adding more currencies for detection and accounting for edge cases like two-digit years and determining the pivot (25/26). 
- Merchant canonicalization: added `data/merchants.json` and `normalize_merchant` (alias lookup → aggressive-clean → `rapidfuzz` fuzzy match → optional embedding fallback) with `issues` tracking for low-confidence rows. I implementing aggressive-cleaning to account for some words that were not being recognized due to a low fuzzy searching score. 
- Categorization & reporting: implemented `parser/categorize.py` and `parser/report.py` to map merchants to categories, convert amounts to USD (using deterministic demo rates), aggregate totals, and write `report/top_spending.json`.
- CLI integration: added the `--report` flag and hooks to write cleaned CSV and the JSON report; added convenience behaviors (fallback to `data/<basename>`, `--default-currency` preview helper). I added deterministic alphabetical tie-break rules to account for the case of two high spending categories. 
- Tests & iteration: wrote unit tests for parsing, normalization, merchant matching and reporting, plus integration tests that exercise the full pipeline. Ran `pytest -q` frequently and iterated on edge cases exposed by failing tests (CSV quoting, currency symbols, fuzzy thresholds).
- Final polishing: added rounding/formatting helpers, deterministic behavior (alphabetical tiebreak), and README documentation with AI disclosure and methodology notes.

This procedure enforced a test-first, reproducible approach so each change was validated with targeted unit tests before moving on.

## Design Decisions

I researched options and chose pragmatic, well-tested libraries that make the program reliable and easy to test. Here’s why I picked each one and where I use it.

- `pandas`: raw CSV parsing is brittle, so I use `pandas` for resilient reading, preview/sample, grouping, and automatic type inference. 
  - Where: `parser/ingest.py`, `cli.py` (preview/sample), `parser/report.py` (aggregation).

- `dateparser` + `dateutil`: `dateparser` handles messy human date inputs; `dateutil` is a solid fallback for tricky inputs. I also strip ordinals and apply an MDY policy with a two-digit-year pivot.
  - Where: `parser/normalize.py::parse_date`.

- `decimal.Decimal`: money needs exact math — `Decimal` prevents floating-point surprises and gives deterministic rounding.
  - Where: `parser/normalize.py::parse_amount`, `convert_amount_to_usd`, and `parser/report.py` when summing/quantizing.

- `rapidfuzz`: fast, deterministic fuzzy matching for merchant aliases. I clean strings aggressively and surface low-confidence matches for review.
  - Where: `parser/merchant.py::normalize_merchant`.

- `sentence-transformers` (optional): embedding fallback for very noisy merchant text — useful but optional due to model downloads, privacy, and cost.
  - Where: optional fallback in `parser/merchant.py` when fuzzy scores are low.


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

## Limitations & Future Improvements

Below are three concrete improvements I would make next, with short explanations of why they matter and why I didn't implement them for this submission.

- Live FX rates via a trusted API
    - Why it matters: Exchange rates change — live rates give accurate USD conversions for real reporting.
    - Why I didn't implement it: Requires API keys, caching, retries, and deterministic tests — more engineering and time than allowed.

- Expand the alias map with LLM/embedding assistance
    - Why it matters: Embeddings find semantic matches that edit-distance misses, improving merchant matching for noisy text.
    - Why I didn't implement it: Models add downloads, cost, and privacy considerations and need a human-review flow, which was out of scope.

- Improve category mapping with API/AI assistance
    - Why it matters: AI can suggest categories at scale and surface ambiguous cases for review.
    - Why I didn't implement it: It needs a safe verification/override workflow to avoid misclassification and more time to design and test.


