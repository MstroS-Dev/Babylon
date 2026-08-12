import datetime
import uuid
from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Text
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
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    tasks = relationship("Task", back_populates="worker")


class Task(Base):
    __tablename__ = "tasks"

    id = Column(String, primary_key=True, default=gen_id)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    detailed_description = Column(Text, nullable=True)
    worker_id = Column(String, ForeignKey("workers.id"), nullable=False)

    status = Column(String, nullable=False, default="assigned")
    # assigned -> in_progress -> done

    before_photo_urls = Column(Text, nullable=True)   # comma-separated URLs
    after_photo_urls = Column(Text, nullable=True)

    claude_review = Column(Text, nullable=True)  # AI suggestion text, filled after after-photos submitted

    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    in_progress_at = Column(DateTime, nullable=True)
    done_at = Column(DateTime, nullable=True)

    worker = relationship("Worker", back_populates="tasks")


class Message(Base):
    __tablename__ = "messages"

    id = Column(String, primary_key=True, default=gen_id)
    worker_id = Column(String, ForeignKey("workers.id"), nullable=False)
    direction = Column(String, nullable=False)  # 'to_worker' or 'from_worker'
    original_text = Column(Text, nullable=False)
    original_lang = Column(String, nullable=False)
    translated_text = Column(Text, nullable=True)
    translated_lang = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
