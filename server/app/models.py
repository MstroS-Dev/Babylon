import datetime
import uuid
from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Text, Integer
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


def gen_id():
    return str(uuid.uuid4())


class Worker(Base):
    __tablename__ = "workers"

    id = Column(String, primary_key=True, default=gen_id)
    name = Column(String, nullable=False)
    photo_url = Column(String, nullable=True)
    language = Column(String, nullable=False, default="en")  # e.g. 'hi', 'ro', 'ur', 'zh'
    phone = Column(String, nullable=True, unique=True)
    channel = Column(String, nullable=False)  # 'app' or 'whatsapp'
    device_token = Column(String, nullable=True)  # push token for app users
    checked_in = Column(Boolean, nullable=False, default=False)
    last_status_change = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    tasks = relationship("Task", back_populates="worker")


class ShiftEvent(Base):
    """History log of check-in/check-out events, separate from Worker's
    current checked_in flag - lets the manager see attendance over time,
    not just the current state."""
    __tablename__ = "shift_events"

    id = Column(String, primary_key=True, default=gen_id)
    worker_id = Column(String, ForeignKey("workers.id"), nullable=False)
    event = Column(String, nullable=False)  # 'check_in' | 'check_out'
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class Task(Base):
    __tablename__ = "tasks"

    id = Column(String, primary_key=True, default=gen_id)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    detailed_description = Column(Text, nullable=True)
    worker_id = Column(String, ForeignKey("workers.id"), nullable=False)

    # What the proof photo should actually show, e.g. "the cement blocks
    # stacked by the north wall" or "the window frame after sealing".
    # When set, every photo the worker uploads for this task gets checked
    # against this description by Claude's vision model (see
    # photo_review.py) instead of just the general before/after review.
    photo_requirement = Column(Text, nullable=True)

    status = Column(String, nullable=False, default="assigned")
    # assigned -> in_progress -> done

    before_photo_urls = Column(Text, nullable=True)   # comma-separated URLs
    after_photo_urls = Column(Text, nullable=True)

    claude_review = Column(Text, nullable=True)  # AI suggestion text, filled after after-photos submitted

    # Location, set from the manager console's building view.
    # location_mode: 'none' (location doesn't matter), 'pin' (exact spot marked,
    # shown to worker), 'gps' (live phone location tracked against the pin),
    # 'photo_checkin' (worker must photograph the spot for approval before starting).
    location_mode = Column(String, nullable=False, default="none")
    floor = Column(String, nullable=True)          # e.g. "1", "2", "Roof"
    pin_x = Column(String, nullable=True)           # normalized 0-1 position on the floor plate
    pin_y = Column(String, nullable=True)
    location_note = Column(Text, nullable=True)     # e.g. "north stairwell, by the electrical panel"
    wall_id = Column(String, nullable=True)         # which wall (N/E/S/W/I1/I2) the workspace is on
    seg_from = Column(Integer, nullable=True)       # first wall segment of the workspace
    seg_to = Column(Integer, nullable=True)         # last wall segment (inclusive)
    checkin_photo_url = Column(String, nullable=True)     # worker's photo_checkin submission
    checkin_approved = Column(Boolean, nullable=True)     # manager's approval of the check-in photo

    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    in_progress_at = Column(DateTime, nullable=True)
    done_at = Column(DateTime, nullable=True)

    worker = relationship("Worker", back_populates="tasks")
    photos = relationship("TaskPhoto", back_populates="task", cascade="all, delete-orphan")


class TaskPhoto(Base):
    """One row per photo a worker uploads for a task. Separate from
    Task.before_photo_urls/after_photo_urls (which stay as the flat
    comma-separated list for backwards compatibility) so each individual
    photo can carry its own AI verdict and admin override, and so the
    admin gets a real log of every photo instead of just the last review."""
    __tablename__ = "task_photos"

    id = Column(String, primary_key=True, default=gen_id)
    task_id = Column(String, ForeignKey("tasks.id"), nullable=False)
    stage = Column(String, nullable=False)  # 'before' or 'after'
    url = Column(String, nullable=False)

    # None until/unless the task has a photo_requirement to check against.
    ai_verdict = Column(String, nullable=True)       # 'match' | 'no_match' | 'unclear'
    ai_explanation = Column(Text, nullable=True)

    # None = admin hasn't looked at it. True = admin confirms it's fine
    # (overriding a no_match/unclear verdict, or just co-signing a match).
    # False = admin says it's actually wrong (overriding a match verdict).
    admin_override = Column(Boolean, nullable=True)

    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    task = relationship("Task", back_populates="photos")


class Message(Base):
    __tablename__ = "messages"

    id = Column(String, primary_key=True, default=gen_id)
    worker_id = Column(String, ForeignKey("workers.id"), nullable=False)
    task_id = Column(String, ForeignKey("tasks.id"), nullable=True)  # set for task-related feedback (e.g. photo mismatch)
    direction = Column(String, nullable=False)  # 'to_worker' or 'from_worker'
    original_text = Column(Text, nullable=False)
    original_lang = Column(String, nullable=False)
    translated_text = Column(Text, nullable=True)
    translated_lang = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
