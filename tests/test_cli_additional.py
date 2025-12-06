import logging
from smart_financial_parser.cli import main


def test_cli_writes_output_file(tmp_path, capfd):
    out = tmp_path / "out.csv"
    rc = main(["--input", "data/messy_transactions.csv", "--preview", "0", "--output", str(out)])
    assert rc == 0
    assert out.exists()
    # basic sanity: output contains header 'date'
    text = out.read_text(encoding="utf-8")
    assert "date" in text


def test_cli_verbose_emits_debug(caplog):
    # calling main with --verbose should emit debug logs captured by caplog
    caplog.set_level(logging.DEBUG)
    rc = main(["--input", "data/messy_transactions.csv", "--preview", "0", "--verbose"]) 
    assert rc == 0
    # Ensure debug messages were logged
    texts = "\n".join(r.getMessage() for r in caplog.records)
    assert "Verbose mode enabled" in texts or "Read CSV shape" in texts


def test_cli_preview_zero_shows_no_table(capfd):
    rc = main(["--input", "data/messy_transactions.csv", "--preview", "0"])
    assert rc == 0
    out, err = capfd.readouterr()
    # Should include Read N rows but not the header line
    assert "Read" in out
    assert "date" not in out


def test_cli_encoding_fallback(tmp_path, capfd):
    # create a latin-1 encoded CSV with an accented character
    p = tmp_path / "latin1.csv"
    content = 'date,merchant,amount,notes\n"2025-01-01","CAFÉ","$1.00","coffee"\n'
    p.write_bytes(content.encode('latin-1'))

    rc = main(["--input", str(p), "--preview", "1"])
    assert rc == 0
    out, err = capfd.readouterr()
    assert "CAFÉ" in out


def test_cli_handles_empty_file(tmp_path, capfd):
    p = tmp_path / "empty.csv"
    # write only headers
    p.write_text("date,merchant,amount,notes\n", encoding="utf-8")
    rc = main(["--input", str(p), "--preview", "1"])
    assert rc == 0
    out, err = capfd.readouterr()
    assert "Read 0 rows" in out