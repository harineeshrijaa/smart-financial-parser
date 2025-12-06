from decimal import Decimal
from smart_financial_parser.parser.normalize import parse_amount


def test_fullwidth_digits():
    s = '１２３４．５６'
    val, curr, issues = parse_amount(s, return_issues=True)
    assert val == Decimal('1234.56')
    assert curr is None
    assert 'unicode_digits_converted' in issues
    assert 'normalized_decimal_separators' in issues


def test_thin_space_grouping():
    # thin space (U+2009) as thousands separator
    s = '1\u2009234.56'
    val, curr, issues = parse_amount(s, return_issues=True)
    assert val == Decimal('1234.56')
    assert 'normalized_space' in issues


def test_apostrophe_grouping_chf():
    s = "1'234.56 CHF"
    val, curr, issues = parse_amount(s, return_issues=True)
    assert val == Decimal('1234.56')
    assert curr == 'CHF'
    assert 'removed_apostrophe_grouping' in issues


def test_multi_dot_repair():
    s = '1.234.56 USD'
    val, curr, issues = parse_amount(s, return_issues=True)
    assert val == Decimal('1234.56')
    assert curr == 'USD'
    assert 'repaired_multiple_dots' in issues


def test_arabic_indic_digits():
    s = '١٢٣٤٫٥٦'
    val, curr, issues = parse_amount(s, return_issues=True)
    assert val == Decimal('1234.56')
    assert 'unicode_digits_converted' in issues
    assert 'normalized_decimal_separators' in issues


def test_nbsp_grouping():
    s = '1\u00A0234.56'
    val, curr, issues = parse_amount(s, return_issues=True)
    assert val == Decimal('1234.56')
    assert 'normalized_space' in issues


def test_currency_word_usd():
    s = '12 dollars'
    val, curr, issues = parse_amount(s, return_issues=True)
    assert val == Decimal('12')
    assert curr == 'USD'
