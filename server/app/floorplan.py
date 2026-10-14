"""Floor-plan import: CAD files -> clean per-floor wall JSON.

Accepts DXF (via ezdxf) and vector PDFs exported from CAD (via PyMuPDF).
DWG is a proprietary binary format and is NOT parsed; the manager exports/
converts it to DXF first (the API tells them so).

Pipeline
  1. extract_segments(): every straight line on every layer, in native units,
     in "plan coordinates" (x east, z south — same handedness as the console).
  2. build_plan():       pick layers -> convert to metres -> merge collinear
     pieces -> pair parallel outline lines into centerline+thickness walls ->
     centre on the origin.
The resulting plan JSON is what the console draws and what the wall-segment
picker snaps to.
"""
from __future__ import annotations

import hashlib
import io
import math
import os
import re
import shutil
import subprocess
import tempfile
from collections import OrderedDict
from typing import Any, Dict, List, Optional, Tuple

PLAN_VERSION = 1
MAX_WALLS = 400
MIN_SEG_M = 0.05           # ignore specks shorter than this
PT_TO_M = 0.0254 / 72.0    # PDF point -> metres on paper

# AutoCAD $INSUNITS code -> metres per unit
_INSUNITS_TO_M = {1: 0.0254, 2: 0.3048, 4: 0.001, 5: 0.01, 6: 1.0, 7: 1000.0}
_UNIT_NAMES = {"mm": 0.001, "cm": 0.01, "m": 1.0, "in": 0.0254, "ft": 0.3048}

_WALL_RE = re.compile(r"wall|קיר|a-wall|a_wall|mur|pared|wand|stene", re.I)
_NOT_WALL_RE = re.compile(r"door|window|furn|dim|text|anno|hatch|grid|axis|ceil|elec|plumb|"
                          r"דלת|חלון|ריהוט|מידות|טקסט", re.I)


class PlanError(ValueError):
    """User-facing problem with the uploaded file or options."""


# --------------------------------------------------------------------------
# 1. Extraction
# --------------------------------------------------------------------------
def detect_kind(filename: str, data: bytes) -> str:
    name = (filename or "").lower()
    if data[:4] == b"%PDF" or name.endswith(".pdf"):
        return "pdf"
    if name.endswith(".dwg") or (data[:2] == b"AC" and data[2:6].isdigit()):
        return "dwg"
    if name.endswith(".dxf") or data[:200].lstrip().startswith((b"0\r\nSECTION", b"0\nSECTION", b"  0", b"999")):
        return "dxf"
    raise PlanError("Unsupported file. Upload a .dwg, a .dxf or a vector .pdf exported from CAD.")


# --------------------------------------------------------------------------
# DWG -> DXF via LibreDWG's `dwg2dxf` (GPL; run as a separate program, not linked)
# --------------------------------------------------------------------------
_DWG_MISSING = ("This server can't read .dwg files yet (the converter isn't installed). "
                "Either upload a .dxf (CAD: Save As -> DXF), or on the server run: "
                "cd /opt/site-comms && ./tools/install-dwg-support.sh")


def dwg2dxf_path() -> Optional[str]:
    cands = [os.environ.get("DWG2DXF_BIN"),
             os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "bin", "dwg2dxf"),
             shutil.which("dwg2dxf")]
    for c in cands:
        if c and os.path.isfile(c) and os.access(c, os.X_OK):
            return c
    return None


