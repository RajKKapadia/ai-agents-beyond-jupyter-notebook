from src.config import REDIS_URL, get_arq_redis_settings
from src.tasks.telegram_tasks import process_callback_query_task, process_message_task
from src.utils.redis_client import redis_client


async def on_startup(ctx: dict) -> None:
    """Connect the Redis singleton used by state_manager on worker startup."""
    print(f"🚀 ARQ worker starting - connecting to Redis at {REDIS_URL}")
    await redis_client.connect(REDIS_URL)


async def on_shutdown(ctx: dict) -> None:
    """Disconnect Redis on worker shutdown."""
    print("🛑 ARQ worker shutting down - disconnecting from Redis")
    await redis_client.disconnect()


class WorkerSettings:
    functions = [process_message_task, process_callback_query_task]
    redis_settings = get_arq_redis_settings()
    on_startup = on_startup
    on_shutdown = on_shutdown
    max_jobs = 10
    job_timeout = 120
    max_tries = 1
