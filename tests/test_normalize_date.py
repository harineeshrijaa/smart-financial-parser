import pytest

from smart_financial_parser.parser.normalize import parse_date


@pytest.mark.parametrize(
    "inp,expected",
    [
        (None, None),
        ("", None),
        ("2020-01-05", "2020-01-05"),
        ("Jan 5, 2020", "2020-01-05"),
        ("5 Jan 2020", "2020-01-05"),
        ("5th Jan 2021", "2021-01-05"),
        ("01/02/03", "2003-01-02"),  # MDY + 2-digit year -> 2003
        ("12/11/10", "2010-12-11"),
        ("7-8-95", "1995-07-08"),
        ("01/02/49", "1949-01-02"),  # pivot: now maps 26+ to 1900s, so 49 -> 1949
        ("01/02/50", "1950-01-02"),  # pivot: 50-99 -> 1900s
        ("March 3rd '99", "1999-03-03"),
        ("20-01-2020", "2020-01-20"),  # day > 12 should be handled as day
        ("not a date", None),
        ("99/99/9999", None),
    ],
)
def test_parse_date_various(inp, expected):
    assert parse_date(inp) == expected
