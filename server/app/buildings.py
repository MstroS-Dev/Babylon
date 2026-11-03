"""Buildings (console tabs), their floors and per-floor phase checklists."""
import json
import datetime
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, Form, HTTPException
from sqlalchemy.orm import Session

from .db import get_db
from .models import Building, BuildingFloorPlan, FloorPhase, Worker

router = APIRouter()

DEFAULT_PHASES = ["Structure", "Walls", "Electrical", "Plumbing", "Plaster", "Flooring", "Painting", "Final inspection"]
MAX_FLOORS = 60


def floors_of(b: Building) -> List[str]:
    try:
        return [str(x) for x in json.loads(b.floors_json or "[]")]
    except Exception:
        return []


def default_floor_labels(n: int) -> List[str]:
    return ["Ground"] + [str(i) for i in range(2, n + 1)] if n >= 1 else []


def clean_floors(raw) -> List[str]:
    out: List[str] = []
    for x in raw:
        s = " ".join(str(x).split())[:20]
        if s and s not in out:
            out.append(s)
    if not out:
        raise HTTPException(422, "A building needs at least one floor.")
    if len(out) > MAX_FLOORS:
        raise HTTPException(422, f"At most {MAX_FLOORS} floors.")
    return out


def default_building(db: Session) -> Building:
    b = db.query(Building).order_by(Building.position, Building.created_at).first()
    if b is None:
        raise HTTPException(500, "No building exists")
    return b


def resolve_building(db: Session, building_id: Optional[str]) -> Building:
    if not building_id:
        return default_building(db)
    b = db.get(Building, building_id)
    if not b:
        raise HTTPException(404, "Building not found")
    return b


def add_template_phases(db: Session, building_id: str, floor: str, titles: Optional[List[str]] = None):
    for i, t in enumerate(titles or DEFAULT_PHASES):
        db.add(FloorPhase(building_id=building_id, floor=floor, title=t, position=i))


def _building_json(db: Session, b: Building) -> dict:
    phases: Dict[str, dict] = {}
    for p in db.query(FloorPhase).filter(FloorPhase.building_id == b.id).all():
        d = phases.setdefault(p.floor, {"done": 0, "total": 0})
        d["total"] += 1
        d["done"] += 1 if p.done else 0
    return {"id": b.id, "name": b.name, "floors": floors_of(b), "position": b.position,
            "worker_count": db.query(Worker).filter(Worker.building_id == b.id).count(),
            "phases": phases}


@router.get("/buildings")
def list_buildings(db: Session = Depends(get_db)):
    return [_building_json(db, b) for b in db.query(Building).order_by(Building.position, Building.created_at)]


@router.post("/buildings")
def create_building(
    name: str = Form(...),
    floors: Optional[str] = Form(None),          # JSON list of labels, or
    floor_count: Optional[int] = Form(None),     # just a number: Ground, 2, 3...
    with_phases: bool = Form(True),
    db: Session = Depends(get_db),
):
    name = " ".join(name.split())[:40]
    if not name:
        raise HTTPException(422, "Give the building a name.")
    if floors:
        try:
            labels = clean_floors(json.loads(floors))
        except (ValueError, TypeError):
            raise HTTPException(422, "floors must be a JSON list")
    else:
        labels = clean_floors(default_floor_labels(max(1, min(floor_count or 1, MAX_FLOORS))))
    last = db.query(Building).count()
    b = Building(name=name, floors_json=json.dumps(labels), position=last)
    db.add(b)
    db.flush()
    if with_phases:
        for f in labels:
            add_template_phases(db, b.id, f)
    db.commit()
    return _building_json(db, b)


