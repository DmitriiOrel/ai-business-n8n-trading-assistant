# AI in Business: n8n + LLM + Telegram Trading Assistant

Проект развернут под схему из твоего скриншота n8n:

`Start Bot -> Load Market -> Parse Market -> Load News -> Parse News -> Group News -> Wait for Both -> Merge Daily Data -> Prepare Batch -> HF Sentiment -> Final Logic & Metrics -> Export CSV`

## Ключевые файлы

- `workflows/slide_style_n8n_workflow.json` - схема n8n как на слайде
- `data/news_sample.csv` - пример новостей
- `data/market_news.csv` - пример market+news для Python fallback
- `src/pipeline.py` - Python fallback запуск (вне n8n)

## Запуск n8n

```powershell
cd C:\projects\Work\work_project_1\ai_business_n8n_trading
Copy-Item .env.example .env
# заполни HF_API_TOKEN / TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID

docker compose up -d
```

Открыть: `http://localhost:5678`

Логин/пароль: `N8N_USER` / `N8N_PASSWORD` из `.env`.

## Импорт workflow

Импортируй файл:

- `workflows/slide_style_n8n_workflow.json`

И запусти `Start Bot` вручную.

## Какие переменные нужны в `.env`

- `MARKET_CSV_URL` - публичный CSV с колонками date/close
- `NEWS_CSV_URL` - публичный CSV с колонками date/title
- `HF_API_TOKEN` - токен Hugging Face Router
- `HF_MODEL` - модель (по умолчанию Mistral)
- `SYMBOL`, `TIMEFRAME`

Опционально:

- `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` (если добавишь в workflow ноду Telegram/HTTP sendMessage)

## Что делает workflow

1. Грузит market CSV и news CSV.
2. Парсит CSV в записи.
3. Группирует новости по дате.
4. Мержит market+news и считает RSI/Bollinger/SMA.
5. Формирует батч-промпт и отправляет в HF Sentiment node.
6. Считает финальные сигналы A/B и метрики.
7. Экспортирует CSV-строку в финальной ноде.

## Быстрый Python fallback

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python src\pipeline.py --llm-mode mock --send-telegram
```

## Безопасность

Если токен Telegram был публично показан, перевыпусти его через `@BotFather` (`/revoke`).
