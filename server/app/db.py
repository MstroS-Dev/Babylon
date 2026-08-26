from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from .models import Base

DATABASE_URL = "sqlite:///./site.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Columns added after the initial release. create_all() only creates missing
# TABLES, not missing COLUMNS on tables that already exist — so on a live
# server with existing data, new Task columns need an additive migration.
_NEW_TASK_COLUMNS = {
    "location_mode": "VARCHAR NOT NULL DEFAULT 'none'",
    "floor": "VARCHAR",
    "pin_x": "VARCHAR",
    "pin_y": "VARCHAR",
    "location_note": "TEXT",
    "checkin_photo_url": "VARCHAR",
    "checkin_approved": "BOOLEAN",
    "photo_requirement": "TEXT",
}

_NEW_MESSAGE_COLUMNS = {
    "task_id": "VARCHAR",
}


def _migrate(engine):
    with engine.connect() as conn:
        existing = {row[1] for row in conn.execute(text("PRAGMA table_info(tasks)"))}
        for col, ddl_type in _NEW_TASK_COLUMNS.items():
            if col not in existing:
                conn.execute(text(f"ALTER TABLE tasks ADD COLUMN {col} {ddl_type}"))

        existing_msg = {row[1] for row in conn.execute(text("PRAGMA table_info(messages)"))}
        for col, ddl_type in _NEW_MESSAGE_COLUMNS.items():
            if col not in existing_msg:
                conn.execute(text(f"ALTER TABLE messages ADD COLUMN {col} {ddl_type}"))
        conn.commit()


def init_db():
    Base.metadata.create_all(bind=engine)
    _migrate(engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
