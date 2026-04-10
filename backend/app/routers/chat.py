"""
FlowMind AI — AI Chat Router
Endpoint for the Gemini-powered decision assistant with multi-language support.
"""

from fastapi import APIRouter

from app.models.schemas import ChatRequest
from app.services.gemini_service import ask_assistant

router = APIRouter(prefix="/api/chat", tags=["AI Chat"])

SUPPORTED_LANGUAGES = {
    "en": "English",
    "hi": "Hindi",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "pt": "Portuguese",
    "ar": "Arabic",
    "ja": "Japanese",
    "zh": "Chinese",
    "ko": "Korean",
}


@router.get("/languages")
async def get_languages():
    """Get list of supported languages for the AI assistant."""
    return {"languages": SUPPORTED_LANGUAGES}


@router.post("")
async def chat(request: ChatRequest):
    """
    Send a question to the FlowMind AI assistant.
    The AI receives live stadium data (density, wait times, alerts) as context,
    so responses are specific and decision-focused, not generic.
    
    Supports multi-language responses via the `language` parameter.
    """
    response = await ask_assistant(
        user_message=request.message,
        user_location=request.user_location,
        language=request.language,
    )
    return response
