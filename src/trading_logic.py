from __future__ import annotations


def baseline_signal_from_rsi(rsi: float) -> str:
    if rsi >= 70:
        return "SELL"
    if rsi <= 30:
        return "BUY"
    return "HOLD"


def llm_enhanced_signal(
    rsi: float,
    close: float,
    bb_lower: float,
    bb_upper: float,
    fear_greed: float,
    sentiment_score: float,
) -> str:
    # Hard contrarian rules from assignment examples.
    if fear_greed >= 80 and rsi >= 70 and close >= bb_upper:
        return "SELL"
    if fear_greed <= 20 and rsi <= 30 and close <= bb_lower:
        return "BUY"

    # Moderate contrarian regime so Strategy B differs from plain RSI baseline.
    greed_regime = fear_greed >= 60 and sentiment_score >= 0.20
    fear_regime = fear_greed <= 40 and sentiment_score <= -0.20

    if greed_regime and rsi >= 25:
        return "SELL"
    if fear_regime and rsi <= 55:
        return "BUY"

    near_upper_band = close >= bb_upper * 0.995
    near_lower_band = close <= bb_lower * 1.005

    # Technical fallback with softer thresholds.
    if near_upper_band and rsi >= 55:
        return "SELL"
    if near_lower_band and rsi <= 45:
        return "BUY"

    # LLM sentiment fallback.
    if sentiment_score >= 0.25 and rsi <= 45:
        return "BUY"
    if sentiment_score <= -0.25 and rsi >= 55:
        return "SELL"

    return "HOLD"


def signal_to_position(signal: str, current_position: int) -> int:
    if signal == "BUY":
        return 1
    if signal == "SELL":
        return -1
    return current_position
