# AI in Business: n8n + LLM + Telegram Trading Assistant

Новый отдельный проект под задание из презентации.

## Что реализовано

- LLM-анализ новостей (`mock`, `ollama`, `huggingface`)
- Техиндикаторы: `RSI`, `Bollinger Bands`, `SMA50`
- Торговая логика:
  - Strategy A: baseline (только RSI)
  - Strategy B: LLM metrics + RSI + Bollinger
- Метрики и логи в CSV/JSON
- График `A vs B` за 30 дней с фоном победителя дня
- Отправка текста + графика в Telegram
- n8n workflow для запуска пайплайна

## Структура

- `src/pipeline.py` - основной пайплайн
- `src/llm_clients.py` - интеграция LLM
- `src/indicators.py` - индикаторы
- `src/trading_logic.py` - правила сигналов
- `src/charting.py` - график A/B
- `src/telegram_client.py` - Telegram API
- `workflows/trading_assistant_workflow.json` - workflow-шаблон n8n
- `data/market_news.csv` - пример входного датасета

## Быстрый старт (через Docker + n8n)

1. Подготовь переменные:

```powershell
cd C:\projects\Work\work_project_1\ai_business_n8n_trading
Copy-Item .env.example .env
```

2. Заполни в `.env`:

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
- `LLM_MODE` (`mock`, `ollama`, `hf`)
- если `hf`: `HF_API_TOKEN`

3. Подними n8n:

```powershell
docker compose up -d --build
```

4. Открой `http://localhost:5678`, зайди под `N8N_USER/N8N_PASSWORD` из `.env`.

5. Импортируй workflow:

- `workflows/trading_assistant_workflow.json`

6. Нажми `Manual Trigger` -> выполни workflow.

## Опционально: Ollama

```powershell
docker compose --profile ollama up -d
```

Затем загрузи модель (например):

```powershell
docker compose exec ollama ollama pull llama3.1:8b
```

И выставь в `.env`:

- `LLM_MODE=ollama`
- `OLLAMA_URL=http://ollama:11434`

## Локальный запуск без n8n

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python src\pipeline.py --llm-mode mock --send-telegram
```

## Выходные артефакты

Папка `outputs/`:

- `trade_log.csv`
- `summary.json`
- `llm_analysis.json`
- `telegram_message.txt`
- `ab_30d.png`

## Как это соответствует слайдам

- Replace sentiment with Generative LLM: да (`ollama`/`hf`)
- Financial Analyst prompt: да (структурированный JSON + explanation)
- Upgrade logic with RSI/Bollinger + LLM metrics: да
- Telegram output: да
- A/B 30-day chart + summary: да

## Важно

- Никогда не публикуй токен Telegram/API ключи в Git.
- Логика в этом шаблоне образовательная, не инвестсовет.
