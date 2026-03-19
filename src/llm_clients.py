from __future__ import annotations

import json
import re
from dataclasses import dataclass

import requests


SYSTEM_PROMPT = (
    "You are a cautious financial analyst assistant. "
    "You never provide direct investment advice. "
    "Return only valid JSON."
)


@dataclass
class LLMPayload:
    symbol: str
    timeframe: str
    rsi: float
    sma_50: float
    close: float
    news_titles: list[str]


class LLMClient:
    def __init__(
        self,
        mode: str,
        ollama_url: str,
        ollama_model: str,
        hf_model: str,
        hf_api_token: str,
        timeout: int = 30,
    ) -> None:
        self.mode = mode
        self.ollama_url = ollama_url.rstrip("/")
        self.ollama_model = ollama_model
        self.hf_model = hf_model
        self.hf_api_token = hf_api_token
        self.timeout = timeout

    def analyze(self, payload: LLMPayload) -> dict:
        if self.mode == "ollama":
            try:
                return self._ollama(payload)
            except Exception:
                return self._heuristic(payload)
        if self.mode == "hf":
            try:
                return self._hf(payload)
            except Exception:
                return self._heuristic(payload)
        return self._heuristic(payload)

    def _build_user_prompt(self, payload: LLMPayload) -> str:
        news_text = "\n".join(f"- {x}" for x in payload.news_titles[-5:])
        return (
            "Analyze market snapshot and news. Return JSON only with keys:\n"
            "fear_greed (0..100), sentiment_label (POSITIVE/NEGATIVE/NEUTRAL), "
            "sentiment_score (-1..1), risk_flags (array of short strings), "
            "analysis_short (max 110 words).\n\n"
            f"Symbol: {payload.symbol}\n"
            f"Timeframe: {payload.timeframe}\n"
            f"RSI: {payload.rsi:.2f}\n"
            f"SMA_50: {payload.sma_50:.4f}\n"
            f"Price: {payload.close:.4f}\n"
            f"Recent News:\n{news_text}\n"
        )

    def _extract_json(self, text: str) -> dict:
        match = re.search(r"\{[\s\S]*\}", text)
        if not match:
            raise ValueError("No JSON object in LLM output")
        parsed = json.loads(match.group(0))
        return self._normalize(parsed)

    def _normalize(self, raw: dict) -> dict:
        fear_greed = float(raw.get("fear_greed", 50))
        sentiment_score = float(raw.get("sentiment_score", 0.0))
        sentiment_label = str(raw.get("sentiment_label", "NEUTRAL")).upper()
        risk_flags = raw.get("risk_flags", [])
        if not isinstance(risk_flags, list):
            risk_flags = [str(risk_flags)]

        out = {
            "fear_greed": max(0.0, min(100.0, fear_greed)),
            "sentiment_score": max(-1.0, min(1.0, sentiment_score)),
            "sentiment_label": sentiment_label if sentiment_label in {"POSITIVE", "NEGATIVE", "NEUTRAL"} else "NEUTRAL",
            "risk_flags": [str(x)[:40] for x in risk_flags][:5],
            "analysis_short": str(raw.get("analysis_short", "No analysis."))[:1000],
        }
        return out

    def _ollama(self, payload: LLMPayload) -> dict:
        url = f"{self.ollama_url}/api/chat"
        body = {
            "model": self.ollama_model,
            "stream": False,
            "format": "json",
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": self._build_user_prompt(payload)},
            ],
        }
        response = requests.post(url, json=body, timeout=self.timeout)
        response.raise_for_status()
        content = response.json().get("message", {}).get("content", "")
        return self._extract_json(content)

    def _hf(self, payload: LLMPayload) -> dict:
        if not self.hf_api_token:
            raise ValueError("HF_API_TOKEN is empty")
        url = f"https://api-inference.huggingface.co/models/{self.hf_model}"
        headers = {"Authorization": f"Bearer {self.hf_api_token}"}
        body = {
            "inputs": f"{SYSTEM_PROMPT}\n\n{self._build_user_prompt(payload)}",
            "parameters": {
                "max_new_tokens": 300,
                "temperature": 0.1,
                "return_full_text": False,
            },
        }
        response = requests.post(url, headers=headers, json=body, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()
        if isinstance(data, list) and data:
            text = data[0].get("generated_text", "")
        elif isinstance(data, dict):
            text = data.get("generated_text", "") or data.get("summary_text", "")
        else:
            text = ""
        return self._extract_json(text)

    def _heuristic(self, payload: LLMPayload) -> dict:
        text = " ".join(payload.news_titles).lower()
        positive = ["surge", "gain", "optimistic", "inflow", "accumulate", "bull"]
        negative = ["warn", "risk", "selloff", "panic", "uncertainty", "bear"]

        score = 0
        for word in positive:
            score += text.count(word)
        for word in negative:
            score -= text.count(word)

        sentiment_score = max(-1.0, min(1.0, score / 5.0))
        fear_greed = max(0.0, min(100.0, 50 + sentiment_score * 35 + (payload.rsi - 50) * 0.3))

        if sentiment_score > 0.2:
            label = "POSITIVE"
        elif sentiment_score < -0.2:
            label = "NEGATIVE"
        else:
            label = "NEUTRAL"

        if fear_greed > 80:
            risk = ["overheating", "momentum_reversal"]
        elif fear_greed < 20:
            risk = ["panic", "capitulation"]
        else:
            risk = ["range_market"]

        analysis = (
            f"Market tone is {label.lower()} with fear/greed {fear_greed:.0f}. "
            f"RSI is {payload.rsi:.1f}; recent headlines suggest {label.lower()} bias. "
            "Watch volatility spikes and liquidity conditions."
        )

        return {
            "fear_greed": fear_greed,
            "sentiment_score": sentiment_score,
            "sentiment_label": label,
            "risk_flags": risk,
            "analysis_short": analysis,
        }
