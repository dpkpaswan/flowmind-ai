"""
FlowMind AI — Gemini AI Service
Integrates Google Gemini Flash for decision-based stadium assistance.
The AI receives live stadium context with every query, making responses
specific and actionable rather than generic chatbot replies.
"""

import json
from typing import Dict, Optional

import google.generativeai as genai

from app.config import settings
from app.data.mock_generator import generate_snapshot
from app.services.alert_service import generate_alerts
from app.utils.helpers import now_iso


# ── System Prompt ────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are FlowMind AI, a smart stadium assistant for {stadium_name}.
Your job is to help fans navigate the stadium, avoid crowds, and make quick decisions.

RULES:
1. Give SPECIFIC, ACTIONABLE advice — never vague or generic answers.
2. Always reference actual data: zone names, density percentages, wait times, facility names.
3. When recommending a location, explain WHY (e.g., "North Stand is at 45% capacity vs South Stand at 82%").
4. If the user asks about food/restrooms/gates, compare real wait times and recommend the best option.
5. For timing advice, be specific: "Leave in the next 5 minutes" not "Leave soon."
6. Keep responses concise — 2-4 sentences max unless the user asks for detail.
7. Use a friendly, confident tone. You're a knowledgeable stadium insider.
8. If you don't have enough context, say so honestly.
9. IMPORTANT: You MUST respond in {language}. Translate your entire response to {language}.

CURRENT STADIUM DATA:
{stadium_context}

