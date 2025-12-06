import argparse
import logging
from pathlib import Path
import sys

from smart_financial_parser.parser.ingest import read_csv
from smart_financial_parser.parser.normalize import parse_date


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
    p.add_argument("--clean-preview", action="store_true", help="Show cleaned preview columns (raw + date_iso)")
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
                # Add a `date_iso` column using parse_date; keep original `date` column
                if "date" in df.columns:
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
                print([{"date": r.get("date"), "date_iso": parse_date(r.get("date"))} for r in df.head(preview_n).to_dict(orient="records")])
            else:
                print(df.head(preview_n).to_dict(orient="records"))

    # Hooks for future features: write output/report if requested
    if args.output:
        try:
            df.to_csv(args.output, index=False)
            log.info("Wrote cleaned CSV to %s", args.output)
        except Exception as e:
            log.error("Failed to write output CSV: %s", e)

    if args.report:
        log.info("Report generation not yet implemented; would write to %s", args.report)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
