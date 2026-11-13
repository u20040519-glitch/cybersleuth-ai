# =============================================================================
# PROJECT NEXUS AI - Forensic Chatbot API
# =============================================================================
# NEXUS AI Forensic Chatbot - backend routes all Gemini requests.
# =============================================================================

import logging
import json
import httpx
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user
from app.core.config import settings
from app.db.database import get_db
from app.models import User, Case, ChatbotConversation, ChatbotMessage

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chatbot", tags=["chatbot"])


# ---------------------------------------------------------------------------
# Create conversation
# ---------------------------------------------------------------------------

@router.post("/conversations")
async def create_conversation(
    title: Optional[str] = None,
    case_id: Optional[str] = None,
    current_user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new chatbot conversation."""
    case_uuid = None
    if case_id:
        try:
            case_uuid = UUID(case_id)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid case ID")

        result = await db.execute(select(Case).where(Case.id == case_uuid))
        case = result.scalar_one_or_none()
        if not case:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")
        if case.owner_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    conversation = ChatbotConversation(
        user_id=current_user.id,
        case_id=case_uuid,
        title=title,
    )
    db.add(conversation)
    await db.commit()
    await db.refresh(conversation)

    return {
        "id": str(conversation.id),
        "title": conversation.title,
        "case_id": str(conversation.case_id) if conversation.case_id else None,
        "created_at": conversation.created_at,
    }


# ---------------------------------------------------------------------------
# List conversations
# ---------------------------------------------------------------------------

@router.get("/conversations")
async def list_conversations(
    current_user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """List user's chatbot conversations."""
    result = await db.execute(
        select(ChatbotConversation)
        .where(ChatbotConversation.user_id == current_user.id)
        .order_by(ChatbotConversation.updated_at.desc())
    )
    conversations = result.scalars().all()

    return [
        {
            "id": str(c.id),
            "title": c.title,
            "case_id": str(c.case_id) if c.case_id else None,
            "created_at": c.created_at,
            "updated_at": c.updated_at,
        }
        for c in conversations
    ]


# ---------------------------------------------------------------------------
# Get conversation messages
# ---------------------------------------------------------------------------

@router.get("/conversations/{conversation_id}/messages")
async def get_messages(
    conversation_id: str,
    current_user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get messages for a conversation."""
    try:
        conv_uuid = UUID(conversation_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid conversation ID")

    result = await db.execute(
        select(ChatbotConversation).where(ChatbotConversation.id == conv_uuid)
    )
    conversation = result.scalar_one_or_none()
    if not conversation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")

    if conversation.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    result = await db.execute(
        select(ChatbotMessage)
        .where(ChatbotMessage.conversation_id == conv_uuid)
        .order_by(ChatbotMessage.created_at)
    )
    messages = result.scalars().all()

    return [
        {
            "id": str(m.id),
            "role": m.role,
            "content": m.content,
            "created_at": m.created_at,
        }
        for m in messages
    ]


# ---------------------------------------------------------------------------
# Send message (AI response via backend - Gemini key never reaches frontend)
# ---------------------------------------------------------------------------

@router.post("/conversations/{conversation_id}/messages")
async def send_message(
    conversation_id: str,
    content: str,
    current_user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Send a message and get AI response. All Gemini API calls go through backend."""
    try:
        conv_uuid = UUID(conversation_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid conversation ID")

    result = await db.execute(
        select(ChatbotConversation).where(ChatbotConversation.id == conv_uuid)
    )
    conversation = result.scalar_one_or_none()
    if not conversation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")

    if conversation.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    # Save user message
    user_msg = ChatbotMessage(
        conversation_id=conv_uuid,
        role="user",
        content=content,
    )
    db.add(user_msg)
    await db.commit()

    # Get AI response via backend (Gemini)
    if settings.is_gemini_configured():
        ai_response = await _get_gemini_response(content, conversation_id)
    else:
        ai_response = (
            "AI processing is not configured. Please set GEMINI_API_KEY in the backend environment. "
            "This is a placeholder response."
        )

    # Save AI response
    ai_msg = ChatbotMessage(
        conversation_id=conv_uuid,
        role="assistant",
        content=ai_response,
    )
    db.add(ai_msg)

    # Update conversation timestamp
    conversation.updated_at = datetime.now(timezone.utc)  # noqa - will import below
    await db.commit()

    return {
        "user_message": {"id": str(user_msg.id), "role": "user", "content": content},
        "assistant_message": {"id": str(ai_msg.id), "role": "assistant", "content": ai_response},
    }


async def _get_gemini_response(content: str, conversation_id: str) -> str:
    """Call Gemini API through backend. API key never exposed to frontend."""
    try:
        url = f"{settings.gemini_api_base_url}/v1/models/{settings.gemini_model}:generateContent?key={settings.gemini_api_key}"
        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": f"You are a forensic investigation assistant for PROJECT NEXUS AI. Help the user with forensic analysis. Conversation: {conversation_id}. User says: {content}"
                        }
                    ]
                }
            ]
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code == 200:
                data = resp.json()
                return data["candidates"][0]["content"]["parts"][0]["text"]
            else:
                logger.error("Gemini API error: %s", resp.status_code)
                return "AI service temporarily unavailable. Please try again later."
    except Exception as exc:
        logger.error("Gemini API error: %s", type(exc).__name__)
        return "AI service temporarily unavailable."