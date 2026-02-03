import httpx
from typing import Optional
from src.config import TELEGRAM_BOT_TOKEN


async def send_message(
    chat_id: int,
    text: str,
    parse_mode: Optional[str] = None,
    reply_markup: Optional[dict] = None
) -> dict:
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
    
    payload = {
        "chat_id": chat_id,
        "text": text
    }
    
    if parse_mode:
        payload["parse_mode"] = parse_mode
    
    if reply_markup:
        payload["reply_markup"] = reply_markup
    
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
