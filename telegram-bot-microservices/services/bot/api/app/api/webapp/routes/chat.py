"""
Chat API routes for webapp

Main endpoint for chatting with personas
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional

from shared.database import get_db

from app.services.chat_flow import process_chat_message, generate_persona_greeting
from app.api.webapp.dependencies import WebAppUser

router = APIRouter()


# ==================== SCHEMAS ====================

class ChatRequest(BaseModel):
    """Request to send a chat message"""
    telegram_id: int
    message: str
    persona_id: Optional[int] = None
    mode: str = "default"
    atmosphere: Optional[str] = None
    story_id: Optional[str] = None


class ChatResponse(BaseModel):
    """Response from chat endpoint"""
    success: bool
    response: Optional[str] = None
    error: Optional[str] = None
    dialog_id: Optional[int] = None
    is_safety_block: bool = False
    message_count: int = 0
    image_url: Optional[str] = None


class GreetingRequest(BaseModel):
    """Request to generate greeting from persona"""
    telegram_id: int
    persona_id: int
    story_id: Optional[str] = None
    atmosphere: Optional[str] = None
    is_return: bool = False
    send_to_telegram: bool = False  # If True, send greeting directly to Telegram


class GreetingResponse(BaseModel):
    """Response from greeting endpoint"""
    success: bool
    response: Optional[str] = None
    error: Optional[str] = None
    dialog_id: Optional[int] = None


# ==================== ROUTES ====================

@router.post("/chat", response_model=ChatResponse)
async def send_message(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Send a message to the active persona.

    The chat flow:
    1. Safety check on user message
    2. Get/create dialog (3-slot system)
    3. Load recent history from PostgreSQL
    4. Search relevant memories from Qdrant
    5. Build prompt with persona + context
    6. Send to LLM Gateway
    7. Save messages to PostgreSQL + Qdrant

    Args:
        request: ChatRequest with message and optional settings

    Returns:
        ChatResponse with persona's reply
    """
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    if len(request.message) > 4000:
        raise HTTPException(status_code=400, detail="Message too long (max 4000 chars)")

    result = await process_chat_message(
        db=db,
        telegram_id=request.telegram_id,
        message=request.message.strip(),
        persona_id=request.persona_id,
        mode=request.mode,
        story_id=request.story_id,
        atmosphere=request.atmosphere,
    )

    return ChatResponse(
        success=result.success,
        response=result.response,
        error=result.error,
        dialog_id=result.dialog_id,
        is_safety_block=result.is_safety_block,
        message_count=result.message_count,
        image_url=result.image_url,
    )


@router.post("/chat/greeting", response_model=GreetingResponse)
async def get_greeting(
    request: GreetingRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Generate a greeting from the persona.

    Used when:
    - User starts a new dialog with a persona
    - User returns to an existing dialog
    - User selects a story/scenario

    Args:
        request: GreetingRequest with persona_id and optional story

    Returns:
        GreetingResponse with persona's greeting
    """
    from shared.database import Persona
    from app.services.telegram_service import send_greeting

    result = await generate_persona_greeting(
        db=db,
        telegram_id=request.telegram_id,
        persona_id=request.persona_id,
        story_id=request.story_id,
        atmosphere=request.atmosphere,
        is_return=request.is_return,
    )

    # Send to Telegram if requested
    if result.success and result.response and request.send_to_telegram:
        from shared.database import Dialog
        persona = await db.get(Persona, request.persona_id)
        persona_name = persona.name if persona else "Персонаж"
        persona_key = persona.key if persona else None
        story_key = request.story_id

        # Get greeting image index from dialog
        greeting_image_index = 0
        dialog = await db.get(Dialog, result.dialog_id) if result.dialog_id else None
        if dialog:
            greeting_image_index = dialog.greeting_image_index or 0

        await send_greeting(
            chat_id=request.telegram_id,
            persona_name=persona_name,
            greeting_text=result.response,
            persona_key=persona_key,
            story_key=story_key or (dialog.story_id if dialog else None),
            greeting_image_index=greeting_image_index,
        )

        # Increment greeting image index
        if dialog:
            dialog.greeting_image_index = (greeting_image_index + 1)
            await db.commit()

    return GreetingResponse(
        success=result.success,
        response=result.response,
        error=result.error,
        dialog_id=result.dialog_id,
    )


@router.get("/chat/dialogs")
async def get_user_dialogs(
    user: WebAppUser,
    db: AsyncSession = Depends(get_db)
):
    """
    Get user's active dialogs (up to 5 slots).

    Returns list of active dialogs with:
    - dialog_id
    - persona info
    - slot_number
    - message_count
    - last_message preview
    """
    from sqlalchemy import select, and_
    from shared.database.models import Dialog, Persona, Message

    telegram_id = user.id

    # Get active dialogs with persona info
    result = await db.execute(
        select(Dialog, Persona)
        .join(Persona, Dialog.persona_id == Persona.id)
        .where(
            and_(
                Dialog.user_id == telegram_id,
                Dialog.is_active == True,
                Dialog.slot_number != None,
            )
        )
        .order_by(Dialog.slot_number)
    )

    dialogs = []
    for dialog, persona in result.fetchall():
        # Get last message preview
        last_msg_result = await db.execute(
            select(Message)
            .where(Message.dialog_id == dialog.id)
            .order_by(Message.created_at.desc())
            .limit(1)
        )
        last_msg = last_msg_result.scalar_one_or_none()
        last_message_preview = None
        if last_msg:
            last_message_preview = last_msg.content[:100]
            if len(last_msg.content) > 100:
                last_message_preview += "..."

        dialogs.append({
            "dialog_id": dialog.id,
            "slot_number": dialog.slot_number,
            "persona_id": persona.id,
            "persona_name": persona.name,
            "persona_key": persona.key,
            "story_id": dialog.story_id,
            "atmosphere": dialog.atmosphere,
            "message_count": dialog.message_count or 0,
            "last_message": last_message_preview,
            "updated_at": dialog.updated_at.isoformat() if dialog.updated_at else None,
        })

    return {"dialogs": dialogs}


@router.delete("/chat/dialogs/{dialog_id}")
async def clear_dialog(
    dialog_id: int,
    user: WebAppUser,
    db: AsyncSession = Depends(get_db)
):
    """
    Clear/delete a dialog slot.

    This:
    1. Deletes all messages from PostgreSQL
    2. Deletes memories from Qdrant
    3. Marks dialog as inactive

    Args:
        dialog_id: ID of dialog to clear
        user: WebAppUser (auto-created if new)
    """
    from shared.database.models import Dialog
    from app.services.embedding_service import embedding_service

    telegram_id = user.id

    # Get dialog
    dialog = await db.get(Dialog, dialog_id)
    if not dialog:
        raise HTTPException(status_code=404, detail="Dialog not found")

    # Verify ownership
    if dialog.user_id != telegram_id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Delete memories from Qdrant
    await embedding_service.delete_dialog_memories(
        user_id=telegram_id,
        dialog_id=dialog_id,
    )

    # Mark dialog as inactive (cascade will delete messages)
    dialog.is_active = False
    dialog.slot_number = None

    await db.commit()

    return {"success": True, "message": "Dialog cleared"}
