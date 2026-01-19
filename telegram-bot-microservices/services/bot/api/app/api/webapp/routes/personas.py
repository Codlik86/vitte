"""
Personas API routes for webapp
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from pydantic import BaseModel

from shared.database import get_db, User, Persona, AccessStatus

router = APIRouter()


# ==================== SCHEMAS ====================

class StoryCard(BaseModel):
    id: str
    key: str
    title: str
    description: str
    atmosphere: str
    prompt: Optional[str] = None
    image: Optional[str] = None


class PersonaListItem(BaseModel):
    id: int
    name: str
    short_title: str
    short_description: Optional[str] = None
    is_default: bool
    is_owner: bool
    is_selected: bool
    is_custom: bool
    avatar_url: Optional[str] = None
    avatar_chat_url: Optional[str] = None
    avatar_card_url: Optional[str] = None
    gender: Optional[str] = None
    kind: Optional[str] = None


class PersonasListResponse(BaseModel):
    items: list[PersonaListItem]


class PersonaDetailResponse(BaseModel):
    id: int
    name: str
    short_title: str
    short_description: Optional[str] = None
    description_short: Optional[str] = None
    description_long: Optional[str] = None
    is_default: bool
    is_owner: bool
    is_selected: bool
    is_custom: bool
    avatar_url: Optional[str] = None
    avatar_chat_url: Optional[str] = None
    avatar_card_url: Optional[str] = None
    gender: Optional[str] = None
    kind: Optional[str] = None
    story_cards: list[StoryCard] = []


class SelectAndGreetRequest(BaseModel):
    persona_id: int
    telegram_id: int
    storyId: Optional[str] = None
    extraDescription: Optional[str] = None
    settingsChanged: bool = False
    sendGreeting: bool = True
    atmosphere: Optional[str] = None


class SelectAndGreetResponse(BaseModel):
    success: bool
    message: Optional[str] = None


class CreateCustomPersonaRequest(BaseModel):
    telegram_id: int
    name: str
    short_description: str
    vibe: Optional[str] = None
    replace_existing: bool = False


class CreateCustomPersonaResponse(BaseModel):
    success: bool
    persona_id: int
    message: Optional[str] = None


# ==================== ROUTES ====================

@router.get("/personas", response_model=PersonasListResponse)
async def get_personas(
    telegram_id: int = Query(..., description="Telegram user ID"),
    db: AsyncSession = Depends(get_db)
):
    """Get list of all available personas"""
    # Get user
    user = await db.get(User, telegram_id)

    # Get all active personas
    result = await db.execute(
        select(Persona).where(
            Persona.is_active == True,
            (Persona.is_custom == False) | (Persona.owner_user_id == telegram_id)
        ).order_by(Persona.id)
    )
    personas = result.scalars().all()

    items = []
    for p in personas:
        is_selected = user and user.active_persona_id == p.id
        is_owner = p.owner_user_id == telegram_id

        items.append(PersonaListItem(
            id=p.id,
            name=p.name,
            short_title=p.short_title or "",
            short_description=p.short_description,
            is_default=p.is_default,
            is_owner=is_owner,
            is_selected=is_selected,
            is_custom=p.is_custom,
            avatar_url=None,  # Will be resolved by frontend
            avatar_chat_url=None,
            avatar_card_url=None,
            gender=p.gender,
            kind=p.kind.value if p.kind else None
        ))

    return PersonasListResponse(items=items)


@router.get("/personas/{persona_id}", response_model=PersonaDetailResponse)
async def get_persona(
    persona_id: int,
    telegram_id: int = Query(..., description="Telegram user ID"),
    db: AsyncSession = Depends(get_db)
):
    """Get persona details by ID"""
    # Get user
    user = await db.get(User, telegram_id)

    # Get persona
    persona = await db.get(Persona, persona_id)
    if not persona:
        raise HTTPException(status_code=404, detail="Persona not found")

    # Check access for custom personas
    if persona.is_custom and persona.owner_user_id != telegram_id:
        raise HTTPException(status_code=403, detail="Access denied")

    is_selected = user and user.active_persona_id == persona.id
    is_owner = persona.owner_user_id == telegram_id

    # Parse story cards from JSON
    story_cards = []
    if persona.story_cards:
        for sc in persona.story_cards:
            story_cards.append(StoryCard(
                id=sc.get("id", sc.get("key", "")),
                key=sc.get("key", ""),
                title=sc.get("title", ""),
                description=sc.get("description", ""),
                atmosphere=sc.get("atmosphere", "flirt_romance"),
                prompt=sc.get("prompt"),
                image=sc.get("image")
            ))

    return PersonaDetailResponse(
        id=persona.id,
        name=persona.name,
        short_title=persona.short_title or "",
        short_description=persona.short_description,
        description_short=persona.description_short,
        description_long=persona.description_long,
        is_default=persona.is_default,
        is_owner=is_owner,
        is_selected=is_selected,
        is_custom=persona.is_custom,
        avatar_url=None,
        avatar_chat_url=None,
        avatar_card_url=None,
        gender=persona.gender,
        kind=persona.kind.value if persona.kind else None,
        story_cards=story_cards
    )


@router.post("/personas/{persona_id}/select")
async def select_persona(
    persona_id: int,
    telegram_id: int = Query(..., description="Telegram user ID"),
    db: AsyncSession = Depends(get_db)
):
    """Select a persona for the user"""
    # Get user
    user = await db.get(User, telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Get persona
    persona = await db.get(Persona, persona_id)
    if not persona:
        raise HTTPException(status_code=404, detail="Persona not found")

    # Check access for custom personas
    if persona.is_custom and persona.owner_user_id != telegram_id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Update user's active persona
    user.active_persona_id = persona_id
    await db.commit()

    return {"success": True, "persona_id": persona_id}


@router.post("/personas/select_and_greet", response_model=SelectAndGreetResponse)
async def select_persona_and_greet(
    request: SelectAndGreetRequest,
    db: AsyncSession = Depends(get_db)
):
    """Select a persona and send greeting message"""
    # Get user
    user = await db.get(User, request.telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Get persona
    persona = await db.get(Persona, request.persona_id)
    if not persona:
        raise HTTPException(status_code=404, detail="Persona not found")

    # Check access for custom personas
    if persona.is_custom and persona.owner_user_id != request.telegram_id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Update user's active persona
    user.active_persona_id = request.persona_id
    await db.commit()

    # TODO: Send greeting via bot (needs integration with bot service)
    # For now, just return success

    return SelectAndGreetResponse(
        success=True,
        message=f"Selected persona: {persona.name}"
    )


@router.post("/personas/custom", response_model=CreateCustomPersonaResponse)
async def create_custom_persona(
    request: CreateCustomPersonaRequest,
    db: AsyncSession = Depends(get_db)
):
    """Create or update a custom persona"""
    # Get user
    user = await db.get(User, request.telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Check if user has subscription (custom personas require premium)
    # For now, allow all users to create custom personas

    # Check for existing custom persona
    if request.replace_existing:
        result = await db.execute(
            select(Persona).where(
                Persona.owner_user_id == request.telegram_id,
                Persona.is_custom == True
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            # Update existing
            existing.name = request.name
            existing.short_description = request.short_description
            existing.description_short = request.vibe or ""
            await db.commit()
            return CreateCustomPersonaResponse(
                success=True,
                persona_id=existing.id,
                message="Custom persona updated"
            )

    # Create new custom persona
    new_persona = Persona(
        key=f"custom_{request.telegram_id}_{int(db.get_bind().url.database or '0')}",
        name=request.name,
        short_title="Свой персонаж",
        short_description=request.short_description,
        description_short=request.vibe or "",
        is_default=False,
        is_custom=True,
        owner_user_id=request.telegram_id
    )
    db.add(new_persona)
    await db.commit()
    await db.refresh(new_persona)

    return CreateCustomPersonaResponse(
        success=True,
        persona_id=new_persona.id,
        message="Custom persona created"
    )
