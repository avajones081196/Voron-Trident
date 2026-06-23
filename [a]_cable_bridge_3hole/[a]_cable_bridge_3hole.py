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
SCRIPT_STEM = Path(__file__).resolve().stem   # output files named after this script
CSV_DIR     = BASE_DIR / "csv_merged"

S_CSV = {
    1: CSV_DIR / "Fusion_Coordinates_S1.csv",
    3: CSV_DIR / "Fusion_Coordinates_S3.csv",
    4: CSV_DIR / "Fusion_Coordinates_S4.csv",
    5: CSV_DIR / "Fusion_Coordinates_S5.csv",
    6: CSV_DIR / "Fusion_Coordinates_S6.csv",
    7: CSV_DIR / "Fusion_Coordinates_S7.csv",
    8: CSV_DIR / "Fusion_Coordinates_S8.csv",
    9: CSV_DIR / "Fusion_Coordinates_S9.csv",
    10: CSV_DIR / "Fusion_Coordinates_S10.csv",
    11: CSV_DIR / "Fusion_Coordinates_S11.csv",
    12: CSV_DIR / "Fusion_Coordinates_S12.csv",
    13: CSV_DIR / "Fusion_Coordinates_S13.csv",
    14: CSV_DIR / "Fusion_Coordinates_S14.csv",
    15: CSV_DIR / "Fusion_Coordinates_S15.csv",
    16: CSV_DIR / "Fusion_Coordinates_S16.csv",
    17: CSV_DIR / "Fusion_Coordinates_S17.csv",
    18: CSV_DIR / "Fusion_Coordinates_S18.csv",
    19: CSV_DIR / "Fusion_Coordinates_S19.csv",
    20: CSV_DIR / "Fusion_Coordinates_S20.csv",
    21: CSV_DIR / "Fusion_Coordinates_S21.csv",
    22: CSV_DIR / "Fusion_Coordinates_S22.csv",
    23: CSV_DIR / "Fusion_Coordinates_S23.csv",
    24: CSV_DIR / "Fusion_Coordinates_S24.csv",
    25: CSV_DIR / "Fusion_Coordinates_S25.csv",
    26: CSV_DIR / "Fusion_Coordinates_S26.csv",
    27: CSV_DIR / "Fusion_Coordinates_S27.csv",
    28: CSV_DIR / "Fusion_Coordinates_S28.csv",
    29: CSV_DIR / "Fusion_Coordinates_S29.csv",
    30: CSV_DIR / "Fusion_Coordinates_S30.csv",
    31: CSV_DIR / "Fusion_Coordinates_S31.csv",
    33: CSV_DIR / "Fusion_Coordinates_S33.csv",
    34: CSV_DIR / "Fusion_Coordinates_S34.csv",
    35: CSV_DIR / "Fusion_Coordinates_S35.csv",
    36: CSV_DIR / "Fusion_Coordinates_S36.csv",
    37: CSV_DIR / "Fusion_Coordinates_S37.csv",
    38: CSV_DIR / "Fusion_Coordinates_S38.csv",
    39: CSV_DIR / "Fusion_Coordinates_S39.csv",
    40: CSV_DIR / "Fusion_Coordinates_S40.csv",
    41: CSV_DIR / "Fusion_Coordinates_S41.csv",
    42: CSV_DIR / "Fusion_Coordinates_S42.csv",
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
from OCP.BRepOffsetAPI import BRepOffsetAPI_MakePipeShell
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeVertex

def point_inside(solid, x, y, z, tol=1e-6):
    """True if the point lies inside `solid` — used to pick the true 'into the
    material' direction per edge (robust where the part centroid is on the
    wrong side, e.g. the thin arm whose centroid sits in the head)."""
    try:
        cls = BRepClass3d_SolidClassifier(solid.wrapped, gp_Pnt(x, y, z), tol)
        return cls.State() == TopAbs_IN
    except Exception:
        return False

# ══════════════════════════════════════════════════════════════════════════
# CHECKPOINT CONFIG
# ══════════════════════════════════════════════════════════════════════════
VIEW_AT              = None     # None -> run the full pipeline through to the G3 export
STOP_AFTER_VIEW      = False     # don't stop early; reach the final export
EXPORT_AT_CHECKPOINT = False     # no per-checkpoint STL/STEP — only the final files

GUIDELINE_RANGE = "G_1_26"

# Per-step .clean() can be pathologically slow / hang on some OCCT builds
# (e.g. build123d master) once the body accumulates many boolean faces. It is
# not required mid-pipeline — G1's pre-chamfer clean and the final export
# clean are kept; the intermediate ones are gated off by default.
CLEAN_EACH_STEP = False

def maybe_clean(b):
    if not CLEAN_EACH_STEP:
        return b
    try:
        return b.clean()
    except Exception:
        return b

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
        try:
            return make_arc_edge_uv(in_plane_uv(row, 1, axis), in_plane_uv(row, 2, axis),
                                    in_plane_uv(row, 3, axis), axis, plane_value)
        except Exception:
            # collinear 3 points (an arc that is really a straight segment) ->
            # build a line from the first to the last point.
            return make_line_edge(in_plane_uv(row, 1, axis), in_plane_uv(row, 3, axis),
                                  axis, plane_value)
    raise ValueError(f"Unsupported draw type: {row['Draw Type']}")

def edges_from_rowids(rows, rowids, axis, plane_value):
    """rowids are 1-based CSV 'Steps' numbers (== line order)."""
    return [edge_from_row(rows[i - 1], axis, plane_value) for i in rowids]

def closed_wire(edges, tol=1e-3):
    """Build a single closed Wire from a list of edges, bridging the tiny
    endpoint gaps (~1e-5 mm) the Fusion export leaves between consecutive
    primitives. Bare Wire(edges) is strict about closure across build123d
    versions; Wire.combine(tol) reconnects within tolerance."""
    try:
        wires = Wire.combine(edges, tol=tol)
    except Exception:
        return Wire(edges)
    closed = [w for w in wires if w.is_closed]
    cand = closed if closed else list(wires)
    return max(cand, key=lambda w: len(w.edges()))

def face_from_edges(edges):
    return Face(closed_wire(edges))

# ══════════════════════════════════════════════════════════════════════════
# Region row-membership (1-based 'Steps' ids), determined from the sketch.
#   outer outline   : 1..27   (closed loop)
#   inner_base path : 28..44  (open; closed below using the outer outline)
#   six ovals       : isolated closed loops
# ══════════════════════════════════════════════════════════════════════════
OUTER_ROWS = list(range(1, 28))                      # 1..27
# Inner_base path 28..41; rows 42-44 (the rounded tab arcs) are REPLACED by the
# S21 step-3/step-4 straight lines so that tab has SHARP corners (see G1 below).
INNER_ROWS = list(range(28, 42))                     # 28..41
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
# After the S21 sharp-corner swap, the tab ends at the S21 step-4 endpoint
# (123.473586, 106.5), which also sits on row 26.
INNER_DANGLE_PT = (123.473586, 106.500006)   # S21 step-4 endpoint (on row 26)
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
# rows 28..41 + the S21 step-3/step-4 sharp lines (replacing the rows 42-44
# rounded-tab arcs), then the row 26/27 closure.
inner_edges = edges_from_rowids(s1_rows, INNER_ROWS, S1_AXIS, S1_PLANE)
s21_rows    = read_rows(S_CSV[21])
sharp_edges = [edge_from_row(s21_rows[2], S1_AXIS, S1_PLANE),   # step 3 line
               edge_from_row(s21_rows[3], S1_AXIS, S1_PLANE)]   # step 4 line
close_line  = make_line_edge(INNER_DANGLE_PT, ROW26_27_JUNCT, S1_AXIS, S1_PLANE)
row27_arc   = edges_from_rowids(s1_rows, [27], S1_AXIS, S1_PLANE)[0]
base_face   = face_from_edges(inner_edges + sharp_edges + [close_line, row27_arc])

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

# Chamfer sweep profile, in the local (inward, up) cross-section frame
# relative to the bottom corner C:
#   v1 = LEG up the wall, v2 = LEG in along the bottom -> the v1-v2 hypotenuse
#   is the 0.4 equal (45°) chamfer face. The third corner D is pushed S2_OVER
#   mm OUTSIDE the part corner so the tool's two legs cross the wall/bottom
#   faces transversally instead of lying on them -> the boolean leaves NO
#   coincident sliver faces, so the exported solid stays watertight.
S2_LEG  = 0.4
S2_OVER = 0.1

def wedge_tool(ref_body, edge, leg=S2_LEG, over=S2_OVER):
    """Build the chamfer-wedge sweep tool for `edge`. The horizontal leg points
    INTO the material, decided by a point-in-solid test against `ref_body`
    (use the ORIGINAL clean body so direction/size don't drift as earlier cuts
    modify the working body)."""
    C  = edge.position_at(0.0)
    T  = edge.tangent_at(0.0)
    up = Vector(0.0, 0.0, 1.0)
    perp = Vector(-T.Y, T.X, 0.0)
    if perp.length < 1e-9:
        perp = Vector(1.0, 0.0, 0.0)
    perp = perp.normalized()
    M = edge.position_at(0.5)                # test inward at the edge midpoint
    t = M + perp * 0.15 + up * 0.1
    H = perp if point_inside(ref_body, t.X, t.Y, t.Z) else -perp
    v1 = C + up * leg                       # LEG up the wall  (on wall face)
    v2 = C + H * leg                        # LEG in the bottom (on bottom face)
    D  = C - H * over - up * over           # corner pushed outside the part
    prof = closed_wire([Edge.make_line(v1, v2),
                        Edge.make_line(v2, D),
                        Edge.make_line(D, v1)])
    return sweep(Face(prof), path=Wire([edge]))

def sweep_wedge_cut(body, edge, ref_xy=None, outward=False, leg=S2_LEG, over=S2_OVER):
    """Cut a single chamfer wedge from `body` (direction tested on `body`)."""
    return body - wedge_tool(body, edge, leg=leg, over=over)

def chamfer_by_sweep(body, want_oval, leg, tag):
    """Replace each z=0 edge's sharp corner with a swept 0.4 wedge cut."""
    try:
        body = maybe_clean(body)
    except Exception:
        pass
    try:
        sols = body.solids()
        if len(sols) == 1:
            body = sols[0]
    except Exception:
        pass

    # Outer wall edges take the OVERSHOOT profile (no coincident slivers ->
    # watertight). The small oval rims invert the boolean when overshot, so
    # they use the corner-on-body profile (over=0).
    over = 0.0 if want_oval else S2_OVER
    edges = select_z0_edges(body, want_oval)
    print(f"     {tag}: {len(edges)} z=0 edge(s) selected for sweep cut (over={over})")
    done = fail = 0
    for e in edges:
        if want_oval:
            c = e.center()
            ref = min(_OVAL_CXY,
                      key=lambda q: (q[0] - c.X) ** 2 + (q[1] - c.Y) ** 2)
        else:
            ref = _PART_CXY
        try:
            body = sweep_wedge_cut(body, e, ref, outward=want_oval, leg=leg, over=over)
            done += 1
        except Exception as exc:
            fail += 1
            print(f"        ⚠ edge at {_edge_key(e)} sweep cut failed ({exc})")
    print(f"     {tag}: swept-cut {done} edge(s), {fail} failed")
    try:
        body = maybe_clean(body)
    except Exception:
        pass
    return body

def oval_countersink(body, faces, leg=0.4, over=0.1, tag="G4"):
    """0.4 (45°) countersink chamfer at each oval hole's z=0 rim, built as a
    LOFT cone (offset the oval outward by `leg` at the bottom, narrowing to the
    original oval at z=`leg`). Robust where the swept profile self-intersects
    around the small holes, and leaves no coincident slivers (the cone's wide
    end overshoots `over` mm below z=0)."""
    done = 0
    for f in faces:
        try:
            w = f.outer_wire()
        except Exception:
            w = f.wires()[0]
        try:
            wide = Wire(w.offset_2d(leg + over))            # expanded rim
            if Face(wide).area < Face(w).area:               # ensure it expands
                wide = Wire(w.offset_2d(-(leg + over)))
            bottom = Location(Vector(0, 0, -over)) * Face(wide)   # z = -over
            top = Location(Vector(0, 0, leg)) * Face(w)           # z = +leg
            body = body - loft([bottom, top])
            done += 1
        except Exception as exc:
            print(f"        ⚠ oval countersink failed ({exc})")
    print(f"     {tag}: countersunk {done}/{len(faces)} oval(s)")
    try:
        body = maybe_clean(body)
    except Exception:
        pass
    return body

# ══════════════════════════════════════════════════════════════════════════
# G2 (revised) — DUAL-radius chamfer on the outer z=0 edges via SWEEP CUT:
#   S16 (steps 1-7: y=89.5 bottom + notch)  -> 0.4 mm chamfer
#   S17 (steps 1-10: y=94.5 bottom + head perimeter) -> 1.0 mm chamfer
#   The shared corner arc (S17 step 11 = S16 step 8) is SPLIT: the portion
#   collinear with S16's step-7 line (near the y=89.5 end) gets 0.4, the rest
#   gets 1.0.  Each edge swept with the overshoot wedge (point-in-solid picks
#   the inward direction).
# ══════════════════════════════════════════════════════════════════════════
print(f"\n[G2] Dual chamfer — S16 edges 0.4, S17 edges 1.0 (shared arc split)")

def _g2_pts(edges):
    pts = []
    for e in edges:
        n = max(8, int(e.length / 0.15) + 2)   # ~0.15 mm sample spacing
        for t in np.linspace(0.0, 1.0, n):
            v = e.position_at(float(t)); pts.append((v.X, v.Y, v.Z))
    return np.array(pts)

def _g2_on(e, cloud, tol):
    for t in np.linspace(0.0, 1.0, 7):
        v = e.position_at(float(t))
        d = np.sqrt(((cloud[:, 0] - v.X) ** 2 + (cloud[:, 1] - v.Y) ** 2
                     + (cloud[:, 2] - v.Z) ** 2)).min()
        if d > tol:
            return False
    return True

s16_rows = read_rows(S_CSV[16]); _, a16, p16 = detect_sketch_plane(s16_rows)
s16_cloud = _g2_pts([edge_from_row(r, a16, p16) for r in s16_rows])
s17_rows = read_rows(S_CSV[17]); _, a17, p17 = detect_sketch_plane(s17_rows)
s17_edges = [edge_from_row(r, a17, p17) for r in s17_rows]
s17_cloud = _g2_pts(s17_edges[:10])           # steps 1-10  -> 1.0
arc_cloud = _g2_pts([s17_edges[10]])          # step 11     -> shared split arc
ARC_Y89 = Vector(117.569189, 89.499998, 0.0)  # the 0.4 (y=89.5) end of the arc
SPLIT_FRAC = 0.3                              # 0.4 portion near the y=89.5 end

g2_src = g1_body
try:
    g2_src = g2_src.solids()[0]
except Exception:
    pass
z0_edges = [e for e in g2_src.edges()
            if edge_in_z0_plane(e) and not edge_is_oval_rim(e)]
print(f"     {len(z0_edges)} z=0 outer edge(s)")

# Build EVERY wedge tool against the ORIGINAL clean body (g2_src), then cut all
# at once — so no edge's direction/size drifts as earlier cuts modify the body
# (which was over-cutting the long head diagonal to -65 mm³).
tools = []
n04 = n10 = 0
for e in z0_edges:
    if _g2_on(e, arc_cloud, 0.4):                          # shared arc -> split
        near0 = ((e.position_at(0.0) - ARC_Y89).length
                 < (e.position_at(1.0) - ARC_Y89).length)
        e04 = e.trim(0.0, SPLIT_FRAC) if near0 else e.trim(1.0 - SPLIT_FRAC, 1.0)
        e10 = e.trim(SPLIT_FRAC, 1.0) if near0 else e.trim(0.0, 1.0 - SPLIT_FRAC)
        try: tools.append(wedge_tool(g2_src, e04, leg=0.4)); n04 += 1
        except Exception as exc: print(f"        ⚠ arc 0.4 part failed ({exc})")
        try: tools.append(wedge_tool(g2_src, e10, leg=1.0)); n10 += 1
        except Exception as exc: print(f"        ⚠ arc 1.0 part failed ({exc})")
        print("     shared corner arc split 0.4 / 1.0")
    elif _g2_on(e, s16_cloud, 0.4):
        try: tools.append(wedge_tool(g2_src, e, leg=0.4)); n04 += 1
        except Exception as exc: print(f"        ⚠ S16 edge failed ({exc})")
    elif _g2_on(e, s17_cloud, 0.4):
        try: tools.append(wedge_tool(g2_src, e, leg=1.0)); n10 += 1
        except Exception as exc: print(f"        ⚠ S17 edge failed ({exc})")
    else:
        try: tools.append(wedge_tool(g2_src, e, leg=0.4)); n04 += 1
        except Exception as exc: print(f"        ⚠ unmatched edge failed ({exc})")
        print(f"     unmatched z=0 edge -> default 0.4 at {_edge_key(e)}")

g2_body = g2_src
if tools:                             # union all pristine tools, subtract once
    combined = tools[0]
    for tl in tools[1:]:
        combined = combined + tl
    g2_body = g2_src - combined
g2_body = maybe_clean(g2_body)
print(f"     G2: chamfered {n04} part(s) @0.4, {n10} part(s) @1.0")

stage_pieces[:] = [p for p in stage_pieces if p is not g1_body]
stage_pieces.append(g2_body)
checkpoint(2, "G2 dual chamfer S16=0.4 / S17=1.0 (shared arc split)")

# ══════════════════════════════════════════════════════════════════════════
# G4 (revised) — 0.4 equal countersink chamfer on the 6 OVAL z=0 rims, built
#   as LOFT cones (robust + sliver-free, so the body stays a valid solid).
# ══════════════════════════════════════════════════════════════════════════
print(f"\n[G4] Loft-countersink 0.4 chamfer on oval rims at z = 0")
g4_body = oval_countersink(g2_body, oval_faces, leg=0.4, over=0.1, tag="G4")

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
    return Face(closed_wire([Edge.make_circle(r, pl)]))

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
    g5_body = maybe_clean(g5_body)
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
    face = Face(closed_wire(loop))
    tool = (extrude(face, amount=CUT_NEG_Y, dir=(0, -1, 0))
            + extrude(face, amount=CUT_POS_Y, dir=(0, 1, 0)))
    g6_body = g6_body - tool
    print(f"     profile[{i}]: area={float(face.area):.3f} mm² -> cut "
          f"{CUT_NEG_Y} (-Y) / {CUT_POS_Y} (+Y)")

try:
    g6_body = maybe_clean(g6_body)
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

def drop_internal_chords(edges):
    """Remove edges whose BOTH endpoints are T-junctions (degree > 2) — these
    are internal chords (e.g. S5 step 5) that stop the outline being a simple
    closed loop. Boundary edges always touch at least one degree-2 node, so
    they are kept; clean profiles are unaffected."""
    def k(p): return (round(p.X, 3), round(p.Y, 3), round(p.Z, 3))
    deg = {}
    ek = []
    for e in edges:
        a, b = k(e.position_at(0.0)), k(e.position_at(1.0))
        ek.append((e, a, b))
        deg[a] = deg.get(a, 0) + 1
        deg[b] = deg.get(b, 0) + 1
    kept = [e for (e, a, b) in ek if not (deg[a] > 2 and deg[b] > 2)]
    if len(kept) != len(edges):
        print(f"     dropped {len(edges) - len(kept)} internal chord edge(s)")
    return kept

def face_from_profile(rows):
    _, ax, pl = detect_sketch_plane(rows)
    edges = drop_internal_chords([edge_from_row(r, ax, pl) for r in rows])
    loop = max(group_connected_edges(edges), key=len)
    return Face(closed_wire(loop)), ax, pl

s5_face, A5, P5 = face_from_profile(read_rows(S_CSV[5]))
s6_face, A6, P6 = face_from_profile(read_rows(S_CSV[6]))
print(f"     S5 plane: axis {A5.upper()}={P5}  area={float(s5_face.area):.3f} mm²")
print(f"     S6 plane: axis {A6.upper()}={P6}  area={float(s6_face.area):.3f} mm²")

# S5 extruded 13.5 mm along +Y; S6 extruded 30 mm along +X. The two prisms
# overlap and their intersection is the new G7 body.
prism_s5 = extrude(s5_face, amount=13.5, dir=(0, 1, 0))
prism_s6 = extrude(s6_face, amount=30.0, dir=(1, 0, 0))

g7_body = prism_s5 & prism_s6          # intersection -> new solid
try:
    g7_body = maybe_clean(g7_body)
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
# G8 — Fuse all solids (G1-G6 body + G7 body) into a single body.
# ══════════════════════════════════════════════════════════════════════════
print(f"\n[G8] Fusing all solids into one body")
g8_body = g6_body + g7_body
try:
    g8_body = maybe_clean(g8_body)
except Exception:
    pass
try:
    n_sol = len(g8_body.solids())
except Exception:
    n_sol = -1
print(f"     fused -> {n_sol} solid(s)")
stage_pieces[:] = [g8_body]
checkpoint(8, "G8 fused G1-G6 body + G7 body into one body")

# ══════════════════════════════════════════════════════════════════════════
# G9 — Read S7: extrude-cut the profile 8 mm along +Z. S7's two short 0.2 mm
#   lines are intentional offsets so the cut boundary avoids coincident edges.
# ══════════════════════════════════════════════════════════════════════════
print(f"\n[G9] Reading {S_CSV[7].name} — extrude-cut S7 (+Z 8)")
s7_face, A7, P7 = face_from_profile(read_rows(S_CSV[7]))
print(f"     S7 plane: axis {A7.upper()}={P7}  area={float(s7_face.area):.3f} mm²")
g9_body = g8_body - extrude(s7_face, amount=8.0, dir=(0, 0, 1))
try:
    g9_body = maybe_clean(g9_body)
except Exception:
    pass
stage_pieces[:] = [g9_body]
checkpoint(9, "G9 extrude-cut S7 profile (+Z 8)")

# ══════════════════════════════════════════════════════════════════════════
# G10 — DEFERRED.  Spec: a continuous 1 mm round across all edges of the S8
#   chain (the outer edge loop of the G7 raised feature: top -> rounded corner
#   -> side -> bottom). Visually a standard constant-radius fillet (Fusion
#   applies it cleanly).
#
#   WHY DEFERRED: OCCT's fillet() cannot round these edges. Confirmed by test
#   that even the *standalone* G7 body (clean, valid) refuses the fillet at
#   r=1 AND r=0.5 — the S8 edges lie on boolean-INTERSECTION surfaces (S5∩S6),
#   which OCCT's fillet kernel won't fillet (Fusion's kernel can). Healing /
#   reordering / fusing-first do not help. The build123d route is a swept-bead
#   round (sweep a 1 mm quarter-round along the chain + boolean) — to be
#   implemented. For now G10 is a no-op; model stays at the G9 geometry.
# ══════════════════════════════════════════════════════════════════════════
print(f"\n[G10] DEFERRED — S8 round needs a swept-bead (OCCT fillet can't; see note)")
g10_body = g9_body

# ══════════════════════════════════════════════════════════════════════════
# G11 — S9: try a 2 mm fillet on the S9 step-1 line; if OCCT can't, fall back
#   to extrude-JOIN the S9 profile (steps 2..N, a closed YZ section at X=90.85)
#   along that step-1 line. S9 carries both: row 1 = the target line/path, the
#   remaining rows = the bead profile to sweep along it.
# ══════════════════════════════════════════════════════════════════════════
print(f"\n[G11] Reading {S_CSV[9].name} — fillet r=2 on step-1 line (else extrude-join)")
s9_rows  = read_rows(S_CSV[9])
path_row = s9_rows[0]
prof_rows = s9_rows[1:]
p1 = np.array([float(path_row["X1"]), float(path_row["Y1"]), float(path_row["Z1"])])
p2 = np.array([float(path_row["X2"]), float(path_row["Y2"]), float(path_row["Z2"])])

g11_src = g10_body
try:
    sols = g11_src.solids()
    if len(sols) == 1:
        g11_src = sols[0]
except Exception:
    pass

def _edge_matches_segment(e, a, b, tol=0.3):
    for t in np.linspace(0.0, 1.0, 7):
        v = e.position_at(float(t)); q = np.array([v.X, v.Y, v.Z])
        ab = b - a; L2 = float(ab @ ab)
        s = 0.0 if L2 == 0 else float((q - a) @ ab) / L2
        s = max(0.0, min(1.0, s))
        if np.linalg.norm(q - (a + s * ab)) > tol:
            return False
    return True

g11_body = None
fillet_edges = [e for e in g11_src.edges() if _edge_matches_segment(e, p1, p2)]
print(f"     step-1 line matched {len(fillet_edges)} body edge(s)")
if fillet_edges:
    try:
        g11_body = fillet(fillet_edges, radius=2.0)
        print("     fillet r=2 applied on step-1 line")
    except Exception as exc:
        print(f"     fillet not possible ({str(exc)[:45]}); using extrude-join")

if g11_body is None:
    prof_face, axp, plp = face_from_profile(prof_rows)
    ai = {"x": 0, "y": 1, "z": 2}[axp]
    base, tip = (p2, p1) if abs(p2[ai] - plp) <= abs(p1[ai] - plp) else (p1, p2)
    vec = tip - base
    length = float(np.linalg.norm(vec))
    d = tuple(float(x) for x in (vec / length))
    print(f"     extrude-join profile (area={float(prof_face.area):.3f}) along line, "
          f"len={length:.3f}, dir={tuple(round(x,2) for x in d)}")
    g11_body = g11_src + extrude(prof_face, amount=length, dir=d)

try:
    g11_body = maybe_clean(g11_body)
except Exception:
    pass
stage_pieces[:] = [g11_body]
checkpoint(11, "G11 fillet/extrude-join from S9 step-1 line")

# ══════════════════════════════════════════════════════════════════════════
# G11 + G12 together reproduce the (failed) 2 mm fillet on the S9 step-1 line:
# G11 joins the bead, G12 trims it to the rounded profile.
# G12 — extrude-cut the S10 profile (closed XY section at Z=10) by 8 mm +Z.
# ══════════════════════════════════════════════════════════════════════════
print(f"\n[G12] Reading {S_CSV[10].name} — extrude-cut S10 (+Z 8)")
s10_face, A10, P10 = face_from_profile(read_rows(S_CSV[10]))
print(f"     S10 plane: axis {A10.upper()}={P10}  area={float(s10_face.area):.3f} mm²")
g12_body = g11_body - extrude(s10_face, amount=8.0, dir=(0, 0, 1))
try:
    g12_body = maybe_clean(g12_body)
except Exception:
    pass
stage_pieces[:] = [g12_body]
checkpoint(12, "G12 extrude-cut S10 profile (+Z 8)")

# ══════════════════════════════════════════════════════════════════════════
# G13 — Extrude-cut the S11 circles (on the Y=131.5 back face) by 7 mm -Y and
#   1 mm +Y (the +Y overshoot avoids a coincident face). S11 circles are
#   encoded as 3-point arcs with start==end; the two distinct points are the
#   diameter ends.
# ══════════════════════════════════════════════════════════════════════════
print(f"\n[G13] Reading {S_CSV[11].name} — extrude-cut S11 circles (-Y 7 / +Y 1)")
g13_body = g12_body
n_holes = 0
for r in read_rows(S_CSV[11]):
    pts = _row_all_xyz_triples(r)
    a, b = np.array(pts[0]), np.array(pts[1])      # diameter endpoints
    cx, cz, y_c = (a[0] + b[0]) / 2, (a[2] + b[2]) / 2, a[1]
    rad = float(np.linalg.norm(a - b) / 2)
    face = circle_face_Y(cx, cz, rad, y_c)
    tool = (extrude(face, amount=7.0, dir=(0, -1, 0))
            + extrude(face, amount=1.0, dir=(0, 1, 0)))
    g13_body = g13_body - tool
    # 0.4 (45°) countersink chamfer at the hole end on the y=131.5 face.
    # Material is on the -Y side, open on +Y -> cone narrows to the hole radius
    # at y=131.1 and widens past the face (+0.3 overshoot avoids a coincident face).
    CH, OV = 0.4, 0.3
    cone = loft([circle_face_Y(cx, cz, rad,            y_c - CH),
                 circle_face_Y(cx, cz, rad + CH + OV,  y_c + OV)])
    g13_body = g13_body - cone
    n_holes += 1
    print(f"     hole @({cx:.2f},{cz:.2f}) Y={y_c} r={rad:.3f} + 0.4 countersink @y={y_c}")
try:
    g13_body = maybe_clean(g13_body)
except Exception:
    pass
stage_pieces[:] = [g13_body]
checkpoint(13, f"G13 extrude-cut {n_holes} S11 circles (-Y 7 / +Y 1)")

# ── Reusable swept-bead CUT: sweep a profile along an edge-chain path and cut.
#    Open path ends are extended `over` mm tangentially so the bead clears the
#    surface (no end-cap slivers). Used for fillet-rounds OCCT can't do.
def swept_bead_cut(body, path_rows, prof_rows, over=0.6, tag="sweep", join=False):
    _, axp, plp = detect_sketch_plane(path_rows)
    path_edges = [edge_from_row(r, axp, plp) for r in path_rows]
    def _ek(p): return (round(p.X, 3), round(p.Y, 3), round(p.Z, 3))
    deg = {}
    for e in path_edges:
        for k in (_ek(e.position_at(0.0)), _ek(e.position_at(1.0))):
            deg[k] = deg.get(k, 0) + 1
    open_keys = {k for k, d in deg.items() if d == 1}
    ext = []
    if over > 1e-9:                       # skip extension when over == 0
        for e in path_edges:
            a, b = e.position_at(0.0), e.position_at(1.0)
            if _ek(a) in open_keys:
                d = (a - b); d = d / d.length; ext.append(Edge.make_line(a, a + d * over))
            if _ek(b) in open_keys:
                d = (b - a); d = d / d.length; ext.append(Edge.make_line(b, b + d * over))
    path = max(Wire.combine(path_edges + ext, tol=1e-3), key=lambda w: len(w.edges()))
    pf, axf, plf = face_from_profile(prof_rows)
    print(f"     {tag}: profile area={float(pf.area):.3f} mm², "
          f"path extended {over} mm past {len(ext)} open end(s)")
    # Transition.ROUND + clean=False: rounds the bead at tight path corners so
    # it stays a valid solid; the default TRANSFORMED self-intersects there and
    # the cut OOMs.
    bead = sweep(pf, path=path, transition=Transition.ROUND, clean=False)
    return (body + bead) if join else (body - bead)

# ══════════════════════════════════════════════════════════════════════════
# G14 — Read S12 (edge selector on the Y=94.5 plane): apply a 0.8 mm fillet to
#   the body edges that lie along the S12 chain. If OCCT refuses them, fall back
#   to a swept-bead CUT of the S13 profile along the S12 chain.
# ══════════════════════════════════════════════════════════════════════════
print(f"\n[G14] Reading {S_CSV[12].name} — fillet r=0.8 on S12 edges")

def _points_along_edges(edges, n=22):
    pts = []
    for e in edges:
        for t in np.linspace(0.0, 1.0, n):
            v = e.position_at(float(t)); pts.append((v.X, v.Y, v.Z))
    return np.array(pts)

def _edge_on_cloud(e, cloud, tol):
    for t in np.linspace(0.0, 1.0, 7):
        v = e.position_at(float(t))
        d = np.sqrt(((cloud[:, 0] - v.X) ** 2 + (cloud[:, 1] - v.Y) ** 2
                     + (cloud[:, 2] - v.Z) ** 2)).min()
        if d > tol:
            return False
    return True

s12_rows = read_rows(S_CSV[12])
_, A12, P12 = detect_sketch_plane(s12_rows)
s12_cloud = _points_along_edges([edge_from_row(r, A12, P12) for r in s12_rows])

g14_src = g13_body
try:
    sols = g14_src.solids()
    if len(sols) == 1:
        g14_src = sols[0]
except Exception:
    pass

S12_TOL = 0.4
sel = [e for e in g14_src.edges() if _edge_on_cloud(e, s12_cloud, S12_TOL)]
print(f"     S12-matched edges: {len(sel)}")
g14_body = None
if sel:
    try:
        g14_body = fillet(sel, radius=0.8)
        print(f"     fillet r=0.8 applied to {len(sel)} edge(s) in one pass")
    except Exception as exc:
        print(f"     ⚠ batch fillet failed ({str(exc)[:45]}); per-edge")
        out = g14_src; done = 0; skip = set()
        while True:
            rem = [e for e in out.edges()
                   if _edge_on_cloud(e, s12_cloud, S12_TOL) and _edge_key(e) not in skip]
            if not rem:
                break
            e = rem[0]; k = _edge_key(e)
            try:
                out = fillet([e], radius=0.8); done += 1
            except Exception:
                skip.add(k)
        if done:
            g14_body = out
            print(f"     filleted {done} edge(s) individually, {len(skip)} skipped")
        else:
            print(f"     ⚠ OCCT could not fillet these edges — using S13 sweep cut")

if g14_body is None:
    g14_body = swept_bead_cut(g13_body, s12_rows, read_rows(S_CSV[13]), tag="G14")

g14_body = maybe_clean(g14_body)
stage_pieces[:] = [g14_body]
checkpoint(14, "G14 fillet r=0.8 on S12 edges (else S13 sweep cut)")

# ══════════════════════════════════════════════════════════════════════════
# G15 — Swept-bead CUT: sweep the S15 profile along the S14 edge chain (same
#   technique as G14's fallback).
# ══════════════════════════════════════════════════════════════════════════
print(f"\n[G15] Sweep-cut S15 profile along S14 edges")
g15_body = swept_bead_cut(g14_body, read_rows(S_CSV[14]), read_rows(S_CSV[15]), tag="G15")
g15_body = maybe_clean(g15_body)
stage_pieces[:] = [g15_body]
checkpoint(15, "G15 sweep-cut S15 profile along S14 edges")

# ══════════════════════════════════════════════════════════════════════════
# G16 — Extrude-cut the S18 profile SYMMETRICALLY by 5 mm each way along its
#   plane normal (the right-wall slot).
# ══════════════════════════════════════════════════════════════════════════
print(f"\n[G16] Reading {S_CSV[18].name} — symmetric extrude-cut ±5")
s18_face, A18, P18 = face_from_profile(read_rows(S_CSV[18]))
_NRM = {"x": (1, 0, 0), "y": (0, 1, 0), "z": (0, 0, 1)}[A18]
_NEG = tuple(-c for c in _NRM)
print(f"     S18 plane: axis {A18.upper()}={P18}  area={float(s18_face.area):.3f} mm²")
g16_body = g15_body - (extrude(s18_face, amount=5.0, dir=_NRM)
                       + extrude(s18_face, amount=5.0, dir=_NEG))
g16_body = maybe_clean(g16_body)
stage_pieces[:] = [g16_body]
checkpoint(16, "G16 symmetric extrude-cut S18 (+/-5)")

# ══════════════════════════════════════════════════════════════════════════
# G17 — Swept-bead CUT: sweep the S19 profile along the S20 edge chain
#   (step3<-step2<-step1->step4->step5), extending the two open ends 5 mm
#   linearly so the cut clears the surface.
# ══════════════════════════════════════════════════════════════════════════
print(f"\n[G17] Sweep-cut S19 profile along S20 edges (ends extended 5)")
g17_body = swept_bead_cut(g16_body, read_rows(S_CSV[20]), read_rows(S_CSV[19]),
                          over=5.0, tag="G17")
g17_body = maybe_clean(g17_body)
stage_pieces[:] = [g17_body]
checkpoint(17, "G17 sweep-cut S19 profile along S20 edges (ends +5)")

# ══════════════════════════════════════════════════════════════════════════
# G18 — Read S22 (single line at y=94.5, z=3): apply a 4 mm fillet to the
#   matching body edge. If OCCT can't, DEFER (a sweep-join profile will follow).
# ══════════════════════════════════════════════════════════════════════════
print(f"\n[G18] Reading {S_CSV[22].name} — fillet r=4 on S22 edge")
s22_rows = read_rows(S_CSV[22])
_, A22, P22 = detect_sketch_plane(s22_rows)
s22_cloud = np.array([(v.X, v.Y, v.Z)
                      for e in (edge_from_row(r, A22, P22) for r in s22_rows)
                      for t in np.linspace(0.0, 1.0, max(8, int(e.length / 0.1) + 2))
                      for v in (e.position_at(float(t)),)])
g18_src = g17_body
try:
    sols = g18_src.solids()
    if len(sols) == 1:
        g18_src = sols[0]
except Exception:
    pass
sel = [e for e in g18_src.edges() if _edge_on_cloud(e, s22_cloud, 0.4)]
print(f"     S22-matched edges: {len(sel)}")
g18_body = None
if sel:
    try:
        g18_body = fillet(sel, radius=4.0)
        print(f"     fillet r=4 applied to {len(sel)} edge(s)")
    except Exception as exc:
        print(f"     ⚠ fillet r=4 not possible ({str(exc)[:45]})")
if g18_body is None:
    # Fallback: sweep-JOIN the S23 profile along the S22 edge, EXTENDED on the
    # low-x end to x=111 (the original edge stops at x=115.34, leaving a gap).
    print("     sweep-join S23 along S22 edge, extended to x=112.16 to avoid gap")
    path_edge = make_line_edge((133.528767, 3.0), (112.16, 3.0), A22, P22)
    s23_face, _, _ = face_from_profile(read_rows(S_CSV[23]))
    bead = sweep(s23_face, path=Wire([path_edge]),
                 transition=Transition.ROUND, clean=False)
    g18_body = g18_src + bead
    # then extrude-cut S24 up to z=7.5 to trim the bead to the fillet shape
    # (sweep-join + this cut == the 4 mm fillet). -0.5 mm overshoot below z=0
    # avoids a coincident bottom face.
    s24_face, _, _ = face_from_profile(read_rows(S_CSV[24]))
    g18_body = g18_body - (extrude(s24_face, amount=7.5, dir=(0, 0, 1))
                           + extrude(s24_face, amount=0.5, dir=(0, 0, -1)))
    print("     extrude-cut S24 to z=7.5 (trims bead to fillet)")
g18_body = maybe_clean(g18_body)
stage_pieces[:] = [g18_body]
checkpoint(18, "G18 fillet r=4 on S22 edge (else S23 sweep-join, extended to x=111)")

# ══════════════════════════════════════════════════════════════════════════
# G19 — Read S25 (single line at y=106.5, z=3): apply a 4 mm fillet. If OCCT
#   can't (the edge is only ~3.3 mm long), DEFER (a sweep-join profile follows).
# ══════════════════════════════════════════════════════════════════════════
print(f"\n[G19] Reading {S_CSV[25].name} — fillet r=4 on S25 edge")
s25_rows = read_rows(S_CSV[25])
_, A25, P25 = detect_sketch_plane(s25_rows)
s25_cloud = np.array([(v.X, v.Y, v.Z)
                      for e in (edge_from_row(r, A25, P25) for r in s25_rows)
                      for t in np.linspace(0.0, 1.0, max(8, int(e.length / 0.1) + 2))
                      for v in (e.position_at(float(t)),)])
g19_src = g18_body
try:
    sols = g19_src.solids()
    if len(sols) == 1:
        g19_src = sols[0]
except Exception:
    pass
n_sel = len([e for e in g19_src.edges() if _edge_on_cloud(e, s25_cloud, 0.4)])
print(f"     S25-matched edges: {n_sel}")
# OCCT fillet r=4 here is DESTRUCTIVE (r=4 >> the 3.3 mm tab edge -> consumes
# features). Instead EXTRUDE-JOIN the S27 r=4 bead profile (on the x=125.96
# plane) along -X to the corner point at x=120.163.
s27_face, A27, P27 = face_from_profile(read_rows(S_CSV[27]))
g19_amt = P27 - 120.163                       # 125.9617 -> 120.163
print(f"     extrude-join S27 profile from x={P27:.3f} to x=120.163 (amt={g19_amt:.3f})")
g19_body = maybe_clean(g18_body + extrude(s27_face, amount=g19_amt, dir=(-1, 0, 0)))
stage_pieces[:] = [g19_body]
checkpoint(19, "G19 fillet r=4 on S25 edge (or deferred to sweep-join)")

# ══════════════════════════════════════════════════════════════════════════
# G20 — Extrude-cut the S28 profile (closed XY section at z=0) by 8 mm +Z.
#   With G19's extrude-join this trims the bead into the perfect 4 mm fillet
#   (join + cut == fillet). -0.5 mm overshoot below z=0 avoids a coincident
#   bottom face.
# ══════════════════════════════════════════════════════════════════════════
print(f"\n[G20] Reading {S_CSV[28].name} — extrude-cut S28 (+Z 8) to trim G19 fillet")
s28_face, A28, P28 = face_from_profile(read_rows(S_CSV[28]))
print(f"     S28 plane: axis {A28.upper()}={P28}  area={float(s28_face.area):.3f} mm²")
g20_body = g19_body - (extrude(s28_face, amount=8.0, dir=(0, 0, 1))
                       + extrude(s28_face, amount=0.5, dir=(0, 0, -1)))
g20_body = maybe_clean(g20_body)
stage_pieces[:] = [g20_body]
checkpoint(20, "G20 extrude-cut S28 (+Z 8) -> completes the G19 4mm fillet")

# ══════════════════════════════════════════════════════════════════════════
# G21 — Sweep-cut the S30 profile along the S29 3-D edge chain (line + arc +
#   10-point spline) -> a ~1 mm filleted surface. S29 is non-planar, so the
#   path edges are built from raw 3-D coordinates (with spline support); the
#   open ends are extended 0.6 mm tangentially to clear the surface.
# ══════════════════════════════════════════════════════════════════════════
print(f"\n[G21] Sweep-cut S30 profile along S29 edges (1-unit fillet surface)")

def _spline_pts(row):
    vals = []
    for k in ("X1", "Y1", "Z1", "X2", "Y2", "Z2", "X3", "Y3", "Z3"):
        v = row.get(k)
        if v not in (None, "") and str(v).strip().upper() != "NA":
            vals.append(float(v))
    for v in (row.get(None) or []):              # extra (unnamed) spline columns
        if v not in (None, "") and str(v).strip().upper() != "NA":
            vals.append(float(v))
    return [(vals[i], vals[i + 1], vals[i + 2]) for i in range(0, len(vals) - 2, 3)]

def _pts_collinear(pts, tol=1e-4):
    """True if all 3-D points lie on a single straight line (a Fusion 'spline'
    whose control points are actually collinear -> a degenerate spline that
    OCCT's sweep adaptor chokes on; build it as a Line instead)."""
    P = np.array(pts, dtype=float); d = P[-1] - P[0]; L = float(np.linalg.norm(d))
    if L < 1e-9:
        return True
    d = d / L
    return all(np.linalg.norm((p - P[0]) - np.dot(p - P[0], d) * d) < tol for p in P)

def _edges_3d(rows):
    es = []
    for r in rows:
        dt = _norm_draw_type(r["Draw Type"])
        if dt.startswith("line"):
            t = _row_all_xyz_triples(r); es.append(Edge.make_line(Vector(*t[0]), Vector(*t[1])))
        elif dt.startswith("3_point_arc"):
            t = _row_all_xyz_triples(r)
            es.append(Edge.make_three_point_arc(Vector(*t[0]), Vector(*t[1]), Vector(*t[2])))
        elif dt.startswith("spline"):
            sp = _spline_pts(r)
            if _pts_collinear(sp):
                es.append(Edge.make_line(Vector(*sp[0]), Vector(*sp[-1])))
            else:
                es.append(Edge.make_spline([Vector(*p) for p in sp]))
    return es

# Sweeping the whole 3-D path twists the section; do it EDGE-BY-EDGE on the
# straight edges instead (a straight path can't twist). S31 lies on a TILTED
# plane (perpendicular to the diagonal step-3), so its face is built in 3-D.
def _face_3d(rows):
    es = _edges_3d(rows)
    w = max(Wire.combine(es, tol=1e-3), key=lambda w: len(w.edges()))
    return Face(w)

def _extrude_cut_along(body, prof_rows, p1, p2, over=0.5, clip_xmax=None):
    # Sweep the profile with full overshoot at BOTH ends (a clean, correctly
    # oriented cut — shortening the path to over=0 makes build123d relocate the
    # section and leave a proud nub). To terminate the cut at a plane, pass
    # clip_xmax: the swept bead is trimmed to x <= clip_xmax before subtracting.
    face = _face_3d(prof_rows)
    d = p2 - p1; dn = d / d.length
    path = Wire([Edge.make_line(p1 - dn * over, p2 + dn * over)])   # extended
    bead = sweep(face, path=path, clean=False)                     # straight: no twist
    if clip_xmax is not None:
        bb = bead.bounding_box()
        x0, y0, z0 = bb.min.X - 1.0, bb.min.Y - 1.0, bb.min.Z - 1.0
        keep = Location(Vector(x0, y0, z0)) * Solid.make_box(
            clip_xmax - x0, bb.size.Y + 2.0, bb.size.Z + 2.0)
        bead = bead & keep                                         # x <= clip_xmax
        print(f"     cut profile (area={float(face.area):.3f}) clipped to x<={clip_xmax}")
    else:
        print(f"     cut profile (area={float(face.area):.3f}) along edge len={float(d.length):.3f}")
    return body - bead

g21_body = g20_body
# step 1 — S30 along the vertical edge (x=123.474, y=106.5, z 7..15)
g21_body = _extrude_cut_along(g21_body, read_rows(S_CSV[30]),
                              Vector(123.473586, 106.500006, 7.0),
                              Vector(123.473586, 106.500006, 15.0))
# step 3 — S31 along the diagonal edge at z=3. Terminate exactly at the far
# end x=127.18462 (over=0) so the cut does NOT overshoot into the step-4 spline
# region (which begins at x=127.204); overshoot only the junction end (over2)
# so it blends into the step-2 arc transition.
g21_body = _extrude_cut_along(g21_body, read_rows(S_CSV[31]),
                              Vector(127.184620, 98.541670, 3.0),
                              Vector(125.338817, 102.500006, 3.0),
                              over=0.5, clip_xmax=127.18462)
# step 2 transition — LOFT (multisection sweep) S30 -> S31 across the step-2
# arc only. Each profile is translated from its drawn position to its
# arc-endpoint junction (preserving orientation) so the loft isn't distorted:
#   S30 -> S1/S2 junction (123.474,106.5,7): drawn on step1 at z=11 -> shift -Z4
#   S31 -> S2/S3 junction (125.339,102.5,3): shift along step3 to its end
s30_face = Location(Vector(0.0, 0.0, -4.0)) * _face_3d(read_rows(S_CSV[30]))
s31_face = Location(Vector(-0.9234, 1.9800, 0.0)) * _face_3d(read_rows(S_CSV[31]))
print(f"     shifted S30 ctr={tuple(round(c,2) for c in s30_face.center())}, "
      f"S31 ctr={tuple(round(c,2) for c in s31_face.center())}")
s29_arc = _edges_3d([read_rows(S_CSV[29])[1]])[0]      # S29 step 2 (the arc)
try:
    bead_arc = sweep([s30_face, s31_face], path=Wire([s29_arc]),
                     multisection=True, clean=False)
    g21_body = g21_body - bead_arc
    print(f"     transition loft along step-2 arc: bead vol={float(bead_arc.volume):.3f}")
except Exception as exc:
    print(f"     ⚠ transition loft failed ({str(exc)[:50]})")

# step 4 — RUNOUT taper to a single POINT at (133.529,94.5,7). Uses the dedicated
# S39 fillet profile (steps 1-3 = line+line+arc = the closed 1-unit fillet cross
# section, already at the step-3/step-4 junction in Fusion coords) as the wide
# section. The two S33 splines are the two EDGES of the fillet surface; a single
# guide leaves the opposite edge ~0.33 mm off its rail (flat-facet artifact), so
# MakePipeShell is driven with rail-1 as the SPINE and rail-2 as the GUIDE ->
# BOTH edges pinned to BOTH rails (<0.1 mm). S39 sits exactly on the junction, so
# no shifting (the earlier S31-shift / cap-extract mis-placed the section).
def _pipe_taper_cut(body, prof_face, spine_wire, guide_wire, end_pt):
    ps = BRepOffsetAPI_MakePipeShell(spine_wire.wrapped)        # spine = S33 rail 1
    ps.SetMode(guide_wire.wrapped, True)                       # guide = S33 rail 2
    ps.Add(prof_face.outer_wire().wrapped, True, False)        # wide end (S31)
    ps.Add(BRepBuilderAPI_MakeVertex(gp_Pnt(*end_pt)).Vertex(), True, False)
    ps.Build(); ps.MakeSolid()
    bead = Solid(ps.Shape())
    fmax = max(bead.faces(), key=lambda f: f.area)
    print(f"     step-4 runout taper (rail-1 spine, rail-2 guide): bead "
          f"vol={float(bead.volume):.3f} valid={bead.is_valid} fillet-face={float(fmax.area):.2f}")
    return body - bead

s31_step4  = Location(Vector(0.9226, -1.9780, 0.0)) * _face_3d(read_rows(S_CSV[31]))
s33_rows   = read_rows(S_CSV[33])
s33_rail1  = Wire([_edges_3d([s33_rows[0]])[0]])               # S33 rail 1 -> spine
s33_rail2  = Wire([_edges_3d([s33_rows[1]])[0]])               # S33 rail 2 -> guide
try:
    g21_body = _pipe_taper_cut(g21_body, s31_step4, s33_rail1, s33_rail2,
                               (133.528767, 94.5, 7.0))
except Exception as exc:
    print(f"     ⚠ step-4 pipe taper failed ({str(exc)[:60]})")

g21_body = maybe_clean(g21_body)
stage_pieces[:] = [g21_body]
checkpoint(21, "G21 fillet step1-4 (arc loft + S33-guided step-4 taper)")

# ══════════════════════════════════════════════════════════════════════════
# G22 — Sweep-CUT the S35 profile along the S34 edge chain (line + arc + line +
#   arc + 4 splines). S34 is a non-planar 3-D path, so the edges are built with
#   the 3-D builder (_edges_3d) which now also demotes collinear "splines" (the
#   straight z18->z17 segment) to lines — OCCT's sweep adaptor fails on those.
#   NOTE: tangential open-end extension makes THIS swept bead self-intersect
#   (invalid solid -> the boolean silently no-ops), so over=0 here: the raw S34
#   path already runs face-to-face. Transition.ROUND keeps it valid at corners.
# ══════════════════════════════════════════════════════════════════════════
print(f"\n[G22] Sweep-cut S35 profile along S34 edges")

def _sweep_cut_3d(body, path_rows, prof_face, tag="G22"):
    # The groove is a CONSTANT S35 section along S34 steps 1-7, then RUNS OUT to
    # a point along step-8 (the curving spline at the end). A plain constant
    # sweep over the whole chain leaves a flat profile END-CAP (the triangular
    # face); Fusion tapers smoothly to the step-8 endpoint vertex. So: sweep the
    # constant part, take its end-cap cross-section at the step7/8 junction, and
    # taper THAT down to the endpoint vertex with MakePipeShell (runout bead).
    pe = _edges_3d(path_rows)
    body_path = max(Wire.combine(pe[:-1], tol=1e-2), key=lambda w: len(w.edges()))
    bead1 = sweep(prof_face, path=body_path, transition=Transition.ROUND, clean=False)
    junc = pe[-1].position_at(0.0); end = pe[-1].position_at(1.0)
    # the end cap is the small face (~profile area) nearest the step7/8 junction
    cap = min((f for f in bead1.faces()
               if abs(f.area - prof_face.area) < 0.5 * prof_face.area),
              key=lambda f: (f.center() - junc).length)
    ps = BRepOffsetAPI_MakePipeShell(Wire([pe[-1]]).wrapped)
    ps.Add(cap.outer_wire().wrapped, False, False)
    ps.Add(BRepBuilderAPI_MakeVertex(gp_Pnt(end.X, end.Y, end.Z)).Vertex(), False, False)
    ps.Build(); ps.MakeSolid()
    bead2 = Solid(ps.Shape())
    print(f"     {tag}: profile area={float(prof_face.area):.3f} mm²; constant bead "
          f"vol={float(bead1.volume):.3f} ({len(pe)-1} edges) + step-8 runout taper "
          f"vol={float(bead2.volume):.3f} valid={bead2.is_valid}")
    return (body - bead1) - bead2

g22_body = _sweep_cut_3d(g21_body, read_rows(S_CSV[34]),
                         _face_3d(read_rows(S_CSV[35])))
g22_body = maybe_clean(g22_body)
stage_pieces[:] = [g22_body]
checkpoint(22, "G22 sweep-cut S35 profile along S34 edges")

# ══════════════════════════════════════════════════════════════════════════
# G23 — Fillet-JOIN a 2 mm fillet along the S37 perimeter (where the wall meets
#   the z=3 floor). OCCT's fillet() is destructive on this body, and a single
#   continuous sweep self-intersects at the tight perimeter corners, so the
#   fillet is built PER-EDGE from a freshly-CONSTRUCTED profile (per the Fusion
#   recipe), then fused into the body:
#     - frame at each edge: horizontal tangent T, up=+Z (wall), side=inward
#       (toward the part interior, ⟂ to T) = floor direction.
#     - 2 mm arc tangent to the wall (at P+up·R) and the floor (at P+side·R),
#       bulging toward the corner P.
#     - close back through an apex offset 0.1 mm INTO both surfaces (penetrates
#       the wall/floor so the fuse isn't coplanar -> no null-triangulation).
#   The profile is built at each edge start and swept along that one edge (a
#   straight sweep can't twist; arcs are refit as splines if OCCT balks). This
#   gives a consistent, on-surface fillet with no deflection or flying ribbons.
# ══════════════════════════════════════════════════════════════════════════
print(f"\n[G23] Fillet-join 2 mm fillet along S37 perimeter (per-edge construct + fuse)")

_FILLET_R, _FILLET_OFF = 2.0, 0.1
_Cpart = np.array(list(g22_body.center()))           # interior reference

def _probe_inside(Q):
    return point_inside(g22_body, Q[0], Q[1], Q[2])

def _fillet_frame(P, T, Pm, target_up=None):
    """Return (up, side) for the fillet at edge point P, both perpendicular to
    the edge. For ~horizontal edges: up=+Z (wall), side=horizontal (floor),
    inward sense chosen so the fillet fills the OPEN corner. For SLOPED edges
    (the z7->z3 ramp) +Z isn't perpendicular to the edge, so build a frame
    perpendicular to the true tangent and PROBE the body to find which (up,side)
    quadrant is the open concave corner (material behind both axes, open on the
    diagonal)."""
    T3 = np.array([T[0], T[1], T[2]], float); T3 = T3 / (np.linalg.norm(T3) or 1.0)
    d = _FILLET_R * 0.6
    if abs(T3[2]) < 0.15:                                 # ~horizontal edge (flat run)
        up = np.array([0.0, 0.0, 1.0])
        side = np.cross(up, np.array([T3[0], T3[1], 0.0]))
        side = side / (np.linalg.norm(side) or 1.0)
        inw = _Cpart - Pm; inw[2] = 0.0          # toward part interior (horizontal)
        if np.linalg.norm(inw) > 1e-6 and np.dot(side, inw) < 0:
            side = -side
        if _probe_inside(Pm + side * d + up * d):
            side = -side
        return up, side
    # sloped edge: frame ⟂ to the true tangent, then probe for the open corner
    a = np.array([0.0, 0.0, 1.0]) - T3 * T3[2]            # +Z projected ⟂ to T
    if np.linalg.norm(a) < 0.1:
        a = np.array([1.0, 0.0, 0.0]) - T3 * T3[0]
    a = a / (np.linalg.norm(a) or 1.0)
    b = np.cross(T3, a); b = b / (np.linalg.norm(b) or 1.0)
    # collect ALL valid concave-corner orientations, then prefer the one whose
    # 'up' points most upward (+Z) — for a steep edge several quadrants can pass
    # the probe, and the first one isn't necessarily the wall/floor we want.
    cands = []
    for up in (a, -a):
        for side in (b, -b):
            wall = _probe_inside(Pm - up * d)             # material behind the 'wall'
            floor = _probe_inside(Pm - side * d)          # material behind the 'floor'
            openc = not _probe_inside(Pm + up * d + side * d)   # corner is open
            if wall and floor and openc:
                cands.append((float(up[2]), up, side))
    if cands:
        if target_up is not None:                         # continuity: match neighbour
            cands.sort(key=lambda c: -float(np.dot(c[1], target_up)))
        else:
            cands.sort(key=lambda c: -c[0])               # else most-upward 'up'
        return cands[0][1], cands[0][2]
    return a, b

def _fillet_profile(P, up, side):
    R, off = _FILLET_R, _FILLET_OFF
    Pw = P + up * R; Pf = P + side * R
    Cc = P + side * R + up * R
    mid = Cc + (P - Cc) / np.linalg.norm(P - Cc) * R
    corner = P - side * off - up * off
    return Face(Wire([
        Edge.make_three_point_arc(Vector(*Pw), Vector(*mid), Vector(*Pf)),
        Edge.make_line(Vector(*Pf), Vector(*corner)),
        Edge.make_line(Vector(*corner), Vector(*Pw)),
    ]))

g23_body = g22_body
_joined = 0
s37_edges = _edges_3d(read_rows(S_CSV[37]))

# Continuity seed for the leading STEEP run (the z7->z3 ramp, e0/e1): a steep
# edge can pass the corner probe in more than one orientation, so decide them
# from the flat side inward — e1 targets +Z (it abuts the flat e2), then e0
# targets e1's 'up' — instead of letting the steepest edge guess alone.
_pre_frame = {}
_zup = np.array([0.0, 0.0, 1.0])
_lead = 0
while _lead < len(s37_edges) and abs(np.array(list(s37_edges[_lead].tangent_at(0.0)))[2]) >= 0.15:
    _lead += 1
if _lead >= 2:                                   # e.g. e0,e1 both steep
    _tgt = _zup
    for _j in range(_lead - 1, -1, -1):          # from flat-adjacent inward
        _ej = s37_edges[_j]
        _Pj = np.array(list(_ej.position_at(0.0)))
        _Tj = np.array(list(_ej.tangent_at(0.0)))
        _Pmj = np.array(list(_ej.position_at(0.5)))
        _uj, _sj = _fillet_frame(_Pj, _Tj, _Pmj, target_up=_tgt)
        _pre_frame[_j] = (_uj, _sj); _tgt = _uj

def _chord_join(body, e, seed_up=None, n=6):
    """Subdivide an edge into straight chords and fillet each — chords can't
    twist (so a steep CURVED edge stays upright) and dodge tight-arc self-
    intersection. The per-chord 'up' is threaded for continuity (seed_up)."""
    pp = [e.position_at(float(t)) for t in np.linspace(0.0, 1.0, n)]
    tgt = seed_up; sub = 0
    for k in range(len(pp) - 1):
        Pk = np.array(list(pp[k])); Tk = np.array(list(pp[k + 1])) - Pk
        Pmk = (Pk + np.array(list(pp[k + 1]))) / 2.0
        try:
            u, s = _fillet_frame(Pk, Tk, Pmk, target_up=tgt)
            bead = sweep(_fillet_profile(Pk, u, s),
                         path=Wire([Edge.make_line(pp[k], pp[k + 1])]),
                         transition=Transition.RIGHT, clean=False)
            if float(bead.volume) > 0.01:
                vb = body.volume; nb = body + bead
                if nb.volume > vb + 0.005:
                    body = nb; sub += 1; tgt = u
        except Exception:
            pass
    return body, sub

# SKIP the very steep CURVED leading edge (the steepest part of the z7->z3 ramp):
# a single sweep twists the profile along its curvature and chord sub-fillets
# facet it — neither reads cleanly on this short start edge, so it's omitted
# (the fillet runs continuously from the next edge onward).
_skip_edges = {i for i in range(_lead)
               if str(s37_edges[i].geom_type) != "GeomType.LINE"
               and abs(np.array(list(s37_edges[i].tangent_at(0.0)))[2]) >= 0.75}

for _ei, _e in enumerate(s37_edges):
    P0 = np.array(list(_e.position_at(0.0))); T0 = np.array(list(_e.tangent_at(0.0)))
    Pm = np.array(list(_e.position_at(0.5)))
    if _ei in _skip_edges:
        print(f"     step{_ei+1}(e{_ei}): skipped (steep ramp start — twists/facets)")
        continue
    try:
        up, side = _pre_frame.get(_ei) or _fillet_frame(P0, T0, Pm)
        prof = _fillet_profile(P0, up, side)
    except Exception as _ex:
        print(f"     step{_ei+1}(e{_ei}): profile FAIL {str(_ex)[:30]}"); continue
    _done = False
    for _mk in (lambda: _e,                                    # exact edge
                lambda: Edge.make_spline([_e.position_at(float(t))   # spline refit (tight arcs)
                                          for t in np.linspace(0.0, 1.0, 12)])):
        try:
            bead = sweep(prof, path=Wire([_mk()]), transition=Transition.RIGHT, clean=False)
            if float(bead.volume) <= 0.01:
                continue
            v_before = g23_body.volume
            nb = g23_body + bead
            dv = nb.volume - v_before
            if dv > 0.005:
                g23_body = nb; _joined += 1; _done = True
                print(f"     step{_ei+1}(e{_ei}): bead={float(bead.volume):.2f} fused Δ={dv:.2f}")
                break
        except Exception:
            pass
    if not _done:
        # fallback: subdivide into chords (dodges tight-arc self-intersection)
        g23_body, _sub = _chord_join(g23_body, _e)
        if _sub:
            _joined += 1
            print(f"     step{_ei+1}(e{_ei}): joined via {_sub} chord sub-fillets")
        else:
            print(f"     step{_ei+1}(e{_ei}): NOT joined")
print(f"     2 mm fillet profile (area≈1.06 mm²); fused {_joined}/{len(s37_edges)} "
      f"fillet segments")
g23_body = maybe_clean(g23_body)
stage_pieces[:] = [g23_body]
checkpoint(23, "G23 fillet-join 2 mm fillet along S37 perimeter (per-edge construct)")

# ══════════════════════════════════════════════════════════════════════════
# G24 — Extrude-cut the 6 S1 ovals (4 small + 2 large) by 7 mm in +Z. The ovals
# are already pierced (G1); this trims the G23 perimeter-rib material that
# overhangs the holes. Cutting to 7 mm (was 4) clears any rib left above z=4.
# ══════════════════════════════════════════════════════════════════════════
print(f"\n[G24] Extrude-cut 6 S1 ovals (+Z 7 mm) — clear G23 rib overhang")
g24_body = g23_body
_orem = 0.0
for _rid in OVAL_ROWS:
    _of = face_from_edges(edges_from_rowids(s1_rows, _rid, S1_AXIS, S1_PLANE))
    _tool = extrude(_of, amount=7.0, dir=up)                  # +Z by 7 mm
    _vb = g24_body.volume
    g24_body = g24_body - _tool
    _orem += _vb - g24_body.volume
print(f"     removed {_orem:.3f} mm³ across {len(OVAL_ROWS)} ovals")
g24_body = maybe_clean(g24_body)
stage_pieces[:] = [g24_body]
checkpoint(24, "G24 extrude-cut 6 S1 ovals (+Z 7 mm)")

# ══════════════════════════════════════════════════════════════════════════
# G25 — Extrude-cut the S40 profile (a closed loop at x≈120.2, in the Y-Z plane)
#   3 mm in -X and 0.01 mm in +X (the hair of +X overshoot avoids a coplanar
#   face at the profile plane). Trims the small protrusion at the boss.
# ══════════════════════════════════════════════════════════════════════════
print(f"\n[G25] Extrude-cut S40 profile (-X 3 mm, +X 0.01 mm)")
g25_body = g24_body
_s40 = _face_3d(read_rows(S_CSV[40]))
_tool = (extrude(_s40, amount=3.0,  dir=(-1, 0, 0))
         + extrude(_s40, amount=0.01, dir=(1, 0, 0)))
_vb = g25_body.volume
g25_body = g25_body - _tool
print(f"     S40 area={float(_s40.area):.3f} mm²; removed {float(_vb - g25_body.volume):.3f} mm³")
g25_body = maybe_clean(g25_body)
stage_pieces[:] = [g25_body]
checkpoint(25, "G25 extrude-cut S40 (-X 3 mm / +X 0.01 mm)")

# ══════════════════════════════════════════════════════════════════════════
# G26 — 1-unit fillet along the S41 edge chain (cable-bridge arm corner, z3.4-15).
#   OCCT fillet(r=1) fails on this body, and sweeping the supplied S42 profile
#   fails because the S41 edge runs THROUGH the S42 cross-section (a slight
#   misposition). So the fillet is CONSTRUCTED per edge (the documented recipe):
#   1-mm arc tangent to the two faces, apex offset 0.1 mm in, frame picked by a
#   point-inside probe. Curved edges sweep directly; the straight upper edge is
#   chord-subdivided.
# ══════════════════════════════════════════════════════════════════════════
print(f"\n[G26] 1-unit fillet along S41 edges (per-edge construct)")
_R26, _OFF26 = 1.0, 0.1
_C26 = np.array(list(g25_body.center()))

def _pin26(Q):
    return point_inside(g25_body, float(Q[0]), float(Q[1]), float(Q[2]))

def _frame26(P, T, Pm):
    T3 = np.array(T, float); T3 /= (np.linalg.norm(T3) or 1.0); d = _R26 * 0.6
    if abs(T3[2]) < 0.15:                                  # ~horizontal edge
        up = np.array([0.0, 0.0, 1.0])
        side = np.cross(up, np.array([T3[0], T3[1], 0.0])); side /= (np.linalg.norm(side) or 1.0)
        inw = _C26 - Pm; inw[2] = 0.0
        if np.linalg.norm(inw) > 1e-6 and np.dot(side, inw) < 0: side = -side
        if _pin26(Pm + side * d + up * d): side = -side
        return up, side
    a = np.array([0.0, 0.0, 1.0]) - T3 * T3[2]
    if np.linalg.norm(a) < 0.1: a = np.array([1.0, 0.0, 0.0]) - T3 * T3[0]
    a /= (np.linalg.norm(a) or 1.0); bb = np.cross(T3, a); bb /= (np.linalg.norm(bb) or 1.0)
    cl = []
    for up in (a, -a):
        for side in (bb, -bb):
            if _pin26(Pm - up * d) and _pin26(Pm - side * d) and not _pin26(Pm + up * d + side * d):
                cl.append((float(up[2]), up, side))
    if cl:
        cl.sort(key=lambda c: -c[0]); return cl[0][1], cl[0][2]
    return a, bb

def _prof26(P, up, side):
    R, off = _R26, _OFF26
    Pw = P + up * R; Pf = P + side * R; Cc = P + side * R + up * R
    mid = Cc + (P - Cc) / np.linalg.norm(P - Cc) * R; cor = P - side * off - up * off
    return Face(Wire([
        Edge.make_three_point_arc(Vector(*Pw), Vector(*mid), Vector(*Pf)),
        Edge.make_line(Vector(*Pf), Vector(*cor)),
        Edge.make_line(Vector(*cor), Vector(*Pw)),
    ]))

# The user's actual S42 fillet profile (1-mm arc + tangent lines, in the Y-Z
# plane at z≈11.74, sitting ON the step-1 edge). Used for the straight step-1
# edge by EXTRUDING it along the edge (a sweep fails — the edge runs through the
# profile). Its normal is +Z, aligned with the vertical step-1 edge.
_s42_face = Face(closed_wire(_edges_3d(read_rows(S_CSV[42])), tol=1e-2))

def _fillet_cut_edge(body, e, ext_profile=None):
    P0 = np.array(list(e.position_at(0.0))); P1 = np.array(list(e.position_at(1.0)))
    Pm = np.array(list(e.position_at(0.5)))
    d = P1 - P0; L = float(np.linalg.norm(d)); Tn = d / (L or 1.0)
    straight = np.linalg.norm(Pm - (P0 + d * 0.5)) < 1e-4    # mid on the chord -> straight
    up, side = _frame26(P0, Tn, Pm)
    prof = _prof26(P0, up, side)
    if straight:
        # straight edge: EXTRUDE the profile along the edge (robust, no MakePipe-
        # Shell, no facets) with a hair of overshoot both ends. Prefer the user's
        # S42 profile when supplied (it gives the smooth cylindrical fillet face).
        try:
            if ext_profile is not None:
                # S42 is in the X-Y plane on the edge's XY; drop it to the edge
                # start (−0.2 overshoot) and extrude up the edge.
                src = Location(Vector(0, 0, (P0[2] - 0.2) - ext_profile.center().Z)) * ext_profile
            else:
                src = Location(Vector(*(-Tn * 0.2))) * prof
            tool = extrude(src, amount=L + 0.4, dir=tuple(Tn))
            nb = body - tool
            if body.volume - nb.volume > 0.005:
                return nb, body.volume - nb.volume
        except Exception:
            pass
    else:
        try:
            bead = sweep(prof, path=Wire([e]), transition=Transition.RIGHT, clean=False)
            nb = body - bead
            if body.volume - nb.volume > 0.005:
                return nb, body.volume - nb.volume
        except Exception:
            pass
    # chord fallback (curved edge that won't sweep)
    pp = [e.position_at(float(t)) for t in np.linspace(0.0, 1.0, 6)]; rem = 0.0
    for k in range(len(pp) - 1):
        Pk = np.array(list(pp[k])); Tk = np.array(list(pp[k + 1])) - Pk
        Pmk = (Pk + np.array(list(pp[k + 1]))) / 2.0
        try:
            u, s = _frame26(Pk, Tk, Pmk)
            bead = sweep(_prof26(Pk, u, s), path=Wire([Edge.make_line(pp[k], pp[k + 1])]),
                         transition=Transition.RIGHT, clean=False)
            nb = body - bead
            if body.volume - nb.volume > 0.005:
                body = nb; rem += body.volume - nb.volume
        except Exception:
            pass
    return body, rem

g26_body = g25_body
_fr = 0
_s41_edges = _edges_3d(read_rows(S_CSV[41]))
for _ei, _e in enumerate(_s41_edges):
    # step-1 edge (straight, vertical) uses the user's S42 profile (smooth
    # cylindrical fillet); the curved edges use the constructed 1-mm profile.
    _ovr = _s42_face if _ei == 0 else None
    g26_body, _rv = _fillet_cut_edge(g26_body, _e, ext_profile=_ovr)
    if _rv > 0.0:
        _tag = " (S42 profile)" if _ei == 0 else ""
        _fr += 1; print(f"     S41 edge {_ei}: filleted (−{_rv:.3f} mm³){_tag}")
    else:
        print(f"     S41 edge {_ei}: nothing to fillet")
print(f"     1-unit fillet applied on {_fr}/{len(_edges_3d(read_rows(S_CSV[41])))} S41 edges")
g26_body = maybe_clean(g26_body)
stage_pieces[:] = [g26_body]
checkpoint(26, "G26 1-unit fillet along S41 edges (per-edge construct)")

# ══════════════════════════════════════════════════════════════════════════
# G3 — EXPORT (ALWAYS LAST): produce a WATERTIGHT STL.
#
#   1. Apply .clean() on the final compound to remove micro-scars accumulated
#      during cutting / joining / mirroring. (Necessary but NOT sufficient on its
#      own for this part — the boolean history still leaves ~zero-area sliver
#      faces that OCCT's STL writer skips, leaving holes; the raw STL then fails
#      validators / Fusion with "mesh not oriented" / "not positive volume" /
#      "not a closed mesh".)
#
#   2. _watertight_stl() then guarantees a closed, manifold STL (see that
#      function). In short:
#        a. STEP export+import ROUND-TRIP — re-parametrizes the surfaces; the
#           in-memory boolean result meshes with un-repairable sliver artifacts,
#           but the round-tripped solid meshes cleanly. (This was THE key step.)
#        b. Conformal mesh with BRepMesh (parallel=False -> deterministic, so a
#           teammate re-running the script gets the identical result).
#        c. Iterative repair: strip non-manifold faces + fill holes -> a valid
#           in-memory manifold; manifold3d re-meshes to split self-touches; a
#           final strip/fill resolves the residual non-manifold edges.
#        d. Verify the EXPORTED STL reloads strictly watertight (else fall back
#           to a raw export with a warning).
#
#   Requires `trimesh` and `manifold3d` (pip install trimesh manifold3d).
#   Exports the watertight STL only (a temporary .step is used internally for
#   the round-trip and deleted).
# ══════════════════════════════════════════════════════════════════════════
print(f"\n[G3] Export — compounding {len(stage_pieces)} body(ies), "
      f"applying .clean(), then watertight STL export.")

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

FINAL_STL  = BASE_DIR / f"{SCRIPT_STEM}.stl"
FINAL_TXT  = BASE_DIR / f"{SCRIPT_STEM}_summary.txt"

# ── Watertight STL export ──────────────────────────────────────────────────
# The B-rep solid is valid, but the complex boolean history leaves a handful of
# ZERO-AREA sliver faces that OCCT's STL writer skips ("null triangulation"),
# making the raw STL non-manifold (solid=False in validators). We mesh the
# solid conformally, fan-close the resulting sliver holes, run manifold3d, then
# iteratively strip non-manifold faces + fill, until trimesh reports watertight.
def _watertight_stl(shape, out_path, defl=0.1):
    import trimesh
    from OCP.BRepMesh import BRepMesh_IncrementalMesh
    from OCP.TopExp import TopExp_Explorer
    from OCP.TopAbs import TopAbs_FACE
    from OCP.TopoDS import TopoDS as _TDS
    from OCP.BRep import BRep_Tool
    from OCP.TopLoc import TopLoc_Location
    # Normalize the solid through a STEP export+import round-trip: the in-memory
    # boolean result meshes with extra sliver artifacts (un-repairable), but the
    # round-tripped geometry meshes cleanly (re-parametrized surfaces) and repairs
    # to watertight deterministically.
    try:
        _stp = str(out_path) + ".norm.step"
        export_step(shape, _stp)
        shape = import_step(_stp).wrapped
        import os as _os
        try: _os.remove(_stp)
        except Exception: pass
    except Exception:
        shape = shape.wrapped if hasattr(shape, "wrapped") else shape
    if hasattr(shape, "wrapped"):
        shape = shape.wrapped

    from OCP.BRepTools import BRepTools
    def conformal(sh, dd=defl):
        BRepTools.Clean_s(sh)                                 # drop any cached triangulation
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
        return trimesh.Trimesh(np.array(V), np.array(T), process=True)

    def fanfill(m):
        u, c = np.unique(m.edges_sorted, axis=0, return_counts=True); bnd = u[c == 1]
        if len(bnd) == 0:
            return m
        par = {}
        def fnd(x):
            par.setdefault(x, x)
            while par[x] != x: par[x] = par[par[x]]; x = par[x]
            return x
        for a, b in bnd: par[fnd(int(a))] = fnd(int(b))
        from collections import defaultdict
        comp = defaultdict(list)
        for a, b in bnd: comp[fnd(int(a))].append((int(a), int(b)))
        V = list(m.vertices); F = list(m.faces)
        for _, edges in comp.items():
            vids = {x for e in edges for x in e}
            ctr = np.mean([V[i] for i in vids], 0); ci = len(V); V.append(ctr)
            for a, b in edges: F.append((ci, a, b))
        return trimesh.Trimesh(np.array(V), np.array(F), process=True)

    def clean(m):
        for _ in range(12):
            u, c = np.unique(m.edges_sorted, axis=0, return_counts=True)
            nm = set(map(tuple, u[c > 2]))
            if not nm and (c == 1).sum() == 0:
                break
            if nm:
                ue = m.edges_unique; bad = set()
                for fi, ei in enumerate(m.faces_unique_edges):
                    for k in ei:
                        a, b = ue[k]
                        if (min(a, b), max(a, b)) in nm: bad.add(fi); break
                if bad:
                    keep = np.ones(len(m.faces), bool); keep[list(bad)] = False
                    m.update_faces(keep); m.remove_unreferenced_vertices()
            trimesh.repair.fill_holes(m); trimesh.repair.fix_normals(m)
            if m.is_watertight:
                break
        return m

    import os
    tmp = str(out_path) + ".tmp.stl"
    try:
        import manifold3d as m3d
    except Exception:
        m3d = None

    def _through_manifold(cand):
        # run a candidate closed-ish mesh through manifold3d, round-trip, final
        # clean; return the mesh if its EXPORTED STL reloads strictly watertight.
        if m3d is None:
            return None
        try:
            om = m3d.Manifold(m3d.Mesh(vert_properties=np.asarray(cand.vertices, np.float32),
                                       tri_verts=np.asarray(cand.faces, np.uint32))).to_mesh()
            if not len(om.tri_verts):
                return None
            mm = trimesh.Trimesh(np.asarray(om.vert_properties)[:, :3].astype(np.float64),
                                 np.asarray(om.tri_verts), process=False)
            mm.export(tmp); mm = trimesh.load(tmp)      # round-trip re-merges the split
            mm = clean(mm)                              # strip+fill the residual non-manifold
            mm.export(tmp)
            return mm if trimesh.load(tmp).is_watertight else None
        except Exception:
            return None

    # Try both the clean-first and fan-first manifold candidates across several
    # mesh deflections; keep the first that reloads strictly watertight.
    result, fallback = None, None
    # Solid is deterministic; defl=0.05 repairs it cleanly. A couple of nearby
    # values are kept only as a safety net (each is tried fresh via BRepTools.Clean).
    _defls = [0.05, 0.045, 0.055, 0.04]
    for d in _defls:
        cm = conformal(shape, d)
        for cand in (clean(cm.copy()), fanfill(cm.copy())):
            if fallback is None:
                fallback = cand
            if cand.is_watertight:                      # already watertight? confirm via reload
                cand.export(tmp)
                if trimesh.load(tmp).is_watertight:
                    result = cand; break
            r = _through_manifold(cand)
            if r is not None:
                result = r; break
        if result is not None:
            break
    if result is None:
        result = fallback if fallback is not None else clean(conformal(shape, defl))
    result.export(str(out_path))
    try: os.remove(tmp)
    except Exception: pass
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

summary_lines = [
    "=" * 70,
    f"BUILD SUMMARY  :  {FOLDER_NAME}",
    f"Time           :  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
    f"Range covered  :  {GUIDELINE_RANGE}",
    f"Guidelines     :  G1, G2, G4, G5, G6, G7, G8, G9, G11, G12, G13, G14, G15, G16, G17, G18, G19, G20, G21 (G10 deferred; G3 = export, last)",
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
