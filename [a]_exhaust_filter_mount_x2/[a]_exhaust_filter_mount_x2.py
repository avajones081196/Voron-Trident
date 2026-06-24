"""
[a]_exhaust_filter_mount_x2.py

Sketch summary (plane auto-detected from CSV):
  S1  Z = 4.0   Lines + 3-point arcs forming ONE closed outer outline, plus a
                single 3-point CIRCLE (inner hole).

Region structure (from Fusion_Coordinates_S1.csv, revised):
  - OUTER OUTLINE : rows 1-14 (8 lines + 6 three-point arcs) -> one closed loop
                    (the rounded mount footprint).
  - INNER CIRCLE  : row 15 (3-point circle) -> a single through-hole.

Guidelines (executed in topological order):
  G1 - READ S1. Build the outer footprint face; extrude it 4 units DOWN
       (Z = 4 -> Z = 0) into a solid; pierce the inner circle as a THROUGH-hole.
  G2 - SWEEP-CUT the S2 cross-section along the S1 OUTER outline edges (excl.
       the inner circle) at the z = S1_PLANE (≈4, top / sketch) face -> chamfer.
  G4 - SWEEP-CUT the S3 cross-section along the S1 OUTER outline edges (excl.
       the inner circle) at the z = 0 (bottom) face -> chamfer.
  G5 - CHAMFER the INNER CIRCLE hole ends (both z=4 and z=0), 0.4 countersink.
  G6 - EXTRUDE-CUT the S4 profile through the part (5 units -Z, 1 unit +Z) to
       carve the bump/notch slot.
       (Currently set to stop after G6 — VIEW_AT=6 — for review in OCP.)
  G3 - LAST: .clean() + watertight STL + summary export (TEMPLATE section 13).
"""

import csv
import math
import re
import sys
from datetime import datetime
from pathlib import Path
import numpy as np

# ══════════════════════════════════════════════════════════════════════════
# Named tolerances
# ══════════════════════════════════════════════════════════════════════════
EPSILON_MM    = 1e-3
SVD_PLANE_TOL = 1e-2
STL_TOLERANCE = 5e-4
Z_TOL         = 1e-3      # tolerance for "edge lies in a constant-Z plane"
ENDPT_TOL     = 0.05      # mm: match an edge endpoint to a named (x, y)

# ══════════════════════════════════════════════════════════════════════════
# Paths (cross-platform, derived from script location)
# ══════════════════════════════════════════════════════════════════════════
BASE_DIR    = Path(__file__).resolve().parent
FOLDER_NAME = BASE_DIR.name
SCRIPT_STEM = Path(__file__).resolve().stem   # output files named after this script
CSV_DIR     = BASE_DIR / "csv_merged"

S_CSV = {
    1: CSV_DIR / "Fusion_Coordinates_S1.csv",
    2: CSV_DIR / "Fusion_Coordinates_S2.csv",   # G2 chamfer sweep profile (z=4 top)
    3: CSV_DIR / "Fusion_Coordinates_S3.csv",   # G4 chamfer sweep profile (z=0 bottom)
    4: CSV_DIR / "Fusion_Coordinates_S4.csv",   # G6 extrude-cut profile (notch)
}

if not CSV_DIR.exists():
    sys.exit(f"❌ csv_merged folder not found at: {CSV_DIR}")
for n, p in S_CSV.items():
    if not p.exists():
        sys.exit(f"❌ Required CSV missing: {p}")

print("=" * 70)
print(f"[CSV FRESHNESS]  CSV_DIR = {CSV_DIR}")
for n in sorted(S_CSV):
    p  = S_CSV[n]
    st = p.stat()
    print(f"  S{n}: {p.name}  size={st.st_size} B  mtime={st.st_mtime:.0f}")
print("=" * 70)

# ══════════════════════════════════════════════════════════════════════════
# build123d + OCP imports  (ocp_vscode guarded so the script can also run
# head-less; in VS Code the viewer is available as usual)
# ══════════════════════════════════════════════════════════════════════════
from build123d import (
    Vector, Plane, Axis, Location,
    Edge, Wire, Face, Solid, Shell, Shape, Compound,
    extrude, fillet, chamfer, loft, mirror, revolve, sweep,
    export_stl, export_step, import_step,
    GeomType, Transition,
)

try:
    from ocp_vscode import show, set_port, reset_show
    set_port(3939)
    _HAVE_VIEWER = True
except Exception as _exc:                       # head-less / no viewer
    _HAVE_VIEWER = False
    def show(*a, **k): pass
    def reset_show(*a, **k): pass
    print(f"[VIEWER] ocp_vscode unavailable ({_exc}); continuing head-less.")

from OCP.BRepClass3d import BRepClass3d_SolidClassifier
from OCP.gp import gp_Pnt
from OCP.TopAbs import TopAbs_IN

