"""
Claude-powered task review.

Given a task description and its before/after photos, asks Claude to flag
whether the work looks consistent with what was asked (wrong material,
missing safety gear, etc). This is a SUGGESTION surfaced to the manager,
never an automatic pass/fail.
"""
import base64
from anthropic import Anthropic

client = Anthropic()


def _image_block(path_or_bytes, media_type="image/jpeg"):
    if isinstance(path_or_bytes, (bytes, bytearray)):
        data = path_or_bytes
    else:
        with open(path_or_bytes, "rb") as f:
            data = f.read()
    return {
        "type": "image",
        "source": {
            "type": "base64",
            "media_type": media_type,
            "data": base64.standard_b64encode(data).decode("utf-8"),
        },
    }


def review_task(task_title: str, task_description: str, before_photo_paths, after_photo_paths) -> str:
    content = [
        {
            "type": "text",
            "text": (
                f"You're reviewing a completed construction task for a site manager.\n\n"
                f"Task: {task_title}\n"
                f"Description: {task_description}\n\n"
                f"Below are the 'before' photos the worker submitted when starting, "
                f"followed by the 'after' photos submitted on completion. "
                f"Briefly note (2-4 sentences) whether the work looks consistent with "
                f"the task description — flag anything that looks wrong (wrong material, "
                f"missing safety gear, incomplete work, mismatched quantities). "
                f"This is a suggestion for the manager to review, not a final verdict. "
                f"Be direct and specific."
            ),
        }
    ]

    for p in before_photo_paths:
        content.append(_image_block(p))
    for p in after_photo_paths:
        content.append(_image_block(p))

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=400,
        messages=[{"role": "user", "content": content}],
    )
    return response.content[0].text.strip()
