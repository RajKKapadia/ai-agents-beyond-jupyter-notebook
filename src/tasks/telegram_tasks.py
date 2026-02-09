"""ARQ task functions for processing Telegram updates in the background."""

from agents import InputGuardrailTripwireTriggered, Runner
from agents.extensions.memory import SQLAlchemySession

from src.agents.main_agent import weather_agent
from src.agents.state_manager import (
    save_pending_approval,
    get_pending_approval,
    delete_pending_approval,
)
from src.agents.user_context import UserContext
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


async def process_message_task(ctx: dict, update: dict) -> None:
    """
    Process an incoming Telegram message via the AI agent.

    Extracted from the webhook handler so it runs in an ARQ background worker
    instead of blocking the HTTP response.
    """
    chat_id = extract_chat_id_from_update(update)
    user_info = extract_user_info_from_update(update)

    if not chat_id:
        print("No chat_id found in update")
        return

    first_name = user_info.first_name if user_info else "User"
    user_id = user_info.user_id if user_info else "Unknown"
    is_bot = user_info.is_bot if user_info else False

    print(f"👤 Message from: {first_name} (ID: {user_id})")

    user_context = UserContext(chat_id=chat_id, first_name=first_name, is_bot=is_bot)

    session = SQLAlchemySession(
        session_id=f"conv_telegram_{chat_id}",
        engine=engine,
        create_tables=True,
    )

    try:
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
                    text=photo_data.get("caption"),
                    file_url=file_url,
                    file_type="image",
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
                return

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
                return

        # Fallback to text
        else:
            agent_input = extract_message_text_from_update(update)
            print(f"💬 Message: {agent_input}")
            input_type = "text"

        # Check if we have valid input
        if not agent_input:
            print("⚠️  No valid input found in update")
            return

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
            return

        # Normal flow if no interruptions
        response_text = result.final_output
        await send_message(
            SendMessageRequest(chat_id=chat_id, text=response_text),
        )
        print("✅ Sent final response to user")

    except InputGuardrailTripwireTriggered:
        await send_message(
            SendMessageRequest(
                chat_id=chat_id,
                text=f"I'm sorry {first_name}, I can't help with that. Please ask me about something else.",
            ),
        )
        await session.pop_item()

    except Exception as e:
        print(f"❌ Error processing message: {e}")
        if chat_id:
            await send_message(
                SendMessageRequest(
                    chat_id=chat_id,
                    text="Sorry, something went wrong. Please try again later.",
                ),
            )
        await session.pop_item()


async def process_callback_query_task(ctx: dict, update: dict) -> None:
    """
    Handle callback query from inline keyboard buttons (approve/reject).

    Extracted from the webhook handler so it runs in an ARQ background worker
    instead of blocking the HTTP response.
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

    session = SQLAlchemySession(
        session_id=f"conv_telegram_{chat_id}",
        engine=engine,
        create_tables=True,
    )

    try:
        # Parse callback data: "approve:{approval_id}" or "reject:{approval_id}"
        action, approval_id = callback_data.split(":", 1)

        print(f"🔘 Callback: {action} for approval {approval_id}")

        # Retrieve state from Redis with proper context restoration
        state = await get_pending_approval(
            approval_id=approval_id,
        )

        # Apply decision
        interruptions = state.get_interruptions()

        print("Interruption: ", interruptions[0])

        if action == "approve":
            if interruptions:
                state.approve(interruptions[0])
                await answer_callback_query(
                    callback_query_id=callback_id, text="✅ Approved"
                )
        else:  # reject
            if interruptions:
                state.reject(interruptions[0])
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

            new_interruption = result.interruptions[0]
            new_approval_id = await save_pending_approval(
                chat_id=chat_id,
                state=result.to_state(),
            )

            await send_approval_request(
                chat_id=chat_id,
                tool_name=new_interruption.name or "unknown_tool",
                arguments=new_interruption.arguments,
                approval_id=new_approval_id,
            )
        else:
            response_text = result.final_output
            await send_message(
                SendMessageRequest(chat_id=chat_id, text=response_text)
            )
            print("✅ Sent final response to user")

        # Cleanup Redis
        await delete_pending_approval(approval_id)

    except ValueError as e:
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