ACTIVE ALERTS:
{alerts_context}
"""

LANGUAGE_NAMES = {
    "en": "English", "hi": "Hindi", "es": "Spanish", "fr": "French",
    "de": "German", "pt": "Portuguese", "ar": "Arabic",
    "ja": "Japanese", "zh": "Chinese", "ko": "Korean",
}


# ── Service ──────────────────────────────────────────────────────────────────

_model = None


def _get_model():
    """Lazy-initialize the Gemini model."""
    global _model
    if _model is None:
        if not settings.GEMINI_API_KEY:
            return None
        genai.configure(api_key=settings.GEMINI_API_KEY)
        _model = genai.GenerativeModel(
            model_name=settings.GEMINI_MODEL,
            generation_config={
                "temperature": 0.7,
                "top_p": 0.9,
                "max_output_tokens": 500,
            },
        )
    return _model


def _build_context() -> tuple:
    """Build live stadium context string for the system prompt."""
    snapshot = generate_snapshot()
    alerts = generate_alerts()

    # Format zone data
    zone_lines = []
    for zid, zdata in snapshot["zones"].items():
        zone_lines.append(
            f"- {zdata['name']}: {zdata['current_density'] * 100:.0f}% capacity "
            f"({zdata['current_count']:,}/{zdata['capacity']:,} people) — Status: {zdata['status']}"
        )

    # Format facility wait times
    facility_lines = []
    for fid, fdata in snapshot["facilities"].items():
        status = "OPEN" if fdata.get("is_open", True) else "CLOSED"
        facility_lines.append(
            f"- {fdata['name']} ({fdata['facility_type'].replace('_', ' ')}) in {fdata['zone_id'].replace('_', ' ').title()}: "
            f"{fdata['current_wait_minutes']:.0f} min wait, {fdata['queue_length']} in queue [{status}]"
        )

    overview = snapshot["overview"]
    stadium_context = (
        f"Stadium: {overview['stadium_name']}\n"
        f"Total Attendance: {overview['current_attendance']:,} / {overview['total_capacity']:,} "
        f"({overview['overall_density'] * 100:.0f}% overall)\n\n"
        f"ZONE DENSITIES:\n" + "\n".join(zone_lines) + "\n\n"
        f"FACILITY WAIT TIMES:\n" + "\n".join(facility_lines)
    )

    # Format alerts
    if alerts:
        alert_lines = [
            f"- [{a['severity'].upper()}] {a['title']}: {a['message']} → Action: {a['action']}"
            for a in alerts[:5]  # Top 5 alerts
        ]
        alerts_context = "\n".join(alert_lines)
    else:
        alerts_context = "No active alerts."

    return stadium_context, alerts_context


async def ask_assistant(user_message: str, user_location: Optional[str] = None, language: str = "en") -> Dict:
    """
    Send a user query to Gemini with full stadium context.
    Returns a structured response with the AI answer and metadata.
    Supports multi-language responses via the language parameter.
    """
    model = _get_model()

    if model is None:
        # Fallback: generate a rule-based response without Gemini
        return _fallback_response(user_message, user_location, language)

    stadium_context, alerts_context = _build_context()

    lang_name = LANGUAGE_NAMES.get(language, "English")
    system = SYSTEM_PROMPT.format(
        stadium_name=settings.STADIUM_NAME,
        stadium_context=stadium_context,
        alerts_context=alerts_context,
        language=lang_name,
    )

    # Add user location context if provided
    user_msg = user_message
    if user_location:
        user_msg = f"[User is currently at: {user_location}] {user_message}"

    try:
        chat = model.start_chat(history=[])
        # Send system context as the first message
        response = await chat.send_message_async(
            f"{system}\n\nUser question: {user_msg}"
        )

        response_text = response.text.strip()

        # Extract related zones from the response
        snapshot = generate_snapshot()
        related_zones = [
            zdata["name"]
            for zid, zdata in snapshot["zones"].items()
            if zdata["name"].lower() in response_text.lower()
        ]

        return {
            "response": response_text,
            "recommended_action": _extract_action(response_text),
            "confidence": 0.85,
            "related_zones": related_zones,
            "timestamp": now_iso(),
        }

    except Exception as e:
        # Gemini failed — fall back to rule-based response instead of error
        print(f"[GEMINI ERROR] {type(e).__name__}: {e}")
        return _fallback_response(user_message, user_location, language)


def _fallback_response(user_message: str, user_location: Optional[str] = None, language: str = "en") -> Dict:
    """Rule-based fallback when Gemini API key is not configured."""
    snapshot = generate_snapshot()
    zones = snapshot["zones"]
    facilities = snapshot["facilities"]
    msg_lower = user_message.lower()

    response = ""

    if any(w in msg_lower for w in ["crowd", "busy", "packed", "crowded", "density"]):
        # Find busiest and quietest zones
        sorted_zones = sorted(zones.values(), key=lambda z: z["current_density"], reverse=True)
        busiest = sorted_zones[0]
        quietest = sorted_zones[-1]
        response = (
            f"Right now, {busiest['name']} is the most crowded at "
            f"{busiest['current_density'] * 100:.0f}% capacity. "
            f"Your best bet is {quietest['name']} at just "
            f"{quietest['current_density'] * 100:.0f}%. "
            f"I'd suggest heading there if you want some breathing room."
        )

    elif any(w in msg_lower for w in ["food", "eat", "hungry", "burger", "pizza", "drink"]):
        food = [f for f in facilities.values() if f["facility_type"] == "food_stall" and f.get("is_open", True)]
        food.sort(key=lambda x: x["current_wait_minutes"])
        if food:
            best = food[0]
            response = (
                f"{best['name']} has the shortest wait right now — just "
                f"{best['current_wait_minutes']:.0f} minutes with {best['queue_length']} "
                f"people in line. It's in the {best['zone_id'].replace('_', ' ').title()} area."
            )
        else:
            response = "All food stalls appear to be closed right now. Check back shortly."

    elif any(w in msg_lower for w in ["restroom", "bathroom", "toilet", "washroom"]):
        restrooms = [f for f in facilities.values() if f["facility_type"] == "restroom" and f.get("is_open", True)]
        restrooms.sort(key=lambda x: x["current_wait_minutes"])
        if restrooms:
            best = restrooms[0]
            response = (
                f"Head to {best['name']} — only {best['current_wait_minutes']:.0f} minutes wait. "
                f"It's in {best['zone_id'].replace('_', ' ').title()}."
            )

    elif any(w in msg_lower for w in ["exit", "leave", "gate", "go home"]):
        gates = [f for f in facilities.values() if f["facility_type"] == "gate" and f.get("is_open", True)]
        gates.sort(key=lambda x: x["current_wait_minutes"])
        if gates:
            best = gates[0]
            response = (
                f"The fastest exit right now is {best['name']} with a "
                f"{best['current_wait_minutes']:.0f}-minute wait. "
                f"I'd recommend leaving in the next 5 minutes before the post-match rush."
            )

    elif any(w in msg_lower for w in ["where", "navigate", "find", "how to get"]):
        response = (
            "I can help you navigate! The stadium has 8 zones: North Stand, South Stand, "
            "East Stand, West Stand, Food Court A & B, Main Gate, and VIP Lounge. "
            "Tell me where you want to go and I'll find you the least crowded route."
        )

    else:
        response = _quick_summary()

    return {
        "response": response,
        "recommended_action": None,
        "confidence": 0.7,
        "related_zones": [],
        "timestamp": now_iso(),
    }


def _quick_summary() -> str:
    """Generate a quick stadium summary."""
    snapshot = generate_snapshot()
    overview = snapshot["overview"]
    zones = snapshot["zones"]
    sorted_z = sorted(zones.values(), key=lambda z: z["current_density"])

    return (
        f"The stadium is at {overview['overall_density'] * 100:.0f}% overall capacity "
        f"({overview['current_attendance']:,} fans). "
        f"Quietest zone: {sorted_z[0]['name']} "
        f"({sorted_z[0]['current_density'] * 100:.0f}%). "
        f"Ask me about food, restrooms, exits, or crowd status for specific advice!"
    )


def _extract_action(response_text: str) -> Optional[str]:
    """Try to extract a key action from the AI response."""
    action_keywords = ["head to", "go to", "avoid", "leave", "try", "recommend", "suggest"]
    sentences = response_text.split(".")
    for sentence in sentences:
        for keyword in action_keywords:
            if keyword in sentence.lower():
                return sentence.strip() + "."
    return None
