import argparse
from pathlib import Path

from smart_financial_parser.parser.ingest import read_csv


def main():
    p = argparse.ArgumentParser(description="Smart Financial Parser — basic CLI")
    p.add_argument("--input", "-i", required=True, help="Path to input CSV file")
    p.add_argument("--preview", "-p", type=int, default=3, help="Number of preview rows")
    args = p.parse_args()

    path = Path(args.input)
    if not path.exists():
        print(f"Input file not found: {path}")
        raise SystemExit(2)

    df = read_csv(str(path))
    print(f"Read {len(df)} rows")
    print(df.head(args.preview).to_string(index=False))


if __name__ == "__main__":
    main()
