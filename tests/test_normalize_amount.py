import pytest
from decimal import Decimal

from smart_financial_parser.parser.normalize import parse_amount


@pytest.mark.parametrize(
    "inp,expected_amt,expected_cur",
    [
        ("$ 12.50", Decimal("12.50"), "USD"),
        ("(200.00)", Decimal("-200.00"), None),
        ("$4,500.00", Decimal("4500.00"), "USD"),
        ("12.00 USD", Decimal("12.00"), "USD"),
        ("USD12.50", Decimal("12.50"), "USD"),
        ("€9,99", Decimal("9.99"), "EUR"),
        ("1.234,56 €", Decimal("1234.56"), "EUR"),
        ("-£8.00", Decimal("-8.00"), "GBP"),
        ("1200 JPY", Decimal("1200"), "JPY"),
        ("12..00", None, None),
        ("", None, None),
        (None, None, None),
    ],
)
def test_parse_amount_various(inp, expected_amt, expected_cur):
    amt, cur = parse_amount(inp)
    assert amt == expected_amt
    assert cur == expected_cur
