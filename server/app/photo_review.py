"""
Per-photo AI verdict for task proof photos.

Separate from claude_review.py (which writes one free-text overall
before/after review once a task is marked done). This runs on EVERY
photo, immediately on upload, and checks it against the specific
photo_requirement the manager set on the task (e.g. "the cement blocks
stacked by the north wall") - not just "does this look reasonable".

Returns a structured verdict so the console can show a clear badge and
the worker can get immediate feedback if it doesn't match.
"""
import base64
import json
from anthropic import Anthropic

client = Anthropic(timeout=20.0)

VALID_VERDICTS = ("match", "no_match", "unclear")


def _image_block(path: str, media_type: str = "image/jpeg"):
    with open(path, "rb") as f:
        data = f.read()
    return {
        "type": "image",
        "source": {
            "type": "base64",
            "media_type": media_type,
            "data": base64.standard_b64encode(data).decode("utf-8"),
        },
    }


def verify_photo(task_title: str, task_description: str, photo_requirement: str, photo_path: str) -> dict:
    """Ask Claude whether the photo actually shows what was asked for.

    Returns {"verdict": "match" | "no_match" | "unclear", "explanation": str}.
    Never raises for a bad/unparseable model response - falls back to
    "unclear" so a hiccup here never blocks the worker's upload.
    """
    prompt = (
        "A construction worker uploaded a photo as proof for a task. Decide whether "
        "the photo actually shows what was specifically requested.\n\n"
        f"Task: {task_title}\n"
        f"Task description: {task_description}\n"
        f"What this photo specifically needs to show: {photo_requirement}\n\n"
        "Respond with ONLY a JSON object and nothing else - no markdown fences, "
        "no preamble. Format exactly:\n"
        '{"verdict": "match", "explanation": "..."}\n\n'
        'Rules: verdict must be exactly "match", "no_match", or "unclear". '
        'Use "unclear" only if the photo itself is too dark/blurry/far away to '
        "tell either way - not as a hedge when you're fairly confident. "
        "The explanation should be one short, plain sentence a worker with "
        "limited English could understand, e.g. \"This shows piping, not the "
        "cement blocks that were asked for.\""
    )

    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=200,
            messages=[{"role": "user", "content": [{"type": "text", "text": prompt}, _image_block(photo_path)]}],
        )
        raw = response.content[0].text.strip()
        cleaned = raw.replace("```json", "").replace("```", "").strip()
        data = json.loads(cleaned)
        verdict = data.get("verdict")
        if verdict not in VALID_VERDICTS:
            verdict = "unclear"
        explanation = str(data.get("explanation", "")).strip()
        return {"verdict": verdict, "explanation": explanation}
    except Exception as e:
        return {"verdict": "unclear", "explanation": f"(AI review failed: {e})"}
