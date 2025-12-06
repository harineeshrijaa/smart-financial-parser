# Smart Financial Parser

Minimal scaffold for the Smart Financial Parser code challenge.

Quick start:

```bash
cd "/Users/harineesaravanakumar/personal projects/Smart Financial Parser"
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

See `smart_financial_parser/` for code and `tests/` for unit tests.

**What I implemented (Step 1-4 partial)**
- **Ingestion & CLI**: `smart_financial_parser/parser/ingest.py` (`read_csv`) and `smart_financial_parser/cli.py` — reads CSV, supports `--preview`, `--sample`, `--output` (hook), `--verbose` and a new `--clean-preview` flag.
- **Date normalization**: `smart_financial_parser/parser/normalize.py` — `parse_date(s)` returns ISO `YYYY-MM-DD` or `None`. Uses `dateparser` first (with `DATE_ORDER=MDY`), expands two-digit years with a pivot (00-49 -> 2000-2049; 50-99 -> 1950-1999), strips ordinal suffixes, and falls back to `dateutil`.
- **Tests**: Unit tests in `tests/test_normalize_date.py` and an integration test `tests/test_integration_clean_dates.py` that asserts `date_iso` for `data/messy_transactions.csv`.

**How to run the CLI and see normalized dates**
```
.venv/bin/python -m smart_financial_parser.cli --input data/messy_transactions.csv --clean-preview --preview 1000
```

**Edge cases we considered and how they are handled**
- **Ordinal suffixes (1st, 2nd, 3rd, 4th):** stripped via a regex `_strip_ordinal()` before parsing so `5th Jan 2021` becomes `5 Jan 2021`.
- **Two-digit years:** detected in numeric dates via regex and expanded using a pivot rule: years `00-25` → `2000-2025`, `26-99` → `1900-1999`. This avoids surprises for recent dates and matches the project's current pivot choice (2025-aware).
- **Ambiguous numeric dates (MM/DD vs DD/MM):** project policy chooses **MDY (month-day-year)** to provide deterministic parsing. `dateparser` is called with `DATE_ORDER="MDY"` and `dateutil` fallback uses `dayfirst=False`.
- **Timezones / ISO timestamps (e.g., `2023-08-01T14:30:00Z`):** parsed and truncated to the date portion (`2023-08-01`).
- **Hyphenated day-first `DD-MM-YY` rows:** our two-digit-year regex and parsing handles `31-12-23` producing `2023-12-31`. If the numeric day is >12, `dateparser/dateutil` will interpret correctly as day.
- **Non-string inputs / empty cells:** input is coerced to `str` when possible; empty or invalid values return `None`.
- **Malformed dates:** unparseable strings (e.g., `not a date`) yield `None` rather than raising.

**Were all edge cases covered?**
- Covered in tests and in the integration check for `data/messy_transactions.csv`: ordinals, two-digit years, numeric ambiguity (MDY policy), ISO timestamps, hyphenated day-first with two-digit years, empty/missing dates, and malformed values.
- Remaining/observed limitations:
	- The two-digit-year pivot is currently set to 26 (00-25 → 2000s, 26-99 → 1900s); if you need a different mapping (e.g., always map `00-99` to 2000s), we can make this configurable.
	- `dateparser`/`strptime` emits deprecation warnings for ambiguous day-of-month without year — these are currently suppressed for tests but should be re-evaluated if we change parsing behavior.

**Acceptance criteria used**
- `parse_date(s)` returns a string in ISO format `YYYY-MM-DD` for valid inputs, otherwise `None`.
- Unit test `tests/test_normalize_date.py` exercises representative inputs; integration test `tests/test_integration_clean_dates.py` verifies the messy CSV mapping.


