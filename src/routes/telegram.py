from typing import Optional

from fastapi import APIRouter, Request, HTTPException, Header
import httpx
from agents import InputGuardrailTripwireTriggered, Runner

from src.agents.user_context import UserContext
from src.config import TELEGRAM_BOT_TOKEN, TELEGRAM_X_SECRET_KEY
from src.utils.telegram import (
    SendMessageRequest,
    send_message,
    extract_chat_id_from_update,
    extract_message_text_from_update,
    extract_user_info_from_update,
)
from src.agents.main_agent import weather_agent

router = APIRouter(prefix="/telegram", tags=["telegram"])


@router.post("/webhook")
async def receive_webhook(
    request: Request, x_telegram_bot_api_secret_token: Optional[str] = Header(None)
):
    """
    Receive webhook requests from Telegram.
    Verifies the secret token for security and sends a message back.
    """
    # Verify the secret token
    if x_telegram_bot_api_secret_token != TELEGRAM_X_SECRET_KEY:
        raise HTTPException(status_code=403, detail="Invalid secret token")

    # Get the webhook payload
    update = await request.json()

    print(f"Received Telegram update: {update}")

    # Send a message back to the user
    try:
        chat_id = extract_chat_id_from_update(update)
        user_message = extract_message_text_from_update(update)
        user_info = extract_user_info_from_update(update)

        if not chat_id:
            return {"status": "ok", "message": "No chat_id found"}

        # Check if message is from a bot
        if user_info and user_info.is_bot:
            print(f"⚠️  Ignoring message from bot: {user_info.first_name}")
            await send_message(
                SendMessageRequest(
                    chat_id=chat_id,
                    text="🤖 I don't respond to other bots. If you're a human, please use a regular account!",
                ),
            )
            return {
                "status": "ok",
                "message": "Message from bot, responded accordingly",
            }

        # Extract user info
        first_name = user_info.first_name if user_info else "User"
        user_id = user_info.user_id if user_info else "Unknown"

        print(f"👤 Message from: {first_name} (ID: {user_id})")
        print(f"💬 Message: {user_message}")

        user_context = UserContext(chat_id=chat_id, first_name=first_name, is_bot=user_info.is_bot)

        # Process the message with the agent
        result = await Runner.run(
            weather_agent,
            user_message,
            context=user_context,
        )
        response_text = result.final_output

        # Send personalized response
        await send_message(
            SendMessageRequest(chat_id=chat_id, text=response_text),
        )

    except InputGuardrailTripwireTriggered:
        await send_message(
            SendMessageRequest(
                chat_id=chat_id,
                text=f"I'm sorry {first_name}, I can't help with that. Please ask me about something else.",
            ),
        )

    except Exception as e:
        print(f"Error sending message back: {e}")
        if chat_id:
            await send_message(
                SendMessageRequest(
                    chat_id=chat_id,
                    text="Sorry, something went wrong. Please try again later.",
                ),
            )

    return {"status": "ok", "message": "Webhook received successfully"}


@router.get("/set-webhook")
async def set_webhook(request: Request):
    """
    Set the webhook URL on Telegram server with secret token.
    Dynamically constructs the webhook URL based on the request.

    Example:
        GET http://localhost:8000/telegram/set-webhook
        or
        GET https://yourdomain.com/telegram/set-webhook
    """
    # Dynamically construct the webhook URL from the request
    base_url = str(request.base_url).rstrip("/")
    webhook_url = f"{base_url}/telegram/webhook"

    telegram_api_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/setWebhook"

    payload = {
        "url": webhook_url,
        "secret_token": TELEGRAM_X_SECRET_KEY,
        "allowed_updates": ["message", "callback_query"],
        "drop_pending_updates": True,
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(telegram_api_url, json=payload)
            response.raise_for_status()
            result = response.json()

            if result.get("ok"):
                return {
                    "status": "success",
                    "message": "Webhook set successfully! 🎉",
                    "webhook_url": webhook_url,
                    "secret_token_set": True,
                    "result": result,
                }
            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"Failed to set webhook: {result.get('description', 'Unknown error')}",
                )
    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=500, detail=f"Error communicating with Telegram API: {str(e)}"
        )
