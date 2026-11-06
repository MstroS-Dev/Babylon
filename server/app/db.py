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
    "wall_id": "VARCHAR",
    "seg_from": "INTEGER",
    "seg_to": "INTEGER",
    "workspace_json": "TEXT",
}

_NEW_MESSAGE_COLUMNS = {
    "task_id": "VARCHAR",
}

_NEW_WORKER_COLUMNS = {
    "checked_in": "BOOLEAN NOT NULL DEFAULT 0",
    "last_status_change": "DATETIME",
    "trade": "VARCHAR",
    "building_id": "VARCHAR",
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

        existing_worker = {row[1] for row in conn.execute(text("PRAGMA table_info(workers)"))}
        for col, ddl_type in _NEW_WORKER_COLUMNS.items():
            if col not in existing_worker:
                conn.execute(text(f"ALTER TABLE workers ADD COLUMN {col} {ddl_type}"))
        conn.commit()


DEFAULT_FLOORS = ["Ground", "2", "3", "4", "5"]


def _ensure_default_building():
    """First start after the buildings feature shipped: wrap everything that already exists
    (workers, saved floor plans) into one building so nothing disappears."""
    import json
    from .models import Building, BuildingFloorPlan, FloorPlan, Worker
    db = SessionLocal()
    try:
        if db.query(Building).count():
            return
        old_plans = db.query(FloorPlan).all()
        floors = list(DEFAULT_FLOORS)
        for p in old_plans:
            if p.floor not in floors:
                floors.append(p.floor)
        b = Building(name="Main building", floors_json=json.dumps(floors), position=0)
        db.add(b)
        db.flush()
        for p in old_plans:
            db.add(BuildingFloorPlan(building_id=b.id, floor=p.floor, plan_json=p.plan_json,
                                     source_name=p.source_name))
        db.query(Worker).filter(Worker.building_id.is_(None)).update({Worker.building_id: b.id})
        db.commit()
    finally:
        db.close()


DEFAULT_PROFESSIONS = [
    ("Foreman", "מנהל עבודה"), ("Engineer", "מהנדס"), ("Electrician", "חשמלאי"), ("Plumber", "אינסטלטור"),
    ("Carpenter", "נגר"), ("Mason", "בנאי"), ("Plasterer", "טייח"), ("Painter", "צבעי"), ("Tiler", "רצף"),
    ("Welder", "רתך"), ("HVAC", "טכנאי מיזוג"), ("Laborer", "פועל"),
]


def _ensure_professions():
    """Seed the usual trades (with Hebrew names) once, and make sure every trade a worker already has exists."""
    from .models import Profession, Worker
    db = SessionLocal()
    try:
        if db.query(Profession).count() == 0:
            for en, he in DEFAULT_PROFESSIONS:
                db.add(Profession(name=en, name_he=he))
            db.flush()
        known = {p.name.lower() for p in db.query(Profession).all()}
        for (t,) in db.query(Worker.trade).filter(Worker.trade.isnot(None)).distinct().all():
            if t and t.lower() not in known:
                db.add(Profession(name=t))
                known.add(t.lower())
        db.commit()
    finally:
        db.close()


def init_db():
    Base.metadata.create_all(bind=engine)
    _migrate(engine)
    _ensure_default_building()
    _ensure_professions()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
