"""
mail_report.py — sends the watchlist scan results as an email via Gmail SMTP.

SETUP REQUIRED:
    1. Use a Gmail "App Password" (NOT your normal Gmail password):
       Google Account -> Security -> 2-Step Verification -> App passwords
       Generate one for "Mail" and copy the 16-character code.
    2. Set these as GitHub Secrets (Settings -> Secrets and variables -> Actions):
       GMAIL_ADDRESS       = your Gmail address (sender AND recipient)
       GMAIL_APP_PASSWORD  = the 16-character app password
       FINNHUB_API_KEY
       ANTHROPIC_API_KEY

Usage:
    python3 mail_report.py            (scans DEFAULT_WATCHLIST, emails results)
    python3 mail_report.py ANET TSLA  (scans just these tickers)
"""

import os
import sys
import smtplib
from email.mime.text import MIMEText
from datetime import datetime

from get_quant_signal import get_quant_signal
from scan_watchlist import DEFAULT_WATCHLIST

GMAIL_ADDRESS = os.environ.get("GMAIL_ADDRESS", "")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "")


def build_report_text(results: list) -> str:
    today = datetime.now().strftime("%Y-%m-%d")
    lines = [f"=== 워치리스트 시그널 스캔 결과 ({today}) ===\n"]

    actionable = [r for r in results if r["confidence"] != "none"]
    quiet = [r for r in results if r["confidence"] == "none"]

    if actionable:
        lines.append("[신호 발생 종목]")
        for r in actionable:
            t = r["technical"]
            lines.append(f"\n{r['ticker']} — confidence: {r['confidence'].upper()}")
            lines.append(f"  stage: {t['stage']}")
            lines.append(f"  10/21 cross: {t['cross_10_21_date']}")
            lines.append(f"  21/50 cross: {t['cross_21_50_date']}")
            if r["news"]:
                n = r["news"]
                lines.append(f"  news catalyst: {n['catalyst_type']} (sentiment {n['sentiment_score']})")
                lines.append(f"  reasoning: {n['reasoning']}")
    else:
        lines.append("[신호 발생 종목 없음]")

    lines.append(f"\n\n[관찰만 필요한 종목: {', '.join(r['ticker'] for r in quiet)}]" if quiet else "")

    return "\n".join(lines)


def send_email(subject: str, body: str):
    if not GMAIL_ADDRESS or not GMAIL_APP_PASSWORD:
        raise RuntimeError("GMAIL_ADDRESS / GMAIL_APP_PASSWORD 환경변수가 설정되지 않았습니다.")

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = GMAIL_ADDRESS
    msg["To"] = GMAIL_ADDRESS

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
        server.send_message(msg)


if __name__ == "__main__":
    tickers = sys.argv[1:] if len(sys.argv) > 1 else DEFAULT_WATCHLIST

    results = []
    for ticker in tickers:
        try:
            results.append(get_quant_signal(ticker))
        except Exception as e:
            print(f"{ticker} error: {e}")

    report = build_report_text(results)
    print(report)  # also print to console/log for GitHub Actions logs

    today = datetime.now().strftime("%Y-%m-%d")
    send_email(f"[워치리스트 스캔] {today}", report)
    print("\n메일 발송 완료")
