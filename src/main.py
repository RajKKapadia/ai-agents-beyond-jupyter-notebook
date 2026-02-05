from fastapi import FastAPI
from contextlib import asynccontextmanager

from src.routes import health, telegram
from src.utils.redis_client import redis_client
from src.config import REDIS_URL


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan event handler for application startup and shutdown.
    """
    # Startup: Connect to Redis
    print(f"🚀 Starting up - connecting to Redis at {REDIS_URL}")
    try:
        await redis_client.connect(REDIS_URL)
    except Exception as e:
        print(f"⚠️  Warning: Failed to connect to Redis: {e}")
        print("⚠️  Human-in-the-loop approvals will not work without Redis")
    
    yield
    
    # Shutdown: Disconnect from Redis
    print("🛑 Shutting down - disconnecting from Redis")
    await redis_client.disconnect()


app = FastAPI(
    title="AI Agents API",
    description="API for AI agents beyond Jupyter notebook",
    version="0.1.0",
    lifespan=lifespan
)

# Include routers
app.include_router(health.router, tags=["health"])
app.include_router(telegram.router, tags=["telegram"])
