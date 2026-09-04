"""
get_universe.py — pulls S&P500 + Nasdaq100 ticker lists from Wikipedia.

Usage:
    from get_universe import get_universe
    tickers = get_universe()   # deduplicated list, ~560-600 tickers
"""

import pandas as pd
import requests
from io import StringIO

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}


def _read_html_tables(url: str):
    """Wikipedia returns 403 for requests without a browser-like User-Agent,
    so fetch with requests first, then hand the HTML text to pandas."""
    resp = requests.get(url, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    return pd.read_html(StringIO(resp.text))


def get_sp500_tickers() -> list:
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    tables = _read_html_tables(url)
    df = tables[0]
    return df["Symbol"].str.replace(".", "-", regex=False).tolist()  # BRK.B -> BRK-B for yfinance


def get_nasdaq100_tickers() -> list:
    url = "https://en.wikipedia.org/wiki/Nasdaq-100"
    tables = _read_html_tables(url)
    # the constituents table is usually the one with a 'Ticker' or 'Symbol' column
    for t in tables:
        cols = [c.lower() for c in t.columns.astype(str)]
        if "ticker" in cols:
            col = t.columns[cols.index("ticker")]
            return t[col].str.replace(".", "-", regex=False).tolist()
        if "symbol" in cols:
            col = t.columns[cols.index("symbol")]
            return t[col].str.replace(".", "-", regex=False).tolist()
    raise ValueError("Could not find ticker column in Nasdaq-100 Wikipedia tables")


def get_universe() -> list:
    sp500 = get_sp500_tickers()
    nasdaq100 = get_nasdaq100_tickers()
    combined = sorted(set(sp500) | set(nasdaq100))
    return combined


if __name__ == "__main__":
    tickers = get_universe()
    print(f"Total unique tickers: {len(tickers)}")
    print(tickers[:20], "...")
