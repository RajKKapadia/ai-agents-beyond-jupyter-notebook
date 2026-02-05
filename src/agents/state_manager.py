"""State manager for handling RunState persistence in Redis for human-in-the-loop approvals."""

import json
import time
import logging

from agents import RunState

from src.agents.user_context import UserContext
from src.utils.redis_client import redis_client
from src.agents.main_agent import weather_agent

logger = logging.getLogger(__name__)

# TTL for approval state in Redis (1 hour)
APPROVAL_TTL = 3600


async def save_pending_approval(
    chat_id: int,
    state: RunState,
) -> str:
    """
    Save pending approval state to Redis.

    Args:
        chat_id: Telegram chat ID
        state: RunState from the agent execution

    Returns:
        Unique approval_id for this pending approval
    """
    # Generate unique approval ID using chat_id and timestamp
    timestamp = int(time.time() * 1000)  # milliseconds for uniqueness
    approval_id = f"hitl:{chat_id}:{timestamp}"

    # Serialize state
    state_data = {
        "state": state.to_string(),
        "chat_id": chat_id,
        "timestamp": timestamp,
    }

    try:
        # Store in Redis with TTL
        success = await redis_client.set(
            key=approval_id, value=json.dumps(state_data), ex=APPROVAL_TTL
        )

        if success:
            logger.info(f"✅ Saved approval state: {approval_id}")
            return approval_id
        else:
            raise Exception("Failed to save state to Redis")

    except Exception as e:
        logger.error(f"❌ Error saving approval state: {e}")
        raise Exception(f"Failed to save state to Redis: {e}")


async def get_pending_approval(
    approval_id: str,
) -> RunState:
    """
    Retrieve pending approval state from Redis.

    Args:
        approval_id: Unique approval ID

    Returns:
        RunState

    Raises:
        ValueError: If approval not found or expired
    """
    try:
        # Get data from Redis
        data_str = await redis_client.get(approval_id)

        if not data_str:
            raise ValueError(f"Approval state not found or expired: {approval_id}")

        # Parse data
        data = json.loads(data_str)

        state = await RunState.from_string(
            initial_agent=weather_agent,
            state_string=data["state"],
        )

        logger.info(f"✅ Retrieved approval state: {approval_id}")
        return state

    except json.JSONDecodeError as e:
        logger.error(f"❌ Error decoding approval state JSON: {e}")
        raise ValueError(f"Invalid approval state data: {approval_id}")
    except Exception as e:
        logger.error(f"❌ Error retrieving approval state: {e}")
        raise


async def delete_pending_approval(approval_id: str) -> bool:
    """
    Delete pending approval state from Redis.

    Args:
        approval_id: Unique approval ID

    Returns:
        True if deleted successfully, False otherwise
    """
    try:
        success = await redis_client.delete(approval_id)
        if success:
            logger.info(f"🗑️  Deleted approval state: {approval_id}")
        return success
    except Exception as e:
        logger.error(f"❌ Error deleting approval state: {e}")
        return False
