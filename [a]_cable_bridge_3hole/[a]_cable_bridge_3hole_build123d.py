"""
[a]_cable_bridge_3hole_build123d.py

Sketch summary (plane auto-detected from CSV):
  S1  Z = 0.0   Lines + 3-point arcs. A single sketch that encodes the whole
                part footprint: one OUTER outline, one INNER (inner_base)
                outline, and SIX oval openings (4 small + 2 larger).

Region structure (verified by polygonizing the sketch):
  - OUTER WALL  : the band between the outer outline and the inner_base
                  outline, plus the long arm/notch  ->  extrude 15 mm (+Z).
                  Visually two sections (head rim + arm); modelled as one
                  region (extruding both by 15 mm gives the same solid).
  - INNER_BASE  : the recessed floor inside the inner outline -> extrude
                  3 mm (+Z).  The inner outline is open in the CSV: its
                  dangling end lies exactly on outer edge S1 row 26, so the
                  inner_base is closed by the outer outline segment
                  (row 26 partial + row 27 arc) down to the pinch point.
  - 6 OVALS     : left as through-holes in the 3 mm floor.

Guidelines (executed in topological order):
  G1 - Read S1; build outer / inner_base / oval faces; extrude the outer
       wall to 15 mm and the inner_base to 3 mm, leaving the 6 ovals as
       through-holes.  (Built by: full 15 mm block, pocket the inner region
       down to 3 mm, then pierce the 6 ovals.)
  G2 - Apply 0.4 unit equal-distance chamfer to the model outer edges at
       z = 0 (outer wall perimeter; includes the small inner_base outline
       portion that reaches the outer wall at z = 0).
  G4 - Apply 0.4 unit equal-distance chamfer to the 4 small + 2 larger oval
       edges at z = 0.
  G3 - LAST: .clean() + STL + STEP + summary export.
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
EPSILON_MM      = 1e-3
SVD_PLANE_TOL   = 1e-2
STL_TOLERANCE   = 5e-4
NODE_SNAP       = 3        # decimals used to snap endpoints when assembling loops
Z0_TOL          = 1e-3     # tolerance for "edge lies in the z = 0 plane"
OVAL_MATCH_TOL  = 0.75     # mm: classify a z=0 edge as an oval-rim edge

# ══════════════════════════════════════════════════════════════════════════
# Paths (cross-platform, derived from script location)
# ══════════════════════════════════════════════════════════════════════════
BASE_DIR    = Path(__file__).resolve().parent
FOLDER_NAME = BASE_DIR.name
CSV_DIR     = BASE_DIR / "csv_merged"

S_CSV = {
    1: CSV_DIR / "Fusion_Coordinates_S1.csv",
    3: CSV_DIR / "Fusion_Coordinates_S3.csv",
    4: CSV_DIR / "Fusion_Coordinates_S4.csv",
    5: CSV_DIR / "Fusion_Coordinates_S5.csv",
    6: CSV_DIR / "Fusion_Coordinates_S6.csv",
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
    export_stl, export_step,
    GeomType,
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

# ══════════════════════════════════════════════════════════════════════════
# CHECKPOINT CONFIG
# ══════════════════════════════════════════════════════════════════════════
VIEW_AT              = 7        # int 1..N, or None for full pipeline
STOP_AFTER_VIEW      = True
EXPORT_AT_CHECKPOINT = True

GUIDELINE_RANGE = "G_1_7"

# ══════════════════════════════════════════════════════════════════════════
# Tracking state
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
# CSV / GEOMETRY HELPERS
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
    triples = []
    for i in _row_present_indices(row):
        triples.append((float(row[f"X{i}"]), float(row[f"Y{i}"]), float(row[f"Z{i}"])))
    return triples

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
        if col.max() - col.min() < tol_axis: return ("axis", axis_letter, float(col.mean()))
    centroid = pts.mean(axis=0)
    centred  = pts - centroid
    _, _, vh = np.linalg.svd(centred, full_matrices=False)
    normal   = vh[-1] / np.linalg.norm(vh[-1])
    return ("general", tuple(centroid), tuple(normal))

def world_vec_axis(in_plane_pt, axis, plane_value):
    u, v = in_plane_pt
    if axis == "z": return Vector(u, v, plane_value)
    elif axis == "y": return Vector(u, plane_value, v)
    else: return Vector(plane_value, u, v)

def axis_normal(axis):
    if axis == "z": return Vector(0, 0, 1)
    elif axis == "y": return Vector(0, 1, 0)
    else: return Vector(1, 0, 0)

def in_plane_uv(row, idx, axis):
    x, y, z = float(row[f"X{idx}"]), float(row[f"Y{idx}"]), float(row[f"Z{idx}"])
    if axis == "z": return (x, y)
    elif axis == "y": return (x, z)
    else: return (y, z)

def make_line_edge(p_uv, q_uv, axis, plane_value):
    return Edge.make_line(world_vec_axis(p_uv, axis, plane_value),
                          world_vec_axis(q_uv, axis, plane_value))

def make_arc_edge_uv(p1_uv, p2_uv, p3_uv, axis, plane_value):
    return Edge.make_three_point_arc(world_vec_axis(p1_uv, axis, plane_value),
                                     world_vec_axis(p2_uv, axis, plane_value),
                                     world_vec_axis(p3_uv, axis, plane_value))

def edge_from_row(row, axis, plane_value):
    """Build one build123d Edge (line or 3-point arc) from a CSV row."""
    dt = _norm_draw_type(row["Draw Type"])
    if dt.startswith("line"):
        return make_line_edge(in_plane_uv(row, 1, axis), in_plane_uv(row, 2, axis),
                              axis, plane_value)
    if dt.startswith("3_point_arc"):
        return make_arc_edge_uv(in_plane_uv(row, 1, axis), in_plane_uv(row, 2, axis),
                                in_plane_uv(row, 3, axis), axis, plane_value)
    raise ValueError(f"Unsupported draw type: {row['Draw Type']}")

def edges_from_rowids(rows, rowids, axis, plane_value):
    """rowids are 1-based CSV 'Steps' numbers (== line order)."""
    return [edge_from_row(rows[i - 1], axis, plane_value) for i in rowids]

def face_from_edges(edges):
    return Face(Wire(edges))

# ══════════════════════════════════════════════════════════════════════════
# Region row-membership (1-based 'Steps' ids), determined from the sketch.
#   outer outline   : 1..27   (closed loop)
#   inner_base path : 28..44  (open; closed below using the outer outline)
#   six ovals       : isolated closed loops
# ══════════════════════════════════════════════════════════════════════════
OUTER_ROWS = list(range(1, 28))                      # 1..27
INNER_ROWS = list(range(28, 45))                     # 28..44
OVAL_ROWS  = [
    [45, 46, 49, 50],            # small oval
    [47, 48, 51, 52],            # small oval
    [57, 58, 71, 72],            # small oval
    [59, 60, 69, 70],            # small oval
    [53, 54, 55, 56, 65, 66, 67, 68],   # larger oval
    [61, 62, 63, 64, 73, 74, 75, 76],   # larger oval
]
# Inner_base closure: the inner path dangles at this point, which lies on the
# outer outline (row 26). Close it with a line to the row 26/27 junction, then
# the row 27 arc carries it to the pinch (= start of row 28).
INNER_DANGLE_PT = (122.810211, 107.922621)   # row 44 end (X3,Y3)
ROW26_27_JUNCT  = (127.184620,  98.541670)    # row 26 end / row 27 start

# ══════════════════════════════════════════════════════════════════════════
# G1 — Read S1; build the tray (15 mm walls, 3 mm inner_base, 6 oval holes)
# ══════════════════════════════════════════════════════════════════════════
print(f"\n[G1] Reading {S_CSV[1].name}")
s1_rows = read_rows(S_CSV[1])
_, S1_AXIS, S1_PLANE = detect_sketch_plane(s1_rows)
print(f"     Sketch plane: axis {S1_AXIS.upper()} = {S1_PLANE}")

# --- outer footprint face -------------------------------------------------
outer_edges = edges_from_rowids(s1_rows, OUTER_ROWS, S1_AXIS, S1_PLANE)
outer_face  = face_from_edges(outer_edges)

# --- inner_base face (close the open inner path with outer row 26/27) -----
inner_edges = edges_from_rowids(s1_rows, INNER_ROWS, S1_AXIS, S1_PLANE)
close_line  = make_line_edge(INNER_DANGLE_PT, ROW26_27_JUNCT, S1_AXIS, S1_PLANE)
row27_arc   = edges_from_rowids(s1_rows, [27], S1_AXIS, S1_PLANE)[0]
base_face   = face_from_edges(inner_edges + [close_line, row27_arc])

# --- six oval faces -------------------------------------------------------
oval_faces = [face_from_edges(edges_from_rowids(s1_rows, rid, S1_AXIS, S1_PLANE))
              for rid in OVAL_ROWS]

print(f"     outer_face area  = {float(outer_face.area):.3f} mm²")
print(f"     base_face  area  = {float(base_face.area):.3f} mm²")
for i, of in enumerate(oval_faces):
    print(f"     oval[{i}] area    = {float(of.area):.3f} mm²")

WALL_H = 15.0
BASE_H = 3.0
up = (0, 0, 1)

# Full 15 mm block over the whole footprint
full_block = extrude(outer_face, amount=WALL_H, dir=up)

# Pocket the inner region down to BASE_H: remove z = BASE_H .. WALL_H over it
pocket = extrude(base_face, amount=WALL_H - BASE_H, dir=up)
pocket = Location(Vector(0, 0, BASE_H)) * pocket
tray = full_block - pocket

# Pierce the 6 ovals through the 3 mm floor (z = -1 .. +4)
oval_tools = []
for of in oval_faces:
    tool = extrude(of, amount=BASE_H + 2.0, dir=up)
    tool = Location(Vector(0, 0, -1.0)) * tool
    oval_tools.append(tool)
    tray = tray - tool

g1_body = tray
# clean() now (not just at export): the boolean cuts leave coplanar seam
# edges in the z=0 bottom face. Chamfer cannot bevel a seam between coplanar
# faces, so without this the chamfer stages fail. Cleaning merges them and
# leaves only genuine convex edges to select.
try:
    g1_body = g1_body.clean()
    print("     .clean() applied to G1 tray (removed boolean seam edges).")
except Exception as exc:
    print(f"     ⚠ G1 .clean() failed (continuing): {exc}")
stage_pieces.append(g1_body)
checkpoint(1, "G1 tray: walls 15mm, inner_base 3mm, 6 oval through-holes")

# ══════════════════════════════════════════════════════════════════════════
# Helpers for chamfer edge selection at z = 0
# ══════════════════════════════════════════════════════════════════════════
def edge_in_z0_plane(e):
    bb = e.bounding_box()
    return abs(bb.min.Z) < Z0_TOL and abs(bb.max.Z) < Z0_TOL

def _oval_boundary_samples():
    """(x, y) sample points along every oval boundary, for proximity tests."""
    pts = []
    for of in oval_faces:
        try:
            w = of.outer_wire()
        except Exception:
            w = of.wires()[0]
        for e in w.edges():
            for t in np.linspace(0.0, 1.0, 9):
                p = e.position_at(float(t))
                pts.append((p.X, p.Y))
    return np.array(pts)

_OVAL_PTS = _oval_boundary_samples()

def edge_is_oval_rim(e):
    c = e.center()
    d = np.hypot(_OVAL_PTS[:, 0] - c.X, _OVAL_PTS[:, 1] - c.Y)
    return float(d.min()) < OVAL_MATCH_TOL

def _edge_key(e):
    c = e.center()
    return (round(c.X, 3), round(c.Y, 3), round(c.Z, 3))

def select_z0_edges(body, want_oval):
    """z=0-plane edges of `body`; want_oval=True -> oval rims, else outer."""
    out = []
    for e in body.edges():
        if not edge_in_z0_plane(e):
            continue
        if edge_is_oval_rim(e) == want_oval:
            out.append(e)
    return out

# --- centroids used to orient the sweep profile (in / out) -----------------
_PART_CXY = (float(outer_face.center().X), float(outer_face.center().Y))
_OVAL_CXY = [(float(of.center().X), float(of.center().Y)) for of in oval_faces]

def _horiz_dir(T, C, ref_xy, outward):
    """Unit horizontal vector perpendicular to tangent T at point C, pointing
    toward ref_xy (outward=False) or away from it (outward=True)."""
    perp = Vector(-T.Y, T.X, 0.0)
    if perp.length < 1e-9:
        perp = Vector(1.0, 0.0, 0.0)
    perp = perp.normalized()
    to_ref = Vector(ref_xy[0] - C.X, ref_xy[1] - C.Y, 0.0)
    toward = perp if perp.dot(to_ref) >= 0 else -perp
    return (-toward) if outward else toward

# Chamfer sweep profile (KNOWN-GOOD version), in the local (inward, up)
# cross-section frame relative to the bottom corner C:
#   C = corner, A = LEG up the wall, B = LEG in along the bottom.
# Sweeping this triangle along the edge and subtracting removes the corner
# wedge -> a 0.4 equal chamfer. The two legs lie on the wall/bottom faces, so
# the boolean leaves thin coincident faces; this is the only artifact, but it
# is the configuration OCCT handles as a VALID solid (pushing the corner
# outside the body inverts the cut on this part).
S2_LEG = 0.4

def sweep_wedge_cut(body, edge, ref_xy, outward, leg=S2_LEG):
    """Build the chamfer triangle perpendicular to `edge` at its start, sweep
    it along the edge, and cut from `body`."""
    C  = edge.position_at(0.0)
    T  = edge.tangent_at(0.0)
    H  = _horiz_dir(T, C, ref_xy, outward)
    up = Vector(0.0, 0.0, 1.0)
    v0 = C                                  # corner
    v1 = C + up * leg                       # LEG up the wall
    v2 = C + H * leg                        # LEG in along the bottom
    prof = Wire([Edge.make_line(v0, v1),
                 Edge.make_line(v1, v2),
                 Edge.make_line(v2, v0)])
    tool = sweep(Face(prof), path=Wire([edge]))
    return body - tool

def chamfer_by_sweep(body, want_oval, leg, tag):
    """Replace each z=0 edge's sharp corner with a swept 0.4 wedge cut."""
    try:
        body = body.clean()
    except Exception:
        pass
    try:
        sols = body.solids()
        if len(sols) == 1:
            body = sols[0]
    except Exception:
        pass

    edges = select_z0_edges(body, want_oval)
    print(f"     {tag}: {len(edges)} z=0 edge(s) selected for sweep cut")
    done = fail = 0
    for e in edges:
        if want_oval:
            c = e.center()
            ref = min(_OVAL_CXY,
                      key=lambda q: (q[0] - c.X) ** 2 + (q[1] - c.Y) ** 2)
        else:
            ref = _PART_CXY
        try:
            body = sweep_wedge_cut(body, e, ref, outward=want_oval, leg=leg)
            done += 1
        except Exception as exc:
            fail += 1
            print(f"        ⚠ edge at {_edge_key(e)} sweep cut failed ({exc})")
    print(f"     {tag}: swept-cut {done} edge(s), {fail} failed")
    try:
        body = body.clean()
    except Exception:
        pass
    return body

