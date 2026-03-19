from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from dotenv import load_dotenv

CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from charting import plot_ab_performance
from config import load_settings
from indicators import add_technical_indicators
from llm_clients import LLMClient, LLMPayload
from telegram_client import send_message, send_photo
from trading_logic import baseline_signal_from_rsi, llm_enhanced_signal, signal_to_position


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    aliases = {
        "timestamp": "date",
        "datetime": "date",
        "time": "date",
        "price": "close",
        "last": "close",
        "news": "news_titles",
        "headlines": "news_titles",
    }
    cols = {c: aliases.get(c.strip().lower(), c.strip().lower()) for c in out.columns}
    out = out.rename(columns=cols)
    required = {"date", "close", "news_titles"}
    missing = sorted(required - set(out.columns))
    if missing:
        raise ValueError(f"Input CSV must contain columns: {sorted(required)}. Missing: {missing}")
    return out


def _generate_demo_data(symbol: str, rows: int = 45) -> pd.DataFrame:
    rng = np.random.default_rng(42)
    dates = pd.date_range(end=pd.Timestamp.today().normalize(), periods=rows, freq="D")

    returns = rng.normal(0.001, 0.02, size=rows)
    close = 100 * np.cumprod(1 + returns)

    positive_news = [
        "Institutional inflows increase",
        "Market sentiment improves",
        "Whales accumulate on dips",
        "Macro data supports risk assets",
    ]
    negative_news = [
        "Regulatory uncertainty rises",
        "Analysts warn of overheating",
        "Risk-off mood in global markets",
        "Profit taking accelerates",
    ]

    titles: list[str] = []
    for r in returns:
        source = positive_news if r >= 0 else negative_news
        titles.append(source[int(rng.integers(0, len(source)))])

    return pd.DataFrame(
        {
            "date": dates,
            "close": close,
            "news_titles": [f"{symbol}: {t}" for t in titles],
        }
    )


def _simple_news_score(text: str) -> float:
    txt = (text or "").lower()
    positive = ["inflow", "optimistic", "bull", "surge", "accumulate", "improves", "supports"]
    negative = ["risk", "warn", "panic", "uncertainty", "selloff", "overheating", "profit taking"]

    score = 0
    for token in positive:
        score += txt.count(token)
    for token in negative:
        score -= txt.count(token)

    return float(max(-1.0, min(1.0, score / 4.0)))


def _positions_from_signals(signals: pd.Series) -> pd.Series:
    current = 0
    positions: list[int] = []
    for signal in signals.astype(str):
        current = signal_to_position(signal, current)
        positions.append(current)
    return pd.Series(positions, index=signals.index, dtype=int)


def _sharpe(daily_returns: pd.Series) -> float:
    std = float(daily_returns.std(ddof=0))
    if std == 0:
        return 0.0
    return float((daily_returns.mean() / std) * math.sqrt(252))


def _max_drawdown(cum_curve: pd.Series) -> float:
    wealth = 1 + cum_curve.fillna(0)
    running_max = wealth.cummax()
    drawdown = wealth / running_max - 1
    return float(drawdown.min())


def _build_message(latest: pd.Series, llm: dict, symbol: str, timeframe: str) -> str:
    return (
        f"📊 {symbol} ({timeframe})\n"
        f"Signal: {latest['signal_b']}\n"
        f"Price: {latest['close']:.4f}\n"
        f"RSI: {latest['rsi']:.2f}\n"
        f"Fear/Greed: {llm['fear_greed']:.0f}\n"
        f"Sentiment: {llm['sentiment_label']} ({llm['sentiment_score']:.2f})\n\n"
        f"🧠 {llm['analysis_short']}\n\n"
        f"⚠️ Risks: {', '.join(llm['risk_flags']) if llm['risk_flags'] else 'n/a'}\n"
        "Educational use only."
    )


