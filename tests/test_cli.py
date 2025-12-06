import sys
from smart_financial_parser.cli import main
import pytest


def capture_all_output(capfd):
    out, err = capfd.readouterr()
    return out + err


def test_cli_preview_shows_rows_and_preview(capfd):
    # Show 1 preview row and assert that output contains row data
    rc = main(["--input", "data/messy_transactions.csv", "--preview", "1"])
    assert rc == 0
    combined = capture_all_output(capfd)
    # Merchant name from first row should appear in stdout preview
    assert "UBER *TRIP" in combined


def test_cli_sample_reads_n_rows(capfd):
    # Use sample flag to limit rows read; preview set to 0 to suppress table
    rc = main(["--input", "data/messy_transactions.csv", "--preview", "0", "--sample", "3"])
    assert rc == 0
    combined = capture_all_output(capfd)
    # Should report 3 rows read and mention sample mode (printed to stdout)
    assert "Read 3 rows" in combined
    assert "sample mode" in combined


def test_cli_missing_file_raises_systemexit():
    with pytest.raises(SystemExit) as exc:
        main(["--input", "data/does_not_exist.csv", "--preview", "1"])
    assert exc.value.code == 2
