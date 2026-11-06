"""Professions (trades) the manager defines, each with an optional "what they're supposed to be doing" prompt."""
from typing import Optional

from fastapi import APIRouter, Depends, Form, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from .db import get_db
from .models import Profession, Worker

router = APIRouter()


def clean(s: Optional[str], n: int) -> Optional[str]:
    t = " ".join((s or "").split())
    return t[:n] or None


def find_profession(db: Session, text: Optional[str]) -> Optional[Profession]:
    """Match a typed trade against English or Hebrew names, case-insensitively."""
    t = (text or "").strip().lower()
    if not t:
        return None
    for p in db.query(Profession).all():
        if p.name.lower() == t or (p.name_he and p.name_he.strip().lower() == t):
            return p
    return None


def ensure_profession(db: Session, text: Optional[str]) -> Optional[Profession]:
    """Used when the manager types a trade on a worker card: reuse the match, or create the profession."""
    name = clean(text, 40)
    if not name:
        return None
    p = find_profession(db, name)
    if p is None:
        p = Profession(name=name)
        db.add(p)
        db.flush()
    return p


def _json(db: Session, p: Profession) -> dict:
    return {"id": p.id, "name": p.name, "name_he": p.name_he, "prompt": p.prompt,
            "worker_count": db.query(Worker).filter(Worker.trade == p.name).count()}


@router.get("/professions")
def list_professions(db: Session = Depends(get_db)):
    return [_json(db, p) for p in db.query(Profession).order_by(func.lower(Profession.name))]


@router.post("/professions")
def create_profession(name: str = Form(...), name_he: Optional[str] = Form(None), prompt: Optional[str] = Form(None),
                      db: Session = Depends(get_db)):
    n = clean(name, 40)
    if not n:
        raise HTTPException(422, "Give the profession a name.")
    if find_profession(db, n) or (clean(name_he, 40) and find_profession(db, clean(name_he, 40))):
        raise HTTPException(409, "A profession with this name already exists.")
    p = Profession(name=n, name_he=clean(name_he, 40), prompt=(prompt or "").strip()[:4000] or None)
    db.add(p)
    db.commit()
    return _json(db, p)


@router.put("/professions/{pid}")
def update_profession(pid: str, name: Optional[str] = Form(None), name_he: Optional[str] = Form(None),
                      prompt: Optional[str] = Form(None), db: Session = Depends(get_db)):
    p = db.get(Profession, pid)
    if not p:
        raise HTTPException(404, "Profession not found")
    if name is not None:
        n = clean(name, 40)
        if not n:
            raise HTTPException(422, "Give the profession a name.")
        other = find_profession(db, n)
        if other and other.id != p.id:
            raise HTTPException(409, "A profession with this name already exists.")
        if n != p.name:
            db.query(Worker).filter(Worker.trade == p.name).update({Worker.trade: n})   # workers follow the rename
            p.name = n
    if name_he is not None:
        he = clean(name_he, 40)
        other = find_profession(db, he) if he else None
        if other and other.id != p.id:
            raise HTTPException(409, "A profession with this name already exists.")
        p.name_he = he
    if prompt is not None:
        p.prompt = prompt.strip()[:4000] or None
    db.commit()
    return _json(db, p)


@router.delete("/professions/{pid}")
def delete_profession(pid: str, db: Session = Depends(get_db)):
    p = db.get(Profession, pid)
    if p:
        db.query(Worker).filter(Worker.trade == p.name).update({Worker.trade: None})
        db.delete(p)
        db.commit()
    return {"ok": True}


def profession_prompt_for(db: Session, worker) -> Optional[str]:
    """Guidance text of this worker's profession, if the manager wrote one (used as AI review context)."""
    p = find_profession(db, worker.trade) if worker is not None else None
    return p.prompt if p and p.prompt else None
