"""
[a]_z_cover_left.py

This part has TWO bodies:
  BODY 1 — the z-cover plate (sketches S1..S4), guidelines G1..G12 (G3 = export).
  BODY 2 — the S5 link, its own guideline numbering starting at G1.
Each body restarts guideline numbering at G1; ACTIVE_BODY + VIEW_AT select which
body's guideline the review checkpoint stops at.  The final export compounds both.

Sketch summary (plane auto-detected from CSV):
  S1  Z = -25.993   ONE closed OUTER OUTLINE (15 Lines + 19 three-point arcs,
                    rows 1..34, a rounded plate with an interior tongue/slot) +
                    5 three-point CIRCLES + 1 TRIANGLE (3 Lines).  (TOP face.)
  S2  Z = -28.993   THREE dia-6.0 CIRCLES (concentric with the S1 3.5-dia through
                    holes) each split by 4 Lines into 5 sections.  (BOTTOM face.)

Region structure S1 (Fusion_Coordinates_S1.csv), all on the Z=-25.993 plane:
  - OUTER OUTLINE  : rows 1..34   (Lines + fillet arcs -> one closed wire)
  - 3.5 dia CIRCLE : row 35  centre (57.649, 35.924)   r=1.750  -> THROUGH HOLE
  - 3.5 dia CIRCLE : row 36  centre (57.649,-10.725)   r=1.750  -> THROUGH HOLE
  - 3.5 dia CIRCLE : row 37  centre (15.000,-10.725)   r=1.750  -> THROUGH HOLE
  - 3.2 dia CIRCLE : row 38  centre (37.501, -9.575)   r=1.600  -> G2 pocket 1.4
  - 3.2 dia CIRCLE : row 39  centre (56.499,  9.424)   r=1.600  -> G2 pocket 1.4
  - TRIANGLE       : rows 40,41,42 (3 Lines)                    -> G4 pocket 0.6

Region structure S2 (Fusion_Coordinates_S2.csv), all on the Z=-28.993 plane:
  - 3 dia-6.0 CIRCLES: rows 1,2,3  centres (57.649,35.924)/(57.649,-10.725)/
                       (15.000,-10.725)  r=3.0  -> concentric counterbores.
  - 12 LINES (rows 4..15): 4 per circle = two verticals at x=cx±1.75 + two
    horizontals at y=cy±1.75, splitting each circle into 5 sections:
      * CENTRAL  : the 3.5x3.5 square (between both verticals & both horizontals)
      * SMALL x2 : top & bottom caps (between the verticals, beyond a horizontal)
      * LARGE x2 : left & right circular segments (beyond a vertical)
    (Verified: cap area 3.745 < segment area 4.268 -> caps=small, segments=large.)

Guidelines (executed in topological order; G3 = export, ALWAYS last):
  G1 - READ S1. Build the outer outline; subtract the THREE 3.5-dia circles as
       THROUGH HOLES; extrude the resulting plate 3 units along -Z
       (Z=-25.993 -> Z=-28.993).  The two 3.2-dia circles and the triangle are
       NOT holes here - they stay solid (filled) on the top face, to be
       partial-depth pocketed in G2 / G4.
  G2 - Extrude-cut BOTH 3.2-dia circles (rows 38,39) 1.4 units along -Z
       (pockets from the Z=-25.993 top face down to Z=-27.393).
  G4 - Extrude-cut the TRIANGLE (rows 40,41,42) 0.6 units along -Z
       (pocket from Z=-25.993 down to Z=-26.593).
  G5 - READ S2.  For each of the three dia-6.0 circles (bottom face Z=-28.993):
       cut the CENTRAL square 2.2, the two SMALL caps 2.0, the two LARGE segments
       1.8 -- all blind pockets cut +Z INTO the material from the bottom face.
       The guideline's "cut the whole circle 1 unit along -Z" is NOT a material
       cut: per the author it exists to avoid a COINCIDENT SURFACE.  It is
       realized here as a 1.0 mm downward (-Z) OVERSHOOT (G5_UNDER) on every
       section-cut tool, so each tool starts 1 mm below the bottom face (in air)
       and no tool mouth face is coincident with the body bottom face (P-11
       sliver hazard).  Section depths are measured from the bottom face.
       Deepest pocket 2.2 leaves 0.8 mm above it -> blind, body stays watertight.
  G6 - 0.4 chamfer on the three "hole" edges placed at z=-28.993.  After G5 the
       only circular hole edges at z=-28.993 (the bottom face) are the three
       dia-6.0 COUNTERBORE MOUTHS -- the 3.5-dia through-hole bottom rims were
       consumed by the G5 counterbores and now sit at the counterbore floor
       (z=-26.793), NOT at z=-28.993.  Per TEMPLATE §7 (trust the coordinate)
       G6 chamfers the three counterbore mouths.  Round hole-end chamfer => cut a
       45 deg loft cone at each rim (COOKBOOK P-16), material on the +Z side.
  G7 - 0.4 chamfer on the FIVE "hole" edges placed at z=-25.993 (the TOP face):
       the three 3.5-dia THROUGH-HOLE top rims + the two 3.2-dia POCKET mouths
       (3 + 2 = 5).  Material is BELOW the top face (md=-1).  Round rim chamfer
       => 45 deg loft cone per hole (COOKBOOK P-16).
  G8 - 0.4 chamfer on the TRIANGLE edges placed at z=-25.993 (the TOP face) --
       the triangular pocket mouth (G4).  Chamfer along a CLOSED outline => an
       offset-loft tool (COOKBOOK P-15) that miters every corner, NOT a per-edge
       sweep.  It's a pocket, so the bevel widens the mouth: outset outline at the
       face -> original outline 0.4 into the material (md=-1).
  G9 - 0.4 chamfer on the MODEL OUTER edges at z=-25.993 (the TOP face): the whole
       outer outline (rows 1..34 = 34 edges, matching Fusion's 34-edge tangent
       chain).  Closed OUTER rim => offset-loft wedge (COOKBOOK P-15): prism over
       the chamfer band MINUS the inset-outline taper; offset_2d miters every
       corner.  Material BELOW the top face (mat_dir=-1) -> bevel runs inward+down.
  G10- UNEQUAL chamfer 1 (horizontal, in-plane) x 2 (z) on the MODEL OUTER edges
       at z=-28.993 (BOTTOM face), running continuously from the S3-step1 edge
       (= S1 outline row 2, the top edge) around the perimeter to the S3-step2
       edge (= S1 outline row 12, the left edge).  At each slot-mouth corner the
       step edge is EXTENDED COLINEARLY (a straight continuation, NOT bending along
       the transition arc) up to the point where that straight chamfer band reaches
       the arc (perp distance CH_G10_H from the step line); the big chamfer runs
       out there.  The remaining arc portion (touch -> far) gets the 0.4 chamfer.
       Material is ABOVE the bottom
       face, so the bevel rises +Z.  OCCT chamfer() FAILS here ("try a smaller
       length", P-05), so the chamfer is CUT as a swept-wedge tool (P-05 fallback):
       one continuous ruled loft of the 1x2 cross-section along the chain, then
       subtract (few booleans -> safe on the master build, P-14).
  G11- EQUAL 0.4 chamfer on the INNER U-slot edges (rows [13,33,14,34,15,16,1])
       PLUS the remaining (touch->far) portions of the two transition arcs that the
       G10 colinear extension did not cover, at z=-28.993.  Together G10+G11 the
       whole bottom outer rim is chamfered (big on the perimeter, small on the slot).
  G12- EQUAL 0.4 chamfer on the S4 edges: the two 3.2-dia POCKET-FLOOR rims at
       z=-27.393 (G2-pocket floors, where floor meets wall).  The chamfer tapers
       INWARD + DOWN (a countersink) so the resultant bottom edge is a LESSER
       diameter (R-0.4).  Loft frustum: wide ring (R) at the floor rim, narrow ring
       (R-0.4) 0.4 below the floor -> removes solid below the floor only (no gouge
       past the -28.993 base).
       whole bottom outer rim, big on the perimeter, small on the slot.  Same
       swept-wedge cut as G10 (0.4 x 0.4 cross-section along the U-slot chain).
  G3 - LAST: .clean() + watertight ASCII STL + summary (TEMPLATE §13 / P-11).

Coordinate convention (TEMPLATE §7): S1 (Z=-25.993) is the TOP face, S2
(Z=-28.993) is the BOTTOM face; "into the material" is -Z from the top and +Z
from the bottom.  Depths come from the guideline literals + profile coordinates,
not verbal direction labels (see the G5 note above).
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
Z_TOL         = 1e-3

# ══════════════════════════════════════════════════════════════════════════
# Paths (cross-platform, derived from script location)
# ══════════════════════════════════════════════════════════════════════════
BASE_DIR    = Path(__file__).resolve().parent
FOLDER_NAME = BASE_DIR.name
SCRIPT_STEM = Path(__file__).resolve().stem
CSV_DIR     = BASE_DIR / "csv_merged"

S_CSV = {
    1: CSV_DIR / "Fusion_Coordinates_S1.csv",
    2: CSV_DIR / "Fusion_Coordinates_S2.csv",
    3: CSV_DIR / "Fusion_Coordinates_S3.csv",
    4: CSV_DIR / "Fusion_Coordinates_S4.csv",
    5: CSV_DIR / "Fusion_Coordinates_S5.csv",
    6: CSV_DIR / "Fusion_Coordinates_S6.csv",
    7: CSV_DIR / "Fusion_Coordinates_S7.csv",
    8: CSV_DIR / "Fusion_Coordinates_S8.csv",
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
# build123d + OCP imports  (ocp_vscode guarded so the script also runs head-less)
# ══════════════════════════════════════════════════════════════════════════
from build123d import (
    Vector, Plane, Axis, Location,
    Edge, Wire, Face, Solid, Shell, Shape, Compound,
    extrude, fillet, chamfer, loft, mirror, revolve, sweep,
    export_stl, export_step, import_step,
    GeomType, Transition, Kind,
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
    """True if the point lies inside `solid`."""
    try:
        cls = BRepClass3d_SolidClassifier(solid.wrapped, gp_Pnt(x, y, z), tol)
        return cls.State() == TopAbs_IN
    except Exception:
        return False

# ══════════════════════════════════════════════════════════════════════════
# CHECKPOINT CONFIG  (TEMPLATE §10)
#   Dev (incremental review): VIEW_AT = latest guideline, STOP_AFTER_VIEW=True,
#   EXPORT_AT_CHECKPOINT=True -> writes <folder>_G_1_N.{stl,step,txt} then exits.
#   Final deliverable run:     VIEW_AT=None, STOP_AFTER_VIEW=False,
#   EXPORT_AT_CHECKPOINT=False -> runs through G3 and writes only the final files.
# ══════════════════════════════════════════════════════════════════════════
# This part has TWO bodies.  ACTIVE_BODY selects which body's guideline the VIEW_AT
# checkpoint refers to (each body restarts its guideline numbering at G1).  Body 1
# (the z-cover plate, G1..G12) always builds; Body 2 (the S5 link) builds after it.
ACTIVE_BODY          = 2        # (irrelevant on the final run — no checkpoint stop)
VIEW_AT              = None     # FINAL RUN: build both bodies fully, no checkpoint stop
STOP_AFTER_VIEW      = False    # run through to the G3 watertight export
EXPORT_AT_CHECKPOINT = False    # no checkpoint files; write only the final deliverable
_cur_body            = 1        # set by the build as it moves from body to body

GUIDELINE_RANGE = "FINAL"

CLEAN_EACH_STEP = False
def maybe_clean(b):
    if not CLEAN_EACH_STEP:
        return b
    try: return b.clean()
    except Exception: return b

# ══════════════════════════════════════════════════════════════════════════
# Tracking state  (TEMPLATE §11)
# ══════════════════════════════════════════════════════════════════════════
stage_pieces = []
area_history = []
body1_final  = None     # set to the Body 1 result after its last guideline (G12)

def _split_bodies(pieces):
    """Split stage pieces into (body1, body2) by identity with body1_final."""
    if body1_final is None:
        return list(pieces), []                 # Body 1 still building
    b1 = [p for p in pieces if p is body1_final]
    b2 = [p for p in pieces if p is not body1_final]
    return b1, b2

def _report_bodies(pieces, indent="     "):
    """Print area+volume for Body 1, Body 2, and the combined total."""
    b1, b2 = _split_bodies(pieces)
    if b2:      # both bodies present -> per-body breakdown
        print(f"{indent}[BODY 1]   area = {cumulative_area(b1):10.3f} mm²   "
              f"volume = {cumulative_volume(b1):10.3f} mm³")
        print(f"{indent}[BODY 2]   area = {cumulative_area(b2):10.3f} mm²   "
              f"volume = {cumulative_volume(b2):10.3f} mm³")
    print(f"{indent}[COMBINED] area = {cumulative_area(pieces):10.3f} mm²   "
          f"volume = {cumulative_volume(pieces):10.3f} mm³")

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
    _btag = "" if _cur_body == 1 else f"B{_cur_body}_"
    name = f"{FOLDER_NAME}_area_history_{_btag}G_1_{last_g}.txt"
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
    cp_range = f"G_1_{g_num}" if _cur_body == 1 else f"B{_cur_body}_G_1_{g_num}"
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
    _b1, _b2 = _split_bodies(pieces)
    lines = [
        "=" * 60, f"CHECKPOINT SUMMARY  :  {FOLDER_NAME}_summary_{cp_range}.txt",
        f"Guideline reached   :  B{_cur_body} G{g_num}  ({label})",
        f"Bodies in compound  :  {len(pieces)}",
    ]
    if _b2:
        lines += [
            f"Body 1  area / vol  :  {cumulative_area(_b1):.3f} mm²  /  {cumulative_volume(_b1):.3f} mm³",
            f"Body 2  area / vol  :  {cumulative_area(_b2):.3f} mm²  /  {cumulative_volume(_b2):.3f} mm³",
        ]
    lines += [
        f"Combined area       :  {cumulative_area(pieces):.3f} mm²",
        f"Combined volume     :  {cumulative_volume(pieces):.3f} mm³", "=" * 60,
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
    print(f"     [AREA] After B{_cur_body} G{g_num}: cumulative = {cum_area:.3f} mm²  (Δ = {darea:+.3f} mm²)")
    print(f"     [VOL ] After B{_cur_body} G{g_num}: cumulative = {cum_vol:.3f} mm³  (Δ = {dvol:+.3f} mm³)")
    _report_bodies(stage_pieces)
    if _cur_body != ACTIVE_BODY or VIEW_AT != g_num: return   # only stop for the body under review
    print(f"\n[VIEW] Cumulative state after Body {_cur_body} G{g_num} ({label})")
    try: reset_show()
    except Exception: pass
    try: show(*stage_pieces)
    except Exception: pass
    if EXPORT_AT_CHECKPOINT: write_checkpoint_export(g_num, label, stage_pieces)
    if STOP_AFTER_VIEW: sys.exit(0)

# ══════════════════════════════════════════════════════════════════════════
# CSV / GEOMETRY HELPERS  (TEMPLATE §7 / COOKBOOK P-02..P-04)
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
    origin = world_vec_axis(centre_uv, axis, plane_value)
    z_dir  = {"z": (0, 0, 1), "y": (0, 1, 0), "x": (1, 0, 0)}[axis]
    return Plane(origin=origin, z_dir=z_dir)

def edge_from_row(row, axis, plane_value):
    """Build one build123d Edge (line, 3-point arc, or 3-point circle) from a row."""
    dt = _norm_draw_type(row["Draw Type"])
    if dt.startswith("line"):
        return make_line_edge(in_plane_uv(row, 1, axis), in_plane_uv(row, 2, axis),
                              axis, plane_value)
    if dt.startswith("3_point_circle"):
        uv  = [in_plane_uv(row, i, axis) for i in (1, 2, 3)]
        cx, cy, r = circle_from_3pts(*uv)
        pl = plane_for_axis(axis, plane_value, (cx, cy))
        return Edge.make_circle(r, pl)
    if dt.startswith("3_point_arc"):
        try:
            return make_arc_edge_uv(in_plane_uv(row, 1, axis), in_plane_uv(row, 2, axis),
                                    in_plane_uv(row, 3, axis), axis, plane_value)
        except Exception:
            return make_line_edge(in_plane_uv(row, 1, axis), in_plane_uv(row, 3, axis),
                                  axis, plane_value)
    raise ValueError(f"Unsupported draw type: {row['Draw Type']}")

def closed_wire(edges, tol=1e-3):
    """Single closed Wire from edges, bridging the ~1e-5 mm endpoint gaps the
    Fusion export leaves between consecutive primitives (COOKBOOK P-03)."""
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
# Region row-membership (1-based 'Steps' ids), read off the S1 sketch.
#   outline       : rows 1..34  (15 Lines + 19 three-point arcs -> one closed wire)
#   3.5-dia holes : rows 35,36,37  (through holes, NOT extruded as material in G1)
#   3.2-dia bores : rows 38,39      (G2 pockets, 1.4 deep)
#   triangle      : rows 40,41,42   (G4 pocket, 0.6 deep)
# ══════════════════════════════════════════════════════════════════════════
OUTLINE_ROWS  = list(range(1, 35))   # 1..34
HOLE35_ROWS   = [35, 36, 37]         # 3.5 dia -> through holes
HOLE32_ROWS   = [38, 39]             # 3.2 dia -> G2 pockets
TRIANGLE_ROWS = [40, 41, 42]         # G4 pocket

# ══════════════════════════════════════════════════════════════════════════
# G1 — READ S1; outer plate minus three 3.5-dia THROUGH HOLES; extrude 3 -Z
# ══════════════════════════════════════════════════════════════════════════
print(f"\n[G1] Reading {S_CSV[1].name}")
s1_rows = read_rows(S_CSV[1])
_, S1_AXIS, S1_PLANE = detect_sketch_plane(s1_rows)
print(f"     Sketch plane: axis {S1_AXIS.upper()} = {S1_PLANE}")

THICK    = 3.0                       # G1 plate thickness, extruded along -Z
Z_TOP    = S1_PLANE                  # sketch plane == top face  (= -25.993)
Z_BOTTOM = S1_PLANE - THICK          # = -28.993
UP   = (0, 0,  1)
DOWN = (0, 0, -1)
OVER = 0.1                           # cut overshoot (no coincident sliver face)

def _face_at_z(wire, z):
    """Place a copy of `wire` (native at z=S1_PLANE) on the z plane and face it."""
    return Face(Location(Vector(0.0, 0.0, z - S1_PLANE)) * wire)

# --- outer plate ----------------------------------------------------------
outline_wire = closed_wire(edges_from_rowids(s1_rows, OUTLINE_ROWS, S1_AXIS, S1_PLANE))
outline_face = Face(outline_wire)
print(f"     outline_face area = {float(outline_face.area):.3f} mm²  "
      f"(closed={outline_wire.is_closed}, edges={len(outline_wire.edges())})")
g1_body = extrude(outline_face, amount=THICK, dir=DOWN)        # Z=-25.993 -> -28.993

# --- three 3.5-dia THROUGH holes (subtract a cylinder overshooting both faces) -
for i in HOLE35_ROWS:
    _uv = [in_plane_uv(s1_rows[i - 1], k, S1_AXIS) for k in (1, 2, 3)]
    cx, cy, r = circle_from_3pts(*_uv)
    hole_wire = closed_wire([edge_from_row(s1_rows[i - 1], S1_AXIS, S1_PLANE)])
    tool = extrude(_face_at_z(hole_wire, Z_TOP + OVER), amount=THICK + 2 * OVER, dir=DOWN)
    g1_body = g1_body - tool
    print(f"     through-hole row {i}: centre=({cx:.3f},{cy:.3f}) dia={2*r:.3f}")

g1_body = maybe_clean(g1_body)
try:
    print(f"     G1 solids = {len(g1_body.solids())}  "
          f"volume = {sum(s.volume for s in g1_body.solids()):.3f} mm³")
except Exception:
    pass

stage_pieces.append(g1_body)
checkpoint(1, "G1 solid: outer plate (3 thick, -Z) with three 3.5-dia through holes")

# ══════════════════════════════════════════════════════════════════════════
# EXTRUDE-CUT HELPER  (pocket from the top face, downward -Z)
#   Tool overshoots OVER above the top face (into air) so the pocket mouth is a
#   clean cut at the top; the pocket bottom sits at z = Z_TOP - depth.
# ══════════════════════════════════════════════════════════════════════════
def extrude_cut(body, make_wire, depth, tag):
    src = body
    try: src = src.solids()[0]
    except Exception: pass
    tool = extrude(_face_at_z(make_wire(), Z_TOP + OVER), amount=depth + OVER, dir=DOWN)
    out = src - tool
    out = maybe_clean(out)
    z_bot = Z_TOP - depth
    try:
        print(f"     {tag}: pocket depth {depth} (z {Z_TOP:.3f} -> {z_bot:.3f})  "
              f"-> volume {sum(s.volume for s in out.solids()):.3f} mm³")
    except Exception:
        pass
    return out

# Fresh-wire builders (rebuild the wire for every cut/face — P-15 hygiene).
def _circle_wire(row_id):
    return closed_wire([edge_from_row(s1_rows[row_id - 1], S1_AXIS, S1_PLANE)])

def _triangle_wire():
    return closed_wire(edges_from_rowids(s1_rows, TRIANGLE_ROWS, S1_AXIS, S1_PLANE))

# ══════════════════════════════════════════════════════════════════════════
# G2 — Extrude-cut BOTH 3.2-dia circles (rows 38,39) 1.4 units along -Z.
# ══════════════════════════════════════════════════════════════════════════
CUT32_DEPTH = 1.4
print(f"\n[G2] Cutting both 3.2-dia circles {CUT32_DEPTH} deep along -Z.")
g2_body = g1_body
for i in HOLE32_ROWS:
    g2_body = extrude_cut(g2_body, (lambda r=i: _circle_wire(r)), CUT32_DEPTH, f"G2.{i}")
stage_pieces[:] = [p for p in stage_pieces if p is not g1_body]
stage_pieces.append(g2_body)
checkpoint(2, f"G2 cut two 3.2-dia circles {CUT32_DEPTH} deep (-Z)")

# ══════════════════════════════════════════════════════════════════════════
# G4 — Extrude-cut the TRIANGLE (rows 40,41,42) 0.6 units along -Z.
# ══════════════════════════════════════════════════════════════════════════
CUT_TRI_DEPTH = 0.6
print(f"\n[G4] Cutting the triangle {CUT_TRI_DEPTH} deep along -Z.")
g4_body = extrude_cut(g2_body, _triangle_wire, CUT_TRI_DEPTH, "G4")
stage_pieces[:] = [p for p in stage_pieces if p is not g2_body]
stage_pieces.append(g4_body)
checkpoint(4, f"G4 cut triangle {CUT_TRI_DEPTH} deep (-Z)")

# ══════════════════════════════════════════════════════════════════════════
# G5 — READ S2; three dia-6.0 counterbores on the BOTTOM face (Z=-28.993), each
#      split into 5 sections, cut as blind pockets INTO the plate (+Z):
#        central square 2.2 | small caps 2.0 | large segments 1.8
#   The guideline's "cut the whole circle 1 unit along -Z" is NOT a material cut:
#   per the author it exists to AVOID A COINCIDENT SURFACE.  S2 lies on the part's
#   bottom face, so a section-cut tool whose mouth face sits exactly on that face
#   is coincident -> sliver/null-triangulation holes (P-11).  We realize the
#   "1 unit -Z" as a 1.0 mm DOWNWARD OVERSHOOT (G5_UNDER) on every section tool:
#   each tool starts 1 mm BELOW the bottom face (in air) and is extruded +Z up to
#   its section depth, so no tool face is coincident with the body bottom face.
#   Section depths are measured from the bottom face (Z=-28.993).
# ══════════════════════════════════════════════════════════════════════════
print(f"\n[G5] Reading {S_CSV[2].name}")
s2_rows = read_rows(S_CSV[2])
_, S2_AXIS, S2_PLANE = detect_sketch_plane(s2_rows)
print(f"     Sketch plane: axis {S2_AXIS.upper()} = {S2_PLANE}  (part BOTTOM face)")
if S2_AXIS != "z":
    print(f"     ⚠  S2 not on a Z plane (axis={S2_AXIS}); G5 assumes Z-plane counterbores.")
Z_S2 = S2_PLANE                                  # = -28.993 (== Z_BOTTOM)

G5_UNDER      = 1.0     # "1 unit along -Z": downward overshoot below the bottom
                        # face (in air) so no cut-tool mouth is coincident w/ it
DEPTH_CENTRAL = 2.2     # central 3.5x3.5 square
DEPTH_SMALL   = 2.0     # top + bottom caps
DEPTH_LARGE   = 1.8     # left + right segments
G5_PAD        = 0.5     # rect overshoot past the arc before clipping to the disc
LINE_TOL      = 1e-3

# --- parse S2: circles + the 4 dividing lines per circle ------------------
s2_circles = []   # {cx,cy,r,xs,ys}
s2_lines   = []   # (p1_uv, p2_uv)
for row in s2_rows:
    dt = _norm_draw_type(row["Draw Type"])
    if dt.startswith("3_point_circle"):
        uv = [in_plane_uv(row, k, S2_AXIS) for k in (1, 2, 3)]
        cx, cy, rad = circle_from_3pts(*uv)
        s2_circles.append({"cx": cx, "cy": cy, "r": rad, "xs": [], "ys": []})
    elif dt.startswith("line"):
        s2_lines.append((in_plane_uv(row, 1, S2_AXIS), in_plane_uv(row, 2, S2_AXIS)))

# assign each line to its nearest circle; classify vertical / horizontal
for (p1, p2) in s2_lines:
    mx, my = (p1[0] + p2[0]) / 2.0, (p1[1] + p2[1]) / 2.0
    c = min(s2_circles, key=lambda c: (c["cx"] - mx) ** 2 + (c["cy"] - my) ** 2)
    if abs(p1[0] - p2[0]) < LINE_TOL:        # vertical line -> an x divider
        c["xs"].append(mx)
    elif abs(p1[1] - p2[1]) < LINE_TOL:      # horizontal line -> a y divider
        c["ys"].append(my)
for c in s2_circles:
    c["xL"], c["xR"] = min(c["xs"]), max(c["xs"])
    c["yB"], c["yT"] = min(c["ys"]), max(c["ys"])

# --- G5 cut tools (faces native at z = Z_S2 - G5_UNDER, extruded +Z) -------
#   Tool spans [Z_S2 - G5_UNDER, Z_S2 + depth]: it starts 1 mm below the bottom
#   face (the "-Z 1 unit", in air) and rises +Z to the section depth, so the
#   pocket mouth is a clean cut, never a face coincident with the bottom face.
def _wire_rect(x0, x1, y0, y1, z):
    pts = [Vector(x0, y0, z), Vector(x1, y0, z), Vector(x1, y1, z), Vector(x0, y1, z)]
    return Wire([Edge.make_line(pts[i], pts[(i + 1) % 4]) for i in range(4)])

def _wire_disk(cx, cy, r, z):
    return Wire([Edge.make_circle(r, Plane(origin=Vector(cx, cy, z), z_dir=(0, 0, 1)))])

def _disk_tool(c, depth):
    return extrude(Face(_wire_disk(c["cx"], c["cy"], c["r"], Z_S2 - G5_UNDER)),
                   amount=depth + G5_UNDER, dir=UP)

def _rect_tool(x0, x1, y0, y1, depth):
    return extrude(Face(_wire_rect(x0, x1, y0, y1, Z_S2 - G5_UNDER)),
                   amount=depth + G5_UNDER, dir=UP)

def _cut(body, tool, tag):
    src = body
    try: src = src.solids()[0]
    except Exception: pass
    out = maybe_clean(src - tool)
    try:
        print(f"     {tag}: -> volume {sum(s.volume for s in out.solids()):.3f} mm³")
    except Exception:
        pass
    return out

print(f"     {len(s2_circles)} counterbore circles; cutting +Z into the plate "
      f"(central={DEPTH_CENTRAL}, small={DEPTH_SMALL}, large={DEPTH_LARGE}; "
      f"-Z overshoot {G5_UNDER} to avoid coincident faces).")
g5_body = g4_body
for k, c in enumerate(s2_circles, start=1):
    cx, cy, rr = c["cx"], c["cy"], c["r"]
    xL, xR, yB, yT = c["xL"], c["xR"], c["yB"], c["yT"]
    print(f"\n     circle {k}: centre=({cx:.3f},{cy:.3f}) dia={2*rr:.3f}  "
          f"x=[{xL:.3f},{xR:.3f}] y=[{yB:.3f},{yT:.3f}]")
    # central 3.5x3.5 square 2.2  (square is fully inside the disc -> rect only)
    g5_body = _cut(g5_body, _rect_tool(xL, xR, yB, yT, DEPTH_CENTRAL),
                   f"G5.{k} central {DEPTH_CENTRAL}")
    # small caps (top, bottom) 2.0  -> rect clipped to the disc
    g5_body = _cut(g5_body, _rect_tool(xL, xR, yT, cy + rr + G5_PAD, DEPTH_SMALL)
                   & _disk_tool(c, DEPTH_SMALL), f"G5.{k} small-top {DEPTH_SMALL}")
    g5_body = _cut(g5_body, _rect_tool(xL, xR, cy - rr - G5_PAD, yB, DEPTH_SMALL)
                   & _disk_tool(c, DEPTH_SMALL), f"G5.{k} small-bottom {DEPTH_SMALL}")
    # large segments (left, right) 1.8  -> rect clipped to the disc
    g5_body = _cut(g5_body, _rect_tool(cx - rr - G5_PAD, xL, cy - rr - G5_PAD,
                   cy + rr + G5_PAD, DEPTH_LARGE) & _disk_tool(c, DEPTH_LARGE),
                   f"G5.{k} large-left {DEPTH_LARGE}")
    g5_body = _cut(g5_body, _rect_tool(xR, cx + rr + G5_PAD, cy - rr - G5_PAD,
                   cy + rr + G5_PAD, DEPTH_LARGE) & _disk_tool(c, DEPTH_LARGE),
                   f"G5.{k} large-right {DEPTH_LARGE}")

g5_body = maybe_clean(g5_body)
stage_pieces[:] = [p for p in stage_pieces if p is not g4_body]
stage_pieces.append(g5_body)
checkpoint(5, "G5 three dia-6 counterbores, 5-section stepped pockets (+Z), bottom face")

# ══════════════════════════════════════════════════════════════════════════
# G6 — 0.4 chamfer on the three "hole" edges at z=-28.993.
#   The only circular hole edges at z=-28.993 (bottom face) are the three dia-6.0
#   COUNTERBORE MOUTHS (the 3.5 through-hole rims were consumed by the G5
#   counterbores -> now at z=-26.793).  Round hole-end chamfer => subtract a 45°
#   loft cone at each rim (COOKBOOK P-16): narrow ring = mouth radius sat L into
#   the material (+Z), wide ring = radius+L overshooting OVER below the face.
# ══════════════════════════════════════════════════════════════════════════
CHAMFER_G6 = 0.4
print(f"\n[G6] Chamfer {CHAMFER_G6} on the three counterbore mouths at z={Z_S2:.3f}.")

def _circle_face_z(cx, cy, r, z):
    return Face(_wire_disk(cx, cy, r, z))

def chamfer_mouth(body, c, leg, z_face, md=1.0):
    """45° hole-rim chamfer via a subtracted loft cone (P-16).  md=+1 -> material
    above the face (here the plate sits at z > z_face)."""
    src = body
    try: src = src.solids()[0]
    except Exception: pass
    R = c["r"]
    narrow = _circle_face_z(c["cx"], c["cy"], R,               z_face + md * leg)
    wide   = _circle_face_z(c["cx"], c["cy"], R + leg + OVER,   z_face - md * OVER)
    cone = None
    for secs in ([wide, narrow], [narrow, wide]):
        try:
            cone = loft(secs); break
        except Exception:
            try:
                cone = loft(secs, ruled=True); break
            except Exception:
                continue
    if cone is None:
        raise RuntimeError("G6 chamfer cone loft failed")
    out = maybe_clean(src - cone)
    try:
        print(f"     mouth @({c['cx']:.3f},{c['cy']:.3f}) dia={2*R:.1f}: "
              f"chamfered -> volume {sum(s.volume for s in out.solids()):.3f} mm³")
    except Exception:
        pass
    return out

g6_body = g5_body
for k, c in enumerate(s2_circles, start=1):
    g6_body = chamfer_mouth(g6_body, c, CHAMFER_G6, Z_S2, md=1.0)

g6_body = maybe_clean(g6_body)
stage_pieces[:] = [p for p in stage_pieces if p is not g5_body]
stage_pieces.append(g6_body)
checkpoint(6, f"G6 chamfer {CHAMFER_G6} on three counterbore mouths z={Z_S2:.3f}")

# ══════════════════════════════════════════════════════════════════════════
# G7 — 0.4 chamfer on the FIVE "hole" edges at z=-25.993 (TOP face):
#   the three 3.5-dia THROUGH-HOLE top rims (rows 35,36,37) + the two 3.2-dia
#   POCKET mouths (rows 38,39) = 5 circular holes.  Material is BELOW the top
#   face (md=-1).  Round rim chamfer => subtract a 45° loft cone per hole (P-16):
#   narrow ring = hole radius sat L DOWN into the material, wide ring = radius+L
#   overshooting OVER above the face.
# ══════════════════════════════════════════════════════════════════════════
CHAMFER_G7    = 0.4
TOP_HOLE_ROWS = HOLE35_ROWS + HOLE32_ROWS        # [35,36,37,38,39] -> 5 holes
print(f"\n[G7] Chamfer {CHAMFER_G7} on the five top-face hole mouths at z={Z_TOP:.3f}.")

def _s1_circle(row_id):
    uv = [in_plane_uv(s1_rows[row_id - 1], k, S1_AXIS) for k in (1, 2, 3)]
    cx, cy, r = circle_from_3pts(*uv)
    return {"cx": cx, "cy": cy, "r": r}

g7_body = g6_body
for row_id in TOP_HOLE_ROWS:
    g7_body = chamfer_mouth(g7_body, _s1_circle(row_id), CHAMFER_G7, Z_TOP, md=-1.0)

g7_body = maybe_clean(g7_body)
stage_pieces[:] = [p for p in stage_pieces if p is not g6_body]
stage_pieces.append(g7_body)
checkpoint(7, f"G7 chamfer {CHAMFER_G7} on five top-face hole mouths z={Z_TOP:.3f}")

# ══════════════════════════════════════════════════════════════════════════
# G8 — 0.4 chamfer on the TRIANGLE edges at z=-25.993 (TOP face): the triangular
#   pocket mouth (G4).  Chamfer along a CLOSED outline => offset-loft tool (P-15):
#   offset_2d miters every corner (no per-edge sweep stepping).  It's a pocket, so
#   the bevel WIDENS the mouth -> outset outline at the face, original outline 0.4
#   into the material (md=-1).  Subtract a ruled loft (wide@face -> narrow@depth).
# ══════════════════════════════════════════════════════════════════════════
CHAMFER_G8 = 0.4
print(f"\n[G8] Chamfer {CHAMFER_G8} on the triangle pocket mouth at z={Z_TOP:.3f}.")

def _outset_wire(make_wire, amt):
    """Offset the closed outline OUTWARD by `amt` (mitered corners), robust to
    winding: try both signs, keep the larger-area (outset) result."""
    cands = []
    for s in (-amt, +amt):
        for kw in ({"kind": Kind.INTERSECTION}, {}):
            try:
                w = make_wire().offset_2d(s, **kw)
                cands.append((float(Face(w).area), w)); break
            except Exception:
                continue
    if not cands:
        raise RuntimeError("offset_2d failed in both directions")
    cands.sort(key=lambda t: t[0])
    return cands[-1][1]                       # largest area = the outset outline

def chamfer_pocket_outline(body, make_wire, leg, z_face, md, tag):
    """45° chamfer along a closed POCKET-mouth outline (P-15 offset-loft).  md=-1
    -> material below the face (top-face pocket); the bevel opens at the face."""
    src = body
    try: src = src.solids()[0]
    except Exception: pass
    narrow = _face_at_z(make_wire(),                       z_face + md * leg)   # orig outline, into material
    wide   = _face_at_z(_outset_wire(make_wire, leg + OVER), z_face - md * OVER) # outset outline, past the face
    cone = None
    for secs in ([wide, narrow], [narrow, wide]):
        try:
            cone = loft(secs, ruled=True); break
        except Exception:
            continue
    if cone is None:
        raise RuntimeError(f"{tag}: chamfer loft failed")
    out = maybe_clean(src - cone)
    try:
        print(f"     {tag}: -> volume {sum(s.volume for s in out.solids()):.3f} mm³")
    except Exception:
        pass
    return out

g8_body = chamfer_pocket_outline(g7_body, _triangle_wire, CHAMFER_G8, Z_TOP, md=-1.0, tag="G8")
g8_body = maybe_clean(g8_body)
stage_pieces[:] = [p for p in stage_pieces if p is not g7_body]
stage_pieces.append(g8_body)
checkpoint(8, f"G8 chamfer {CHAMFER_G8} on triangle pocket mouth z={Z_TOP:.3f}")

# ══════════════════════════════════════════════════════════════════════════
# G9 — 0.4 chamfer on the MODEL OUTER edges at z=-25.993 (TOP face): the whole
#   outer outline (rows 1..34, 34 edges).  Closed OUTER rim => offset-loft wedge
#   (P-15): wedge = prism over the chamfer band MINUS the inset-outline taper.
#   offset_2d miters every corner (incl. the tongue/slot).  Material BELOW the top
#   face (mat_dir=-1) -> z_inner = z_face - leg (down), z_far overshoots above.
#   Holes/pockets inside are untouched (the wedge only hugs the outer boundary).
# ══════════════════════════════════════════════════════════════════════════
CHAMFER_G9 = 0.4
print(f"\n[G9] Chamfer {CHAMFER_G9} on the outer outline (34 edges) at z={Z_TOP:.3f}.")

def _outline_wire():
    """Fresh outer-outline wire (P-15: rebuild for each loft/offset)."""
    return closed_wire(edges_from_rowids(s1_rows, OUTLINE_ROWS, S1_AXIS, S1_PLANE))

def _inset_wire(make_wire, leg):
    """Offset the outline INWARD by `leg` (mitered), robust to winding: try both
    signs, keep the smaller-area (inset) result."""
    cands = []
    for s in (-leg, +leg):
        for kw in ({"kind": Kind.INTERSECTION}, {}):
            try:
                w = make_wire().offset_2d(s, **kw)
                cands.append((float(Face(w).area), w)); break
            except Exception:
                continue
    if not cands:
        raise RuntimeError("offset_2d failed in both directions")
    cands.sort(key=lambda t: t[0])
    return cands[0][1]                        # smallest area = the inset outline

def chamfer_outer_outline(body, make_wire, leg, z_face, mat_dir, tag):
    """45° chamfer along a closed OUTER outline (P-15 offset-loft wedge).
    mat_dir=-1 -> material below the face (top rim)."""
    src = body
    try: src = src.solids()[0]
    except Exception: pass
    z_inner = z_face + mat_dir * leg          # bevel meets the full outline here
    z_far   = z_face - mat_dir * OVER         # prism overshoots past the face
    lo, hi  = min(z_inner, z_far), max(z_inner, z_far)
    prism = extrude(_face_at_z(make_wire(), lo), amount=(hi - lo), dir=UP)
    taper = None
    for secs in ([_face_at_z(_inset_wire(make_wire, leg), z_face),
                  _face_at_z(make_wire(), z_inner)],
                 [_face_at_z(make_wire(), z_inner),
                  _face_at_z(_inset_wire(make_wire, leg), z_face)]):
        try:
            taper = loft(secs, ruled=True); break
        except Exception:
            continue
    if taper is None:
        raise RuntimeError(f"{tag}: chamfer taper loft failed")
    out = maybe_clean(src - (prism - taper))
    try:
        print(f"     {tag}: -> volume {sum(s.volume for s in out.solids()):.3f} mm³")
    except Exception:
        pass
    return out

g9_body = chamfer_outer_outline(g8_body, _outline_wire, CHAMFER_G9, Z_TOP, mat_dir=-1.0, tag="G9")
g9_body = maybe_clean(g9_body)
stage_pieces[:] = [p for p in stage_pieces if p is not g8_body]
stage_pieces.append(g9_body)
checkpoint(9, f"G9 chamfer {CHAMFER_G9} on outer outline (34 edges) z={Z_TOP:.3f}")

# ══════════════════════════════════════════════════════════════════════════
# G10 / G11 — BOTTOM outer-rim chamfers at z=-28.993, split by S3 into two
#   edge-sets (native build123d chamfer with data-driven edge selection, P-05):
#     G10: UNEQUAL 1 (in-plane) x 2 (z) on the continuous perimeter run from the
#          S3-step1 edge (row 2) to the S3-step2 edge (row 12);
#     G11: EQUAL 0.4 on the avoided U-slot chain.
#   Order: G10 (big) then G11 (small).  G11 edges are re-selected from the post-G10
#   body as z=-28.993 edges still carrying an original U-slot outline endpoint.
# ══════════════════════════════════════════════════════════════════════════
print(f"\n[G10/G11] Reading {S_CSV[3].name} (chamfer-chain start/end edges)")
s3_rows = read_rows(S_CSV[3])

# --- outline-row metadata (endpoints in x,y) for edge matching ---
def _row_ends_xy(rid):
    r = s1_rows[rid - 1]
    dt = _norm_draw_type(r["Draw Type"])
    if dt.startswith("line"):
        return ((float(r["X1"]), float(r["Y1"])), (float(r["X2"]), float(r["Y2"])))
    return ((float(r["X1"]), float(r["Y1"])), (float(r["X3"]), float(r["Y3"])))   # arc: 1st & 3rd

OUTLINE_ENDS = {rid: _row_ends_xy(rid) for rid in OUTLINE_ROWS}

def _match_outline_row(p, q, tol=0.15):
    """Return the outline row id whose endpoints match (p,q) in either order."""
    for rid, (a, b) in OUTLINE_ENDS.items():
        if (math.hypot(p[0]-a[0], p[1]-a[1]) < tol and math.hypot(q[0]-b[0], q[1]-b[1]) < tol) or \
           (math.hypot(p[0]-b[0], p[1]-b[1]) < tol and math.hypot(q[0]-a[0], q[1]-a[1]) < tol):
            return rid
    return None

def _s3_row_to_outline(s3_row):
    p = (float(s3_row["X1"]), float(s3_row["Y1"]))
    q = (float(s3_row["X2"]), float(s3_row["Y2"]))
    return _match_outline_row(p, q)

START_ROW = _s3_row_to_outline(s3_rows[0])     # S3 step1 -> expect row 2
END_ROW   = _s3_row_to_outline(s3_rows[1])     # S3 step2 -> expect row 12
print(f"     S3 step1 edge -> outline row {START_ROW};  step2 edge -> outline row {END_ROW}")

# --- ordered outline loop walk (deterministic) -> split into the two arcs ---
def _ordered_outline_loop():
    segs = {rid: _row_ends_xy(rid) for rid in OUTLINE_ROWS}
    def cl(u, v): return math.hypot(u[0]-v[0], u[1]-v[1]) < 1e-2
    start = START_ROW if START_ROW in segs else OUTLINE_ROWS[0]
    a, b = segs[start]; order = [start]; used = {start}; cur = b
    while True:
        nxt = None
        for s, (p, q) in segs.items():
            if s in used: continue
            if cl(cur, p): nxt = (s, q); break
            if cl(cur, q): nxt = (s, p); break
        if nxt is None: break
        used.add(nxt[0]); order.append(nxt[0]); cur = nxt[1]
    return order

_loop = _ordered_outline_loop()
_ie = _loop.index(END_ROW)
_runA = _loop[:_ie + 1]                       # START..END (one direction)
_runB = [_loop[0]] + _loop[_ie:][::-1]        # the other arc (START..END the other way)
# the U-slot arc carries the two longest DIAGONAL line edges (rows 14,15); G10 is
# the perimeter run that does NOT contain them.
def _is_long_diag(rid):
    r = s1_rows[rid - 1]
    if not _norm_draw_type(r["Draw Type"]).startswith("line"): return False
    (ax, ay), (bx, by) = OUTLINE_ENDS[rid]
    return (abs(ax-bx) > 1e-2 and abs(ay-by) > 1e-2) and math.hypot(bx-ax, by-ay) > 20.0
G10_base = _runA if not any(_is_long_diag(r) for r in _runA) else _runB
# The leftover loop rows (the U-slot chain) in CONTINUOUS LOOP ORDER — never
# numeric order, or the swept-wedge polyline would jump across the part.
_base_set = set(G10_base)
_uslot_chain = [r for r in _loop if r not in _base_set]
# Two transition ARCS join the step edges to the U-slot (first/last of the slot
# chain).  Each is SPLIT (not whole): the portion within CH_G10_H of the step-edge
# line — i.e. where the step edge's 1x2 chamfer band, extended linearly, still
# reaches the arc — joins the BIG (G10) chamfer; the remaining arc + the inner
# slot edges get the small (G11) chamfer.
TRANS_ARC_END   = _uslot_chain[0]      # arc adjacent to END_ROW   (S3 step2 / row12)
TRANS_ARC_START = _uslot_chain[-1]     # arc adjacent to START_ROW (S3 step1 / row2)
INNER_ROWS      = _uslot_chain[1:-1]   # inner U-slot edges (all 0.4)
print(f"     G10 base perimeter ({len(G10_base)} edges): {G10_base}")
print(f"     transition arcs (split): start={TRANS_ARC_START}@step{START_ROW}, "
      f"end={TRANS_ARC_END}@step{END_ROW}")
print(f"     G11 inner U-slot chain ({len(INNER_ROWS)} edges): {INNER_ROWS}")

# --- swept-wedge chamfer cut (COOKBOOK P-05 fallback: OCCT chamfer fails on this
#     boolean-heavy body, so cut the chamfer as a tool).  ONE continuous loft per
#     chain (few booleans -> safe on the master build, P-14).  The chain is built
#     directly from the CSV outline rows (no fragile solid-edge selection).
def _solid_of(body):
    try: return body.solids()[0]
    except Exception: return body

def _arc_points(p1, p2, p3, target=1.5):
    """Sample a 3-point arc into ordered points (>= 3)."""
    cx, cy, r = circle_from_3pts(p1, p2, p3)
    def ang(p): return math.atan2(p[1] - cy, p[0] - cx)
    def n2pi(a):
        while a < 0: a += 2 * math.pi
        while a >= 2 * math.pi: a -= 2 * math.pi
        return a
    t1 = ang(p1); d3 = n2pi(ang(p3) - t1); d2 = n2pi(ang(p2) - t1)
    total = d3 if d2 < d3 else d3 - 2 * math.pi        # signed sweep through p2
    K = max(3, int(abs(total) * r / target))
    return [(cx + r * math.cos(t1 + total * i / K),
             cy + r * math.sin(t1 + total * i / K)) for i in range(K + 1)]

def _edge_points(rid):
    r = s1_rows[rid - 1]; dt = _norm_draw_type(r["Draw Type"])
    if dt.startswith("line"):
        return [(float(r["X1"]), float(r["Y1"])), (float(r["X2"]), float(r["Y2"]))]
    return _arc_points((float(r["X1"]), float(r["Y1"])),
                       (float(r["X2"]), float(r["Y2"])),
                       (float(r["X3"]), float(r["Y3"])))

def _chain_polyline(rows):
    """Ordered, de-duplicated (x,y) polyline along a continuous chain of rows."""
    def d(u, v): return math.hypot(u[0] - v[0], u[1] - v[1])
    poly = list(_edge_points(rows[0]))
    for rid in rows[1:]:
        pl = _edge_points(rid)
        if d(poly[-1], pl[0]) > d(poly[-1], pl[-1]):
            pl = list(reversed(pl))
        if d(poly[-1], pl[0]) < 1e-2:
            pl = pl[1:]
        poly.extend(pl)
    return poly

# Deterministic 2D "inside the plate footprint" test.  The earlier 3D point_inside
# probe (at z=Z_S2+0.5) caught bottom-face features (G5 counterbores, chamfers) and
# returned noisy/flipped normals, which tilted the loft cross-sections and produced
# jagged / self-intersecting chamfer surfaces.  A pure 2D outline test is immune to
# those features, so straight edges get identical normals (-> clean flat chamfers).
_OUTLINE_POLY = _chain_polyline(_loop)          # closed plate footprint (x,y)

def _pt_in_outline(x, y):
    inside = False; n = len(_OUTLINE_POLY); j = n - 1
    for i in range(n):
        xi, yi = _OUTLINE_POLY[i]; xj, yj = _OUTLINE_POLY[j]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    return inside

def _inward_xy(body, mx, my, tx, ty, probe=0.35):
    """Unit in-plane normal at (mx,my) pointing INTO the plate footprint (2D test,
    deterministic — no interference from bottom-face features)."""
    for nx, ny in ((-ty, tx), (ty, -tx)):
        if _pt_in_outline(mx + nx * probe, my + ny * probe):
            return (nx, ny)
    return (-ty, tx)

def _orient_polyline(poly, start_pt):
    """Return poly oriented so its first point is the end nearest `start_pt`."""
    if (math.hypot(poly[0][0]-start_pt[0], poly[0][1]-start_pt[1]) >
        math.hypot(poly[-1][0]-start_pt[0], poly[-1][1]-start_pt[1])):
        return list(reversed(poly))
    return poly

def _split_transition_arc(arc_rid, step_rid, leg):
    """Split a transition arc where it has curved `leg` away from the step edge's
    line (i.e. where the step edge's chamfer band, extended, leaves the arc).
    Returns (step_side, slot_side) point lists, each ordered JUNCTION/​split outward
    and sharing the split point."""
    apts = _edge_points(arc_rid)
    sa, sb = OUTLINE_ENDS[step_rid]
    def near(p, q): return math.hypot(p[0]-q[0], p[1]-q[1]) < 1e-2
    junction = sa if (near(sa, apts[0]) or near(sa, apts[-1])) else sb
    dx, dy = sb[0]-sa[0], sb[1]-sa[1]; L = math.hypot(dx, dy) or 1.0
    dxu, dyu = dx/L, dy/L
    def perp(p):
        vx, vy = p[0]-junction[0], p[1]-junction[1]
        proj = vx*dxu + vy*dyu
        return math.hypot(vx - proj*dxu, vy - proj*dyu)
    seq = apts if near(apts[0], junction) else list(reversed(apts))
    step_side = [seq[0]]; slot_side = None
    for i in range(1, len(seq)):
        if slot_side is None and perp(seq[i]) >= leg:
            d0, d1 = perp(seq[i-1]), perp(seq[i])
            t = (leg - d0)/(d1 - d0) if d1 != d0 else 0.0
            split = (seq[i-1][0] + t*(seq[i][0]-seq[i-1][0]),
                     seq[i-1][1] + t*(seq[i][1]-seq[i-1][1]))
            step_side.append(split); slot_side = [split, seq[i]]
        elif slot_side is None:
            step_side.append(seq[i])
        else:
            slot_side.append(seq[i])
    if slot_side is None:                       # arc fully within leg -> all step-side
        slot_side = [seq[-1]]
    return step_side, slot_side

def _wedge_from_polyline(body, poly, leg_h, leg_z, tag, normals=None):
    """Build a chamfer-cut tool by lofting a constant chamfer cross-section along
    the (x,y) polyline.  Cross-section (in the plane ⟂ to the path) is the exact
    45°/uneq triangle (wall->bottom) padded OUTWARD+BELOW by OVER (air) so no tool
    face is coincident with the body wall/bottom face.  `normals[i]`, if given,
    overrides the inside-probe (used for colinear-extension points that sit OUTSIDE
    the part where the probe can't find material)."""
    n = len(poly)
    faces = []
    for i, (px, py) in enumerate(poly):
        a = poly[max(0, i - 1)]; b = poly[min(n - 1, i + 1)]
        tx, ty = b[0] - a[0], b[1] - a[1]
        tl = math.hypot(tx, ty) or 1.0
        tx, ty = tx / tl, ty / tl
        if normals is not None and normals[i] is not None:
            nx, ny = normals[i]
        else:
            nx, ny = _inward_xy(body, px, py, tx, ty)
        def P(s, z): return Vector(px + nx * s, py + ny * s, z)
        # pentagon: exact triangle (top-wall -> inward-bottom) + air pad below/out
        wire = Wire([
            Edge.make_line(P(0.0,    Z_S2 + leg_z), P(leg_h, Z_S2)),         # bevel (exact)
            Edge.make_line(P(leg_h,  Z_S2),          P(leg_h, Z_S2 - OVER)), # inward wall down
            Edge.make_line(P(leg_h,  Z_S2 - OVER),   P(-OVER, Z_S2 - OVER)), # below (air)
            Edge.make_line(P(-OVER,  Z_S2 - OVER),   P(-OVER, Z_S2 + leg_z)),# outward (air)
            Edge.make_line(P(-OVER,  Z_S2 + leg_z),  P(0.0,   Z_S2 + leg_z)),# top back to wall
        ])
        faces.append(Face(wire))
    tool = None
    for secs in (faces, list(reversed(faces))):
        try:
            tool = loft(secs, ruled=True); break
        except Exception:
            continue
    if tool is None:
        raise RuntimeError(f"{tag}: chamfer wedge loft failed ({len(faces)} sections)")
    return tool

# --- chamfer legs + the split transition-arc polylines ---------------------
CH_G10_H = 1.0      # in-plane (horizontal) leg of the big chamfer
CH_G10_Z = 2.0      # vertical (z) leg of the big chamfer
CH_G11   = 0.4      # equal-distance chamfer on the inner U-slot

# Precise G10/G11 MEETING (from the reference measurements): the G10 chamfer's
# inner line (step edge offset CH_G10_H inward) meets the G11 chamfer's INNER arc
# (radius = r_arc - CH_G11).  The G10 colinear extension ends at that meeting; the
# G11 arc portion starts at the matching arc-rim point.  Matches ref vertices
# (27.01,43.924) & (7.00,23.914) and the 1.99 mm step-edge extension.
def _step_inward(step_rid, junction):
    sa, sb = OUTLINE_ENDS[step_rid]
    dx, dy = sb[0]-sa[0], sb[1]-sa[1]; L = math.hypot(dx, dy) or 1.0
    return _inward_xy(g9_body, junction[0], junction[1], dx/L, dy/L)

def _arc_cr(arc_rid):
    rr = s1_rows[arc_rid - 1]
    uv = [(float(rr["X1"]), float(rr["Y1"])), (float(rr["X2"]), float(rr["Y2"])),
          (float(rr["X3"]), float(rr["Y3"]))]
    return circle_from_3pts(*uv)                         # (cx, cy, rad)

def _line_circle_meet(p0, d, cx, cy, R, prefer):
    fx, fy = p0[0]-cx, p0[1]-cy
    a = d[0]*d[0] + d[1]*d[1]; b = 2*(fx*d[0]+fy*d[1]); c = fx*fx+fy*fy-R*R
    disc = b*b - 4*a*c
    if disc < 0:
        return None
    sq = math.sqrt(disc)
    cands = [(p0[0]+t*d[0], p0[1]+t*d[1]) for t in ((-b-sq)/(2*a), (-b+sq)/(2*a))]
    return min(cands, key=lambda p: (p[0]-prefer[0])**2 + (p[1]-prefer[1])**2)

def _transition(step_rid, arc_rid):
    """Corner data: (junction, ext_pt, arc_start, inward_n).  ext_pt = colinear
    extension endpoint on the step rim; arc_start = arc-rim point where G11 begins."""
    apts = _edge_points(arc_rid)
    sa, sb = OUTLINE_ENDS[step_rid]
    near = lambda p, q: math.hypot(p[0]-q[0], p[1]-q[1]) < 1e-2
    junction = sa if (near(sa, apts[0]) or near(sa, apts[-1])) else sb
    L = math.hypot(sb[0]-sa[0], sb[1]-sa[1]) or 1.0
    d = ((sb[0]-sa[0])/L, (sb[1]-sa[1])/L)
    n = _step_inward(step_rid, junction)
    p0 = (junction[0] + n[0]*CH_G10_H, junction[1] + n[1]*CH_G10_H)   # G10 inner line pt
    cx, cy, rad = _arc_cr(arc_rid)
    # prefer the intersection in the EXTENSION direction (past the junction, toward
    # the corner) — both line-circle roots are equidistant from the junction itself.
    ext_dir = (-d[0], -d[1]) if near(junction, sa) else (d[0], d[1])
    prefer = (junction[0] + ext_dir[0]*5.0, junction[1] + ext_dir[1]*5.0)
    M = _line_circle_meet(p0, d, cx, cy, rad - CH_G11, prefer=prefer) or p0
    proj = (M[0]-junction[0])*d[0] + (M[1]-junction[1])*d[1]
    ext_pt = (junction[0] + proj*d[0], junction[1] + proj*d[1])       # on the step rim
    ang = math.atan2(M[1]-cy, M[0]-cx)
    arc_start = (cx + rad*math.cos(ang), cy + rad*math.sin(ang))      # arc-rim start for G11
    return junction, ext_pt, arc_start, n

def _arc_far_portion(arc_rid, junction, arc_start):
    """Arc sample points from `arc_start` to the far end (away from the junction)."""
    pts = _edge_points(arc_rid)
    if (math.hypot(pts[0][0]-junction[0], pts[0][1]-junction[1]) >
        math.hypot(pts[-1][0]-junction[0], pts[-1][1]-junction[1])):
        pts = list(reversed(pts))                        # pts[0] near junction, pts[-1] far
    di = min(range(len(pts)), key=lambda i: (pts[i][0]-arc_start[0])**2 + (pts[i][1]-arc_start[1])**2)
    return [arc_start] + pts[di + 1:]

_j_s, _ext_start, _as_s, _n_start = _transition(START_ROW, TRANS_ARC_START)
_j_e, _ext_end,   _as_e, _n_end   = _transition(END_ROW,   TRANS_ARC_END)
print(f"     G10/G11 meeting: cornerA arc_start≈({_as_s[0]:.2f},{_as_s[1]:.2f}) "
      f"ext->({_ext_start[0]:.2f},{_ext_start[1]:.2f}); cornerB arc_start≈({_as_e[0]:.2f},{_as_e[1]:.2f}) "
      f"ext->({_ext_end[0]:.2f},{_ext_end[1]:.2f})")

# G10 polyline: ext_start -> junction_start -> [perimeter] -> junction_end -> ext_end
_perim = _orient_polyline(_chain_polyline(G10_base), _j_s)
g10_poly  = [_ext_start] + _perim + [_ext_end]
g10_norms = [_n_start] + [None]*len(_perim) + [_n_end]

# G11 polyline: arc_start_A -> far_A -> [inner slot] -> far_B -> arc_start_B
_seg_s = _arc_far_portion(TRANS_ARC_START, _j_s, _as_s)   # arc_start -> far (toward row1)
_seg_e = _arc_far_portion(TRANS_ARC_END,   _j_e, _as_e)   # arc_start -> far (toward row13)
if INNER_ROWS:
    _inner = _orient_polyline(_chain_polyline(INNER_ROWS), _seg_s[-1])
    g11_poly = _seg_s + _inner[1:] + list(reversed(_seg_e))[1:]
else:
    g11_poly = _seg_s + list(reversed(_seg_e))[1:]

print(f"\n[G10] Unequal chamfer {CH_G10_H} (in-plane) x {CH_G10_Z} (z) on perimeter + "
      f"colinear step-edge extensions ({len(g10_poly)} pts) at z={Z_S2:.3f} (swept-wedge cut).")
g10_body = g9_body
try:
    g10_tool = _wedge_from_polyline(g9_body, g10_poly, CH_G10_H, CH_G10_Z, "G10", normals=g10_norms)
    g10_body = maybe_clean(_solid_of(g9_body) - g10_tool)
    print(f"     G10: wedge cut -> volume {sum(s.volume for s in g10_body.solids()):.3f} mm³")
except Exception as exc:
    print(f"     ⚠  G10 wedge cut failed ({exc}); leaving body unchamfered for review.")
    g10_body = g9_body
stage_pieces[:] = [p for p in stage_pieces if p is not g9_body]
stage_pieces.append(g10_body)
checkpoint(10, f"G10 unequal {CH_G10_H}x{CH_G10_Z} chamfer on perimeter + arc-starts z={Z_S2:.3f}")

print(f"\n[G11] Equal {CH_G11} chamfer on inner U-slot + transition-arc remainders "
      f"({len(g11_poly)} pts) at z={Z_S2:.3f} (swept-wedge cut).")
g11_body = g10_body
try:
    g11_tool = _wedge_from_polyline(g10_body, g11_poly, CH_G11, CH_G11, "G11")
    g11_body = maybe_clean(_solid_of(g10_body) - g11_tool)
    print(f"     G11: wedge cut -> volume {sum(s.volume for s in g11_body.solids()):.3f} mm³")
except Exception as exc:
    print(f"     ⚠  G11 wedge cut failed ({exc}); leaving body as-is for review.")
    g11_body = g10_body
stage_pieces[:] = [p for p in stage_pieces if p is not g10_body]
stage_pieces.append(g11_body)
checkpoint(11, f"G11 equal {CH_G11} chamfer on inner U-slot + arc remainders z={Z_S2:.3f}")

# ══════════════════════════════════════════════════════════════════════════
# G12 — 0.4 chamfer on the S4 edges: the two 3.2-dia POCKET-FLOOR rims at
#   z=-27.393 (the floors of the G2 pockets, where floor meets wall).  The chamfer
#   tapers INWARD + DOWN so the resultant bottom edge is a LESSER diameter (a
#   countersink at the pocket bottom).  Cut a loft FRUSTUM: wide ring (R) at the
#   floor rim, narrow ring (R-leg) a depth `leg` BELOW the floor.  This removes
#   solid below the floor only (floor z=-27.393, cone bottom z=-27.793, still above
#   the -28.993 base -> no gouge past the part).  Resultant floor edge = R-leg.
# ══════════════════════════════════════════════════════════════════════════
CHAMFER_G12 = 0.4
print(f"\n[G12] Reading {S_CSV[4].name}")
s4_rows = read_rows(S_CSV[4])
_, S4_AXIS, S4_PLANE = detect_sketch_plane(s4_rows)
Z_S4 = S4_PLANE
print(f"     Sketch plane: axis {S4_AXIS.upper()} = {S4_PLANE}  (3.2-dia pocket floors)")

def chamfer_floor_rim(body, cx, cy, R, leg, zf, tag):
    src = body
    try: src = src.solids()[0]
    except Exception: pass
    wide   = _circle_face_z(cx, cy, R,        zf)           # r=R at the floor rim
    narrow = _circle_face_z(cx, cy, R - leg,  zf - leg)     # r=R-leg, `leg` below the floor
    cone = None
    for secs in ([wide, narrow], [narrow, wide]):
        try:
            cone = loft(secs); break
        except Exception:
            try:
                cone = loft(secs, ruled=True); break
            except Exception:
                continue
    if cone is None:
        raise RuntimeError(f"{tag}: floor-rim cone loft failed")
    out = maybe_clean(src - cone)
    try:
        print(f"     {tag}: dia={2*R:.1f} floor rim chamfered inward "
              f"(resultant edge dia={2*(R-leg):.1f}) -> volume "
              f"{sum(s.volume for s in out.solids()):.3f} mm³")
    except Exception:
        pass
    return out

print(f"[G12] Chamfer {CHAMFER_G12} on {len(s4_rows)} pocket-floor rims at z={Z_S4:.3f}.")
g12_body = g11_body
for row in s4_rows:
    _uv = [in_plane_uv(row, k, S4_AXIS) for k in (1, 2, 3)]
    cx, cy, R = circle_from_3pts(*_uv)
    g12_body = chamfer_floor_rim(g12_body, cx, cy, R, CHAMFER_G12, Z_S4,
                                 f"G12@({cx:.1f},{cy:.1f})")
g12_body = maybe_clean(g12_body)
stage_pieces[:] = [p for p in stage_pieces if p is not g11_body]
stage_pieces.append(g12_body)
checkpoint(12, f"G12 chamfer {CHAMFER_G12} on two 3.2-dia pocket-floor rims z={Z_S4:.3f}")

# ══════════════════════════════════════════════════════════════════════════
# G13 — extrude-cut the S8 profile 12 units along -X.  S8 is the EXACT corner
#   chamfer cross-section, drawn in the YZ plane at X=33.843 (its diagonal edge
#   is the 1x2 bevel: dY=1, dZ=2, with a 0.15 overshoot past the top edge/base).
#   Cutting it -X carves the precise chamfer surface through the top-left
#   slot-mouth corner region (X 33.84 -> 21.84), refining the swept G10/G11 meet.
# ══════════════════════════════════════════════════════════════════════════
print(f"\n[G13] Reading {S_CSV[8].name}")
s8_rows = read_rows(S_CSV[8])
_, S8_AXIS, S8_PLANE = detect_sketch_plane(s8_rows)
print(f"     Sketch plane: axis {S8_AXIS.upper()} = {S8_PLANE}")
CUT_X_G13 = 12.0
s8_face = face_from_edges(edges_from_rowids(s8_rows, list(range(1, len(s8_rows) + 1)),
                                            S8_AXIS, S8_PLANE))
print(f"     S8 profile area = {float(s8_face.area):.3f} mm²")
s8_tool = extrude(s8_face, amount=CUT_X_G13, dir=(-1, 0, 0))       # 12 along -X
g13_body = maybe_clean(_solid_of(g12_body) - s8_tool)
try:
    print(f"     G13: -X cut -> volume {sum(s.volume for s in g13_body.solids()):.3f} mm³")
except Exception:
    pass
stage_pieces[:] = [p for p in stage_pieces if p is not g12_body]
stage_pieces.append(g13_body)
checkpoint(13, "Body1 G13: extrude-cut S8 profile 12 along -X (exact corner chamfer surface)")

# ══════════════════════════════════════════════════════════════════════════
# G14 — same as G13 but for the OTHER slot-mouth corner (row 12 / arc 32).  No S9
#   sketch was supplied, so the profile is the MIRROR of S8: row 12 is the left
#   vertical edge (x=5.99999), so its 1x2 chamfer cross-section lies in the XZ
#   plane and is swept along +Y toward the corner.  Same construction as S8: plane
#   set 4.8427 into the perimeter past the junction, 1x2 bevel + 0.15 overshoot,
#   extrude-cut 12 along +Y.  Lands the meeting exactly at (7, 23.914).
# ══════════════════════════════════════════════════════════════════════════
print(f"\n[G14] Other corner (row 12 / arc 32): mirror of S8 in the XZ plane, cut +Y.")
_J12_Y   = float(s1_rows[12 - 1]["Y2"])          # row 12 top end (junction w/ arc 32) = 21.9239
_S8_OFF  = 33.842685 - float(s1_rows[2 - 1]["X1"])  # S8 plane offset past its junction (=4.8427)
_Y14     = _J12_Y - _S8_OFF                       # plane position (into the perimeter)
_X12     = float(s1_rows[12 - 1]["X1"])           # row 12 x (=5.99999)
_ZB, _ZT, _ZU = -28.993001, -26.993001, -29.143001   # bottom / +2 (chamfer top) / -0.15 base
_OV15    = 0.15
_s9_pts_xz = [
    (_X12 + CH_G10_H, _ZB),          # inner-bottom  (x+1, z bottom)   -> (7, -28.993)
    (_X12,            _ZT),          # edge-top      (x,   z +2)       -> (6, -26.993)
    (_X12 - _OV15,    _ZT),          # 0.15 out, top
    (_X12 - _OV15,    _ZU),          # 0.15 out, below
    (_X12 + CH_G10_H, _ZU),          # inner, below
]
_v14 = [Vector(x, _Y14, z) for (x, z) in _s9_pts_xz]
s9_face = Face(Wire([Edge.make_line(_v14[i], _v14[(i + 1) % len(_v14)]) for i in range(len(_v14))]))
print(f"     mirror profile at Y={_Y14:.3f} (area {float(s9_face.area):.3f} mm²); cut 12 along +Y.")
s9_tool = extrude(s9_face, amount=12.0, dir=(0, 1, 0))            # 12 along +Y
g14_body = maybe_clean(_solid_of(g13_body) - s9_tool)
try:
    print(f"     G14: +Y cut -> volume {sum(s.volume for s in g14_body.solids()):.3f} mm³")
except Exception:
    pass
stage_pieces[:] = [p for p in stage_pieces if p is not g13_body]
stage_pieces.append(g14_body)
checkpoint(14, "Body1 G14: mirror-of-S8 cut 12 along +Y (exact other-corner chamfer surface)")
body1_final = g14_body    # Body 1 (the z-cover plate) is complete after G14

# ══════════════════════════════════════════════════════════════════════════
# ██  BODY 2  —  the S5 link (separate body, its own guideline numbering)  ██
# ══════════════════════════════════════════════════════════════════════════
_cur_body = 2

# ── Body 2 / G1 — READ S5; outer outline minus the inner 2.2-dia THROUGH hole,
#    extrude the plate 3 units along -Z (Z=-25.993 -> Z=-28.993).
print(f"\n[BODY2 G1] Reading {S_CSV[5].name}")
s5_rows = read_rows(S_CSV[5])
_, S5_AXIS, S5_PLANE = detect_sketch_plane(s5_rows)
print(f"     Sketch plane: axis {S5_AXIS.upper()} = {S5_PLANE}")

B2_OUTLINE_ROWS = list(range(1, 11))     # rows 1..10 (4 lines + 6 arcs -> one loop)
B2_HOLE_ROW     = 11                      # inner 2.2-dia circle -> through hole
B2_THICK        = 3.0
B2_Z_TOP        = S5_PLANE                 # = -25.993 (== S1 top plane)
B2_Z_BOTTOM     = S5_PLANE - B2_THICK      # = -28.993

b2_outline_wire = closed_wire(edges_from_rowids(s5_rows, B2_OUTLINE_ROWS, S5_AXIS, S5_PLANE))
b2_outline_face = Face(b2_outline_wire)
print(f"     S5 outline area = {float(b2_outline_face.area):.3f} mm²  "
      f"(closed={b2_outline_wire.is_closed}, edges={len(b2_outline_wire.edges())})")
b2_body = extrude(b2_outline_face, amount=B2_THICK, dir=DOWN)      # Z=-25.993 -> -28.993

# inner circle -> through hole (subtract a cylinder overshooting both faces)
_b2_uv = [in_plane_uv(s5_rows[B2_HOLE_ROW - 1], k, S5_AXIS) for k in (1, 2, 3)]
b2_cx, b2_cy, b2_r = circle_from_3pts(*_b2_uv)
b2_hole_wire = closed_wire([edge_from_row(s5_rows[B2_HOLE_ROW - 1], S5_AXIS, S5_PLANE)])
b2_tool = extrude(_face_at_z(b2_hole_wire, B2_Z_TOP + OVER), amount=B2_THICK + 2 * OVER, dir=DOWN)
b2_body = maybe_clean(b2_body - b2_tool)
print(f"     through-hole: centre=({b2_cx:.3f},{b2_cy:.3f}) dia={2*b2_r:.3f}")
try:
    print(f"     Body2 G1 solids = {len(b2_body.solids())}  "
          f"volume = {sum(s.volume for s in b2_body.solids()):.3f} mm³")
except Exception:
    pass

stage_pieces.append(b2_body)
checkpoint(1, "Body2 G1: S5 outline extruded 3 down (-Z), inner 2.2-dia through hole")

# ── Body 2 / G2 — 0.4 chamfer on the OUTER outline at BOTH faces (top z=-25.993
#    and bottom z=-28.993); the inner 2.2-dia hole is left untouched (the tool
#    uses only the outer outline).  Closed OUTER rim => offset-loft wedge (P-15),
#    material BELOW the top face (mat_dir=-1) and ABOVE the bottom face (+1).
B2_CHAMFER = 0.4
def _b2_outline_wire():
    return closed_wire(edges_from_rowids(s5_rows, B2_OUTLINE_ROWS, S5_AXIS, S5_PLANE))

print(f"\n[BODY2 G2] Chamfer {B2_CHAMFER} on the S5 outer outline, top & bottom "
      f"(hole left untouched).")
b2_g2 = chamfer_outer_outline(b2_body, _b2_outline_wire, B2_CHAMFER,
                              B2_Z_TOP, mat_dir=-1.0, tag="B2G2-top")
b2_g2 = chamfer_outer_outline(b2_g2, _b2_outline_wire, B2_CHAMFER,
                              B2_Z_BOTTOM, mat_dir=+1.0, tag="B2G2-bot")
b2_g2 = maybe_clean(b2_g2)
stage_pieces[:] = [p for p in stage_pieces if p is not b2_body]
stage_pieces.append(b2_g2)
checkpoint(2, f"Body2 G2: {B2_CHAMFER} chamfer on S5 outer outline top & bottom (hole untouched)")

# ── Body 2 / G3 — S6 counterbore (dia 4.0) on Body 2's BOTTOM face (z=-28.993),
#    concentric with the hole, split by 4 lines into 5 sections cut +Z:
#      section 5 (central square, bounded by lines)          -> 2.0
#      sections 3&4 (top/bottom caps, SHORT line + circle)   -> 1.8
#      sections 1&2 (left/right segments, LONG line + circle)-> 1.6
#    The guideline's "cut the whole circle 1 unit -Z" is the coincidence-avoidance
#    overshoot (G5_UNDER); every section tool starts 1 below the bottom face (air).
#    Reuses the G5 section tooling (Body 2's bottom plane == Z_S2 = -28.993).
print(f"\n[BODY2 G3] Reading {S_CSV[6].name}")
s6_rows = read_rows(S_CSV[6])
_, S6_AXIS, S6_PLANE = detect_sketch_plane(s6_rows)
print(f"     Sketch plane: axis {S6_AXIS.upper()} = {S6_PLANE}  (Body 2 bottom face)")

_c6 = None; _vx = []; _hy = []; _Lv = 0.0; _Lh = 0.0
for row in s6_rows:
    dt = _norm_draw_type(row["Draw Type"])
    if dt.startswith("3_point_circle"):
        _uv6 = [in_plane_uv(row, k, S6_AXIS) for k in (1, 2, 3)]
        _cx6, _cy6, _r6 = circle_from_3pts(*_uv6)
        _c6 = {"cx": _cx6, "cy": _cy6, "r": _r6}
    elif dt.startswith("line"):
        p1 = in_plane_uv(row, 1, S6_AXIS); p2 = in_plane_uv(row, 2, S6_AXIS)
        if abs(p1[0] - p2[0]) < LINE_TOL:        # vertical divider
            _vx.append((p1[0] + p2[0]) / 2.0); _Lv = abs(p1[1] - p2[1])
        elif abs(p1[1] - p2[1]) < LINE_TOL:      # horizontal divider
            _hy.append((p1[1] + p2[1]) / 2.0); _Lh = abs(p1[0] - p2[0])
b2_cx, b2_cy, b2_rr = _c6["cx"], _c6["cy"], _c6["r"]
b2_xL, b2_xR = min(_vx), max(_vx)
b2_yB, b2_yT = min(_hy), max(_hy)

B2_DEPTH_CENTRAL = 2.0     # section 5
B2_DEPTH_LONG    = 1.6     # sections 1&2 (bounded by the LONG line + circle)
B2_DEPTH_SHORT   = 1.8     # sections 3&4 (bounded by the SHORT line + circle)
# segments are bounded by the VERTICAL lines, caps by the HORIZONTAL lines; map
# each to long/short by measured line length (data-driven).
_seg_depth = B2_DEPTH_LONG if _Lv >= _Lh else B2_DEPTH_SHORT
_cap_depth = B2_DEPTH_SHORT if _Lv >= _Lh else B2_DEPTH_LONG
print(f"     S6 dia={2*b2_rr:.1f} @({b2_cx:.3f},{b2_cy:.3f}); Lv={_Lv:.2f} Lh={_Lh:.2f} "
      f"-> segments={_seg_depth}, caps={_cap_depth}, central={B2_DEPTH_CENTRAL}")

b2_g3 = b2_g2
# section 5 — central square (fully inside the disc -> rect only)
b2_g3 = _cut(b2_g3, _rect_tool(b2_xL, b2_xR, b2_yB, b2_yT, B2_DEPTH_CENTRAL), "B2G3 central(5)")
# sections 3&4 — top/bottom caps (short line), clipped to the disc
b2_g3 = _cut(b2_g3, _rect_tool(b2_xL, b2_xR, b2_yT, b2_cy + b2_rr + G5_PAD, _cap_depth)
             & _disk_tool(_c6, _cap_depth), "B2G3 cap-top(3)")
b2_g3 = _cut(b2_g3, _rect_tool(b2_xL, b2_xR, b2_cy - b2_rr - G5_PAD, b2_yB, _cap_depth)
             & _disk_tool(_c6, _cap_depth), "B2G3 cap-bottom(4)")
# sections 1&2 — left/right segments (long line), clipped to the disc
b2_g3 = _cut(b2_g3, _rect_tool(b2_cx - b2_rr - G5_PAD, b2_xL, b2_cy - b2_rr - G5_PAD,
             b2_cy + b2_rr + G5_PAD, _seg_depth) & _disk_tool(_c6, _seg_depth), "B2G3 seg-left(1)")
b2_g3 = _cut(b2_g3, _rect_tool(b2_xR, b2_cx + b2_rr + G5_PAD, b2_cy - b2_rr - G5_PAD,
             b2_cy + b2_rr + G5_PAD, _seg_depth) & _disk_tool(_c6, _seg_depth), "B2G3 seg-right(2)")
b2_g3 = maybe_clean(b2_g3)
stage_pieces[:] = [p for p in stage_pieces if p is not b2_g2]
stage_pieces.append(b2_g3)
checkpoint(3, "Body2 G3: S6 dia-4 counterbore, 5-section stepped pattern (+Z)")

# ── Body 2 / G4 — 0.4 chamfer on the two round hole rims:
#     SMALL hole (S5 through-hole, dia 2.2) TOP rim  z=-25.993, material below (md=-1)
#     LARGE hole (S6 counterbore mouth, dia 4.0) BOTTOM rim z=-28.993, above  (md=+1)
#   Round hole-end chamfer => 45° loft cone per rim (COOKBOOK P-16, reuses G6/G7's
#   chamfer_mouth).  Both interiors are void so the cone removes only the rim ring.
B2_CHAMFER_G4 = 0.4
_b2_small = {"cx": b2_cx, "cy": b2_cy, "r": b2_r}      # S5 through-hole (r=1.1)
_b2_large = {"cx": b2_cx, "cy": b2_cy, "r": b2_rr}     # S6 counterbore mouth (r=2.0)
print(f"\n[BODY2 G4] Chamfer {B2_CHAMFER_G4}: small hole top rim (dia {2*b2_r:.1f}, "
      f"z={B2_Z_TOP:.3f}) + large counterbore mouth (dia {2*b2_rr:.1f}, z={B2_Z_BOTTOM:.3f}).")
b2_g4 = chamfer_mouth(b2_g3, _b2_small, B2_CHAMFER_G4, B2_Z_TOP,    md=-1.0)   # small, top
b2_g4 = chamfer_mouth(b2_g4, _b2_large, B2_CHAMFER_G4, B2_Z_BOTTOM, md=+1.0)   # large, bottom
b2_g4 = maybe_clean(b2_g4)
stage_pieces[:] = [p for p in stage_pieces if p is not b2_g3]
stage_pieces.append(b2_g4)
checkpoint(4, f"Body2 G4: {B2_CHAMFER_G4} chamfer on small-hole top rim + large-hole bottom mouth")

# ══════════════════════════════════════════════════════════════════════════
# G3 — EXPORT (ALWAYS LAST): WATERTIGHT STL  (TEMPLATE §13 / COOKBOOK P-11/P-11a)
#   1. .clean() the final compound.
#   2. Deterministic conformal mesh (BRepMesh, parallel=False).
#   3. WELD near-coincident shared-edge vertices + drop duplicate/degenerate
#      faces -> manifold, watertight in-memory mesh (P-11a).
#   4. manifold3d to split any residual self-touch.
#   5. Write ASCII STL; verify it reloads strictly watertight; else raw + WARN.
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

# per-body area / volume breakdown (Body 1, Body 2, combined)
_b1_pieces, _b2_pieces = _split_bodies(stage_pieces)
B1_AREA, B1_VOL = cumulative_area(_b1_pieces), cumulative_volume(_b1_pieces)
B2_AREA, B2_VOL = cumulative_area(_b2_pieces), cumulative_volume(_b2_pieces)
print(f"     [BODY 1]   area = {B1_AREA:.3f} mm²   volume = {B1_VOL:.3f} mm³")
print(f"     [BODY 2]   area = {B2_AREA:.3f} mm²   volume = {B2_VOL:.3f} mm³")
print(f"     [COMBINED] area = {B1_AREA + B2_AREA:.3f} mm²   volume = {B1_VOL + B2_VOL:.3f} mm³")

FINAL_STL = BASE_DIR / f"{SCRIPT_STEM}.stl"
FINAL_TXT = BASE_DIR / f"{SCRIPT_STEM}_summary.txt"

def _watertight_stl(compound, out_path):
    """Mesh EACH body separately through the P-11/P-11a pipeline (per-face
    deterministic BRepMesh -> weld coincident vertices + drop duplicate/degenerate
    faces -> manifold3d), so one body's defects don't fail the others.  Report each
    body's in-memory watertightness, then MERGE the per-body meshes into one ASCII
    STL and verify watertight on reload."""
    import trimesh
    from OCP.BRepMesh import BRepMesh_IncrementalMesh
    from OCP.TopExp import TopExp_Explorer
    from OCP.TopAbs import TopAbs_FACE
    from OCP.TopoDS import TopoDS as _TDS
    from OCP.BRep import BRep_Tool
    from OCP.TopLoc import TopLoc_Location
    from OCP.BRepTools import BRepTools

    try:
        import manifold3d as m3d
    except Exception:
        m3d = None

    def raw_mesh(sh, dd):
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

    def _fix_tjunctions(mesh, tol=1e-3):
        """Close T-junction cracks: a hanging vertex lying on the interior of a
        boundary edge of the spanning face (verified cause of Body 1's 3 collinear
        boundary edges at the G5 counterbore-3 pocket edge).  Splits the spanning
        face at the hanging vertex so every edge pairs up.  fill_holes/manifold3d
        can't fix these (zero-area), so this is the key repair."""
        m = mesh
        for _ in range(10):
            inv = np.asarray(m.edges_unique_inverse)
            cnt = np.bincount(inv, minlength=len(m.edges_unique))
            if not (cnt == 1).any():
                break
            V = np.asarray(m.vertices); F = np.asarray(m.faces)
            bnd_v = np.unique(m.edges_unique[cnt == 1].ravel())
            ef = {}
            for fi, es in enumerate(m.faces_unique_edges):
                for e in es:
                    ef.setdefault(int(e), []).append(fi)
            new_f = []; drop = set(); changed = False
            for ei in np.where(cnt == 1)[0]:
                a, b = m.edges_unique[ei]; A = V[a]; B = V[b]; AB = B - A; L2 = float(AB.dot(AB))
                if L2 < 1e-12:
                    continue
                for vi in bnd_v:
                    if vi == a or vi == b:
                        continue
                    t = float((V[vi] - A).dot(AB) / L2)
                    if 0.02 < t < 0.98 and np.linalg.norm(A + t * AB - V[vi]) < tol:
                        for fi in ef.get(int(ei), []):
                            if fi in drop:
                                continue
                            w = [x for x in F[fi] if x not in (a, b)]
                            if len(w) != 1:
                                continue
                            drop.add(fi); new_f += [[a, vi, w[0]], [vi, b, w[0]]]; changed = True
                        break
            if not changed:
                break
            keep = [i for i in range(len(F)) if i not in drop]
            F2 = np.vstack([F[keep], np.array(new_f, np.int64)]) if new_f else F[keep]
            m = trimesh.Trimesh(V, F2, process=True); trimesh.repair.fix_normals(m)
        return m

    def weld_clean(V, T, dec=5):
        """Weld coincident vertices (round to 1e-`dec`), drop duplicate/degenerate
        faces, fill_holes, and split T-junction cracks — iterate until watertight
        (P-11 / P-11a).  Coarser `dec` welds the ~1e-4 shared-edge gaps the OCCT
        mesher leaves.  Verified on the real export: Body 1 -> watertight, 11688 mm³."""
        m = trimesh.Trimesh(np.round(V, dec), T, process=True)
        def _tidy():
            m.merge_vertices()
            m.update_faces(m.unique_faces());       m.remove_unreferenced_vertices()
            m.update_faces(m.nondegenerate_faces()); m.remove_unreferenced_vertices()
        _tidy(); trimesh.repair.fix_normals(m)
        for _ in range(6):                                 # iterative repair
            if m.is_watertight:
                break
            try: trimesh.repair.fill_holes(m)
            except Exception: pass
            _tidy(); trimesh.repair.fix_normals(m)
            if m.is_watertight:
                break
            m = _fix_tjunctions(m)                         # split spanning faces at hanging verts
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

    import tempfile, os as _os
    def _step_roundtrip(solid):
        """STEP export+import round-trip (P-11 KEY step): re-parametrizes surfaces
        and clears un-meshable sliver faces left by a long boolean history."""
        try:
            tmp = _os.path.join(tempfile.gettempdir(), "b123d_rt_body.step")
            export_step(solid, tmp)
            rt = import_step(tmp)
            return rt.wrapped if hasattr(rt, "wrapped") else rt
        except Exception:
            return None

    def best_mesh(solid):
        """Best watertight mesh for a single solid across a few deflections; tries
        the STEP round-trip variant FIRST (clears slivers), then the raw solid."""
        variants = []
        _rt = _step_roundtrip(solid)
        if _rt is not None:
            variants.append(_rt)
        variants.append(solid.wrapped if hasattr(solid, "wrapped") else solid)
        fallback = None
        for sh in variants:
            for d in (0.05, 0.04, 0.06, 0.03):
                V, T = raw_mesh(sh, d)
                for dec in (5, 4, 3):            # progressively coarser weld tolerance
                    m = weld_clean(V, T, dec)
                    if fallback is None:
                        fallback = m
                    if m.is_watertight:
                        mm = via_manifold(m)     # split any residual self-touch
                        return (mm if mm.is_watertight else m), True
                    mm = via_manifold(m)         # last resort: let manifold3d rebuild it
                    if mm is not m and mm.is_watertight:
                        return mm, True
        return fallback, bool(fallback.is_watertight)

    solids = list(compound.solids())
    meshes = []; per_body_wt = []
    for i, s in enumerate(solids, start=1):
        m, wt = best_mesh(s)
        per_body_wt.append(wt)
        _v = float(m.volume) if wt else float("nan")
        print(f"     [MESH] body {i}: watertight={wt}, triangles={len(m.faces)}, volume={_v:.3f} mm³")
        meshes.append(m)

    combined = trimesh.util.concatenate(meshes) if len(meshes) > 1 else meshes[0]
    with open(out_path, "w") as fh:                     # ASCII (P-11: avoid float32 jitter)
        fh.write(trimesh.exchange.stl.export_stl_ascii(combined))
    rl = trimesh.load(str(out_path))
    return (bool(rl.is_watertight),
            (float(rl.volume) if rl.is_watertight else float("nan")),
            len(rl.faces), per_body_wt)

try:
    _wt, _vol, _ntri, _per_body = _watertight_stl(final_compound, FINAL_STL)
    print(f"     [EXPORT] Wrote: {FINAL_STL.name}  (watertight={_wt}, "
          f"volume={_vol:.3f} mm³, {_ntri} triangles)")
    if not _wt:
        _bad = [i + 1 for i, w in enumerate(_per_body) if not w]
        if _bad:
            print(f"     ⚠  Body(ies) {_bad} meshed non-watertight (see [MESH] lines) — "
                  f"likely the deferred G10/G11 chamfer cleanup; the other body is fine.")
        else:
            print("     ⚠  Per-body meshes are watertight but the merged STL isn't "
                  "(possible touching/coincident bodies).")
except Exception as exc:
    print(f"     [EXPORT] watertight export failed ({exc}); raw STL.")
    export_stl(final_compound, str(FINAL_STL), tolerance=STL_TOLERANCE)

summary_lines = [
    "=" * 70,
    f"BUILD SUMMARY  :  {FOLDER_NAME}",
    f"Time           :  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
    f"Range covered  :  {GUIDELINE_RANGE}",
    f"Guidelines     :  G1, G2, G4, G5, G6, G7, G8, G9, G10, G11, G12 (G3 = export, last)",
    f"Part type      :  Volumetric Solid Part (Z-axis motor cover, left)",
    "=" * 70, "",
    f"-- G1 : S1 on {S1_AXIS.upper()}={S1_PLANE} --",
    f"  Outer outline rows   : 1..34 ({len(outline_wire.edges())} edges, closed={outline_wire.is_closed})",
    f"  Plate extrusion      : {THICK} mm along -Z (Z={S1_PLANE} -> Z={Z_BOTTOM:.3f})",
    f"  Through holes (3.5)  : rows {HOLE35_ROWS} (subtracted full thickness)",
    "",
    f"-- G2 : Cut two 3.2-dia circles {CUT32_DEPTH} deep (-Z) --",
    f"  Circle rows          : {HOLE32_ROWS}",
    f"  Pocket               : Z={Z_TOP:.3f} -> Z={Z_TOP - CUT32_DEPTH:.3f}",
    "",
    f"-- G4 : Cut triangle {CUT_TRI_DEPTH} deep (-Z) --",
    f"  Triangle rows        : {TRIANGLE_ROWS}",
    f"  Pocket               : Z={Z_TOP:.3f} -> Z={Z_TOP - CUT_TRI_DEPTH:.3f}",
    "",
    f"-- G5 : S2 on {S2_AXIS.upper()}={S2_PLANE} (bottom face) — 3 dia-6 counterbores, 5 sections each --",
    f"  Circles              : {len(s2_circles)} (dia 6.0, concentric w/ 3.5 through holes)",
    f"  Cut direction        : +Z into the plate from the bottom face",
    f"  '-Z 1 unit'          : {G5_UNDER} downward overshoot (avoids coincident face; no material removed)",
    f"  Central square        : {DEPTH_CENTRAL} deep (Z={Z_S2:.3f} -> Z={Z_S2 + DEPTH_CENTRAL:.3f})",
    f"  Small caps (x2)      : {DEPTH_SMALL} deep (Z={Z_S2:.3f} -> Z={Z_S2 + DEPTH_SMALL:.3f})",
    f"  Large segments (x2)  : {DEPTH_LARGE} deep (Z={Z_S2:.3f} -> Z={Z_S2 + DEPTH_LARGE:.3f})",
    "",
    f"-- G6 : Chamfer {CHAMFER_G6} on three counterbore mouths at z={Z_S2:.3f} --",
    f"  Edges                : 3 dia-6.0 counterbore mouths (bottom face)",
    f"  NOTE                 : 3.5 through-hole rims are now at z={Z_S2 + DEPTH_CENTRAL:.3f} (G5 floor), not -28.993",
    f"  Tool                 : 45° loft cone per rim (P-16), material on +Z side",
    "",
    f"-- G7 : Chamfer {CHAMFER_G7} on five hole mouths at z={Z_TOP:.3f} (top face) --",
    f"  Edges                : 3 through-hole top rims (rows {HOLE35_ROWS}) + 2 pocket mouths (rows {HOLE32_ROWS})",
    f"  Tool                 : 45° loft cone per rim (P-16), material on -Z side (md=-1)",
    "",
    f"-- G8 : Chamfer {CHAMFER_G8} on triangle pocket mouth at z={Z_TOP:.3f} (top face) --",
    f"  Edges                : triangle outline (rows {TRIANGLE_ROWS})",
    f"  Tool                 : offset-loft, mitered corners (P-15); outset@face -> outline 0.4 down",
    "",
    f"-- G9 : Chamfer {CHAMFER_G9} on outer outline (34 edges) at z={Z_TOP:.3f} (top face) --",
    f"  Edges                : full outer outline rows {OUTLINE_ROWS[0]}..{OUTLINE_ROWS[-1]} ({len(OUTLINE_ROWS)} edges)",
    f"  Tool                 : offset-loft wedge (P-15), prism minus inset taper; mat_dir=-1",
    "",
    f"-- G10 : Unequal chamfer {CH_G10_H} (in-plane) x {CH_G10_Z} (z) on bottom perimeter run z={Z_S2:.3f} --",
    f"  Chain                : perimeter rows {G10_base} + colinear step-edge extensions into arcs {TRANS_ARC_START}/{TRANS_ARC_END}",
    f"  Tool                 : swept-wedge cut (P-05 fallback), 1x2 cross-section lofted along chain ({len(g10_poly)} pts)",
    "",
    f"-- G11 : Equal {CH_G11} chamfer on inner U-slot + arc remainders z={Z_S2:.3f} --",
    f"  Chain                : inner rows {INNER_ROWS} + remaining (touch->far) of arcs {TRANS_ARC_START}/{TRANS_ARC_END}",
    f"  Tool                 : swept-wedge cut (P-05 fallback), {CH_G11}x{CH_G11} cross-section ({len(g11_poly)} pts)",
    "",
    f"-- G12 : Chamfer {CHAMFER_G12} on two 3.2-dia pocket-floor rims at z={Z_S4:.3f} (S4) --",
    f"  Edges                : {len(s4_rows)} pocket-floor rims (G2 pocket bottoms)",
    f"  Tool                 : loft frustum tapering inward+down (countersink); resultant edge dia lesser by 2x{CHAMFER_G12}",
    "",
    "-- BODY 2 : S5 link (G1..G4) --",
    f"  G1  : S5 outline extruded {B2_THICK} mm along -Z, inner {2*b2_r:.1f}-dia through hole",
    f"  G2  : {B2_CHAMFER} chamfer on S5 outer outline (top & bottom), hole untouched",
    f"  G3  : S6 dia-{2*b2_rr:.1f} counterbore, 5 sections (seg {_seg_depth} / cap {_cap_depth} / central {B2_DEPTH_CENTRAL})",
    f"  G4  : {B2_CHAMFER_G4} chamfer on small-hole top rim + large counterbore mouth",
    "",
    "-- AREA / VOLUME BY BODY --",
    f"  Body 1    : area {B1_AREA:.3f} mm²   volume {B1_VOL:.3f} mm³",
    f"  Body 2    : area {B2_AREA:.3f} mm²   volume {B2_VOL:.3f} mm³",
    f"  Combined  : area {B1_AREA + B2_AREA:.3f} mm²   volume {B1_VOL + B2_VOL:.3f} mm³",
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