# ══════════════════════════════════════════════════════════════════════════
# G2 (revised) — 0.4 equal chamfer on OUTER wall edges at z=0 via SWEEP CUT
#   Build the S2 right-triangle profile and sweep it across the outer wall
#   edges only (one edge at a time, profile re-built per edge).
# ══════════════════════════════════════════════════════════════════════════
print(f"\n[G2] Sweep-cut 0.4 chamfer on outer wall edges at z = 0")
g2_body = chamfer_by_sweep(g1_body, want_oval=False, leg=0.4, tag="G2")

stage_pieces[:] = [p for p in stage_pieces if p is not g1_body]
stage_pieces.append(g2_body)
checkpoint(2, "G2 sweep-cut 0.4 chamfer on outer wall edges at z=0")

# ══════════════════════════════════════════════════════════════════════════
# G4 (revised) — 0.4 equal chamfer on the 6 OVAL edges at z=0 via SWEEP CUT
#   Same swept S2 profile; horizontal leg points away from each oval centre
#   (countersink of the through-hole bottom rim).
# ══════════════════════════════════════════════════════════════════════════
print(f"\n[G4] Sweep-cut 0.4 chamfer on oval edges at z = 0")
g4_body = chamfer_by_sweep(g2_body, want_oval=True, leg=0.4, tag="G4")

