import pandas as pd
from typing import Any


def read_csv(path: str) -> Any:
    """Read a CSV file and return a pandas.DataFrame.

    This is intentionally small for step 1; later steps will add
    sanitization, logging, and chunking.
    """
    return pd.read_csv(path)
