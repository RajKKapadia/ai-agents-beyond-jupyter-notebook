from typing import Optional

import httpx
from pydantic import BaseModel

from src.config import TELEGRAM_BOT_TOKEN


class SendMessageRequest(BaseModel):
    chat_id: int
    text: str


async def send_message(request: SendMessageRequest) -> dict:
    """
    Send a message to a Telegram chat.

    Args:
        chat_id: The chat ID to send the message to
        text: The message text to send
        parse_mode: Optional parse mode (e.g., "HTML", "Markdown")
        reply_markup: Optional reply markup for inline keyboards

    Returns:
        dict: Response from Telegram API

    Raises:
        httpx.HTTPError: If the request fails
    """
    telegram_api_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

    payload = request.model_dump(exclude_none=True)

    async with httpx.AsyncClient() as client:
        response = await client.post(telegram_api_url, json=payload)
        response.raise_for_status()
        return response.json()


def extract_chat_id_from_update(update: dict) -> Optional[int]:
    """
    Extract chat_id from a Telegram update.

    Args:
        update: The Telegram update object

    Returns:
        int: The chat_id if found, None otherwise
    """
    if "message" in update:
        return update["message"]["chat"]["id"]
    elif "callback_query" in update:
        return update["callback_query"]["message"]["chat"]["id"]
    elif "edited_message" in update:
        return update["edited_message"]["chat"]["id"]

    return None


def extract_message_text_from_update(update: dict) -> Optional[str]:
    """
    Extract message text from a Telegram update.

    Args:
        update: The Telegram update object

    Returns:
        str: The message text if found, empty string otherwise
    """
    if "message" in update:
        return update["message"].get("text", "")
    elif "callback_query" in update:
        return update["callback_query"].get("data", "")
    elif "edited_message" in update:
        return update["edited_message"].get("text", "")

    return ""


class UserInfo(BaseModel):
    user_id: int
    first_name: str
    last_name: Optional[str] = None
    username: Optional[str] = None
    is_bot: bool
    language_code: Optional[str] = None


def extract_user_info_from_update(update: dict) -> Optional[UserInfo]:
    """
    Extract user information (firstname, username, user_id) from a Telegram update.

    Args:
        update: The Telegram update object

    Returns:
        dict: User info containing firstname, username, user_id, and is_bot flag
              Returns None if user info cannot be extracted
    """
    user_data = None

    if "message" in update:
        user_data = update["message"].get("from")
    elif "callback_query" in update:
        user_data = update["callback_query"].get("from")
    elif "edited_message" in update:
        user_data = update["edited_message"].get("from")

    if not user_data:
        return None

    return (
        UserInfo(
            user_id=user_data.get("id"),
            first_name=user_data.get("first_name", "User"),  # firstname is always there
            last_name=user_data.get("last_name"),  # Optional
            username=user_data.get("username"),  # Optional
            is_bot=user_data.get("is_bot", False),
            language_code=user_data.get("language_code"),  # Optional
        )
        if user_data
        else None
    )
