"""
zaphod_bot_mec_de_man_out_printer_order_4_homing_block_build123d.py

Sketch summary (planes auto-detected from CSV):
  S1  Y = 1.0    Lines + 3-point arcs forming the outer profile.
                 -> G1: extrude 1 unit along +Y with 45 deg taper, and 1 unit along -Y (no taper), then fuse.
                 
  G2             Target specific edges.
                 -> G2: apply 0.5 unit radius fillet to edges near Y=1.0 and Y=2.0.

  G4             Read S2 for drill locations.
                 -> G4: create 2.5 mm diameter drill cut (cyl + 118 deg cone tip) at each point along +Y.

  G5             Translate model.
                 -> G5: shift by +12.5 in X and +4.5 in Z to match reference.

  G3             LAST: .clean() + STL + STEP + summary export.

Guidelines (Executed in Topological Order):
  G1 - Read S1; build closed profile; extrude both directions, tapering the +Y side.
  G2 - Apply 0.5 unit radius fillet to edges located at Y=1 and Y=2.
  G4 - Drill holes from S2 points along the +Y axis.
  G5 - Translate the model so its bounding box matches the reference.
  G3 - Export.
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
EDGE_MATCH_TOL  = 1.00
DENSE_MATCH_TOL = 1.00

# ══════════════════════════════════════════════════════════════════════════
# Paths (cross-platform, derived from script location)
# ══════════════════════════════════════════════════════════════════════════
BASE_DIR    = Path(__file__).resolve().parent
FOLDER_NAME = BASE_DIR.name
CSV_DIR     = BASE_DIR / "csv_merged"

# We require S1 and S2 for this part
S_CSV = {
    1: CSV_DIR / "Fusion_Coordinates_S1.csv",
    2: CSV_DIR / "Fusion_Coordinates_S2.csv"
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
# build123d + OCP imports
# ══════════════════════════════════════════════════════════════════════════
from build123d import (
    Vector, Plane, Axis, Location,
    Edge, Wire, Face, Solid, Shell, Shape, Compound,
    extrude, fillet, chamfer, loft, mirror, revolve,
    export_stl, export_step,
    GeomType,
)
from ocp_vscode import show, set_port, reset_show
set_port(3939)

from OCP.gp import gp_Ax2, gp_Pnt, gp_Dir, gp_Circ
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeEdge, BRepBuilderAPI_MakeWire
from OCP.BRepOffsetAPI import BRepOffsetAPI_ThruSections

# ══════════════════════════════════════════════════════════════════════════
# CHECKPOINT CONFIG
# ══════════════════════════════════════════════════════════════════════════
VIEW_AT              = 5  
STOP_AFTER_VIEW      = True
EXPORT_AT_CHECKPOINT = True

GUIDELINE_RANGE = "G_1_5"

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
    except Exception as exc: pass
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
    area_history.append({"g": g_num, "label": label, "area": cum_area, "darea": darea, "vol": cum_vol, "dvol": dvol})
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

def parse_line_segments(rows, axis):
    segs = []
    for r in rows:
        if _norm_draw_type(r["Draw Type"]).startswith("line"):
            segs.append((in_plane_uv(r, 1, axis), in_plane_uv(r, 2, axis)))
    return segs

def parse_three_point_arcs(rows, axis):
    arcs = []
    for r in rows:
        if _norm_draw_type(r["Draw Type"]).startswith("3_point_arc"):
            arcs.append((in_plane_uv(r, 1, axis), in_plane_uv(r, 2, axis), in_plane_uv(r, 3, axis)))
    return arcs

def make_line_edge(p_uv, q_uv, axis, plane_value):
    return Edge.make_line(world_vec_axis(p_uv, axis, plane_value), world_vec_axis(q_uv, axis, plane_value))

def make_arc_edge_uv(p1_uv, p2_uv, p3_uv, axis, plane_value):
    return Edge.make_three_point_arc(world_vec_axis(p1_uv, axis, plane_value), world_vec_axis(p2_uv, axis, plane_value), world_vec_axis(p3_uv, axis, plane_value))

def closed_face_from_edges(edges):
    return Face(Wire(edges))

def closed_face_from_lines_and_arcs(line_segs, arc_triples, axis, plane_value):
    edges = [make_line_edge(a, b, axis, plane_value) for a, b in line_segs]
    edges += [make_arc_edge_uv(p1, p2, p3, axis, plane_value) for p1, p2, p3 in arc_triples]
    return closed_face_from_edges(edges)


# ══════════════════════════════════════════════════════════════════════════
# G1 — Read S1 Sketch: build closed profile, extrude both directions with taper
# ══════════════════════════════════════════════════════════════════════════
print(f"\n[G1] Reading {S_CSV[1].name}")
s1_rows = read_rows(S_CSV[1])
_, S1_AXIS, S1_PLANE = detect_sketch_plane(s1_rows)

s1_lines = parse_line_segments(s1_rows, S1_AXIS)
s1_arcs  = parse_three_point_arcs(s1_rows, S1_AXIS)

# Construct the face from the provided arcs and lines
s1_outer_face = closed_face_from_lines_and_arcs(s1_lines, s1_arcs, S1_AXIS, S1_PLANE)

# Extrude +1 unit along +Y with 45 degree taper to make it smaller
ext_plus = extrude(s1_outer_face, amount=1.0, dir=tuple(axis_normal(S1_AXIS)), taper=45.0)

# Extrude 1 unit along -Y with no taper
neg_dir = tuple(-1 * v for v in axis_normal(S1_AXIS))
ext_minus = extrude(s1_outer_face, amount=1.0, dir=neg_dir)

# Fuse them together
g1_body = ext_plus + ext_minus

stage_pieces.append(g1_body)
checkpoint(1, f"G1 S1 profile extruded 1 unit +Y (45 taper) and 1 unit -Y")


# ══════════════════════════════════════════════════════════════════════════
# G2 — Apply 0.5 unit radius fillet to edges at y=1 and y=2
# ══════════════════════════════════════════════════════════════════════════
print(f"\n[G2] Fillet 0.5 to specific edges at Y=1 and Y=2")

g2_body = g1_body
edges_to_fillet = []

for e in g1_body.edges():
    cy = e.center().Y
    if abs(cy - 1.0) < EPSILON_MM or abs(cy - 2.0) < EPSILON_MM:
        edges_to_fillet.append(e)

if edges_to_fillet:
    try:
        g2_body = fillet(edges_to_fillet, radius=0.5)
    except Exception as exc:
        print(f"     ⚠ Fillet failed ({exc})")

stage_pieces[:] = [p for p in stage_pieces if p is not g1_body]
stage_pieces.append(g2_body)
checkpoint(2, f"G2 Fillet radius=0.5 applied to edges at Y=1 and Y=2")


# ══════════════════════════════════════════════════════════════════════════
# G4 — Drill holes from S2 points
# ══════════════════════════════════════════════════════════════════════════
print(f"\n[G4] Reading {S_CSV[2].name} and creating drill cuts")

s2_rows = read_rows(S_CSV[2])
s2_pts  = _collect_all_points(s2_rows)

g4_body = g2_body
drill_radius = 2.5 / 2.0
cyl_depth = 1.0
drill_angle = 118.0
half_angle = drill_angle / 2.0
tip_height = drill_radius / math.tan(math.radians(half_angle))

for pt in s2_pts:
    px, py, pz = float(pt[0]), float(pt[1]), float(pt[2])
    
    # Base cylinder (straight part of the drill)
    cyl_plane = Plane(origin=(px, py, pz), z_dir=(0, 1, 0))
    cyl = Solid.make_cylinder(drill_radius, cyl_depth, cyl_plane)
    
    # Drill tip (cone shape at the end)
    cone_plane = Plane(origin=(px, py + cyl_depth, pz), z_dir=(0, 1, 0))
    cone = Solid.make_cone(drill_radius, 0.0, tip_height, cone_plane)
    
    # Combine tool and cut from main body
    tool = cyl + cone
    g4_body = g4_body - tool

stage_pieces[:] = [p for p in stage_pieces if p is not g2_body]
stage_pieces.append(g4_body)
checkpoint(4, f"G4 Created {len(s2_pts)} drill cuts (diam 2.5, depth 1.0, tip 118 deg)")


# ══════════════════════════════════════════════════════════════════════════
# G5 — Translate the model to match the bounding box/centroid
# ══════════════════════════════════════════════════════════════════════════
shift_x = 12.5000
shift_y = 0.0000
shift_z = 4.5000

print(f"\n[G5] Translating model to align bounding box with reference")
print(f"      Shift vector: X = {shift_x:+.4f}, Y = {shift_y:+.4f}, Z = {shift_z:+.4f}")

g5_body = Location(Vector(shift_x, shift_y, shift_z)) * g4_body

stage_pieces[:] = [p for p in stage_pieces if p is not g4_body]
stage_pieces.append(g5_body)
checkpoint(5, f"G5 Translated model by ({shift_x}, {shift_y}, {shift_z})")


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

# ── Pre-export checks ──────────────────────────────────────────────────────
all_faces          = list(final_compound.faces())
n_edges            = len(list(final_compound.edges()))
total_surface_area = sum(float(f.area) for f in all_faces)
print(f"     Total surface area : {total_surface_area:.3f} mm²")
print(f"     Face / edge count  : {len(all_faces)} / {n_edges}")

solids         = list(final_compound.solids())
all_watertight = all(s.is_valid for s in solids)
total_volume   = sum(float(s.volume) for s in solids)

if len(solids) == 0:
    print(f"     Model is a surface compound (unstitched faces), no volumetric solids present.")
else:
    print(f"     Closed solids      : {len(solids)} (all_valid={all_watertight})")
    print(f"     Total volume       : {total_volume:.3f} mm³")
    if len(solids) > 1:
        print(f"     ⚠  {len(solids)} disjoint solids in compound.")

# ── File output ────────────────────────────────────────────────────────────
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

# ── Summary file ───────────────────────────────────────────────────────────
summary_lines = [
    "=" * 70,
    f"BUILD SUMMARY  :  {FOLDER_NAME}",
    f"Time           :  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
    f"Range covered  :  {GUIDELINE_RANGE}",
    f"Guidelines     :  G1, G2, G4, G5 (G3 = export, last)",
    f"Part type      :  Volumetric Solid Part",
    "=" * 70, "",
    f"-- G1 : S1 — profile extrusion on {S1_AXIS.upper()}={S1_PLANE} --",
    f"  G1 body volume       : {g1_body.volume:.3f} mm³",
    "",
    f"-- G2 : Fillet on specified edges --",
    f"  G2 body volume       : {g2_body.volume:.3f} mm³",
    "",
    f"-- G4 : Drill holes from S2 points --",
    f"  Cut count            : {len(s2_pts)}",
    f"  G4 body volume       : {g4_body.volume:.3f} mm³",
    "",
    f"-- G5 : Move to align Bbox --",
    f"  Shift X              : +{shift_x:.4f} mm",
    f"  Shift Z              : +{shift_z:.4f} mm",
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