stage_pieces[:] = [p for p in stage_pieces if p is not g2_body]
stage_pieces.append(g4_body)
checkpoint(4, "G4 sweep-cut 0.4 chamfer on 4 small + 2 larger oval edges at z=0")

# ══════════════════════════════════════════════════════════════════════════
# G5 — Read S3: loft two bosses on the -Y wall, then drill their holes.
#   S3 circles lie on constant-Y planes (XZ plane):
#     Y=88.5  -> per axis: inner (small r) + outer (large r) circle
#     Y=89.5  -> per axis: one circle (largest r)
#   Loft each OUTER circle (Y=88.5) to its Y=89.5 circle -> tapered boss.
#   Extrude-cut each INNER circle (Y=88.5) by +10 / -1 along Y -> through-hole.
# ══════════════════════════════════════════════════════════════════════════
print(f"\n[G5] Reading {S_CSV[3].name} — loft bosses + drill holes")

def circle_from_3pts(p1, p2, p3):
    """Centre (u,v) and radius of the circle through three 2-D points."""
    (ax, av), (bx, bv), (cx_, cv) = p1, p2, p3
    d = 2.0 * (ax * (bv - cv) + bx * (cv - av) + cx_ * (av - bv))
    if abs(d) < 1e-12:
        raise ValueError("colinear circle points")
    ux = ((ax**2 + av**2) * (bv - cv) + (bx**2 + bv**2) * (cv - av)
          + (cx_**2 + cv**2) * (av - bv)) / d
    uv = ((ax**2 + av**2) * (cx_ - bx) + (bx**2 + bv**2) * (ax - cx_)
          + (cx_**2 + cv**2) * (bx - ax)) / d
    return (ux, uv, math.hypot(ax - ux, av - uv))

