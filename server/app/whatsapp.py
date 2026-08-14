"""
WhatsApp fallback channel.

Uses Twilio's WhatsApp Business API. Fill in TWILIO_ACCOUNT_SID,
TWILIO_AUTH_TOKEN and TWILIO_WHATSAPP_FROM as environment variables
once you've set up a Twilio account (or swap this for another provider).

This is a stub — send_whatsapp_message just needs real credentials to go live.
"""
import os

TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")
TWILIO_WHATSAPP_FROM = os.environ.get("TWILIO_WHATSAPP_FROM")  # e.g. 'whatsapp:+14155238886'


def send_whatsapp_message(to_phone: str, text: str, media_url: str = None):
    """
    Sends a WhatsApp message via Twilio. Falls back to a console log if
    credentials aren't configured yet, so the rest of the app still runs
    during development.
    """
    if not (TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN and TWILIO_WHATSAPP_FROM):
        print(f"[whatsapp:DEV MODE] to={to_phone} text={text!r} media={media_url}")
        return {"status": "dev_mode_logged"}

    from twilio.rest import Client
    from twilio.http.http_client import TwilioHttpClient
    http_client = TwilioHttpClient(timeout=15)
    client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, http_client=http_client)
    kwargs = {"from_": TWILIO_WHATSAPP_FROM, "to": f"whatsapp:{to_phone}", "body": text}
    if media_url:
        kwargs["media_url"] = [media_url]
    message = client.messages.create(**kwargs)
    return {"status": "sent", "sid": message.sid}