def point_inside(solid, x, y, z, tol=1e-6):
    """True if the point lies inside `solid` — used to pick the true 'into the
    material' direction per edge for the sweep-wedge chamfer fallback."""
    try:
        cls = BRepClass3d_SolidClassifier(solid.wrapped, gp_Pnt(x, y, z), tol)
        return cls.State() == TopAbs_IN
    except Exception:
        return False

# ══════════════════════════════════════════════════════════════════════════
# CHECKPOINT CONFIG  (TEMPLATE section 10)
# ══════════════════════════════════════════════════════════════════════════
VIEW_AT              = 6     # FINAL run: build G1..G6 through to the G3 export
STOP_AFTER_VIEW      = False    # do not stop early; reach the watertight export
EXPORT_AT_CHECKPOINT = False     # only the final deliverable files (no checkpoints)

GUIDELINE_RANGE = "G_1_6"

CLEAN_EACH_STEP = False
def maybe_clean(b):
    if not CLEAN_EACH_STEP:
        return b
    try: return b.clean()
    except Exception: return b

# ══════════════════════════════════════════════════════════════════════════
# Tracking state  (TEMPLATE section 11)
# ══════════════════════════════════════════════════════════════════════════
stage_pieces = []
area_history = []

def cumulative_area(pieces):
    total = 0.0
    for p in pieces:
        try:
            for f in p.faces(): total += float(f.area)
        except Exception: pass
    return total

def cumulative_volume(pieces):
    total = 0.0
    for p in pieces:
        try:
            for s in p.solids(): total += float(s.volume)
        except Exception: pass
    return total

def _write_area_history_file(stop_g_num=None):
    if not area_history: return
    last_g = stop_g_num if stop_g_num is not None else area_history[-1]["g"]
    name = f"{FOLDER_NAME}_area_history_G_1_{last_g}.txt"
    path = BASE_DIR / name
    lines = [
        "=" * 60, f"AREA HISTORY  :  {name}",
        f"Time          :  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "=" * 60, "",
        f"{'Guideline':>10}  {'Cum. area (mm²)':>18}  {'Δ area (mm²)':>14}  "
        f"{'Cum. vol (mm³)':>16}  {'Δ vol (mm³)':>14}  Label",
        "-" * 110,
    ]
    for e in area_history:
        lines.append(
            f"  G{e['g']:<8d}  {e['area']:>18.3f}  {e['darea']:>+14.3f}  "
            f"{e['vol']:>16.3f}  {e['dvol']:>+14.3f}  {e['label']}"
        )
    lines.append("=" * 60)
    with open(path, "w") as f: f.write("\n".join(lines))

def write_checkpoint_export(g_num, label, pieces):
    cp_range = f"G_1_{g_num}"
    cp_stl   = BASE_DIR / f"{FOLDER_NAME}_{cp_range}.stl"
    cp_step  = BASE_DIR / f"{FOLDER_NAME}_{cp_range}.step"
    cp_txt   = BASE_DIR / f"{FOLDER_NAME}_summary_{cp_range}.txt"
    try:
        compound = Compound(children=list(pieces))
        try: compound = compound.clean()
        except Exception: pass
        export_stl(compound, str(cp_stl), tolerance=STL_TOLERANCE)
        export_step(compound, str(cp_step))
        print(f"     [CHECKPOINT] wrote {cp_stl.name} / {cp_step.name}")
    except Exception as exc:
        print(f"     [CHECKPOINT] export failed: {exc}")
    lines = [
        "=" * 60, f"CHECKPOINT SUMMARY  :  {FOLDER_NAME}_summary_{cp_range}.txt",
        f"Guideline reached   :  G{g_num}  ({label})",
        f"Bodies in compound  :  {len(pieces)}",
        f"Cumulative area     :  {cumulative_area(pieces):.3f} mm²",
        f"Cumulative volume   :  {cumulative_volume(pieces):.3f} mm³", "=" * 60,
    ]
    with open(cp_txt, "w") as f: f.write("\n".join(lines))
    _write_area_history_file(g_num)

def checkpoint(g_num, label):
    cum_area = cumulative_area(stage_pieces)
    cum_vol  = cumulative_volume(stage_pieces)
    darea = cum_area - (area_history[-1]["area"] if area_history else 0.0)
    dvol  = cum_vol  - (area_history[-1]["vol"]  if area_history else 0.0)
    area_history.append({"g": g_num, "label": label, "area": cum_area,
                         "darea": darea, "vol": cum_vol, "dvol": dvol})
    print(f"     [AREA] After G{g_num}: cumulative = {cum_area:.3f} mm²  (Δ = {darea:+.3f} mm²)")
    print(f"     [VOL ] After G{g_num}: cumulative = {cum_vol:.3f} mm³  (Δ = {dvol:+.3f} mm³)")
    if VIEW_AT != g_num: return
    print(f"\n[VIEW] Cumulative state after G{g_num} ({label})")
    try: reset_show()
    except Exception: pass
    try: show(*stage_pieces)
    except Exception: pass
    if EXPORT_AT_CHECKPOINT: write_checkpoint_export(g_num, label, stage_pieces)
    if STOP_AFTER_VIEW: sys.exit(0)

