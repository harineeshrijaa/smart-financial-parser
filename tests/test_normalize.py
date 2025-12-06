from decimal import Decimal
from smart_financial_parser.parser.normalize import parse_date, parse_amount


def test_parse_date_basic():
    assert parse_date("2023-01-01") == "2023-01-01"
    assert parse_date("Jan 1st 23") == "2023-01-01"
    assert parse_date("2023-08-01T14:30:00Z") == "2023-08-01"


def test_parse_amount_basic():
    val, cur = parse_amount("$ 12.50")
    assert val == Decimal("12.50")
    assert cur == "USD"

    val2, cur2 = parse_amount("(200.00)")
    assert val2 == Decimal("-200.00")
