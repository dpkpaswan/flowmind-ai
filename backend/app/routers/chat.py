"""FlowMind AI -- AI Chat Router.

Endpoint for the Vertex AI powered decision assistant with
multi-language support and input sanitization.
"""

from typing import Any, Dict

from fastapi import APIRouter

from app.middleware.security import sanitize_input
from app.models.schemas import ChatRequest
from app.services.gemini_service import ask_assistant

__all__ = ["router"]

router = APIRouter(prefix="/api/chat", tags=["AI Chat"])

SUPPORTED_LANGUAGES: Dict[str, str] = {
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
async def get_languages() -> Dict[str, Any]:
    """Get list of supported languages for the AI assistant.

    Returns:
        A dict mapping ISO 639-1 codes to human-readable language names.
    """
    return {"languages": SUPPORTED_LANGUAGES}


@router.post("")
async def chat(request: ChatRequest) -> Dict[str, Any]:
    """Send a question to the FlowMind AI assistant.

    The AI receives live stadium data (density, wait times, alerts) as
    context, so responses are specific and decision-focused.

    Input is sanitized to prevent XSS and log injection before being
    passed to the AI service.

    Args:
        request: A ``ChatRequest`` with ``message``, optional
            ``user_location``, and optional ``language`` code.

    Returns:
        A dict with ``response``, ``recommended_action``,
        ``confidence``, ``related_zones``, and ``timestamp``.
    """
    # Sanitize user input to prevent XSS and log injection
    safe_message: str = sanitize_input(request.message, max_length=500)
    safe_location: str | None = (
        sanitize_input(request.user_location, max_length=100)
        if request.user_location else None
    )

    response = await ask_assistant(
        user_message=safe_message,
        user_location=safe_location,
        language=request.language,
    )
    return response