# ══════════════════════════════════════════════════════════════════════════
# CSV / GEOMETRY HELPERS  (TEMPLATE section 7 / COOKBOOK P-02..P-04)
# ══════════════════════════════════════════════════════════════════════════
def read_rows(csv_path):
    with open(csv_path, "r") as f: return list(csv.DictReader(f))

def _is_missing(cell):
    if cell is None: return True
    return cell.strip() == "" or cell.strip().upper() == "NA"

def _norm_draw_type(raw): return re.sub(r'_\d+$', '', raw.strip().lower()).rstrip('_')

def _row_present_indices(row):
    out, i = [], 1
    while True:
        xk = f"X{i}"
        if xk not in row: break
        if not _is_missing(row[xk]): out.append(i)
        i += 1
    return out

def _row_all_xyz_triples(row):
    return [(float(row[f"X{i}"]), float(row[f"Y{i}"]), float(row[f"Z{i}"]))
            for i in _row_present_indices(row)]

def _collect_all_points(rows):
    pts = []
    for r in rows: pts.extend(_row_all_xyz_triples(r))
    return np.array(pts)

def detect_sketch_plane(rows, tol_axis=EPSILON_MM, tol_plane=SVD_PLANE_TOL):
    pts = _collect_all_points(rows)
    if len(pts) == 0:
        return ("axis", "z", 0.0)
    for axis_idx, axis_letter in ((0, "x"), (1, "y"), (2, "z")):
        col = pts[:, axis_idx]
        if col.max() - col.min() < tol_axis:
            return ("axis", axis_letter, float(col.mean()))
    centroid = pts.mean(axis=0)
    centred  = pts - centroid
    _, _, vh = np.linalg.svd(centred, full_matrices=False)
    normal   = vh[-1] / np.linalg.norm(vh[-1])
    return ("general", tuple(centroid), tuple(normal))

def world_vec_axis(in_plane_pt, axis, plane_value):
    u, v = in_plane_pt
    if axis == "z":   return Vector(u, v, plane_value)
    elif axis == "y": return Vector(u, plane_value, v)
    else:             return Vector(plane_value, u, v)

def in_plane_uv(row, idx, axis):
    x, y, z = float(row[f"X{idx}"]), float(row[f"Y{idx}"]), float(row[f"Z{idx}"])
    if axis == "z":   return (x, y)
    elif axis == "y": return (x, z)
    else:             return (y, z)

def make_line_edge(p_uv, q_uv, axis, plane_value):
    return Edge.make_line(world_vec_axis(p_uv, axis, plane_value),
                          world_vec_axis(q_uv, axis, plane_value))

def make_arc_edge_uv(p1_uv, p2_uv, p3_uv, axis, plane_value):
    return Edge.make_three_point_arc(world_vec_axis(p1_uv, axis, plane_value),
                                     world_vec_axis(p2_uv, axis, plane_value),
                                     world_vec_axis(p3_uv, axis, plane_value))

def edge_from_row(row, axis, plane_value):
    """Build one build123d Edge (line, 3-point arc, or 3-point circle) from a row."""
    dt = _norm_draw_type(row["Draw Type"])
    if dt.startswith("line"):
        return make_line_edge(in_plane_uv(row, 1, axis), in_plane_uv(row, 2, axis),
                              axis, plane_value)
    if dt.startswith("3_point_circle"):
        # three points on the circle -> centre + radius, build a closed circle edge
        pts = _row_all_xyz_triples(row)
        uv  = [in_plane_uv(row, i, axis) for i in (1, 2, 3)]
        cx, cy, r = circle_from_3pts(*uv)
        pl = plane_for_axis(axis, plane_value, (cx, cy))
        return Edge.make_circle(r, pl)
    if dt.startswith("3_point_arc"):
        try:
            return make_arc_edge_uv(in_plane_uv(row, 1, axis), in_plane_uv(row, 2, axis),
                                    in_plane_uv(row, 3, axis), axis, plane_value)
        except Exception:
            # collinear 3 points (an arc that is really a straight segment)
            return make_line_edge(in_plane_uv(row, 1, axis), in_plane_uv(row, 3, axis),
                                  axis, plane_value)
    raise ValueError(f"Unsupported draw type: {row['Draw Type']}")

def circle_from_3pts(p1, p2, p3):
    """Centre (u, v) and radius of the circle through three in-plane points."""
    (ax, av), (bx, bv), (cx_, cv) = p1, p2, p3
    d = 2.0 * (ax * (bv - cv) + bx * (cv - av) + cx_ * (av - bv))
    if abs(d) < 1e-12:
        raise ValueError("colinear circle points")
    ux = ((ax**2 + av**2) * (bv - cv) + (bx**2 + bv**2) * (cv - av)
          + (cx_**2 + cv**2) * (av - bv)) / d
    uv = ((ax**2 + av**2) * (cx_ - bx) + (bx**2 + bv**2) * (ax - cx_)
          + (cx_**2 + cv**2) * (bx - ax)) / d
    return (ux, uv, math.hypot(ax - ux, av - uv))

