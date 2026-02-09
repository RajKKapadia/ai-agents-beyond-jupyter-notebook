from fastapi import FastAPI
from contextlib import asynccontextmanager

from arq import create_pool

from src.routes import health, telegram
from src.utils.redis_client import redis_client
from src.config import REDIS_URL, get_arq_redis_settings


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

    # Startup: Create ARQ connection pool for enqueuing jobs
    print("🚀 Starting up - creating ARQ connection pool")
    app.state.arq_pool = await create_pool(get_arq_redis_settings())

    yield

    # Shutdown: Close ARQ pool
    print("🛑 Shutting down - closing ARQ connection pool")
    await app.state.arq_pool.aclose()

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
