"""
WhatsApp fallback channel.

Uses Twilio's WhatsApp Business API. Fill in TWILIO_ACCOUNT_SID,
TWILIO_AUTH_TOKEN and TWILIO_WHATSAPP_FROM as environment variables
once you've set up a Twilio account (or swap this for another provider).

This is a stub — send_whatsapp_message just needs real credentials to go live.

IMPORTANT — WhatsApp template requirement:
WhatsApp only allows plain freeform text within 24h of the worker's last
inbound message ("session message"). Since this app is manager-initiated
(assigning tasks, not replying), most sends are "business-initiated" and
WhatsApp requires a pre-approved message Content Template instead of plain
text, or Twilio rejects it with "ContentSid Required".

To fix: create a WhatsApp Content Template in Twilio Console -> Messaging ->
Content Template Builder (a simple one like "New task from your site manager:
\\n\\n{{1}}" works well), submit it for WhatsApp approval, then set
TWILIO_CONTENT_SID to its SID (starts with HX...) as an env var. Once set,
this module sends via that template automatically.
"""
import os
import json

TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")
TWILIO_WHATSAPP_FROM = os.environ.get("TWILIO_WHATSAPP_FROM")  # e.g. 'whatsapp:+14155238886'
TWILIO_CONTENT_SID = os.environ.get("TWILIO_CONTENT_SID")      # e.g. 'HX...', optional


def send_whatsapp_message(to_phone: str, text: str, media_url: str = None):
    """
    Sends a WhatsApp message via Twilio. Falls back to a console log if
    credentials aren't configured yet, so the rest of the app still runs
    during development.

    If TWILIO_CONTENT_SID is set, sends via that approved template (required
    for business-initiated messages). Otherwise sends plain body text, which
    only works as a reply within 24h of the worker's last inbound message.
    """
    if not (TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN and TWILIO_WHATSAPP_FROM):
        print(f"[whatsapp:DEV MODE] to={to_phone} text={text!r} media={media_url}")
        return {"status": "dev_mode_logged"}

    from twilio.rest import Client
    from twilio.http.http_client import TwilioHttpClient
    http_client = TwilioHttpClient(timeout=15)
    client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, http_client=http_client)

    kwargs = {"from_": TWILIO_WHATSAPP_FROM, "to": f"whatsapp:{to_phone}"}
    if TWILIO_CONTENT_SID:
        # Twilio WhatsApp Content Template variables are capped at 1024
        # characters. Going over silently produces a generic 400
        # "Content Variables parameter is invalid" error with no length
        # hint, so we guard and log here rather than let it fail blind.
        # WhatsApp Content Template variables cannot contain newline
        # characters - Twilio rejects them with the same generic 400
        # "Content Variables parameter is invalid" error as the length
        # issue below, with no indication that newlines were the cause.
        # Collapse them into a readable separator instead.
        var_text = " \u2014 ".join(line.strip() for line in text.splitlines() if line.strip())
        if len(var_text) > 1024:
            print(f"[whatsapp:WARN] content variable too long ({len(var_text)} chars), truncating to 1024")
            var_text = var_text[:1000].rsplit(" ", 1)[0] + "\u2026"
        kwargs["content_sid"] = TWILIO_CONTENT_SID
        kwargs["content_variables"] = json.dumps({"1": var_text})
        print(f"[whatsapp:DEBUG] content_variables length={len(var_text)} preview={var_text[:80]!r}")
    else:
        kwargs["body"] = text
        if media_url:
            kwargs["media_url"] = [media_url]

    message = client.messages.create(**kwargs)
    return {"status": "sent", "sid": message.sid}
