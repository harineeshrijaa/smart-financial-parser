import argparse
import logging
import pandas as pd
from pathlib import Path
import sys

from smart_financial_parser.parser.ingest import read_csv
import json

from smart_financial_parser.parser.normalize import parse_date, parse_amount, normalize_merchant
from smart_financial_parser.parser.report import build_report_from_dataframe, write_report_json, format_usd


def configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format="%(message)s")


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    p = argparse.ArgumentParser(description="Smart Financial Parser — basic CLI")
    p.add_argument("--input", "-i", required=True, help="Path to input CSV file")
    p.add_argument("--preview", "-p", type=int, default=3, help="Number of preview rows")
    p.add_argument("--sample", "-s", type=int, default=None, help="Read only first N rows (fast iteration)")
    p.add_argument("--output", "-o", default=None, help="Optional path to write cleaned CSV (not yet implemented)")
    p.add_argument("--report", "-r", default=None, help="Optional path to write report JSON (not yet implemented)")
    p.add_argument("--clean-preview", action="store_true", help="Show cleaned preview columns (raw + date_iso + amount_decimal/currency)")
    p.add_argument("--default-currency", default=None, help="Default currency code to apply in preview when currency is missing (optional)")
    p.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    args = p.parse_args(argv)

    configure_logging(args.verbose)
    log = logging.getLogger(__name__)
    if args.verbose:
        log.debug("Verbose mode enabled")

    path = Path(args.input)
    if not path.exists():
        log.error("Input file not found: %s", path)
        raise SystemExit(2)

    try:
        df = read_csv(str(path), sample=args.sample)
        log.debug("Read CSV shape: %s", getattr(df, 'shape', None))
    except Exception as e:
        log.error("Failed to read input: %s", e)
        raise SystemExit(3)

    log.info("Read %d rows", len(df))
    # Also print to stdout so CLI output is visible in non-logging contexts/tests
    print(f"Read {len(df)} rows")
    if args.sample:
        log.info("(sample mode: showing first %d rows)", args.sample)
        print(f"(sample mode: showing first {args.sample} rows)")

    # Print preview
    preview_n = max(0, int(args.preview))
    if preview_n > 0:
        try:
            if args.clean_preview:
                # Add cleaned columns using parse_date and parse_amount; keep original columns
                if "date" in df.columns and "amount" in df.columns:
                    df = df.copy()
                    df["date_iso"] = df["date"].apply(parse_date)
                    # request issues from parse_amount so we can show/record repairs
                    parsed = df["amount"].apply(lambda s: pd.Series(parse_amount(s, return_issues=True), index=["amount_decimal", "currency", "issues"]))
                    df = pd.concat([df, parsed], axis=1)
                    # If a default currency was provided, apply it for preview only where currency is missing
                    if args.default_currency:
                        df["currency"] = df["currency"].where(pd.notna(df["currency"]), args.default_currency)
                    cols = ["date", "date_iso", "amount", "amount_decimal", "currency", "issues"]
                    print(df.loc[:, cols].head(preview_n).to_string(index=False))
                elif "date" in df.columns:
                    df = df.copy()
                    df["date_iso"] = df["date"].apply(parse_date)
                    print(df.loc[:, ["date", "date_iso"]].head(preview_n).to_string(index=False))
                else:
                    print("(clean-preview requested but no `date` column found)")
            else:
                print(df.head(preview_n).to_string(index=False))
        except Exception:
            # Fallback: pretty-print limited columns if to_string fails
            if args.clean_preview and "date" in df.columns:
                out = []
                for r in df.head(preview_n).to_dict(orient="records"):
                    amt_val = None
                    curr = None
                    issues = None
                    if "amount" in r:
                        parsed = parse_amount(r.get("amount"), return_issues=True)
                        if parsed:
                            try:
                                amt_val, curr, issues = parsed
                            except Exception:
                                amt_val, curr = parsed
                    out.append({"date": r.get("date"), "date_iso": parse_date(r.get("date")), "amount": r.get("amount"), "amount_decimal": amt_val, "currency": curr, "issues": issues})
                print(out)
            else:
                print(df.head(preview_n).to_dict(orient="records"))

    # Hooks for future features: write output/report if requested
    if args.output:
        try:
            # Prepare cleaned DataFrame to persist normalized columns
            df_out = df.copy()
            if "date" in df_out.columns and "date_iso" not in df_out.columns:
                df_out["date_iso"] = df_out["date"].apply(parse_date)
            if "amount" in df_out.columns and ("amount_decimal" not in df_out.columns or "currency" not in df_out.columns or "issues" not in df_out.columns):
                parsed_out = df_out["amount"].apply(lambda s: pd.Series(parse_amount(s, return_issues=True), index=["amount_decimal", "currency", "issues"]))
                df_out = pd.concat([df_out, parsed_out], axis=1)
            # Apply default currency if requested (persisted to output)
            if args.default_currency:
                df_out["currency"] = df_out["currency"].where(pd.notna(df_out["currency"]), args.default_currency)
            # Write cleaned CSV
            df_out.to_csv(args.output, index=False)
            log.info("Wrote cleaned CSV to %s", args.output)
        except Exception as e:
            log.error("Failed to write output CSV: %s", e)

    if args.report:
        try:
            # Prepare cleaned DataFrame similar to --output step so report uses cleaned fields
            df_out = df.copy()
            if "date" in df_out.columns and "date_iso" not in df_out.columns:
                df_out["date_iso"] = df_out["date"].apply(parse_date)
            if "amount" in df_out.columns and ("amount_decimal" not in df_out.columns or "currency" not in df_out.columns or "issues" not in df_out.columns):
                parsed_out = df_out["amount"].apply(lambda s: pd.Series(parse_amount(s, return_issues=True), index=["amount_decimal", "currency", "issues"]))
                df_out = pd.concat([df_out, parsed_out], axis=1)

            # Load merchant map if available and normalize merchants
            merchant_map_path = Path("data/merchants.json")
            merchant_map = None
            if merchant_map_path.exists():
                try:
                    merchant_map = json.loads(merchant_map_path.read_text(encoding="utf-8"))
                except Exception:
                    merchant_map = None

            if "merchant" in df_out.columns:
                # compute canonical names where possible
                if merchant_map:
                    def _norm(m):
                        try:
                            canon, score = normalize_merchant(m, merchant_map)
                            return canon
                        except Exception:
                            return None
                    df_out["merchant_canonical"] = df_out["merchant"].apply(_norm)
                else:
                    df_out["merchant_canonical"] = None

            # Build report and write JSON (formatted amounts written)
            report = build_report_from_dataframe(df_out)
            write_report_json(report, args.report)
            # Print short summary to stdout (formatted)
            top = report.get("top_category")
            amt = report.get("amount")
            print(f"Top spending category: {top} — {format_usd(amt)}")
            log.info("Wrote report to %s", args.report)
        except Exception as e:
            log.error("Failed to generate report: %s", e)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