def circle_face_Y(cx, cz, r, y):
    pl = Plane(origin=Vector(cx, y, cz), z_dir=(0, 1, 0))
    return Face(Wire([Edge.make_circle(r, pl)]))

s3_rows = read_rows(S_CSV[3])
s3_circles = []
for r in s3_rows:
    pts = _row_all_xyz_triples(r)           # three (x, y, z) points
    y_c = pts[0][1]
    xz  = [(p[0], p[2]) for p in pts]        # circle lies in the XZ (Y=const) plane
    cx, cz, rad = circle_from_3pts(*xz)
    s3_circles.append({"cx": cx, "cz": cz, "r": rad, "y": y_c})
    print(f"     circle: centre=({cx:.3f},{cz:.3f}) r={rad:.3f} Y={y_c}")

# group circles by axis using PROXIMITY clustering (not rounding): the two
# bosses are ~16 mm apart in X, while the circles of one boss share an axis to
# within a fraction of a mm. A 5 mm tolerance cleanly separates the two bosses
# and is robust to the slight centre offsets from STL extraction.
AXIS_CLUSTER_TOL = 5.0
axis_clusters = []
for c in s3_circles:
    for cl in axis_clusters:
        if abs(cl[0]["cx"] - c["cx"]) < AXIS_CLUSTER_TOL:
            cl.append(c)
            break
    else:
        axis_clusters.append([c])

