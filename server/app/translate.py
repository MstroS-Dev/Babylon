"""
Server-side translation.

App users translate locally on-device via Google ML Kit — the server never
needs to translate for them. This module is only used for:
  - WhatsApp-only workers (no ML Kit available)
  - Translating worker replies back to the manager's language (Hebrew/English)

Uses the Claude API for translation so you don't need a separate Google
Translate API key. Swap this out for Google Cloud Translation if you prefer.
"""
import os
from anthropic import Anthropic

client = Anthropic()  # reads ANTHROPIC_API_KEY from environment

LANGUAGE_NAMES = {
    "en": "English",
    "he": "Hebrew",
    "hi": "Hindi",
    "zh": "Chinese",
    "ro": "Romanian",
    "ur": "Urdu",
    "ar": "Arabic",
    "th": "Thai",
    "tl": "Tagalog",
}


def translate_text(text: str, source_lang: str, target_lang: str) -> str:
    if source_lang == target_lang:
        return text

    source_name = LANGUAGE_NAMES.get(source_lang, source_lang)
    target_name = LANGUAGE_NAMES.get(target_lang, target_lang)

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=500,
        messages=[{
            "role": "user",
            "content": (
                f"Translate the following construction site instruction from "
                f"{source_name} to {target_name}. Keep it short, direct, and "
                f"clear for a worker on-site. Reply with ONLY the translation, "
                f"nothing else.\n\nText: {text}"
            )
        }]
    )
    return response.content[0].text.strip()
