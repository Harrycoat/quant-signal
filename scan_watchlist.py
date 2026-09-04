"""
scan_watchlist.py — runs get_quant_signal() across your whole watchlist at once
and prints only the tickers worth looking at (skips 'none' confidence to reduce noise).

Usage:
    python3 scan_watchlist.py
    python3 scan_watchlist.py ANET PLTR NBIS   (override the default list)
"""

import sys
import json
from get_quant_signal import get_quant_signal

DEFAULT_WATCHLIST = [
    "ANET", "PLTR", "NBIS", "NET", "TEM", "SPCX",
    # add/remove tickers here as your watchlist changes
]


def scan(tickers):
    results = []
    for ticker in tickers:
        print(f"Checking {ticker}...")
        try:
            result = get_quant_signal(ticker)
        except Exception as e:
            print(f"  -> error: {e}")
            continue

        results.append(result)

        if result["confidence"] == "none":
            continue  # skip printing full detail for non-candidates

        print(json.dumps(result, indent=2, default=str))
        print("-" * 60)

    # summary line at the end
    print("\n=== Summary ===")
    for r in results:
        print(f"{r['ticker']:6s} stage={r['technical']['stage']:20s} confidence={r['confidence']}")


if __name__ == "__main__":
    tickers = sys.argv[1:] if len(sys.argv) > 1 else DEFAULT_WATCHLIST
    scan(tickers)