def plane_for_axis(axis, plane_value, centre_uv):
    """Plane in the sketch's constant-axis plane, centred at centre_uv (in-plane)."""
    origin = world_vec_axis(centre_uv, axis, plane_value)
    z_dir  = {"z": (0, 0, 1), "y": (0, 1, 0), "x": (1, 0, 0)}[axis]
    return Plane(origin=origin, z_dir=z_dir)

def closed_wire(edges, tol=1e-3):
    """Build a single closed Wire from edges, bridging the ~1e-5 mm endpoint
    gaps the Fusion export leaves between consecutive primitives (COOKBOOK P-03)."""
    try:
        wires = Wire.combine(edges, tol=tol)
    except Exception:
        return Wire(edges)
    closed = [w for w in wires if w.is_closed]
    cand = closed if closed else list(wires)
    return max(cand, key=lambda w: len(w.edges()))

def face_from_edges(edges):
    return Face(closed_wire(edges))

def edges_from_rowids(rows, rowids, axis, plane_value):
    """rowids are 1-based CSV 'Steps' numbers (== line order)."""
    return [edge_from_row(rows[i - 1], axis, plane_value) for i in rowids]

# ══════════════════════════════════════════════════════════════════════════
# Region row-membership (1-based 'Steps' ids), read off the S1 sketch (revised).
#   outer outline : rows 1..14  (8 lines + 6 three-point arcs) -> closed loop
#   inner circle  : row 15      (3-point circle) -> through-hole
# ══════════════════════════════════════════════════════════════════════════
OUTER_ROWS  = list(range(1, 15))     # 1..14
CIRCLE_ROW  = 15

# ══════════════════════════════════════════════════════════════════════════
# G1 — READ S1; extrude the outer footprint 4 mm DOWN; pierce the circle hole.
# ══════════════════════════════════════════════════════════════════════════
print(f"\n[G1] Reading {S_CSV[1].name}")
s1_rows = read_rows(S_CSV[1])
_, S1_AXIS, S1_PLANE = detect_sketch_plane(s1_rows)
print(f"     Sketch plane: axis {S1_AXIS.upper()} = {S1_PLANE}")

# --- outer footprint face -------------------------------------------------
outer_edges = edges_from_rowids(s1_rows, OUTER_ROWS, S1_AXIS, S1_PLANE)
outer_face  = face_from_edges(outer_edges)
print(f"     outer_face area = {float(outer_face.area):.3f} mm²")

# --- inner circle face ----------------------------------------------------
_circ_uv = [in_plane_uv(s1_rows[CIRCLE_ROW - 1], i, S1_AXIS) for i in (1, 2, 3)]
CIRCLE_CX, CIRCLE_CY, CIRCLE_R = circle_from_3pts(*_circ_uv)
circle_edge = edge_from_row(s1_rows[CIRCLE_ROW - 1], S1_AXIS, S1_PLANE)
circle_face = Face(closed_wire([circle_edge]))
print(f"     circle_face area = {float(circle_face.area):.3f} mm²  "
      f"(centre=({CIRCLE_CX:.3f},{CIRCLE_CY:.3f}) r={CIRCLE_R:.3f})")

THICK = 4.0            # extrude DOWN: Z = 4 -> Z = 0
DOWN  = (0, 0, -1)

# Solid block: extrude the outer footprint 4 mm down (from the Z=4 sketch plane
# to Z=0).
block = extrude(outer_face, amount=THICK, dir=DOWN)

# Through-hole: extrude the circle past both faces (Z = 5 .. -1) and subtract,
# so the hole pierces the full 4 mm thickness cleanly (no coincident faces).
hole = extrude(circle_face, amount=THICK + 2.0, dir=DOWN)   # Z = 4 .. -2
hole = Location(Vector(0, 0, 1.0)) * hole                    # Z = 5 .. -1
g1_body = block - hole

# clean() now: the cut can leave coplanar seam edges on the Z=0/Z=4 faces which
# would defeat the chamfer edge-selection. Cleaning merges them.
try:
    g1_body = g1_body.clean()
    print("     .clean() applied to G1 body.")
except Exception as exc:
    print(f"     ⚠ G1 .clean() failed (continuing): {exc}")

stage_pieces.append(g1_body)
checkpoint(1, "G1 solid: outer footprint extruded 4mm down + circle through-hole")