BOSS_DEPTH_PLUS = 10.0      # hole into +Y (into the body)
BOSS_DEPTH_MINUS = 1.0      # hole overshoot along -Y (avoid coincident face)

g5_body = g4_body
n_boss = 0
for cs in sorted(axis_clusters, key=lambda g: g[0]["cx"]):
    axis_x = sum(c["cx"] for c in cs) / len(cs)
    y_lo = min(c["y"] for c in cs)          # 88.5 : inner + outer
    y_hi = max(c["y"] for c in cs)          # 89.5 : single circle
    lo = sorted([c for c in cs if abs(c["y"] - y_lo) < 1e-6], key=lambda c: c["r"])
    hi = [c for c in cs if abs(c["y"] - y_hi) < 1e-6]
    if len(lo) < 2 or not hi:
        print(f"     ⚠ axis X={axis_x}: unexpected circle set, skipping")
        continue
    inner, outer = lo[0], lo[-1]
    top = hi[0]
    # boss = loft( outer circle @Y_lo  ->  circle @Y_hi )
    boss = loft([circle_face_Y(outer["cx"], outer["cz"], outer["r"], outer["y"]),
                 circle_face_Y(top["cx"],   top["cz"],   top["r"],   top["y"])])
    g5_body = g5_body + boss
    # hole = inner circle extruded +10 / -1 along Y, then cut
    inner_face = circle_face_Y(inner["cx"], inner["cz"], inner["r"], inner["y"])
    tool = (extrude(inner_face, amount=BOSS_DEPTH_PLUS,  dir=(0, 1, 0))
            + extrude(inner_face, amount=BOSS_DEPTH_MINUS, dir=(0, -1, 0)))
    g5_body = g5_body - tool
    # 0.4 (equal/45°) countersink chamfer at the hole exit on the y=94.5 face.
    # Material is on the -Y side, open on +Y, so the cone narrows to the hole
    # radius at y=94.1 and widens past the face (+OV overshoot avoids a
    # coincident surface).
    FACE_Y, CH, OV = 94.5, 0.4, 0.3
    cone = loft([circle_face_Y(inner["cx"], inner["cz"], inner["r"],
                               FACE_Y - CH),
                 circle_face_Y(inner["cx"], inner["cz"], inner["r"] + CH + OV,
                               FACE_Y + OV)])
    g5_body = g5_body - cone
    n_boss += 1
    print(f"     boss @X={axis_x}: loft r{outer['r']:.2f}->r{top['r']:.2f}, "
          f"hole r{inner['r']:.2f}, 0.4 countersink @y={FACE_Y}")