def run_pipeline(
    input_csv: Path,
    out_dir: Path,
    symbol: str,
    timeframe: str,
    llm_mode: str,
    send_telegram_enabled: bool,
) -> dict:
    if input_csv.exists():
        source_df = pd.read_csv(input_csv)
        source_df = _normalize_columns(source_df)
    else:
        source_df = _generate_demo_data(symbol=symbol)

    df = source_df.copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["close"] = pd.to_numeric(df["close"], errors="coerce")
    df["news_titles"] = df["news_titles"].fillna("").astype(str)
    df = df.dropna(subset=["date", "close"]).sort_values("date").reset_index(drop=True)

    if len(df) < 10:
        raise ValueError("Need at least 10 rows for meaningful indicators")

    df = add_technical_indicators(df)

    df["sentiment_score"] = df["news_titles"].map(_simple_news_score)
    df["fear_greed"] = (50 + 35 * df["sentiment_score"] + (df["rsi"] - 50) * 0.2).clip(0, 100)

    df["signal_a"] = df["rsi"].map(baseline_signal_from_rsi)
    df["signal_b"] = df.apply(
        lambda r: llm_enhanced_signal(
            rsi=float(r["rsi"]),
            close=float(r["close"]),
            bb_lower=float(r["bb_lower"]),
            bb_upper=float(r["bb_upper"]),
            fear_greed=float(r["fear_greed"]),
            sentiment_score=float(r["sentiment_score"]),
        ),
        axis=1,
    )

    settings = load_settings()
    llm_client = LLMClient(
        mode=llm_mode,
        ollama_url=settings.ollama_url,
        ollama_model=settings.ollama_model,
        hf_model=settings.hf_model,
        hf_api_token=settings.hf_api_token,
    )

    recent_news = df["news_titles"].tail(5).tolist()
    last_idx = df.index[-1]
    llm_response = llm_client.analyze(
        LLMPayload(
            symbol=symbol,
            timeframe=timeframe,
            rsi=float(df.loc[last_idx, "rsi"]),
            sma_50=float(df.loc[last_idx, "sma_50"]),
            close=float(df.loc[last_idx, "close"]),
            news_titles=recent_news,
        )
    )

    df.loc[last_idx, "fear_greed"] = llm_response["fear_greed"]
    df.loc[last_idx, "sentiment_score"] = llm_response["sentiment_score"]
    df.loc[last_idx, "signal_b"] = llm_enhanced_signal(
        rsi=float(df.loc[last_idx, "rsi"]),
        close=float(df.loc[last_idx, "close"]),
        bb_lower=float(df.loc[last_idx, "bb_lower"]),
        bb_upper=float(df.loc[last_idx, "bb_upper"]),
        fear_greed=float(df.loc[last_idx, "fear_greed"]),
        sentiment_score=float(df.loc[last_idx, "sentiment_score"]),
    )

    df["pos_a"] = _positions_from_signals(df["signal_a"])
    df["pos_b"] = _positions_from_signals(df["signal_b"])
    df["ret"] = df["close"].pct_change().fillna(0.0)

    df["daily_a"] = df["pos_a"].shift(1).fillna(0) * df["ret"]
    df["daily_b"] = df["pos_b"].shift(1).fillna(0) * df["ret"]
    df["cum_a"] = (1 + df["daily_a"]).cumprod() - 1
    df["cum_b"] = (1 + df["daily_b"]).cumprod() - 1

    out_dir.mkdir(parents=True, exist_ok=True)

    chart_path = out_dir / "ab_30d.png"
    plot_ab_performance(df=df, output_path=chart_path, days=30)

    report_cols = [
        "date",
        "close",
        "rsi",
        "bb_lower",
        "bb_upper",
        "fear_greed",
        "sentiment_score",
        "signal_a",
        "signal_b",
        "daily_a",
        "daily_b",
        "cum_a",
        "cum_b",
    ]
    report_df = df[report_cols].copy()
    report_df.to_csv(out_dir / "trade_log.csv", index=False)

    latest = df.iloc[-1]
    message = _build_message(latest=latest, llm=llm_response, symbol=symbol, timeframe=timeframe)

    summary = {
        "symbol": symbol,
        "timeframe": timeframe,
        "rows": int(len(df)),
        "latest_signal": str(latest["signal_b"]),
        "latest_price": float(latest["close"]),
        "fear_greed": float(llm_response["fear_greed"]),
        "sentiment_label": str(llm_response["sentiment_label"]),
        "sentiment_score": float(llm_response["sentiment_score"]),
        "sharpe_a": _sharpe(df["daily_a"]),
        "sharpe_b": _sharpe(df["daily_b"]),
        "max_drawdown_a": _max_drawdown(df["cum_a"]),
        "max_drawdown_b": _max_drawdown(df["cum_b"]),
    }

    (out_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / "llm_analysis.json").write_text(json.dumps(llm_response, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / "telegram_message.txt").write_text(message, encoding="utf-8")

    if send_telegram_enabled:
        if settings.telegram_bot_token and settings.telegram_chat_id:
            send_message(settings.telegram_bot_token, settings.telegram_chat_id, message)
            send_photo(
                settings.telegram_bot_token,
                settings.telegram_chat_id,
                chart_path,
                caption="A vs B performance (30 days)",
            )
        else:
            print("TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID not configured; skipped Telegram send")

    return summary


def main() -> None:
    project_root = CURRENT_DIR.parent
    load_dotenv(project_root / ".env")

    parser = argparse.ArgumentParser(description="Run AI in Business trading assistant pipeline")
    parser.add_argument("--input-csv", type=Path, default=project_root / "data" / "market_news.csv")
    parser.add_argument("--out-dir", type=Path, default=project_root / "outputs")
    parser.add_argument("--symbol", type=str, default="BTCUSDT")
    parser.add_argument("--timeframe", type=str, default="1d")
    parser.add_argument("--llm-mode", type=str, default="mock", choices=["mock", "ollama", "hf"])
    parser.add_argument("--send-telegram", action="store_true")
    args = parser.parse_args()

    summary = run_pipeline(
        input_csv=args.input_csv,
        out_dir=args.out_dir,
        symbol=args.symbol,
        timeframe=args.timeframe,
        llm_mode=args.llm_mode,
        send_telegram_enabled=args.send_telegram,
    )

    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