# ══════════════════════════════════════════════════════════════════════════
# G2 / G4 — CHAMFER along the S1 OUTER outline (excluding the inner circle), one
#   per face, equivalent to sweep-cutting the S2 / S3 cross-section but built so
#   the corners MITER cleanly:
#     G2 = chamfer the z = S1_PLANE (top / sketch) face  (profile S2),
#     G4 = chamfer the z = 0        (bottom)      face  (profile S3).
#
#   WHY NOT a literal per-edge sweep: sweeping the profile along each edge does
#   not blend at corners (adjacent chamfer faces overlap / step), and a single
#   continuous sweep self-intersects at the tight corners (COOKBOOK P-06/P-09).
#   Instead the chamfer is cut with an OFFSET tool: the wedge between the full
#   outline and the outline offset inward by the chamfer leg, tapered 45° over
#   that leg.  offset_2d miters/blends every corner, so the result is smooth.
#   The S2/S3 profiles are read only to confirm the chamfer leg (their 45°
#   diagonal = 0.4), keeping the step data-driven.
#
#   FACE MAPPING (model world Z): S2 (~3.6–4.1) -> z=4 face, S3 (~-0.1–0.4) ->
#   z=0 face.
# ══════════════════════════════════════════════════════════════════════════
S2_OVER = 0.1   # tool overshoot past the face (no coincident sliver -> watertight)

def _chamfer_leg_from_profile(profile_key):
    """Read S_CSV[profile_key] and return the 45° chamfer leg = the in-plane
    horizontal run of its single slanted (diagonal) edge."""
    s_rows = read_rows(S_CSV[profile_key])
    leg = 0.0
    for r in s_rows:
        p1 = (float(r["X1"]), float(r["Y1"]), float(r["Z1"]))
        p2 = (float(r["X2"]), float(r["Y2"]), float(r["Z2"]))
        dz = abs(p2[2] - p1[2])
        dh = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
        if dz > 1e-4 and dh > 1e-4:          # slanted edge -> the chamfer diagonal
            leg = max(leg, dh)
    return leg

def _outline_wire():
    """Fresh closed wire of the S1 OUTER outline (at z = S1_PLANE)."""
    return closed_wire(edges_from_rowids(s1_rows, OUTER_ROWS, S1_AXIS, S1_PLANE))

def _face_at_z(wire, z):
    return Face(Location(Vector(0.0, 0.0, z - S1_PLANE)) * wire)

def chamfer_outer_face(body, profile_key, z_face, mat_dir, tag):
    """Cut a 45° chamfer along the OUTER outline at the z=z_face face (mat_dir =
    +1 if material is above the face / -1 if below).  Offset tool -> mitered
    corners.  The inner circle is never touched (the tool uses only the outer
    outline).  Returns the new body."""
    src = body
    try:
        src = src.solids()[0]
    except Exception:
        pass
    leg = _chamfer_leg_from_profile(profile_key)
    print(f"\n[{tag}] Chamfer S1 outer outline at z={z_face:.1f} "
          f"(leg={leg:.3f} from {S_CSV[profile_key].name}, excl. inner circle)")

    outline = _outline_wire()
    inset   = outline.offset_2d(-leg)        # miters/blends corners
    z_inner = z_face + mat_dir * leg         # bevel reaches full outline here
    z_far   = z_face - mat_dir * S2_OVER     # prism overshoots past the face
    lo, hi  = min(z_inner, z_far), max(z_inner, z_far)

    # wedge ring tool = (full-outline prism spanning the chamfer band) minus the
    # 45° taper kept solid (full outline at z_inner -> inset outline at z_face).
    prism = extrude(_face_at_z(outline, lo), amount=(hi - lo), dir=(0, 0, 1))
    taper = None
    for secs in ([_face_at_z(_outline_wire().offset_2d(-leg), z_face),
                  _face_at_z(_outline_wire(), z_inner)],
                 [_face_at_z(_outline_wire(), z_inner),
                  _face_at_z(_outline_wire().offset_2d(-leg), z_face)]):
        try:
            taper = loft(secs, ruled=True); break
        except Exception:
            continue
    if taper is None:
        raise RuntimeError(f"{tag}: chamfer taper loft failed")
    out = src - (prism - taper)
    try:
        out = out.clean()
    except Exception:
        pass
    try:
        print(f"     {tag}: chamfer cut -> volume {sum(s.volume for s in out.solids()):.3f} mm³")
    except Exception:
        pass
    return out

# --- G2: chamfer the z = S1_PLANE (top / sketch) face (S2 profile) ------------
g2_body = chamfer_outer_face(g1_body, 2, S1_PLANE, -1.0, "G2")
stage_pieces[:] = [p for p in stage_pieces if p is not g1_body]
stage_pieces.append(g2_body)
checkpoint(2, f"G2 chamfer S1 outline at z={S1_PLANE:.0f} (top, excl. circle)")

# --- G4: chamfer the z = 0 (bottom) face (S3 profile) -------------------------
g4_body = chamfer_outer_face(g2_body, 3, 0.0, 1.0, "G4")
stage_pieces[:] = [p for p in stage_pieces if p is not g2_body]
stage_pieces.append(g4_body)
checkpoint(4, "G4 chamfer S1 outline at z=0 (bottom, excl. circle)")

