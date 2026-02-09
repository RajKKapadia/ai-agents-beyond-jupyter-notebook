# AI Agents Beyond Jupyter Notebook

FastAPI + Telegram bot backend that runs an OpenAI Agent with background job processing via ARQ.

## What this project does

- Receives Telegram webhook updates.
- Queues message processing in Redis-backed ARQ workers.
- Runs an OpenAI Agent with a weather tool powered by OpenWeatherMap and optional web search support.
- Sends responses back to Telegram.
- Supports human-in-the-loop approval for tool calls that require confirmation.

## Tech stack

- Python `3.12+`
- FastAPI + Uvicorn
- OpenAI Agents SDK
- Redis + ARQ
- PostgreSQL (conversation/session persistence through SQLAlchemy)

## Project structure

```text
.
├── run.py                    # FastAPI app runner
├── run_worker.py             # ARQ worker runner
├── src/
│   ├── main.py               # FastAPI app + lifespan setup
│   ├── worker.py             # ARQ worker settings
│   ├── routes/
│   │   ├── health.py         # Health endpoint
│   │   └── telegram.py       # Telegram webhook endpoints
│   ├── tasks/
│   │   └── telegram_tasks.py # Background processing tasks
│   └── agents/               # Agent, tools, hooks, state handling
└── .env.example              # Required environment variables
```

## Prerequisites

- Python `3.12` or newer
- Redis running locally or remotely
- PostgreSQL database
- Telegram bot token (from BotFather)
- OpenAI API key
- OpenWeatherMap API key

## Setup

1. Create environment file:

```bash
cp .env.example .env
```

2. Fill all values in `.env`.

3. Install dependencies (recommended with `uv`):

```bash
uv sync
```

Alternative (pip):

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Environment variables

Required values (see `.env.example`):

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_X_SECRET_KEY`
- `OPENAI_API_KEY`
- `OPENWEATHERMAP_API_KEY`
- `DATABASE_URL`
- `REDIS_URL`

## Run the app

Start the API server:

```bash
uv run python run.py
```

Start the worker in a second terminal:

```bash
uv run python run_worker.py
```

Default API address: `http://127.0.0.1:8080`

## API endpoints

- `GET /` health check
- `POST /telegram/webhook` Telegram webhook receiver (validates secret header)
- `GET /telegram/set-webhook` convenience endpoint to set webhook on Telegram

## Telegram webhook setup

After the API is reachable from the public internet:

1. Call:

```bash
curl http://127.0.0.1:8080/telegram/set-webhook
```

2. Telegram will send updates to:

`{BASE_URL}/telegram/webhook`

3. Requests are validated with the `X-Telegram-Bot-Api-Secret-Token` header.

## Development notes

- Keep API and worker running together for full functionality.
- Redis is required for job queuing and approval-state persistence.
- If environment variables are missing, startup fails fast in `src/config.py`.
