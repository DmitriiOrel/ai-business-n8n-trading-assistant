from __future__ import annotations

from pathlib import Path

import requests


def _is_configured(token: str, chat_id: str) -> bool:
    return bool(token and chat_id)


def send_message(token: str, chat_id: str, text: str, timeout: int = 20) -> None:
    if not _is_configured(token, chat_id):
        return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    response = requests.post(url, json={"chat_id": chat_id, "text": text}, timeout=timeout)
    response.raise_for_status()


def send_photo(token: str, chat_id: str, photo_path: Path, caption: str = "", timeout: int = 30) -> None:
    if not _is_configured(token, chat_id):
        return
    url = f"https://api.telegram.org/bot{token}/sendPhoto"
    with photo_path.open("rb") as f:
        files = {"photo": f}
        data = {"chat_id": chat_id, "caption": caption}
        response = requests.post(url, data=data, files=files, timeout=timeout)
    response.raise_for_status()
