"""
Server-side translation.

App users translate locally on-device via Google ML Kit — the server never
needs to translate for them. This module is only used for:
  - WhatsApp-only workers (no ML Kit available)
  - Translating worker replies back to the manager's language (Hebrew/English)

Uses the Claude API for translation so you don't need a separate Google
Translate API key. Swap this out for Google Cloud Translation if you prefer.

All outgoing messages are also run through a "plain language" pass: simple
words, short sentences, no slang or profanity, no idioms — since these are
read by workers in a second language, sometimes aloud via text-to-speech.
"""
import os
from anthropic import Anthropic

client = Anthropic(timeout=15.0)  # reads ANTHROPIC_API_KEY from environment

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
    "ru": "Russian",
    "uz": "Uzbek",
    "si": "Sinhala",
}

# The console's "add WhatsApp worker" form stores full language words
# (e.g. "hebrew", "uzbek") rather than ISO codes, while workers created
# elsewhere may use 2-letter codes. Accept either so translation always
# gets a real language name instead of falling back to the raw string.
_FULL_NAME_ALIASES = {name.lower(): name for name in LANGUAGE_NAMES.values()}


def _resolve_language_name(lang: str) -> str:
    if not lang:
        return lang
    key = lang.strip().lower()
    if key in _FULL_NAME_ALIASES:
        return _FULL_NAME_ALIASES[key]
    return LANGUAGE_NAMES.get(lang, lang.capitalize())

PLAIN_LANGUAGE_RULES = (
    "Rules for the translation:\n"
    "1. Use simple, everyday words. Avoid idioms, slang, and technical jargon "
    "unless it's a necessary construction term (e.g. 'cement', 'rebar').\n"
    "2. Keep sentences short and direct, like clear spoken instructions.\n"
    "3. Remove or neutralize any profanity, insults, or harsh tone from the "
    "original message — translate the instruction, not the attitude.\n"
    "4. Do not add extra commentary, greetings, or explanations — translate "
    "only the instruction itself.\n"
    "5. The result should sound natural and polite when read aloud by a "
    "text-to-speech engine to a worker on a construction site."
)


def translate_text(text: str, source_lang: str, target_lang: str) -> str:
    if source_lang == target_lang:
        return _plain_language_pass(text, source_lang)

    source_name = _resolve_language_name(source_lang)
    target_name = _resolve_language_name(target_lang)

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=500,
        messages=[{
            "role": "user",
            "content": (
                f"Translate the following construction site instruction from "
                f"{source_name} to {target_name}.\n\n"
                f"{PLAIN_LANGUAGE_RULES}\n\n"
                f"Reply with ONLY the translation, nothing else.\n\n"
                f"Text: {text}"
            )
        }]
    )
    return response.content[0].text.strip()


def _plain_language_pass(text: str, lang: str) -> str:
    """Used when source and target language are the same (e.g. manager
    reviewing his own message) — still cleans up tone and simplifies wording."""
    lang_name = _resolve_language_name(lang)
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=500,
        messages=[{
            "role": "user",
            "content": (
                f"Rewrite the following construction site instruction in "
                f"{lang_name}, keeping the same language.\n\n"
                f"{PLAIN_LANGUAGE_RULES}\n\n"
                f"Reply with ONLY the rewritten instruction, nothing else.\n\n"
                f"Text: {text}"
            )
        }]
    )
    return response.content[0].text.strip()
