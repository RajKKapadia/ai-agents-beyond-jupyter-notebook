from typing import Optional, Literal

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


async def get_telegram_file_url(file_id: str) -> str:
    """
    Get the public URL for a Telegram file using the bot token and file_id.

    Args:
        file_id: The Telegram file_id

    Returns:
        str: Public URL to access the file

    Raises:
        httpx.HTTPError: If the request to Telegram API fails
    """
    telegram_api_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getFile"
    
    async with httpx.AsyncClient() as client:
        response = await client.get(telegram_api_url, params={"file_id": file_id})
        response.raise_for_status()
        result = response.json()
        
        if not result.get("ok"):
            raise ValueError(f"Failed to get file info: {result}")
        
        file_path = result["result"]["file_path"]
        return f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{file_path}"


def extract_photo_from_update(update: dict) -> Optional[dict]:
    """
    Extract photo data (file_id, caption) from a Telegram update.

    Args:
        update: The Telegram update object

    Returns:
        dict: Photo data with file_id and optional caption, or None if no photo found
    """
    if "message" in update and "photo" in update["message"]:
        # Telegram sends multiple photo sizes, get the largest one (last in array)
        photos = update["message"]["photo"]
        if photos:
            largest_photo = photos[-1]
            return {
                "file_id": largest_photo["file_id"],
                "caption": update["message"].get("caption"),
            }
    elif "edited_message" in update and "photo" in update["edited_message"]:
        photos = update["edited_message"]["photo"]
        if photos:
            largest_photo = photos[-1]
            return {
                "file_id": largest_photo["file_id"],
                "caption": update["edited_message"].get("caption"),
            }
    
    return None


def extract_document_from_update(update: dict) -> Optional[dict]:
    """
    Extract document data (file_id, file_name, mime_type, caption) from a Telegram update.

    Args:
        update: The Telegram update object

    Returns:
        dict: Document data with file_id, file_name, mime_type and optional caption,
              or None if no document found
    """
    if "message" in update and "document" in update["message"]:
        document = update["message"]["document"]
        return {
            "file_id": document["file_id"],
            "file_name": document.get("file_name", "document"),
            "mime_type": document.get("mime_type", "application/octet-stream"),
            "caption": update["message"].get("caption"),
        }
    elif "edited_message" in update and "document" in update["edited_message"]:
        document = update["edited_message"]["document"]
        return {
            "file_id": document["file_id"],
            "file_name": document.get("file_name", "document"),
            "mime_type": document.get("mime_type", "application/octet-stream"),
            "caption": update["edited_message"].get("caption"),
        }
    
    return None


def build_multimodal_input(
    text: Optional[str], 
    file_url: str, 
    file_type: Literal["image", "file"]
) -> list[dict]:
    """
    Build the multimodal input structure for the agent.

    Args:
        text: Optional text/caption to include
        file_url: URL to the image or file
        file_type: Type of file - "image" or "file"

    Returns:
        list: Multimodal input structure compatible with OpenAI Responses API
    """
    content = []
    
    # Add text if provided
    if text:
        content.append({"type": "input_text", "text": text})
    
    # Add file based on type
    if file_type == "image":
        content.append({"type": "input_image", "image_url": file_url})
    else:  # file_type == "file"
        content.append({"type": "input_file", "file_url": file_url})
    
    return [{"role": "user", "content": content}]


def build_approval_keyboard(approval_id: str) -> dict:
    """
    Build inline keyboard with Approve/Reject buttons for human-in-the-loop approval.

    Args:
        approval_id: Unique approval ID to include in callback data

    Returns:
        dict: Inline keyboard markup for Telegram
    """
    return {
        "inline_keyboard": [
            [
                {"text": "✅ Approve", "callback_data": f"approve:{approval_id}"},
                {"text": "❌ Reject", "callback_data": f"reject:{approval_id}"}
            ]
        ]
    }


async def send_approval_request(
    chat_id: int, 
    tool_name: str, 
    arguments: Optional[str],
    approval_id: str
) -> dict:
    """
    Send approval request message with inline keyboard to user.

    Args:
        chat_id: Telegram chat ID
        tool_name: Name of the tool requiring approval
        arguments: Tool arguments (JSON string)
        approval_id: Unique approval ID

    Returns:
        dict: Response from Telegram API
    """
    telegram_api_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    
    # Format the approval message
    message = "🔐 **Approval Required**\n\n"
    message += f"Tool: `{tool_name}`\n"
    if arguments:
        message += f"Arguments: `{arguments}`\n\n"
    message += "Please approve or reject this action:"
    
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown",
        "reply_markup": build_approval_keyboard(approval_id)
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(telegram_api_url, json=payload)
        response.raise_for_status()
        return response.json()


async def answer_callback_query(callback_query_id: str, text: Optional[str] = None) -> dict:
    """
    Answer callback query to remove loading state from inline keyboard button.

    Args:
        callback_query_id: The callback query ID from Telegram
        text: Optional text to show as notification (not used if None)

    Returns:
        dict: Response from Telegram API
    """
    telegram_api_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/answerCallbackQuery"
    
    payload = {"callback_query_id": callback_query_id}
    if text:
        payload["text"] = text
    
    async with httpx.AsyncClient() as client:
        response = await client.post(telegram_api_url, json=payload)
        response.raise_for_status()
        return response.json()
