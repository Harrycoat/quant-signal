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

    candidates = []
    for t in tables:
        # flatten MultiIndex columns (Wikipedia tables sometimes have these) to plain strings
        cols = [
            " ".join(str(x) for x in c).strip() if isinstance(c, tuple) else str(c)
            for c in t.columns
        ]
        cols_lower = [c.lower() for c in cols]

        match_col = None
        for i, c in enumerate(cols_lower):
            if "ticker" in c or c.strip() == "symbol" or "symbol" in c:
                match_col = t.columns[i]
                break

        if match_col is not None:
            candidates.append((t, match_col))

    if not candidates:
        raise ValueError("Could not find ticker column in Nasdaq-100 Wikipedia tables")

    # prefer the table whose row count looks like the actual 100-ish constituent list
    candidates.sort(key=lambda tc: abs(len(tc[0]) - 101))
    best_table, best_col = candidates[0]

    tickers = best_table[best_col].astype(str).str.strip()
    tickers = tickers[tickers.str.match(r"^[A-Za-z.\-]{1,6}$")]  # drop stray non-ticker rows
    return tickers.str.replace(".", "-", regex=False).tolist()


def get_universe() -> list:
    sp500 = get_sp500_tickers()
    nasdaq100 = get_nasdaq100_tickers()
    combined = sorted(set(sp500) | set(nasdaq100))
    return combined


if __name__ == "__main__":
    tickers = get_universe()
    print(f"Total unique tickers: {len(tickers)}")
    print(tickers[:20], "...")