try:
    g5_body = g5_body.clean()
except Exception:
    pass

stage_pieces[:] = [p for p in stage_pieces if p is not g4_body]
stage_pieces.append(g5_body)
checkpoint(5, f"G5 lofted {n_boss} boss(es) + drilled holes from S3")

# ══════════════════════════════════════════════════════════════════════════
# G6 — Read S4: extrude-cut both enclosed profiles through the body.
#   S4 profiles lie on the Y=94.5 plane (XZ). Cut 13 mm along -Y and 1 mm
#   along +Y (the +Y overshoot avoids coincident / sliver surfaces).
# ══════════════════════════════════════════════════════════════════════════
print(f"\n[G6] Reading {S_CSV[4].name} — extrude-cut S4 profiles")

def group_connected_edges(edges):
    """Cluster edges into connected closed loops by shared endpoints."""
    def key(p): return (round(p.X, 3), round(p.Y, 3), round(p.Z, 3))
    parent = {}
    def find(x):
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]; x = parent[x]
        return x
    def union(a, b): parent[find(a)] = find(b)
    info = []
    for e in edges:
        a, b = key(e.position_at(0.0)), key(e.position_at(1.0))
        info.append((e, a, b)); union(a, b)
    groups = {}
    for e, a, b in info:
        groups.setdefault(find(a), []).append(e)
    return list(groups.values())

s4_rows = read_rows(S_CSV[4])
_, S4_AXIS, S4_PLANE = detect_sketch_plane(s4_rows)
print(f"     S4 plane: axis {S4_AXIS.upper()} = {S4_PLANE}")
s4_edges = [edge_from_row(r, S4_AXIS, S4_PLANE) for r in s4_rows]
s4_loops = group_connected_edges(s4_edges)
print(f"     S4 enclosed profiles found: {len(s4_loops)}")

CUT_NEG_Y = 13.0
CUT_POS_Y = 1.0
g6_body = g5_body
for i, loop in enumerate(s4_loops):
    face = Face(Wire(loop))
    tool = (extrude(face, amount=CUT_NEG_Y, dir=(0, -1, 0))
            + extrude(face, amount=CUT_POS_Y, dir=(0, 1, 0)))
    g6_body = g6_body - tool
    print(f"     profile[{i}]: area={float(face.area):.3f} mm² -> cut "
          f"{CUT_NEG_Y} (-Y) / {CUT_POS_Y} (+Y)")

try:
    g6_body = g6_body.clean()
except Exception:
    pass

stage_pieces[:] = [p for p in stage_pieces if p is not g5_body]
stage_pieces.append(g6_body)
checkpoint(6, f"G6 extrude-cut {len(s4_loops)} S4 profiles (13 -Y / 1 +Y)")

# ══════════════════════════════════════════════════════════════════════════
# G7 — Read S5 & S6: form a NEW body by intersecting the two perpendicular
#   extrusions.  S5 lies on the Y=126.5 plane (extrude along Y); S6 lies on
#   the X=87.85 plane (extrude along X).  Each is extruded far enough to span
#   the other's extent, then INTERSECTED.  The result is kept as a SEPARATE
#   solid -> the model now holds two bodies (G1-G6 part + this G7 body).
# ══════════════════════════════════════════════════════════════════════════
print(f"\n[G7] Reading {S_CSV[5].name} & {S_CSV[6].name} — intersect to new body")

