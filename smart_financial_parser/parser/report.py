import json
from decimal import Decimal
from typing import Any, Dict


def write_top_spending(summary: Dict[str, Any], path: str):
    # Convert Decimal to float for JSON
    def _default(o):
        if isinstance(o, Decimal):
            return float(o)
        raise TypeError

    with open(path, "w", encoding="utf-8") as f:
        json.dump(summary, f, default=_default, indent=2)