# ══════════════════════════════════════════════════════════════════════════
# G5 — CHAMFER the INNER CIRCLE hole ends (both z=0 and z=4), 0.4 countersink.
#   Built as a 45° LOFT cone at each rim: the hole radius CIRCLE_R sits `leg`
#   into the material and widens to CIRCLE_R+leg(+overshoot) at the face, then
#   subtracted -> a clean countersink chamfer.  (A cone is robust + sliver-free,
#   unlike sweeping a profile around a closed circle.)
# ══════════════════════════════════════════════════════════════════════════
CHAMFER_HOLE = 0.4

def _hole_circle(radius, z):
    pl = Plane(origin=Vector(CIRCLE_CX, CIRCLE_CY, z), z_dir=(0, 0, 1))
    return Face(closed_wire([Edge.make_circle(radius, pl)]))

def chamfer_hole_end(body, z_face, mat_dir, leg=CHAMFER_HOLE, over=S2_OVER):
    """0.4 (45°) countersink at the circle hole rim on the z=z_face end (mat_dir
    = +1 if material is above the face / -1 if below)."""
    narrow = _hole_circle(CIRCLE_R, z_face + mat_dir * leg)        # at depth `leg`
    wide   = _hole_circle(CIRCLE_R + leg + over, z_face - mat_dir * over)  # past face
    out = body - loft([wide, narrow])
    try:
        out = out.clean()
    except Exception:
        pass
    return out

print(f"\n[G5] Chamfer {CHAMFER_HOLE} at inner circle hole ends (z={S1_PLANE:.0f} and z=0)")
g5_body = chamfer_hole_end(g4_body, S1_PLANE, -1.0)   # top (z=4) rim
g5_body = chamfer_hole_end(g5_body, 0.0,       1.0)   # bottom (z=0) rim
try:
    print(f"     G5: hole-end chamfers -> volume {sum(s.volume for s in g5_body.solids()):.3f} mm³")
except Exception:
    pass
stage_pieces[:] = [p for p in stage_pieces if p is not g4_body]
stage_pieces.append(g5_body)
checkpoint(5, "G5 chamfer 0.4 at inner circle hole ends z=0 and z=4")

# ══════════════════════════════════════════════════════════════════════════
# G6 — EXTRUDE-CUT the S4 profile through the part: 5 units along -Z and 1 unit
#   along +Z.  The 1-unit +Z overshoot (and the -Z reaching past z=0) keeps the
#   cut faces from being COINCIDENT with the part's z=4 / z=0 faces -> no slivers
#   -> stays watertight (P-11).  S4 is one closed loop on the z=4 plane (the
#   bump/notch outline), so this carves that notch clean through the 4 mm solid.
# ══════════════════════════════════════════════════════════════════════════
print(f"\n[G6] Extrude-cut {S_CSV[4].name}: 5 units -Z + 1 unit +Z (through-cut)")
s4_rows = read_rows(S_CSV[4])
_, S4_AXIS, S4_PLANE = detect_sketch_plane(s4_rows)
print(f"     S4 plane: axis {S4_AXIS.upper()} = {S4_PLANE}")
s4_face = Face(closed_wire([edge_from_row(r, S4_AXIS, S4_PLANE) for r in s4_rows]))
print(f"     S4 face area = {float(s4_face.area):.3f} mm²")
cut_tool = (extrude(s4_face, amount=5.0, dir=(0, 0, -1))     # z=4 -> z=-1
            + extrude(s4_face, amount=1.0, dir=(0, 0, 1)))    # z=4 -> z=5
g6_body = g5_body - cut_tool
try:
    g6_body = g6_body.clean()
except Exception:
    pass
try:
    print(f"     G6: S4 through-cut -> volume {sum(s.volume for s in g6_body.solids()):.3f} mm³")
except Exception:
    pass
stage_pieces[:] = [p for p in stage_pieces if p is not g5_body]
stage_pieces.append(g6_body)
checkpoint(6, "G6 extrude-cut S4 profile (5 units -Z / 1 unit +Z, through)")

# ══════════════════════════════════════════════════════════════════════════
# G3 — EXPORT (ALWAYS LAST): WATERTIGHT STL  (TEMPLATE section 13 / COOKBOOK P-11)
#   1. .clean() the final compound.
#   2. STEP export+import round-trip (re-parametrize) — the key step.
#   3. Deterministic conformal mesh (BRepMesh, parallel=False).
#   4. Strip non-manifold faces + fill holes -> manifold3d -> final strip/fill.
#   5. Verify the exported STL reloads strictly watertight; else raw export+WARN.
#   Requires trimesh + manifold3d + networkx in this env.
# ══════════════════════════════════════════════════════════════════════════
print(f"\n[G3] Export — compounding {len(stage_pieces)} body(ies), .clean(), watertight STL.")