@router.put("/buildings/{building_id}")
def update_building(
    building_id: str,
    name: Optional[str] = Form(None),
    floors: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    b = resolve_building(db, building_id)
    if name is not None:
        n = " ".join(name.split())[:40]
        if not n:
            raise HTTPException(422, "Give the building a name.")
        b.name = n
    if floors is not None:
        try:
            labels = clean_floors(json.loads(floors))
        except (ValueError, TypeError):
            raise HTTPException(422, "floors must be a JSON list")
        old = floors_of(b)
        for gone in [f for f in old if f not in labels]:
            db.query(BuildingFloorPlan).filter(BuildingFloorPlan.building_id == b.id, BuildingFloorPlan.floor == gone).delete()
            db.query(FloorPhase).filter(FloorPhase.building_id == b.id, FloorPhase.floor == gone).delete()
        for new in [f for f in labels if f not in old]:
            add_template_phases(db, b.id, new)
        b.floors_json = json.dumps(labels)
    db.commit()
    return _building_json(db, b)


@router.delete("/buildings/{building_id}")
def delete_building(building_id: str, db: Session = Depends(get_db)):
    b = resolve_building(db, building_id)
    if db.query(Building).count() <= 1:
        raise HTTPException(409, "You can't delete the only building.")
    db.query(BuildingFloorPlan).filter(BuildingFloorPlan.building_id == b.id).delete()
    db.query(FloorPhase).filter(FloorPhase.building_id == b.id).delete()
    db.query(Worker).filter(Worker.building_id == b.id).update({Worker.building_id: None})   # back to "unassigned"
    db.delete(b)
    db.commit()
    return {"ok": True}


@router.put("/workers/{worker_id}/building")
def set_worker_building(worker_id: str, building_id: Optional[str] = Form(None), db: Session = Depends(get_db)):
    """Manager-only. A worker belongs to one building at a time; empty = unassigned."""
    w = db.get(Worker, worker_id)
    if not w:
        raise HTTPException(404, "Worker not found")
    if building_id:
        resolve_building(db, building_id)
    w.building_id = building_id or None
    db.commit()
    return {"id": w.id, "building_id": w.building_id}


# ---------------- phases ----------------
def _phase_json(p: FloorPhase) -> dict:
    return {"id": p.id, "floor": p.floor, "title": p.title, "done": p.done, "position": p.position,
            "done_at": p.done_at.isoformat() if p.done_at else None}


@router.get("/buildings/{building_id}/phases")
def list_phases(building_id: str, db: Session = Depends(get_db)):
    b = resolve_building(db, building_id)
    rows = db.query(FloorPhase).filter(FloorPhase.building_id == b.id).order_by(FloorPhase.position, FloorPhase.id).all()
    return [_phase_json(p) for p in rows]


@router.post("/buildings/{building_id}/phases")
def add_phase(building_id: str, floor: str = Form(...), title: str = Form(...), db: Session = Depends(get_db)):
    b = resolve_building(db, building_id)
    if floor not in floors_of(b):
        raise HTTPException(422, "That floor doesn't exist in this building.")
    t = " ".join(title.split())[:60]
    if not t:
        raise HTTPException(422, "Give the step a name.")
    pos = db.query(FloorPhase).filter(FloorPhase.building_id == b.id, FloorPhase.floor == floor).count()
    p = FloorPhase(building_id=b.id, floor=floor, title=t, position=pos)
    db.add(p)
    db.commit()
    return _phase_json(p)


@router.put("/phases/{phase_id}")
def update_phase(phase_id: str, done: Optional[bool] = Form(None), title: Optional[str] = Form(None),
                 db: Session = Depends(get_db)):
    p = db.get(FloorPhase, phase_id)
    if not p:
        raise HTTPException(404, "Step not found")
    if title is not None:
        t = " ".join(title.split())[:60]
        if t:
            p.title = t
    if done is not None and done != p.done:
        p.done = done
        p.done_at = datetime.datetime.utcnow() if done else None
    db.commit()
    return _phase_json(p)


@router.delete("/phases/{phase_id}")
def delete_phase(phase_id: str, db: Session = Depends(get_db)):
    p = db.get(FloorPhase, phase_id)
    if p:
        db.delete(p)
        db.commit()
    return {"ok": True}


@router.post("/buildings/{building_id}/phases/apply-template")
def apply_template(building_id: str, floor: str = Form(...), db: Session = Depends(get_db)):
    """Add the standard step list to a floor that has none."""
    b = resolve_building(db, building_id)
    if floor not in floors_of(b):
        raise HTTPException(422, "That floor doesn't exist in this building.")
    if db.query(FloorPhase).filter(FloorPhase.building_id == b.id, FloorPhase.floor == floor).count():
        raise HTTPException(409, "This floor already has steps.")
    add_template_phases(db, b.id, floor)
    db.commit()
    return {"ok": True}
