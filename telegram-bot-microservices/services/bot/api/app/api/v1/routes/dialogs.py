"""
Dialog API endpoints
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database import (
    get_db,
    get_dialog_by_id,
    get_user_dialogs,
    create_dialog,
    update_dialog,
    delete_dialog,
    get_dialog_messages,
    create_message,
    get_message_count
)
from shared.schemas import (
    DialogResponse,
    DialogListResponse,
    DialogUpdate,
    MessageResponse,
    MessageListResponse,
    MessageCreate
)

router = APIRouter()


# ==================== DIALOG ENDPOINTS ====================

@router.get("/{dialog_id}", response_model=DialogResponse)
async def get_dialog(dialog_id: int):
    """
    Get dialog by ID

    Args:
        dialog_id: Dialog ID

    Returns:
        Dialog data
    """
    async for db in get_db():
        dialog = await get_dialog_by_id(db, dialog_id)

        if not dialog:
            raise HTTPException(status_code=404, detail="Dialog not found")

        return dialog


@router.get("/user/{user_id}", response_model=DialogListResponse)
async def get_user_dialogs_list(
    user_id: int,
    active_only: bool = Query(True, description="Return only active dialogs"),
    limit: int = Query(50, ge=1, le=100, description="Max dialogs to return")
):
    """
    Get all dialogs for user

    Args:
        user_id: User ID
        active_only: Return only active dialogs
        limit: Maximum dialogs to return

    Returns:
        List of dialogs
    """
    async for db in get_db():
        dialogs = await get_user_dialogs(db, user_id, active_only, limit)

        return DialogListResponse(
            dialogs=dialogs,
            total=len(dialogs)
        )


@router.post("/user/{user_id}", response_model=DialogResponse, status_code=201)
async def create_user_dialog(
    user_id: int,
    title: str = Query(None, description="Dialog title")
):
    """
    Create new dialog for user

    Args:
        user_id: User ID
        title: Dialog title (optional)

    Returns:
        Created dialog
    """
    async for db in get_db():
        dialog = await create_dialog(db, user_id, title)
        return dialog


@router.patch("/{dialog_id}", response_model=DialogResponse)
async def update_dialog_data(
    dialog_id: int,
    data: DialogUpdate
):
    """
    Update dialog

    Args:
        dialog_id: Dialog ID
        data: Update data

    Returns:
        Updated dialog
    """
    async for db in get_db():
        # Build update dict from non-None fields
        update_data = {k: v for k, v in data.model_dump().items() if v is not None}

        if not update_data:
            raise HTTPException(status_code=400, detail="No fields to update")

        dialog = await update_dialog(db, dialog_id, **update_data)

        if not dialog:
            raise HTTPException(status_code=404, detail="Dialog not found")

        return dialog


@router.delete("/{dialog_id}", status_code=204)
async def delete_dialog_endpoint(dialog_id: int):
    """
    Delete dialog (soft delete - mark as inactive)

    Args:
        dialog_id: Dialog ID
    """
    async for db in get_db():
        deleted = await delete_dialog(db, dialog_id)

        if not deleted:
            raise HTTPException(status_code=404, detail="Dialog not found")

        return None


# ==================== MESSAGE ENDPOINTS ====================

@router.get("/{dialog_id}/messages", response_model=MessageListResponse)
async def get_messages(
    dialog_id: int,
    limit: int = Query(100, ge=1, le=500, description="Max messages"),
    offset: int = Query(0, ge=0, description="Offset for pagination")
):
    """
    Get messages for dialog

    Args:
        dialog_id: Dialog ID
        limit: Maximum messages to return
        offset: Offset for pagination

    Returns:
        List of messages
    """
    async for db in get_db():
        # Check if dialog exists
        dialog = await get_dialog_by_id(db, dialog_id)
        if not dialog:
            raise HTTPException(status_code=404, detail="Dialog not found")

        messages = await get_dialog_messages(db, dialog_id, limit, offset)
        total = await get_message_count(db, dialog_id)

        return MessageListResponse(
            messages=messages,
            total=total,
            dialog_id=dialog_id
        )


@router.post("/{dialog_id}/messages", response_model=MessageResponse, status_code=201)
async def create_message_endpoint(
    dialog_id: int,
    data: MessageCreate
):
    """
    Create message in dialog

    Args:
        dialog_id: Dialog ID
        data: Message data

    Returns:
        Created message
    """
    async for db in get_db():
        # Check if dialog exists
        dialog = await get_dialog_by_id(db, dialog_id)
        if not dialog:
            raise HTTPException(status_code=404, detail="Dialog not found")

        # Validate role
        if data.role not in ["user", "assistant", "system"]:
            raise HTTPException(
                status_code=400,
                detail="Invalid role. Must be: user, assistant, or system"
            )

        message = await create_message(
            db,
            dialog_id=dialog_id,
            role=data.role,
            content=data.content
        )

        return message
