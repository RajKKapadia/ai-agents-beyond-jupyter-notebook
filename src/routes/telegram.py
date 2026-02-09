from typing import Optional

from fastapi import APIRouter, Request, HTTPException, Header
import httpx

from src.config import TELEGRAM_BOT_TOKEN, TELEGRAM_X_SECRET_KEY
from src.utils.telegram import (
    SendMessageRequest,
    send_message,
    extract_chat_id_from_update,
    extract_user_info_from_update,
)

router = APIRouter(prefix="/telegram", tags=["telegram"])


@router.post("/webhook")
async def receive_webhook(
    request: Request, x_telegram_bot_api_secret_token: Optional[str] = Header(None)
):
    """
    Receive webhook requests from Telegram.
    Verifies the secret token for security, then enqueues the update
    for background processing via ARQ.
    """
    # Verify the secret token
    if x_telegram_bot_api_secret_token != TELEGRAM_X_SECRET_KEY:
        raise HTTPException(status_code=403, detail="Invalid secret token")

    # Get the webhook payload
    update = await request.json()

    print(f"Received Telegram update: {update}")

    arq_pool = request.app.state.arq_pool

    # Handle callback queries (button clicks) for human-in-the-loop approvals
    if "callback_query" in update:
        await arq_pool.enqueue_job("process_callback_query_task", update)
        return {"status": "ok"}

    # Quick bot check before enqueuing
    user_info = extract_user_info_from_update(update)
    if user_info and user_info.is_bot:
        chat_id = extract_chat_id_from_update(update)
        if chat_id:
            print(f"⚠️  Ignoring message from bot: {user_info.first_name}")
            await send_message(
                SendMessageRequest(
                    chat_id=chat_id,
                    text="🤖 I don't respond to other bots. If you're a human, please use a regular account!",
                ),
            )
        return {"status": "ok", "message": "Message from bot, responded accordingly"}

    # Enqueue message processing
    await arq_pool.enqueue_job("process_message_task", update)
    return {"status": "ok"}


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
