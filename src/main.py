from fastapi import FastAPI
from src.routes import health, telegram

app = FastAPI(
    title="AI Agents API",
    description="API for AI agents beyond Jupyter notebook",
    version="0.1.0"
)

# Include routers
app.include_router(health.router, tags=["health"])
app.include_router(telegram.router, tags=["telegram"])
