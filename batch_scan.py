"""
batch_scan.py — scans the full S&P500 + Nasdaq100 universe in a handful of
batch requests (instead of one yfinance call per ticker), then runs the
news-catalyst check only on tickers whose golden cross just confirmed.

Usage:
    python3 batch_scan.py                 (scans full universe, emails report)
    python3 batch_scan.py --no-email       (prints only, skips sending mail)
"""

import sys
import time
import json
from datetime import datetime

import pandas as pd
import yfinance as yf

from hull_ma import detect_dual_cross
from get_quant_signal import fetch_recent_news, check_news_catalyst, gate_signal
from get_universe import get_universe
from mail_report import send_email

BATCH_SIZE = 80          # tickers per yfinance batch request
PAUSE_BETWEEN_BATCHES = 2  # seconds, to stay polite to Yahoo's servers


def chunk(lst, size):
    for i in range(0, len(lst), size):
        yield lst[i:i + size]


def batch_download(tickers: list, period_days: int = 200) -> dict:
    """
    Downloads price history for many tickers in batches.
    Returns {ticker: DataFrame with 'close' column}.
    """
    results = {}
    batches = list(chunk(tickers, BATCH_SIZE))

    for i, batch in enumerate(batches, 1):
        print(f"Batch {i}/{len(batches)} ({len(batch)} tickers)...")
        try:
            data = yf.download(
                batch, period=f"{period_days}d", interval="1d",
                group_by="ticker", progress=False, auto_adjust=True,
                threads=True,
            )
        except Exception as e:
            print(f"  batch download failed: {e}")
            continue

        for ticker in batch:
            try:
                if len(batch) == 1:
                    close = data["Close"]
                else:
                    close = data[ticker]["Close"]
                close = close.dropna()
                if close.empty:
                    continue
                df = pd.DataFrame({"close": close})
                df.index = pd.to_datetime(df.index).tz_localize(None)
                results[ticker] = df
            except (KeyError, Exception):
                continue  # ticker delisted / no data / renamed, skip quietly

        if i < len(batches):
            time.sleep(PAUSE_BETWEEN_BATCHES)

    return results


def scan_universe(send_mail: bool = True):
    print("Fetching ticker universe (S&P500 + Nasdaq100)...")
    tickers = get_universe()
    print(f"Universe size: {len(tickers)} tickers")

    price_data = batch_download(tickers)
    print(f"Successfully downloaded: {len(price_data)}/{len(tickers)} tickers")

    confirmed = []  # tickers with uptrend_confirmed stage
    all_results = []

    for ticker, df in price_data.items():
        if len(df) < 55:  # need enough bars for hull50
            continue
        try:
            cross_result = detect_dual_cross(df, lookback=10)
        except Exception:
            continue

        result = {
            "ticker": ticker,
            "checked_at": datetime.now().isoformat(),
            "technical": cross_result,
            "news": None,
            "confidence": "none",
        }

        if cross_result["stage"] == "uptrend_confirmed":
            confirmed.append(ticker)
        all_results.append(result)

    print(f"\nTickers with confirmed golden cross: {len(confirmed)}")
    print(confirmed)

    # only spend Claude/Finnhub calls on the confirmed ones
    final_results = []
    for result in all_results:
        if result["technical"]["stage"] != "uptrend_confirmed":
            continue  # skip emailing/detailing the 'none' bulk — too much noise
        ticker = result["ticker"]
        try:
            news = fetch_recent_news(ticker)
            news_result = check_news_catalyst(ticker, news)
            result["news"] = news_result
            result["confidence"] = gate_signal(result["technical"], news_result)
        except Exception as e:
            print(f"  news check failed for {ticker}: {e}")
        final_results.append(result)

    print(json.dumps(final_results, indent=2, default=str))

    if send_mail:
        from mail_report import build_report_text
        report = build_report_text(final_results) if final_results else \
            f"=== 전체 유니버스 스캔 ({datetime.now().strftime('%Y-%m-%d')}) ===\n\n[골든크로스 확정 종목 없음]\n(총 {len(price_data)}개 종목 체크)"
        print(report)
        send_email(f"[전체 유니버스 스캔] {datetime.now().strftime('%Y-%m-%d')}", report)
        print("\n메일 발송 완료")


if __name__ == "__main__":
    send_mail = "--no-email" not in sys.argv
    scan_universe(send_mail=send_mail)
