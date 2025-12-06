import pandas as pd
from typing import Any, Optional


def read_csv(path: str, sample: Optional[int] = None, *, encoding: str = "utf-8", keep_default_na: bool = False) -> Any:
    """Read a CSV file into a pandas.DataFrame with robust defaults.

    Parameters
    - path: path to CSV file
    - sample: if provided, only read the first `sample` rows (fast iteration)
    - encoding: file encoding (defaults to 'utf-8')
    - keep_default_na: pass-through to pandas to control NA parsing; default False keeps raw strings

    Returns a pandas.DataFrame with all columns read as strings (to preserve messy input).

    Raises ValueError with a helpful message on failure to read.
    """
    try:
        read_kwargs = {
            "dtype": str,
            "encoding": encoding,
            "keep_default_na": keep_default_na,
        }
        if sample is not None and sample > 0:
            # Use nrows for efficient sampling on read
            df = pd.read_csv(path, nrows=sample, **read_kwargs)
        else:
            df = pd.read_csv(path, **read_kwargs)
    except FileNotFoundError:
        raise ValueError(f"Input file not found: {path}")
    except UnicodeDecodeError:
        # Try a common fallback encoding and re-raise a helpful message if that fails
        try:
            read_kwargs["encoding"] = "latin-1"
            if sample is not None and sample > 0:
                df = pd.read_csv(path, nrows=sample, **read_kwargs)
            else:
                df = pd.read_csv(path, **read_kwargs)
        except Exception as e:
            raise ValueError(f"Unable to read {path}: encoding error (tried utf-8 and latin-1). Original: {e}")
    except Exception as e:
        raise ValueError(f"Failed to read CSV at {path}: {e}")

    # Ensure DataFrame columns are present even for empty files
    if df.empty:
        # Permit empty frames but warn via exception to make failures explicit to callers
        # Caller can decide whether empty is acceptable.
        return df

    # Strip BOM from column names if present
    df.rename(columns=lambda c: c.strip("\ufeff") if isinstance(c, str) else c, inplace=True)

    return df
