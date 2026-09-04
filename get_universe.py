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
    """
    Nasdaq-100 constituents as a static list (as of Sep 2026).
    Wikipedia's Nasdaq-100 page doesn't reliably expose a parseable
    constituents table (structure changes / table gets dropped), so a
    static list refreshed a few times a year is far more reliable for
    a daily automated job than scraping. Update this list when Nasdaq
    does its annual December reconstitution, or if you notice a new
    addition (e.g. from financial news) missing here.
    """
    return [
        "NVDA", "AAPL", "GOOGL", "GOOG", "MSFT", "MU", "AMZN", "AMD", "TSLA", "META",
        "AVGO", "WMT", "INTC", "CSCO", "PLTR", "COST", "LRCX", "NFLX", "AMAT", "PANW",
        "AMGN", "SNDK", "TXN", "KLAC", "LIN", "CRWD", "TMUS", "PEP", "GILD", "MRVL",
        "STX", "SHOP", "QCOM", "ADI", "ASML", "WDC", "BKNG", "VRTX", "ISRG", "SBUX",
        "ADBE", "FTNT", "ADP", "ARM", "CEG", "MELI", "APP", "CMCSA", "INTU", "DASH",
        "CSX", "MAR", "REGN", "CDNS", "CTAS", "SNPS", "MDLZ", "ABNB", "ROST", "ORLY",
        "DDOG", "WBD", "AEP", "LITE", "HON", "PCAR", "BKR", "MPWR", "NXPI", "FANG",
        "FAST", "TER", "PYPL", "ADSK", "CCEP", "ALAB", "MSTR", "XEL", "NBIS", "EXC",
        "PAYX", "AXON", "KDP", "MNST", "ROP", "TRI", "IDXX", "WDAY", "TTWO", "MCHP",
        "ODFL", "CRWV", "RKLB", "ALNY", "DXCM", "GEHC", "CPRT", "KHC", "EA", "PDD",
    ]


def get_universe() -> list:
    sp500 = get_sp500_tickers()
    nasdaq100 = get_nasdaq100_tickers()
    combined = sorted(set(sp500) | set(nasdaq100))
    return combined


if __name__ == "__main__":
    tickers = get_universe()
    print(f"Total unique tickers: {len(tickers)}")
    print(tickers[:20], "...")
