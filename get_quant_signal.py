"""
get_quant_signal(ticker) — Step 1~3 of Harry's directional swing pipeline.

Pipeline:
    1. Pull price history (Finnhub / your existing data source)
    2. Detect 10/21/50 Hull MA dual-cross (hull_ma.py)
    3. If a cross fired, pull recent news (Finnhub) and ask Claude
       whether a real catalyst supports the move, or if it's a
       technical-only bounce (divergence risk)
    4. Return a single dict with a confidence gate:
         'high'   -> golden cross + catalyst confirmed
         'medium' -> golden cross, no clear catalyst (neutral news)
         'low'    -> golden cross, but news is negative (divergence flag)
         'none'   -> no valid cross

SETUP REQUIRED (fill these in before running for real):
    - FINNHUB_API_KEY   (used for news only — free tier is fine)
    - ANTHROPIC_API_KEY (get from console.anthropic.com)
    pip install anthropic requests pandas numpy yfinance --break-system-packages
"""

import os
import json
from datetime import datetime, timedelta

import pandas as pd
import requests

from hull_ma import detect_dual_cross

FINNHUB_API_KEY = os.environ.get("FINNHUB_API_KEY", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

FINNHUB_BASE = "https://finnhub.io/api/v1"


# ---------------------------------------------------------------------------
# 1. Price data
# ---------------------------------------------------------------------------
def fetch_price_history(ticker: str, days: int = 200) -> pd.DataFrame:
    """
    Pulls daily close prices via yfinance (free, no API key needed).

    NOTE: Finnhub's free tier no longer allows the /stock/candle endpoint
    for US equities (returns 403 "You don't have access to this resource").
    yfinance is used here instead for price history. Finnhub is still used
    for news (fetch_recent_news) since that endpoint remains free.

    Swap this out for Massive.com / Barchart if you prefer that source —
    just make sure the returned DataFrame has a 'close' column indexed by date.
    """
    import yfinance as yf

    buffer_days = int(days * 1.6) + 30  # buffer for weekends/holidays
    df_raw = yf.download(ticker, period=f"{buffer_days}d", interval="1d", progress=False, auto_adjust=True)

    if df_raw is None or df_raw.empty:
        raise ValueError(f"No price data returned for {ticker}")

    close_col = df_raw["Close"]
    if isinstance(close_col, pd.DataFrame):  # yfinance sometimes returns multi-index columns
        close_col = close_col.iloc[:, 0]

    df = pd.DataFrame({"close": close_col})
    df.index = pd.to_datetime(df.index).tz_localize(None)
    return df.tail(days)


# ---------------------------------------------------------------------------
# 2. News
# ---------------------------------------------------------------------------
def fetch_recent_news(ticker: str, lookback_days: int = 5) -> list:
    """Pulls recent company news headlines + summaries from Finnhub."""
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=lookback_days)

    url = f"{FINNHUB_BASE}/company-news"
    params = {
        "symbol": ticker,
        "from": start_date.isoformat(),
        "to": end_date.isoformat(),
        "token": FINNHUB_API_KEY,
    }
    resp = requests.get(url, params=params, timeout=10)
    resp.raise_for_status()
    articles = resp.json()

    # keep it light — headline + summary only, cap at 10 most recent
    return [
        {"headline": a.get("headline", ""), "summary": a.get("summary", "")}
        for a in articles[:10]
    ]


# ---------------------------------------------------------------------------
# 3. Claude catalyst check
# ---------------------------------------------------------------------------
def check_news_catalyst(ticker: str, news: list) -> dict:
    """
    Asks Claude whether recent news supports the technical breakout,
    or whether it looks like a technical-only move with no catalyst.
    Returns: {catalyst_found, catalyst_type, sentiment_score, divergence_flag, reasoning}
    """
    if not news:
        return {
            "catalyst_found": False,
            "catalyst_type": None,
            "sentiment_score": 0,
            "divergence_flag": True,
            "reasoning": "No recent news found — cannot confirm a fundamental catalyst.",
        }

    try:
        import anthropic
    except ImportError:
        raise RuntimeError("Run: pip install anthropic --break-system-packages")

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    news_text = "\n".join(
        f"- {a['headline']}: {a['summary']}" for a in news if a["headline"]
    )

    prompt = f"""You are a trading analyst helping evaluate whether a stock's recent \
technical breakout (10/21/50 Hull MA golden cross) is backed by a real fundamental \
catalyst, or if it's likely just a technical/short-covering bounce.

Ticker: {ticker}

Recent news (last few days):
{news_text}

Respond with ONLY a JSON object, no other text, in this exact format:
{{
  "catalyst_found": true or false,
  "catalyst_type": "earnings_beat" | "guidance_raise" | "analyst_upgrade" | "product_launch" | "sector_rotation" | "none" | "other",
  "sentiment_score": a number from -1.0 (very negative) to 1.0 (very positive),
  "divergence_flag": true if the news is neutral/negative despite the price breakout,
  "reasoning": "one or two sentences explaining your assessment"
}}"""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=400,
        messages=[{"role": "user", "content": prompt}],
    )

    raw_text = response.content[0].text.strip()
    raw_text = raw_text.replace("```json", "").replace("```", "").strip()
    return json.loads(raw_text)


# ---------------------------------------------------------------------------
# 4. Gate logic — combine technical + news into one confidence level
# ---------------------------------------------------------------------------
def gate_signal(cross_result: dict, news_result: dict | None) -> str:
    if cross_result["stage"] != "uptrend_confirmed":
        return "none"

    if news_result is None:
        return "medium"  # cross confirmed, news check skipped/unavailable

    if news_result["divergence_flag"]:
        return "low"
    if news_result["catalyst_found"] and news_result["sentiment_score"] > 0.2:
        return "high"
    return "medium"


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------
def get_quant_signal(ticker: str, run_news_check: bool = True) -> dict:
    price_df = fetch_price_history(ticker)
    cross_result = detect_dual_cross(price_df, lookback=10)

    news_result = None
    if run_news_check and cross_result["stage"] == "uptrend_confirmed":
        news = fetch_recent_news(ticker)
        news_result = check_news_catalyst(ticker, news)

    confidence = gate_signal(cross_result, news_result)

    return {
        "ticker": ticker,
        "checked_at": datetime.now().isoformat(),
        "technical": cross_result,
        "news": news_result,
        "confidence": confidence,  # 'high' | 'medium' | 'low' | 'none'
    }


if __name__ == "__main__":
    import sys
    ticker = sys.argv[1] if len(sys.argv) > 1 else "PLTR"
    result = get_quant_signal(ticker)
    print(json.dumps(result, indent=2, default=str))
