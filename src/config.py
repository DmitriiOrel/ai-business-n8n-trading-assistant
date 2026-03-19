from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    llm_mode: str
    ollama_url: str
    ollama_model: str
    hf_model: str
    hf_api_token: str
    telegram_bot_token: str
    telegram_chat_id: str


def load_settings() -> Settings:
    return Settings(
        llm_mode=os.getenv("LLM_MODE", "mock").strip().lower(),
        ollama_url=os.getenv("OLLAMA_URL", "http://localhost:11434").strip(),
        ollama_model=os.getenv("OLLAMA_MODEL", "llama3.1:8b").strip(),
        hf_model=os.getenv("HF_MODEL", "mistralai/Mistral-7B-Instruct-v0.3").strip(),
        hf_api_token=os.getenv("HF_API_TOKEN", "").strip(),
        telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN", "").strip(),
        telegram_chat_id=os.getenv("TELEGRAM_CHAT_ID", "").strip(),
    )
