# get_quant_signal — Step 1~3 스켈레톤

## 파일 구성
- `hull_ma.py` — 10/21/50 Hull MA 계산 + 순차 크로스(골든크로스) 감지
- `get_quant_signal.py` — 가격 데이터 → 크로스 감지 → 뉴스 촉매 확인(Claude) → 신뢰도 게이트

## 설치
```bash
pip install anthropic requests pandas numpy --break-system-packages
```

## 환경변수 설정
```bash
export FINNHUB_API_KEY="your_finnhub_key"
export ANTHROPIC_API_KEY="your_anthropic_key"   # console.anthropic.com 에서 발급
```

## 실행
```bash
python3 get_quant_signal.py PLTR
```

## 출력 예시
```json
{
  "ticker": "PLTR",
  "confidence": "high",
  "technical": {
    "hull10": 172.3, "hull21": 170.1, "hull50": 165.8,
    "cross_10_21_date": "2026-08-20", "cross_21_50_date": "2026-08-25",
    "sequence_valid": true, "stage": "uptrend_confirmed"
  },
  "news": {
    "catalyst_found": true, "catalyst_type": "earnings_beat",
    "sentiment_score": 0.6, "divergence_flag": false,
    "reasoning": "..."
  }
}
```

## confidence 값 의미
- `high`   — 골든크로스 + 뉴스 촉매 확인 → 풀사이즈 피라미딩 후보
- `medium` — 골든크로스는 확인됐지만 뉴스가 중립 → 1차만 소액 진입
- `low`    — 골든크로스는 떴지만 뉴스가 부정적/없음 → 진입 보류 (기술-펀더멘털 괴리)
- `none`   — 크로스 자체가 아직 발생 안 함

## 다음 단계 (본인이 이어서 할 것)
1. `fetch_price_history`를 Massive.com/Barchart로 교체하고 싶으면 해당 함수만 바꾸면 됨
   (DataFrame에 'close' 컬럼 + date index만 유지하면 나머지 코드는 그대로 작동)
2. GEX 레벨(Call Wall/Put Wall) 체크를 `gate_signal`에 추가 조건으로 넣기
3. 여러 워치리스트 종목을 순회하며 모닝 브리핑에 통합
4. 페이퍼 트레이딩으로 최소 2주, 20~30개 시그널 이상 쌓일 때까지 실전 자금 투입 보류

## 주의
- 이건 리서치/보조 도구입니다. `confidence: high`가 나와도 최종 진입/사이징 판단은 본인 규칙(Livermore 피라미딩 등)을 따르세요.
- Claude API 호출은 크로스가 확정된 종목에만 실행되도록 설계되어 있어 비용이 크지 않습니다.