def dwg_to_dxf(data: bytes, timeout: int = 240) -> bytes:
    exe = dwg2dxf_path()
    if not exe:
        raise PlanError(_DWG_MISSING)
    with tempfile.TemporaryDirectory() as d:
        src, dst = os.path.join(d, "in.dwg"), os.path.join(d, "out.dxf")
        with open(src, "wb") as f:
            f.write(data)
        try:
            proc = subprocess.run([exe, "-y", "-o", dst, src], capture_output=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            raise PlanError("Converting this DWG took too long. Export it as DXF from your CAD tool instead.")
        if not os.path.isfile(dst) or os.path.getsize(dst) < 500:
            tail = (proc.stderr or b"").decode("utf-8", "replace").strip().splitlines()[-1:] or ["no output"]
            raise PlanError("Couldn't convert this DWG (" + tail[0][:120] + "). "
                            "Export it as DXF from your CAD tool (Save As -> DXF) and upload that.")
        with open(dst, "rb") as f:
            return f.read()


_RAW_CACHE: "OrderedDict[str, Dict[str, Any]]" = OrderedDict()
_RAW_CACHE_MAX = 3


def extract_segments(filename: str, data: bytes, page: int = 0) -> Dict[str, Any]:
    """Parse once per distinct upload: the console re-requests a preview every time the manager
    toggles a layer or changes the scale, so the (slow) parse result is cached by content hash."""
    key = hashlib.sha256(data).hexdigest() + f":{page}"
    hit = _RAW_CACHE.get(key)
    if hit is not None:
        _RAW_CACHE.move_to_end(key)
        return hit
    kind = detect_kind(filename, data)
    origin = kind
    if kind == "dwg":
        raw = _extract_dxf(dwg_to_dxf(data))
    elif kind == "dxf":
        raw = _extract_dxf(data)
    else:
        raw = _extract_pdf(data, page)
    raw["origin"] = origin
    # ezdxf/PyMuPDF hand back numpy/own float types; keep everything plain Python
    raw["segments"] = [(str(l), float(a), float(b), float(c), float(d)) for l, a, b, c, d in raw["segments"]]
    _RAW_CACHE[key] = raw
    while len(_RAW_CACHE) > _RAW_CACHE_MAX:
        _RAW_CACHE.popitem(last=False)
    return raw


def _arc_points(cx, cy, r, a0, a1, n_max=16):
    """Polyline approximation of an arc given in degrees (CCW from a0 to a1)."""
    if a1 <= a0:
        a1 += 360.0
    sweep = a1 - a0
    n = max(2, min(n_max, int(sweep / 15) + 1))
    return [(cx + r * math.cos(math.radians(a0 + sweep * i / n)),
             cy + r * math.sin(math.radians(a0 + sweep * i / n))) for i in range(n + 1)]


def _extract_dxf(data: bytes) -> Dict[str, Any]:
    import ezdxf
    from ezdxf import recover

    with tempfile.NamedTemporaryFile(suffix=".dxf", delete=False) as tmp:
        tmp.write(data)
        path = tmp.name
    try:
        try:
            doc = ezdxf.readfile(path)
        except Exception:
            try:
                doc, _auditor = recover.readfile(path)
            except Exception as e:  # noqa: BLE001
                raise PlanError(f"Couldn't read this DXF file ({e.__class__.__name__}). "
                                "Try re-exporting it as a 2018 ASCII DXF.")
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass

    off_layers = set()
    for lay in doc.layers:
        try:
            if lay.is_off() or lay.is_frozen():
                off_layers.add(lay.dxf.name)
        except Exception:  # noqa: BLE001
            pass

    segs: List[Tuple[str, float, float, float, float]] = []   # layer,x1,z1,x2,z2 (z = -y)

    def add_poly(layer, pts, closed):
        n = len(pts)
        for i in range(n - 1):
            segs.append((layer, pts[i][0], -pts[i][1], pts[i + 1][0], -pts[i + 1][1]))
        if closed and n > 2:
            segs.append((layer, pts[-1][0], -pts[-1][1], pts[0][0], -pts[0][1]))

    def walk(entities, inherit_layer=None, depth=0):
        for e in entities:
            t = e.dxftype()
            layer = e.dxf.layer if e.dxf.hasattr("layer") else "0"
            if layer == "0" and inherit_layer:
                layer = inherit_layer
            try:
                if t == "LINE":
                    s, en = e.dxf.start, e.dxf.end
                    segs.append((layer, s.x, -s.y, en.x, -en.y))
                elif t == "LWPOLYLINE":
                    pts = [(p[0], p[1]) for p in e.get_points("xy")]
                    add_poly(layer, pts, e.closed)
                elif t == "POLYLINE" and not (e.is_3d_polyline or e.is_polygon_mesh or e.is_poly_face_mesh):
                    pts = [(v.dxf.location.x, v.dxf.location.y) for v in e.vertices]
                    add_poly(layer, pts, e.is_closed)
                elif t == "ARC":
                    c = e.dxf.center
                    add_poly(layer, _arc_points(c.x, c.y, e.dxf.radius, e.dxf.start_angle, e.dxf.end_angle), False)
                elif t == "INSERT" and depth < 3:
                    walk(e.virtual_entities(), inherit_layer=layer, depth=depth + 1)
            except Exception:  # noqa: BLE001 - one bad entity shouldn't sink the import
                continue

    walk(doc.modelspace())
    if not segs:
        raise PlanError("No lines found in this DXF's model space. Is the plan in a layout/paper-space tab? "
                        "Export from model space.")

    insunits = int(doc.header.get("$INSUNITS", 0) or 0)
    return {
        "kind": "dxf", "segments": segs, "off_layers": sorted(off_layers),
        "insunits": insunits, "page_count": 1, "group_hint": "layer",
    }


def _extract_pdf(data: bytes, page_no: int) -> Dict[str, Any]:
    import pymupdf

    try:
        doc = pymupdf.open(stream=data, filetype="pdf")
    except Exception as e:  # noqa: BLE001
        raise PlanError(f"Couldn't open this PDF ({e.__class__.__name__}).")
    if doc.page_count == 0:
        raise PlanError("This PDF has no pages.")
    page_no = max(0, min(page_no, doc.page_count - 1))
    page = doc[page_no]
    drawings = page.get_drawings()
    if not drawings:
        raise PlanError("No vector drawing found on this page. If this PDF is a scan/photo, "
                        "it can't be converted automatically — upload the DXF instead.")
    if len(drawings) > 600_000:
        raise PlanError("This PDF page is too complex to import. Export just the wall layer, or use DXF.")

    segs = []
    for d in drawings:
        col = d.get("color") or d.get("fill")
        if col:
            colour = "#%02x%02x%02x" % tuple(int(round(c * 255)) for c in col[:3])
        else:
            colour = "#000000"
        w = d.get("width") or 0
        layer = d.get("layer") or f"{colour} · {round(w, 2)}pt"
        for item in d["items"]:
            op = item[0]
            if op == "l":
                p1, p2 = item[1], item[2]
                segs.append((layer, p1.x, p1.y, p2.x, p2.y))
            elif op == "re":
                r = item[1]
                x0, y0, x1, y1 = r.x0, r.y0, r.x1, r.y1
                segs += [(layer, x0, y0, x1, y0), (layer, x1, y0, x1, y1),
                         (layer, x1, y1, x0, y1), (layer, x0, y1, x0, y0)]
            elif op == "qu":
                q = item[1]
                pts = [q.ul, q.ur, q.lr, q.ll]
                for i in range(4):
                    a, b = pts[i], pts[(i + 1) % 4]
                    segs.append((layer, a.x, a.y, b.x, b.y))
    if not segs:
        raise PlanError("This PDF page has only curves/fills, no straight lines to build walls from.")
    return {
        "kind": "pdf", "segments": segs, "off_layers": [], "insunits": 0,
        "page_count": doc.page_count, "page": page_no, "group_hint": "stroke style",
    }


# --------------------------------------------------------------------------
# Units
# --------------------------------------------------------------------------
def unit_factor(raw: Dict[str, Any], opts: Dict[str, Any]) -> Tuple[float, str]:
    """Metres per native unit, and a human description of how it was chosen."""
    if raw["kind"] == "pdf":
        denom = float(opts.get("scale") or 100)
        if denom <= 0:
            raise PlanError("Drawing scale must be positive (e.g. 100 for 1:100).")
        return PT_TO_M * denom, f"PDF at 1:{denom:g}"
    override = opts.get("units")
    if override:
        if override not in _UNIT_NAMES:
            raise PlanError(f"Unknown units '{override}'.")
        return _UNIT_NAMES[override], f"set to {override}"
    code = raw.get("insunits", 0)
    if code in _INSUNITS_TO_M:
        return _INSUNITS_TO_M[code], {1: "inches", 2: "feet", 4: "mm", 5: "cm", 6: "m", 7: "km"}[code] + " (from file)"
    # Unitless file: guess from the drawing's extent (buildings are tens of metres)
    xs = [v for s in raw["segments"] for v in (s[1], s[3])]
    zs = [v for s in raw["segments"] for v in (s[2], s[4])]
    ext = max(max(xs) - min(xs), max(zs) - min(zs))
    if ext > 2000:
        return 0.001, "mm (guessed from size)"
    if ext > 300:
        return 0.01, "cm (guessed from size)"
    return 1.0, "m (guessed from size)"


# --------------------------------------------------------------------------
# Layer summary
# --------------------------------------------------------------------------
def summarize_layers(raw: Dict[str, Any], factor: float) -> List[Dict[str, Any]]:
    agg: Dict[str, List[float]] = {}
    for layer, x1, z1, x2, z2 in raw["segments"]:
        a = agg.setdefault(layer, [0, 0.0])
        a[0] += 1
        a[1] += math.hypot(x2 - x1, z2 - z1) * factor
    out = [{"name": k, "count": int(v[0]), "length_m": round(v[1], 1),
            "off": k in raw["off_layers"]} for k, v in agg.items()]
    out.sort(key=lambda l: -l["length_m"])
    # preselect: layers that look like walls; else the single longest non-obvious-junk layer
    chosen = [l for l in out if _WALL_RE.search(l["name"]) and not l["off"]]
    if not chosen:
        cands = [l for l in out if not _NOT_WALL_RE.search(l["name"]) and not l["off"]]
        chosen = cands[:1]
    names = {l["name"] for l in chosen}
    for l in out:
        l["preselected"] = l["name"] in names
    return out


# --------------------------------------------------------------------------
# 2. Geometry cleanup
# --------------------------------------------------------------------------
def _dir_angle(dx: float, dz: float) -> float:
    """Direction angle folded into (-pi/2, pi/2] so a line and its reverse agree."""
    th = math.atan2(dz, dx)
    if th <= -math.pi / 2 + 1e-9:
        th += math.pi
    elif th > math.pi / 2 + 1e-9:
        th -= math.pi
    return th


def _group_lines(segs: List[Tuple[float, float, float, float]],
                 ang_tol=math.radians(0.6), off_tol=0.03, gap_tol=0.03) -> List[Dict[str, Any]]:
    """Merge collinear/overlapping pieces. Returns angle groups with lines as
    (offset, a, b) in the group's own (u along, n across) frame."""
    items = []
    for x1, z1, x2, z2 in segs:
        dx, dz = x2 - x1, z2 - z1
        if math.hypot(dx, dz) < MIN_SEG_M:
            continue
        items.append((_dir_angle(dx, dz), x1, z1, x2, z2))
    items.sort(key=lambda t: t[0])

    groups: List[List[Tuple]] = []
    for it in items:
        if groups and it[0] - groups[-1][0][0] <= ang_tol:
            groups[-1].append(it)
        else:
            groups.append([it])

    out = []
    for g in groups:
        # snap near-axis groups exactly onto the axis (CAD noise)
        th = sum(i[0] for i in g) / len(g)
        for axis in (0.0, math.pi / 2):
            if abs(th - axis) < math.radians(0.6):
                th = axis
        ux, uz = math.cos(th), math.sin(th)
        nx, nz = -uz, ux
        lines = []
        for _, x1, z1, x2, z2 in g:
            o = ((x1 + x2) / 2) * nx + ((z1 + z2) / 2) * nz
            a, b = sorted((x1 * ux + z1 * uz, x2 * ux + z2 * uz))
            lines.append([o, a, b])
        lines.sort(key=lambda l: l[0])
        # cluster by offset, then merge intervals in each cluster
        merged: List[List[float]] = []
        cluster: List[List[float]] = []
        for l in lines:
            if cluster and l[0] - cluster[0][0] > off_tol:
                merged += _merge_cluster(cluster, gap_tol)
                cluster = []
            cluster.append(l)
        if cluster:
            merged += _merge_cluster(cluster, gap_tol)
        out.append({"th": th, "u": (ux, uz), "n": (nx, nz), "lines": merged})
    return out


def _merge_cluster(cluster, gap_tol):
    o = sum(l[0] for l in cluster) / len(cluster)
    cluster = sorted(cluster, key=lambda l: l[1])
    res = []
    cur_a, cur_b = cluster[0][1], cluster[0][2]
    for _, a, b in cluster[1:]:
        if a <= cur_b + gap_tol:
            cur_b = max(cur_b, b)
        else:
            res.append([o, cur_a, cur_b])
            cur_a, cur_b = a, b
    res.append([o, cur_a, cur_b])
    return res


def _intersect(A: List[Tuple[float, float]], B: List[Tuple[float, float]], min_len: float):
    out = []
    for a0, a1 in A:
        for b0, b1 in B:
            s, e = max(a0, b0), min(a1, b1)
            if e - s >= min_len:
                out.append((s, e))
    return out


def _subtract(R: List[Tuple[float, float]], s: float, e: float):
    out = []
    for r0, r1 in R:
        if e <= r0 or s >= r1:
            out.append((r0, r1))
            continue
        if s > r0:
            out.append((r0, s))
        if e < r1:
            out.append((e, r1))
    return out


def _pair_walls(group: Dict[str, Any], t_min: float, t_max: float, min_overlap: float,
                keep_unpaired: bool, default_t: float, min_single: float) -> List[Dict[str, Any]]:
    """Pair parallel outline lines into centreline walls.

    Candidate pairs are taken longest-overlap first, so when a partition is drawn on top of
    a thicker wall (several parallel lines within a few cm) the long, consistent double line
    wins instead of a short spurious pair. Leftover single lines that lie inside an already
    found wall are discarded as duplicates.
    """
    lines = group["lines"]               # sorted by offset
    rem = [[(l[1], l[2])] for l in lines]
    cands = []
    for i in range(len(lines)):
        for j in range(i + 1, len(lines)):
            d = lines[j][0] - lines[i][0]
            if d > t_max:
                break
            if d < t_min:
                continue
            ov = _intersect(rem[i], rem[j], min_overlap)
            if ov:
                cands.append((sum(e - s for s, e in ov), i, j))
    cands.sort(key=lambda c: -c[0])

    walls = []
    for _, i, j in cands:
        d = lines[j][0] - lines[i][0]
        for s, e in _intersect(rem[i], rem[j], min_overlap):
            walls.append({"o": (lines[i][0] + lines[j][0]) / 2, "a": s, "b": e, "t": d})
            rem[i] = _subtract(rem[i], s, e)
            rem[j] = _subtract(rem[j], s, e)

    if keep_unpaired:
        for i, l in enumerate(lines):
            pieces = rem[i]
            for w in walls:                      # drop duplicates hiding inside a found wall
                if abs(l[0] - w["o"]) <= w["t"] / 2 + 0.02:
                    for s, e in [(w["a"], w["b"])]:
                        pieces = _subtract(pieces, s, e)
            for s, e in pieces:
                if e - s >= min_single:
                    walls.append({"o": l[0], "a": s, "b": e, "t": default_t})
    return walls


# --------------------------------------------------------------------------
# 3. Build the plan
# --------------------------------------------------------------------------
def build_plan(raw: Dict[str, Any], filename: str, opts: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    opts = opts or {}
    factor, unit_note = unit_factor(raw, opts)
    layers = summarize_layers(raw, factor)
    selected = opts.get("layers")
    if selected is None:
        selected = [l["name"] for l in layers if l["preselected"]]
    selected = set(selected)
    if not selected:
        raise PlanError("Pick at least one layer to build walls from.")

    segs = [(x1 * factor, z1 * factor, x2 * factor, z2 * factor)
            for layer, x1, z1, x2, z2 in raw["segments"] if layer in selected]
    if not segs:
        raise PlanError("The selected layers contain no lines.")

    warnings: List[str] = []
    merge_pairs = bool(opts.get("merge_pairs", True))
    default_t = float(opts.get("default_thickness", 0.15))

    groups = _group_lines(segs)
    walls_raw: List[Tuple[float, float, float, float, float]] = []
    for g in groups:
        if merge_pairs:
            ws = _pair_walls(g, t_min=0.05, t_max=float(opts.get("max_thickness", 0.5)),
                             min_overlap=0.3, keep_unpaired=True, default_t=default_t, min_single=0.5)
        else:
            ws = [{"o": l[0], "a": l[1], "b": l[2], "t": default_t} for l in g["lines"] if l[2] - l[1] >= 0.3]
        ux, uz = g["u"]
        nx, nz = g["n"]
        for w in ws:
            x1, z1 = w["a"] * ux + w["o"] * nx, w["a"] * uz + w["o"] * nz
            x2, z2 = w["b"] * ux + w["o"] * nx, w["b"] * uz + w["o"] * nz
            walls_raw.append((x1, z1, x2, z2, w["t"]))

    if not walls_raw:
        raise PlanError("No wall-length lines found on the selected layers.")
    if len(walls_raw) > MAX_WALLS:
        warnings.append(f"{len(walls_raw)} wall pieces found; keeping the {MAX_WALLS} longest. "
                        "Select fewer/cleaner layers for a better result.")
        walls_raw.sort(key=lambda w: -math.hypot(w[2] - w[0], w[3] - w[1]))
        walls_raw = walls_raw[:MAX_WALLS]

    xs = [v for w in walls_raw for v in (w[0], w[2])]
    zs = [v for w in walls_raw for v in (w[1], w[3])]
    cx, cz = (min(xs) + max(xs)) / 2, (min(zs) + max(zs)) / 2
    width, depth = max(xs) - min(xs), max(zs) - min(zs)
    if max(width, depth) > 250 or max(width, depth) < 4:
        warnings.append(f"Plan is {width:.1f} m × {depth:.1f} m — that looks unlikely for a building floor. "
                        "Check the units / drawing scale.")

    # stable numbering: top-to-bottom, then left-to-right (by wall midpoint)
    walls_raw.sort(key=lambda w: (round(((w[1] + w[3]) / 2 - cz) / 0.5), (w[0] + w[2]) / 2))
    walls = []
    for i, (x1, z1, x2, z2, t) in enumerate(walls_raw, 1):
        walls.append({"id": f"W{i}", "x1": round(x1 - cx, 3), "z1": round(z1 - cz, 3),
                      "x2": round(x2 - cx, 3), "z2": round(z2 - cz, 3), "t": round(t, 3)})

    return {
        "version": PLAN_VERSION,
        "units": "m",
        "source": {"type": raw.get("origin", raw["kind"]), "filename": filename, "layers": sorted(selected),
                   "units_note": unit_note, "page": raw.get("page", 0)},
        "bounds": {"w": round(width, 2), "d": round(depth, 2)},
        "walls": walls,
        "stats": {"walls": len(walls), "total_length_m": round(sum(
            math.hypot(w["x2"] - w["x1"], w["z2"] - w["z1"]) for w in walls), 1)},
        "warnings": warnings,
    }


def preview(filename: str, data: bytes, opts: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    opts = opts or {}
    raw = extract_segments(filename, data, int(opts.get("page", 0) or 0))
    factor, unit_note = unit_factor(raw, opts)
    layers = summarize_layers(raw, factor)
    plan, error = None, None
    try:
        plan = build_plan(raw, filename, opts)
    except PlanError as e:      # still return the layer list so the user can fix their selection
        error = str(e)
    return {"kind": raw["kind"], "page_count": raw["page_count"], "units_note": unit_note,
            "group_hint": raw["group_hint"], "layers": layers, "plan": plan, "error": error}
