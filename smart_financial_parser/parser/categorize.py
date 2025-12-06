# categorize.py

# Small placeholder mapping for later steps.
merchant_to_category = {
    "Uber": "Transport",
    "Starbucks": "Food",
    "Amazon": "Shopping",
    "Walmart": "Groceries",
    "Shell": "Fuel",
}


def categorize(merchant_canonical: str):
    return merchant_to_category.get(merchant_canonical)
