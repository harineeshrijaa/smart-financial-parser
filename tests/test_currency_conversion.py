from decimal import Decimal

from smart_financial_parser.parser.normalize import convert_amount_to_usd


def test_convert_amounts_with_default_rates():
    # Using defaults embedded in the function
    assert convert_amount_to_usd(Decimal("10"), "EUR") == Decimal("10.80")
    assert convert_amount_to_usd(Decimal("5"), "GBP") == Decimal("6.25")
    assert convert_amount_to_usd(Decimal("1000"), "JPY") == Decimal("7")
    assert convert_amount_to_usd(Decimal("100"), "INR") == Decimal("1.2")
    assert convert_amount_to_usd(Decimal("2"), "ETH") == Decimal("3600")


def test_convert_with_custom_rates_and_missing_currency_behavior():
    rates = {"EUR": "1.1", "GBP": "1.3"}
    assert convert_amount_to_usd(Decimal("10"), "EUR", rates=rates) == Decimal("11.0")
    # Unknown currency -> None
    assert convert_amount_to_usd(Decimal("10"), "ZZZ", rates=rates) is None
    # Missing currency assumed as USD by default
    assert convert_amount_to_usd(Decimal("5"), None) == Decimal("5")
    # If we don't want to assume missing as USD
    assert convert_amount_to_usd(Decimal("5"), None, assume_missing_usd=False) is None
