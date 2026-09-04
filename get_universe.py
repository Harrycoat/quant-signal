"""
get_universe.py — pulls S&P500 + Nasdaq100 ticker lists from Wikipedia.

Usage:
    from get_universe import get_universe
    tickers = get_universe()   # deduplicated list, ~560-600 tickers
"""

import pandas as pd


def get_sp500_tickers() -> list:
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    tables = pd.read_html(url)
    df = tables[0]
    return df["Symbol"].str.replace(".", "-", regex=False).tolist()  # BRK.B -> BRK-B for yfinance


def get_nasdaq100_tickers() -> list:
    url = "https://en.wikipedia.org/wiki/Nasdaq-100"
    tables = pd.read_html(url)
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