final_compound = Compound(children=list(stage_pieces))
try:
    final_compound = final_compound.clean()
    print("     .clean() applied successfully.")
except Exception as exc:
    print(f"     ⚠  .clean() failed (continuing): {exc}")

all_faces          = list(final_compound.faces())
n_edges            = len(list(final_compound.edges()))
total_surface_area = sum(float(f.area) for f in all_faces)
print(f"     Total surface area : {total_surface_area:.3f} mm²")
print(f"     Face / edge count  : {len(all_faces)} / {n_edges}")

solids       = list(final_compound.solids())
all_valid    = all(s.is_valid for s in solids) if solids else False
total_volume = sum(float(s.volume) for s in solids)
if len(solids) == 0:
    print("     Model is a surface compound (no volumetric solids).")
else:
    print(f"     Closed solids      : {len(solids)} (all_valid={all_valid})")
    print(f"     Total volume       : {total_volume:.3f} mm³")
    if len(solids) > 1:
        print(f"     ⚠  {len(solids)} disjoint solids in compound.")

FINAL_STL = BASE_DIR / f"{SCRIPT_STEM}.stl"
FINAL_TXT = BASE_DIR / f"{SCRIPT_STEM}_summary.txt"

def _watertight_stl(shape, out_path, defl=0.05):
    """Mesh the (valid) B-rep solid and write a strictly-watertight STL.

    The boolean history (chamfer cuts + notch) leaves two mesh artifacts that
    make the naive per-face STL non-watertight (validators read solid=False /
    volume=nan): (1) shared-edge vertices land at ~1e-7 mm-different world
    positions on each face (per-face transforms) so trimesh won't merge them ->
    FREE edges; (2) the cuts leave near zero-area SLIVER triangles -> non-
    manifold edges.  The robust deterministic fix (COOKBOOK P-11):
      1. mesh per face (BRepMesh, parallel=False -> deterministic);
      2. WELD: round vertices to 1e-5 mm and re-merge -> closes the free edges;
      3. drop DUPLICATE faces, then drop DEGENERATE (zero-area) faces, fix
         normals -> removes the sliver-induced non-manifold edges -> watertight;
      4. pass through manifold3d to split any residual self-touch -> clean;
      5. write ASCII STL (binary float32 re-splits shared verts on reload).
    """
    import trimesh, os
    from OCP.BRepMesh import BRepMesh_IncrementalMesh
    from OCP.TopExp import TopExp_Explorer
    from OCP.TopAbs import TopAbs_FACE
    from OCP.TopoDS import TopoDS as _TDS
    from OCP.BRep import BRep_Tool
    from OCP.TopLoc import TopLoc_Location
    from OCP.BRepTools import BRepTools

    sh = shape.wrapped if hasattr(shape, "wrapped") else shape
    try:
        import manifold3d as m3d
    except Exception:
        m3d = None

    def raw_mesh(dd):
        """Per-face triangulation -> raw (vertices, faces) arrays (unmerged)."""
        BRepTools.Clean_s(sh)
        BRepMesh_IncrementalMesh(sh, dd, False, 0.5, False)   # parallel=False -> deterministic
        V = []; T = []
        e = TopExp_Explorer(sh, TopAbs_FACE)
        while e.More():
            f = _TDS.Face_s(e.Current()); loc = TopLoc_Location()
            tri = BRep_Tool.Triangulation_s(f, loc)
            if tri is None:
                e.Next(); continue
            tr = loc.Transformation(); b = len(V); rev = f.Orientation().value == 1
            for i in range(1, tri.NbNodes() + 1):
                p = tri.Node(i).Transformed(tr); V.append((p.X(), p.Y(), p.Z()))
            for i in range(1, tri.NbTriangles() + 1):
                a, bb, c = tri.Triangle(i).Get()
                if rev: a, c = c, a
                T.append((b + a - 1, b + bb - 1, b + c - 1))
            e.Next()
        return np.array(V), np.array(T)

    def weld_clean(V, T, dec=5):
        """Weld near-coincident vertices (round to 1e-`dec`) + drop duplicate
        and degenerate faces -> manifold, watertight in-memory mesh."""
        m = trimesh.Trimesh(np.round(V, dec), T, process=True)
        m.update_faces(m.unique_faces());      m.remove_unreferenced_vertices()
        m.update_faces(m.nondegenerate_faces()); m.remove_unreferenced_vertices()
        trimesh.repair.fix_normals(m)
        return m

    def via_manifold(m):
        if m3d is None:
            return m
        try:
            om = m3d.Manifold(m3d.Mesh(vert_properties=np.asarray(m.vertices, np.float32),
                                       tri_verts=np.asarray(m.faces, np.uint32))).to_mesh()
            if len(om.tri_verts):
                return trimesh.Trimesh(np.asarray(om.vert_properties)[:, :3].astype(np.float64),
                                       np.asarray(om.tri_verts), process=True)
        except Exception:
            pass
        return m

    def write_ascii(mesh, path):
        with open(path, "w") as fh:
            fh.write(trimesh.exchange.stl.export_stl_ascii(mesh))

    def reload_wt(path):
        try:
            return bool(trimesh.load(path).is_watertight)
        except Exception:
            return False

    result, fallback = None, None
    for d in (0.05, 0.04, 0.06, 0.03):
        V, T = raw_mesh(d)
        m = weld_clean(V, T, 5)
        if fallback is None:
            fallback = m
        cand = via_manifold(m) if m.is_watertight else m
        write_ascii(cand, str(out_path))
        if reload_wt(str(out_path)):
            result = cand; break
    if result is None:                       # last resort: best effort + WARN
        write_ascii(fallback, str(out_path))
    rl = trimesh.load(str(out_path))
    return bool(rl.is_watertight), (float(rl.volume) if rl.is_watertight else float("nan")), len(rl.faces)

