from typing import Optional

from fastapi import APIRouter, Request, HTTPException, Header
import httpx
from agents import InputGuardrailTripwireTriggered, Runner
from agents.extensions.memory import SQLAlchemySession

from src.agents.user_context import UserContext
from src.config import TELEGRAM_BOT_TOKEN, TELEGRAM_X_SECRET_KEY
from src.database import engine
from src.utils.telegram import (
    SendMessageRequest,
    send_message,
    extract_chat_id_from_update,
    extract_message_text_from_update,
    extract_user_info_from_update,
    extract_photo_from_update,
    extract_document_from_update,
    get_telegram_file_url,
    build_multimodal_input,
    send_approval_request,
    answer_callback_query,
)
from src.agents.main_agent import weather_agent
from src.agents.state_manager import (
    save_pending_approval,
    get_pending_approval,
    delete_pending_approval,
)

router = APIRouter(prefix="/telegram", tags=["telegram"])


async def handle_callback_query(update: dict) -> dict:
    """
    Handle callback query from inline keyboard buttons (approve/reject).

    Args:
        update: Telegram update containing callback_query

    Returns:
        dict: Status response
    """
    callback_query = update["callback_query"]
    callback_id = callback_query["id"]
    callback_data = callback_query["data"]
    chat_id = callback_query["message"]["chat"]["id"]

    # Extract user info
    user_info = extract_user_info_from_update(update)
    first_name = user_info.first_name if user_info else "User"
    is_bot = user_info.is_bot if user_info else False

    user_context = UserContext(chat_id=chat_id, first_name=first_name, is_bot=is_bot)

    try:
        # Parse callback data: "approve:{approval_id}" or "reject:{approval_id}"
        action, approval_id = callback_data.split(":", 1)

        print(f"🔘 Callback: {action} for approval {approval_id}")

        # Retrieve state from Redis with proper context restoration
        state = await get_pending_approval(
            approval_id=approval_id,
        )

        # Create session for resuming
        session = SQLAlchemySession(
            session_id=f"conv_telegram_{chat_id}",
            engine=engine,
            create_tables=True,
        )

        # Apply decision
        interruptions = state.get_interruptions()

        print("Interruption: ", interruptions[0])

        if action == "approve":
            # Find the interruption to approve
            if interruptions:
                state.approve(interruptions[0])

                # Answer callback query with success message
                await answer_callback_query(
                    callback_query_id=callback_id, text="✅ Approved"
                )
        else:  # reject
            if interruptions:
                state.reject(interruptions[0])

                # Answer callback query with reject message
                await answer_callback_query(
                    callback_query_id=callback_id, text="❌ Rejected"
                )

        print("Interruption: ", interruptions[0])

        # Resume agent execution
        print("▶️  Resuming agent execution...")
        result = await Runner.run(
            starting_agent=weather_agent,
            input=state,
            session=session,
            context=user_context,
        )

        # Check if there are more interruptions (nested approvals)
        if result.interruptions:
            print("⏸️  Agent paused again - another approval required")

            # Save new state
            new_interruption = result.interruptions[0]
            new_approval_id = await save_pending_approval(
                chat_id=chat_id,
                state=result.to_state(),
            )

            # Send new approval request
            await send_approval_request(
                chat_id=chat_id,
                tool_name=new_interruption.name or "unknown_tool",
                arguments=new_interruption.arguments,
                approval_id=new_approval_id,
            )
        else:
            # Send final result
            response_text = result.final_output
            await send_message(SendMessageRequest(chat_id=chat_id, text=response_text))
            print("✅ Sent final response to user")

        # Cleanup Redis
        await delete_pending_approval(approval_id)

        return {"status": "ok", "message": "Approval processed"}

    except ValueError as e:
        # Approval not found or expired
        print(f"⚠️  Approval error: {e}")
        await answer_callback_query(
            callback_query_id=callback_id, text="⚠️ This approval has expired"
        )
        await send_message(
            SendMessageRequest(
                chat_id=chat_id,
                text="⚠️ This approval request has expired. Please try your request again.",
            )
        )
        await session.pop_item()
        await session.pop_item()
        return {"status": "ok", "message": "Approval expired"}

    except Exception as e:
        print(f"❌ Error processing callback: {e}")
        await answer_callback_query(
            callback_query_id=callback_id, text="❌ Error processing approval"
        )
        await send_message(
            SendMessageRequest(
                chat_id=chat_id, text=f"❌ Error processing approval: {str(e)}"
            )
        )
        await session.pop_item()
        await session.pop_item()
        return {"status": "error", "message": str(e)}


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

    # Handle callback queries (button clicks) for human-in-the-loop approvals
    if "callback_query" in update:
        return await handle_callback_query(update)

    # Send a message back to the user
    try:
        chat_id = extract_chat_id_from_update(update)
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
        is_bot = user_info.is_bot if user_info else False

        print(f"👤 Message from: {first_name} (ID: {user_id})")

        user_context = UserContext(
            chat_id=chat_id, first_name=first_name, is_bot=is_bot
        )

        session = SQLAlchemySession(
            session_id=f"conv_telegram_{chat_id}",
            engine=engine,
            create_tables=True,
        )

        # Determine input type and build appropriate agent input
        agent_input = None
        input_type = "text"

        # Check for photos first
        photo_data = extract_photo_from_update(update)
        if photo_data:
            try:
                print(f"📷 Processing photo with caption: {photo_data.get('caption')}")
                file_url = await get_telegram_file_url(photo_data["file_id"])
                agent_input = build_multimodal_input(
                    text=photo_data.get("caption"), file_url=file_url, file_type="image"
                )
                input_type = "image"
            except Exception as e:
                print(f"❌ Error processing photo: {e}")
                await send_message(
                    SendMessageRequest(
                        chat_id=chat_id,
                        text="Sorry, I couldn't process that image. Please try again or send a different image.",
                    ),
                )
                return {"status": "ok", "message": f"Failed to process photo: {str(e)}"}

        # Check for documents
        elif document_data := extract_document_from_update(update):
            try:
                print(
                    f"📄 Processing document: {document_data.get('file_name')} ({document_data.get('mime_type')})"
                )
                print(f"   Caption: {document_data.get('caption')}")
                file_url = await get_telegram_file_url(document_data["file_id"])
                agent_input = build_multimodal_input(
                    text=document_data.get("caption"),
                    file_url=file_url,
                    file_type="file",
                )
                input_type = "document"
            except Exception as e:
                print(f"❌ Error processing document: {e}")
                await send_message(
                    SendMessageRequest(
                        chat_id=chat_id,
                        text="Sorry, I couldn't process that document. Please try again or send a different file.",
                    ),
                )
                return {
                    "status": "ok",
                    "message": f"Failed to process document: {str(e)}",
                }

        # Fallback to text
        else:
            agent_input = extract_message_text_from_update(update)
            print(f"💬 Message: {agent_input}")
            input_type = "text"

        # Check if we have valid input
        if not agent_input:
            print("⚠️  No valid input found in update")
            return {"status": "ok", "message": "No valid input found"}

        # Process the message with the agent
        print(f"🤖 Sending {input_type} input to agent...")
        result = await Runner.run(
            starting_agent=weather_agent,
            input=agent_input,
            context=user_context,
            session=session,
        )

        # Check for interruptions (human-in-the-loop approvals)
        if result.interruptions:
            print(
                f"⏸️  Agent paused - approval required for {len(result.interruptions)} tool(s)"
            )

            # Get the first interruption (typically one at a time)
            interruption = result.interruptions[0]

            # Save state to Redis
            approval_id = await save_pending_approval(
                chat_id=chat_id,
                state=result.to_state(),
            )

            # Send approval request with inline keyboard
            await send_approval_request(
                chat_id=chat_id,
                tool_name=interruption.name or "unknown_tool",
                arguments=interruption.arguments,
                approval_id=approval_id,
            )

            print(f"✅ Sent approval request with ID: {approval_id}")
            return {"status": "ok", "message": "Awaiting approval"}

        # Normal flow if no interruptions
        response_text = result.final_output

        # Send personalized response
        await send_message(
            SendMessageRequest(chat_id=chat_id, text=response_text),
        )
        return {"status": "ok", "message": "Sent final response to user"}

    except InputGuardrailTripwireTriggered:
        await send_message(
            SendMessageRequest(
                chat_id=chat_id,
                text=f"I'm sorry {first_name}, I can't help with that. Please ask me about something else.",
            ),
        )
        await session.pop_item()

    except Exception as e:
        print(f"Error sending message back: {e}")
        if chat_id:
            await send_message(
                SendMessageRequest(
                    chat_id=chat_id,
                    text="Sorry, something went wrong. Please try again later.",
                ),
            )
        await session.pop_item()

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