def face_from_profile(rows):
    _, ax, pl = detect_sketch_plane(rows)
    edges = [edge_from_row(r, ax, pl) for r in rows]
    loop = max(group_connected_edges(edges), key=len)
    return Face(Wire(loop)), ax, pl

s5_face, A5, P5 = face_from_profile(read_rows(S_CSV[5]))
s6_face, A6, P6 = face_from_profile(read_rows(S_CSV[6]))
print(f"     S5 plane: axis {A5.upper()}={P5}  area={float(s5_face.area):.3f} mm²")
print(f"     S6 plane: axis {A6.upper()}={P6}  area={float(s6_face.area):.3f} mm²")

# S5 extruded along +/-Y to span S6's Y-extent (124.5..131.5);
# S6 extruded along +X to span S5's X-extent (90.85..113.43).
prism_s5 = (extrude(s5_face, amount=8.0, dir=(0, 1, 0))
            + extrude(s5_face, amount=4.0, dir=(0, -1, 0)))
prism_s6 = extrude(s6_face, amount=32.0, dir=(1, 0, 0))

g7_body = prism_s5 & prism_s6          # intersection -> new solid
try:
    g7_body = g7_body.clean()
except Exception:
    pass
try:
    g7_vol = sum(float(s.volume) for s in g7_body.solids())
except Exception:
    g7_vol = float("nan")
print(f"     G7 intersected body volume: {g7_vol:.3f} mm³")

# keep the G1-G6 body AND add the G7 body -> two solids total
stage_pieces.append(g7_body)
checkpoint(7, "G7 intersected S5∩S6 -> new separate body (2 solids total)")

# ══════════════════════════════════════════════════════════════════════════
# G3 — EXPORT (always last): .clean() + STL + STEP + summary
# ══════════════════════════════════════════════════════════════════════════
print(f"\n[G3] Export — compounding {len(stage_pieces)} body(ies), "
      f"applying .clean(), then exporting.")

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

FINAL_STL  = BASE_DIR / f"{FOLDER_NAME}_{GUIDELINE_RANGE}.stl"
FINAL_STEP = BASE_DIR / f"{FOLDER_NAME}_{GUIDELINE_RANGE}.step"
FINAL_TXT  = BASE_DIR / f"{FOLDER_NAME}_summary_{GUIDELINE_RANGE}.txt"

try:
    export_stl(final_compound, str(FINAL_STL), tolerance=STL_TOLERANCE)
    print(f"     [EXPORT] Wrote: {FINAL_STL.name}")
except Exception as exc:
    print(f"     [EXPORT] STL failed: {exc}")
try:
    export_step(final_compound, str(FINAL_STEP))
    print(f"     [EXPORT] Wrote: {FINAL_STEP.name}")
except Exception as exc:
    print(f"     [EXPORT] STEP failed: {exc}")

summary_lines = [
    "=" * 70,
    f"BUILD SUMMARY  :  {FOLDER_NAME}",
    f"Time           :  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
    f"Range covered  :  {GUIDELINE_RANGE}",
    f"Guidelines     :  G1, G2, G4, G5, G6, G7 (G3 = export, last)",
    f"Part type      :  Volumetric Solid Part (tray)",
    "=" * 70, "",
    f"-- G1 : S1 tray on {S1_AXIS.upper()}={S1_PLANE} --",
    f"  Outer wall height    : {WALL_H} mm",
    f"  Inner_base height    : {BASE_H} mm",
    f"  Oval through-holes    : {len(oval_faces)} (4 small + 2 larger)",
    "",
    f"-- G2 : Chamfer 0.4 (equal) on outer edges at z=0 --",
    "",
    f"-- G4 : Chamfer 0.4 (equal) on oval edges at z=0 --",
    "",
    "-- G3 : Export --",
    f"  STL                  : {FINAL_STL.name}",
    f"  STEP                 : {FINAL_STEP.name}",
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

print(f"\nDone — Operations complete (G3 = export, last).  "
      f"Output range: {GUIDELINE_RANGE}")