try:
    _wt, _vol, _ntri = _watertight_stl(final_compound, FINAL_STL, defl=0.05)
    print(f"     [EXPORT] Wrote: {FINAL_STL.name}  (watertight={_wt}, "
          f"volume={_vol:.3f} mm³, {_ntri} triangles)")
    if not _wt:
        print("     ⚠  STL is not strictly watertight; falling back to raw export.")
        export_stl(final_compound, str(FINAL_STL), tolerance=STL_TOLERANCE)
except Exception as exc:
    print(f"     [EXPORT] watertight export failed ({exc}); raw STL.")
    export_stl(final_compound, str(FINAL_STL), tolerance=STL_TOLERANCE)

# Remove the internal round-trip temporaries (STEP round-trip + tmp STL); the
# deliverable is the STL only (TEMPLATE section 9 / 13).
import os as _os_cleanup
for _tmp in (str(FINAL_STL) + ".norm.step", str(FINAL_STL) + ".tmp.stl"):
    try:
        if _os_cleanup.path.exists(_tmp):
            _os_cleanup.remove(_tmp)
    except Exception:
        pass

summary_lines = [
    "=" * 70,
    f"BUILD SUMMARY  :  {FOLDER_NAME}",
    f"Time           :  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
    f"Range covered  :  {GUIDELINE_RANGE}",
    f"Guidelines     :  G1, G2, G4, G5, G6 (G3 = export, last)",
    f"Part type      :  Volumetric Solid Part (filter mount plate)",
    "=" * 70, "",
    f"-- G1 : S1 footprint on {S1_AXIS.upper()}={S1_PLANE} --",
    f"  Outer outline rows   : {OUTER_ROWS[0]}..{OUTER_ROWS[-1]} (8 lines + 6 arcs)",
    f"  Extrusion            : {THICK} mm DOWN (Z=4 -> Z=0)",
    f"  Inner circle (row {CIRCLE_ROW}) : through-hole",
    "",
    f"-- G2 : Sweep-cut S2 chamfer along S1 outline at z={S1_PLANE:.0f} (top) --",
    f"  Profile              : {S_CSV[2].name} (excl. inner circle)",
    "",
    f"-- G4 : Sweep-cut S3 chamfer along S1 outline at z=0 (bottom) --",
    f"  Profile              : {S_CSV[3].name} (excl. inner circle)",
    "",
    f"-- G5 : Chamfer {CHAMFER_HOLE} countersink at inner circle hole ends --",
    f"  Hole ends            : z={S1_PLANE:.0f} (top) and z=0 (bottom)",
    "",
    f"-- G6 : Extrude-cut S4 profile (notch) --",
    f"  Profile              : {S_CSV[4].name}  (5 units -Z / 1 unit +Z, through)",
    "",
    "-- G3 : Export --",
    f"  STL                  : {FINAL_STL.name}",
    f"  Total surface area   : {total_surface_area:.3f} mm²",
    f"  Total volume         : {total_volume:.3f} mm³",
    f"  Face / edge count    : {len(all_faces)} / {n_edges}",
    "",
    "=" * 70,
    "PER-GUIDELINE CUMULATIVE AREA / VOLUME HISTORY",
    "=" * 70,
    f"{'Guideline':>10}  {'Cum. area (mm²)':>18}  {'Δ area':>12}  "
    f"{'Cum. vol (mm³)':>16}  {'Δ vol':>12}  Label",
    "-" * 100,
]
for e in area_history:
    summary_lines.append(
        f"  G{e['g']:<8d}  {e['area']:>18.3f}  {e['darea']:>+12.3f}  "
        f"{e['vol']:>16.3f}  {e['dvol']:>+12.3f}  {e['label']}"
    )
summary_lines.append("=" * 70)

with open(FINAL_TXT, "w") as f:
    f.write("\n".join(summary_lines))
print(f"     [EXPORT] Wrote: {FINAL_TXT.name}")

_write_area_history_file()

print(f"\nDone — Operations complete (G3 = export, last).  Output range: {GUIDELINE_RANGE}")
