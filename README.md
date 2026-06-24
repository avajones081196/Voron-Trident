# Voron-Trident Reconstruction

Reconstruction of the [Voron-Trident](https://github.com/VoronDesign/Voron-Trident) printed STL parts in [build123d](https://github.com/gumyr/build123d), each part rebuilt **parametrically from extracted Fusion 360 coordinates** and validated against the original upstream STL.

**Reference (source STLs):** https://github.com/VoronDesign/Voron-Trident
**This repo:** https://github.com/avajones081196/Voron-Trident

Every part is rebuilt **from scratch in build123d** — not converted from the mesh — so the result is a clean parametric model that matches the original geometry as closely as the source data allows.

> **Progress: 3 of 145 parts reconstructed & validated.** `[a]_cable_bridge_3hole` (G1–G26), `[a]_exhaust_filter_mount_x2` (G1–G6) and `[a]_skirt_logo_x2` (G1–G4) all **pass validation against the upstream STL** in VOLUME mode — cable_bridge: **volumetric 0.029 %, symmetric 0.232 %**; exhaust_filter_mount: **volumetric 0.019 %, symmetric 0.104 %**; skirt_logo: **volumetric 0.071 %, symmetric 0.071 %**; bounding box & centroid PASS for all. The remaining 142 parts are listed as **Pending** in the status section below.
>
> Two reusable files now live in this folder and drive every future part: **`TEMPLATE.md`** (the stable build spec) and **`COOKBOOK.md`** (patterns P-01…P-14, plus **P-11a** added from part 2 — plane detection, fillet/chamfer-by-sweep, offset-chamfer with mitered corners, watertight export, determinism, etc.).

---

## Project Overview

For each part the repo provides a self-contained `<part_name>/` folder. Folder names are the upstream part names (e.g. `[a]_cable_bridge_3hole`, `z_carriage_left`, `Octopus_bracket_set`).

Each folder contains:

```
<part_name>/
├── csv_data_<part_name>/          # raw extracted Fusion CSVs
├── csv_merged/                    # cleaned / merged CSVs (input to the build script)
├── 0_preprocess_csvs.py           # CSV cleaner (csv_data_<part_name> -> csv_merged)
├── 0_preprocess_csvs_summary.txt
├── <part_name>.py                 # build123d reconstruction script (name == folder name)
├── <part_name>.stl                # FINAL build output — a WATERTIGHT mesh
├── <part_name>_summary.txt        # per-guideline build summary
├── source_<part_name>.stl         # reference STL from the upstream Voron-Trident repo
├── validation.py                  # build-vs-source comparison (auto volume / surface mode)
└── <part_name>_validation.txt     # validation report
```

The script name matches the folder/part name, and the final deliverable STL is
named to match too (a stable `<part_name>.stl` the validator expects). During
development the script can stop at a checkpoint guideline and write range-tagged
files instead (`<part_name>_G_1_<n>.{stl,step,txt}`); see *Per-guideline
checkpointing*. The CSV preprocessor reads `csv_data_<part_name>/` and writes
`csv_merged/`. **Repo-root files:** `TEMPLATE.md` (build spec) and `COOKBOOK.md`
(reusable patterns) apply to all parts.

---

## Validation & metric selection

`validation.py` is identical in every folder. It compares the build output against the reference `source_<part_name>.stl` and **chooses its metrics automatically** from the geometry it is given.

**Reference resolution (priority order).** The reference mesh is located by trying, in order:

1. the current GitHub raw path — `raw.githubusercontent.com/avajones081196/Voron-Trident/main/<part_name>/source_<part_name>.stl`,
2. the same path after ownership transfer — `avajones081196` replaced by **`sft-01`**,
3. the **local** `source_<part_name>.stl` already sitting in the folder.

A network copy is cached locally (without clobbering an existing local file), so once a copy is present the validation runs fully offline.

> Note: the attached `validation.py` currently targets the `zaphod-bot` repo (`GITHUB_REPO = "zaphod-bot"`). For this project that constant should be set to `"Voron-Trident"`; the local-fallback path works regardless.

**Watertight check → which metrics are reported.** The script builds each mesh into a solid with `manifold3d` (which merges coincident vertices and tolerates minor non-manifold defects). Then:

- **Both meshes watertight → VOLUME mode.** Used only when the source **and** the build both close into valid solids. Reports **Volumetric difference %** = `|V_build − V_ref| / V_ref · 100` and **Symmetric volume difference %** = `(V_build + V_ref − 2·V_intersection) / V_ref · 100`.
- **Either mesh open → SURFACE mode.** Used when a build or its reference does not enclose a solid. Falls back to **surface-area % error**, **Hausdorff (max) distance** and **mean point-to-point distance**, sampled over the two surfaces.

Both modes always print the per-axis **bounding box** and the **centroid**, and the report states which mode was chosen and why.

**Grading thresholds** (from `validation.py`):

| Metric | 🟢 Excellent | 🟡 Good | 🟠 Acceptable | 🔴 Poor |
|--------|-----------|-------|-------------|-------|
| Volumetric difference % | ≤ 1.0 | ≤ 3.0 | ≤ 5.0 | > 5.0 |
| Symmetric volume diff % | ≤ 2.0 | ≤ 5.0 | ≤ 10.0 | > 10.0 |
| Surface-area % error | ≤ 0.5 | ≤ 2.0 | ≤ 5.0 | > 5.0 |
| Hausdorff (max), mm | ≤ 0.1 | ≤ 0.5 | ≤ 1.0 | > 1.0 |
| Bounding box / axis, mm | ≤ 0.1 | — | — | > 0.1 |
| Centroid / axis, mm | ≤ 0.1 | — | — | > 0.1 |

These are **FDM print-tolerance** thresholds and are intentionally looser than reverse-engineering / metrology defaults, which are inappropriate for CAD-vs-CAD comparison of print-grade parts.

---

## Status

### Completed / in progress

| # | Part | Status | Guidelines | Vol diff % | Symm vol diff % |
|---|------|--------|-----------|-----------|-----------------|
| 1 | `[a]_cable_bridge_3hole` | ✅ Built & validated | G1–G26 (G3 = export; G10 deferred) | **0.029 %** 🟢 | **0.232 %** 🟢 |
| 2 | `[a]_exhaust_filter_mount_x2` | ✅ Built & validated | G1–G6 (G3 = export) | **0.019 %** 🟢 | **0.104 %** 🟢 |
| 3 | `[a]_skirt_logo_x2` | ✅ Built & validated | G1–G4 (G3 = export) | **0.071 %** 🟢 | **0.071 %** 🟢 |

> **Any not-yet-built component** carries the placeholder *"discuss structure, methodology and validation script details"* in place of its metrics until it is reconstructed and validated.

### Pending (142 parts, grouped by subsystem)

**[a] assembly group**
`[a]_btt_knob_light_shield`, `[a]_cable_bridge_2hole`, `[a]_cover_bearing_x2`, `[a]_cover_logo_x2`, `[a]_d2f_cover`, `[a]_exhaust_fan_grill`, `[a]_exhaust_grill`, `[a]_fan_grill_a_x2`, `[a]_fan_grill_b_x2`, `[a]_fan_grill_open_optional_x2`, `[a]_fan_grill_retainer_x2`, `[a]_filter_access_cover`, `[a]_idler_carrier_a_x2`, `[a]_idler_carrier_b_x2`, `[a]_idler_front_x2`, `[a]_keystone_blank_insert_x2`, `[a]_mini12864_case_front_insert`, `[a]_mini12864_case_hinge`, `[a]_skirt_corner_a_x2`, `[a]_skirt_corner_b_x2`, `[a]_xy_left`, `[a]_xy_right`, `[a]_xy_right_d2f`, `[a]_y_bumper`, `[a]_y_endstop_pod`, `[a]_z_carriage_left`, `[a]_z_carriage_rear`, `[a]_z_carriage_right`, `[a]_z_cover_left`, `[a]_z_cover_rear`, `[a]_z_cover_right`, `[a]_z_rail_stop_x2`

**Z axis / bed**
`z_alignment_tool_rear`, `z_bed_left`, `z_bed_rear`, `z_bed_right`, `z_carriage_left`, `z_carriage_rear`, `z_carriage_right`, `z_endstop`, `z_lower_2hole`, `z_lower_3hole`, `z_rear_insert_2hole`, `z_rear_insert_3hole`, `z_stepper_left`, `z_stepper_rear`, `z_stepper_right`

**XY / X-carriage (motion)**
`x_carriage_frame_left`, `x_carriage_frame_right`, `xy_left_lower`, `xy_left_upper`, `xy_right_lower`, `xy_right_upper`

**A/B steppers**
`a_stepper_lower`, `a_stepper_upper`, `b_stepper_lower`, `b_stepper_upper`, `ba_pulley_align_tool`

**Skirts**
`front_skirt_left_250`, `front_skirt_left_300`, `front_skirt_left_350`, `front_skirt_right_250`, `front_skirt_right_300`, `front_skirt_right_350`, `rear_skirt_center_250`, `rear_skirt_center_300`, `rear_skirt_center_350`, `rear_skirt_keystone`, `rear_skirt_power_adamstech`, `rear_skirt_power_filtered`, `side_skirt_a_250_x2`, `side_skirt_a_300_x2`, `side_skirt_a_350_x2`, `side_skirt_b_250_x2`, `side_skirt_b_300_x2`, `side_skirt_b_350_x2`, `skirt_corner_a_x2`, `skirt_corner_b_x2`

**Panels / clips / supports**
`bottom_panel_clip_x4`, `bottom_panel_hinge_x2`, `corner_panel_clip_4mm_x8`, `corner_panel_clip_6mm_x8`, `midspan_panel_clip_4mm_x7`, `midspan_panel_clip_6mm_x8`, `deck_support_3mm_optional_x6`, `deck_support_4mm_optional_x6`, `cable_frame_anchor_x9`, `chain_wire_anchor_3hole_x2`, `chain_wire_anchor_a_3hole`

**Electronics / board brackets**
`BIGDIPPER_bracket_set`, `BTT_MOT_EXP_bracket`, `Duet2_Duet3Mini5_bracket_set`, `GTR_bracket_set`, `Octopus_bracket_set`, `S6_bracket_set`, `SKR_Pro_bracket_set`, `SKR_bracket_inline_set`, `Spider_bracket_set`, `raspberrypi_bracket`, `pcb_din_clip_x3`, `din_center_support_x2`, `din_frame_mount_x4`, `wago_221-412_mount`, `wago_221-415_corner_mount`

**PSU**
`lrs_psu_bracket_x2`, `rs25_psu_bracket`, `psu_stabilizer_50mm`

**PTFE**
`corner_ptfe_plate`, `ptfe_holder`, `ptfe_inlet_clamp`, `ptfe_jig_35mm`, `ptfe_plate`

**Exhaust / filter**
`exhaust_filter_grill`, `exhaust_filter_housing`

**Mini12864 display**
`mini12864_case_front`, `mini12864_case_rear`

**Umbilical**
`umbilical_mount_bottom_2hole`, `umbilical_mount_bottom_3hole`, `umbilical_mount_front_2hole`, `umbilical_mount_front_3hole`

**Rails / guides**
`MGN9_rail_guide_x2`, `MGN12_rail_guide_x2`

**UHP mounts**
`UHP_200_Mount_x2`, `UHP_350_Mount_x2`

**Probe**
`pinda_adapter`, `probe_retainer_bracket`, `probe_retainer_bracket_9mm`

**Handles / latch / hinges**
`handle_a_x2`, `handle_b_x2`, `latch_x2`, `door_hinge_x6`

**Wire covers**
`wire_cover_left`, `wire_cover_right`

**Spool holder**
`spool_holder_arm`, `spool_holder_base`

**Misc / tools / jigs**
`10mm_extrusion_drill_guide`, `140mm_extrusion_drill_guide`, `110mm_Y_alignment_spacer_x2`, `idler_housing_x2`, `side_fan_support_x2`, `circlip_x2`, `rear_vertext_upper_brace`

---

## Per-part reconstruction notes

### `[a]_cable_bridge_3hole`

The first part, built end-to-end across **G1–G26** (G3 = export, G10 deferred) from one main sketch (S1) plus ~40 auxiliary sketches (S2–S42). Final solid is **watertight, volume 8655.1 mm³**, validated against the source STL at **0.029 % volumetric / 0.232 % symmetric difference** (both 🟢), bounding box and centroid PASS.

Highlights / techniques (each recurring trick is captured in `COOKBOOK.md`):

- **G1 — tray (S1).** 76-primitive sketch → outer outline + inner_base + six oval openings; outer walls extruded 15 mm, floor 3 mm, ovals pierced through.
- **G2 / G4 — chamfers by swept cut.** OCCT's edge-chamfer refused the solid, so 0.4 mm chamfers on the outer-wall and oval-rim edges are applied as swept profile cuts (P-05).
- **G5–G9, G11–G13 — bosses, slots, intersected body, mounting features.** Lofted bosses + drilled/countersunk holes (S3), through-slots (S4), an S5∩S6 intersected solid unioned in, and several extrude-cuts.
- **G14–G20 — edge rounding via sweeps.** Where OCCT fillet failed or was destructive, fillets/rounds are reconstructed as swept-bead cuts/joins along the matched edges.
- **G21 — the 1 mm cable-bridge fillet (S29).** Straight cuts + an arc transition loft + a **run-out taper to a point** along the S29 spline, driven by `MakePipeShell` with one S33 rail as spine and the other as guide so both edges stay pinned (P-08).
- **G22 — S35 groove along the S34 rail.** Constant-section sweep along a line+arc+spline chain, with a step-8 run-out taper; collinear "splines" demoted to lines so OCCT can sweep them (P-04).
- **G23 — 2 mm perimeter fillet (S37/S38).** Built **per edge** (P-06): each fillet profile constructed in the edge's wall/floor frame (inward side chosen by a point-inside probe), straight edges extruded, curved edges swept, tight corners/ramp chord-subdivided.
- **G24 — oval clear-out.** Re-cuts the six S1 ovals +Z so the G23 rib doesn't overhang the holes.
- **G25 / G26 — S40 cut and the S41 1 mm fillet.** S41 step-1 fillet uses the user's S42 profile extruded along the edge for a smooth cylindrical surface.
- **G3 — watertight export.** `.clean()` → STEP round-trip → deterministic conformal mesh → sliver removal + manifold3d repair → verified watertight (P-11). The raw STL was non-watertight because the boolean history leaves zero-area sliver faces; this recipe produces a reproducible solid every run.

**Validation (VOLUME mode):** volumetric diff 0.0290 %, symmetric volume diff 0.2316 %, bbox PASS (exact on all axes), centroid distance 0.0087 mm. Report: `[a]_cable_bridge_3hole_validation.txt`.

### `[a]_exhaust_filter_mount_x2`

A flat mount plate built across **G1–G6** (G3 = export) from one main sketch (S1, the footprint + circular through-hole) plus three auxiliary chamfer/cut sketches (S2–S4). Final solid is **watertight, volume 2112.9 mm³**, validated against the source STL at **0.019 % volumetric / 0.104 % symmetric difference** (both 🟢), bounding box exact on all axes, centroid distance 0.0009 mm.

Highlights / techniques (captured in `COOKBOOK.md`):

- **G1 — footprint (S1).** Outer outline (8 lines + 6 arcs) extruded 4 mm down (sketch plane z=4 → z=0); the inner circle (row 15) pierced as a through-hole.
- **G2 / G4 — outer chamfers (S2 / S3).** 0.4 mm × 45° chamfer along the outer outline at the z=4 (top) and z=0 (bottom) faces. A literal per-edge sweep of the S2/S3 profile left rough, stepped corners and a continuous sweep self-intersects (P-06/P-09), so the chamfer is cut with an **offset tool** — the wedge between the full outline and the outline offset inward by the chamfer leg, tapered 45°. `offset_2d` miters/blends every corner, so the result is smooth. The chamfer leg (0.4) is read from the S2/S3 diagonal to stay data-driven; the inner circle is excluded.
- **G5 — hole-end countersinks.** 0.4 mm × 45° chamfer at both ends of the circular hole (z=4 and z=0), built as loft cones (robust + sliver-free, vs sweeping a profile around a closed circle).
- **G6 — notch (S4).** Extrude-cut the S4 bump/notch profile through the part (5 units −Z, 1 unit +Z; the +Z overshoot avoids coincident faces). This carves the feature that the revised S1 outline left flat.
- **G3 — watertight export (P-11 + P-11a).** The chamfer cuts + notch leave (1) shared-edge vertices ~1e-7 mm apart on adjacent faces (free edges) and (2) near zero-area sliver triangles (non-manifold edges), so the naive STL reads `solid=False` / `volume=nan`. Fix: **weld** vertices (round to 1e-5 mm) + drop **duplicate and degenerate** faces + fix normals → watertight in-memory → `manifold3d` → **ASCII** STL (binary float32 re-splits shared verts on reload). Deterministic across runs.

**Validation (VOLUME mode):** volumetric diff 0.0194 %, symmetric volume diff 0.1042 %, bbox PASS (exact on all axes), centroid distance 0.0009 mm. Report: `[a]_exhaust_filter_mount_x2_validation.txt`.

### `[a]_skirt_logo_x2`

A round logo badge built across **G1–G4** (G3 = export) from a single sketch (S1): one 3-point circle plus three parallelograms (the stylised Voron "V"). Final solid is **watertight, volume 1280.7 mm³**, validated against the source STL at **0.071 % volumetric / 0.071 % symmetric difference** (both 🟢), bounding box PASS on all axes, centroid distance 0.0029 mm.

Highlights / techniques (captured in `COOKBOOK.md`):

- **G1 — base + logo (S1).** The circle (centre (155,155), r=13) is extruded 0.8 mm down (sketch plane z=0.8 → z=0) into the round base; the three parallelograms are extruded 8 mm up (z=0.8 → z=8.8) and **fused with the base into ONE solid**. All three parallelograms sit within the disc footprint, so the union is naturally connected (logo prisms standing on the base).
- **G2 — base rim chamfer.** 0.4 mm × 45° chamfer along the circular base bottom edge at z=0, cut with the **offset-loft wedge** tool (P-15) using only the circle outline, so the logo prisms are untouched.
- **G4 — logo top chamfers.** 0.4 mm × 45° chamfer along each of the three parallelogram top edges. The guideline labelled this "z=8", but the data puts the top face at **z=8.8** (extruded +8 from the z=0.8 sketch plane); built to the data per TEMPLATE §7 and flagged in the script. Each outline is chamfered with its own offset-loft tool so every corner miters cleanly.
- **G3 — watertight export (P-11 / P-11a).** Deterministic per-face BRepMesh (`parallel=False`) → weld coincident shared-edge vertices + drop duplicate/degenerate faces + fix normals → `manifold3d` → **ASCII** STL, verified watertight on reload.

**Validation (VOLUME mode):** volumetric diff 0.0706 %, symmetric volume diff 0.0708 %, bbox PASS (within ±0.025 mm on all axes; the curved base introduces small mesh-facet deviation), centroid distance 0.0029 mm. Report: `[a]_skirt_logo_x2_validation.txt`.

---

## Methodology

The reconstruction pipeline is the same for every part. The comparison metrics differ by validation mode (volume vs surface — see *Validation & metric selection*); everything else is identical.

**Step 1 — Coordinate extraction in Fusion 360.** The reference STL is imported into Fusion 360. A custom Fusion add-in writes each sketch profile's line / arc / circle / spline endpoints to a CSV (`Fusion_Coordinates_S<N>.csv`), one logical sketch per file, in world-space millimetres.

**Step 2 — CSV preprocessing.** `0_preprocess_csvs.py` reads `csv_data_<part_name>/`, removes duplicate primitives, and writes cleaned files to `csv_merged/`. A summary log records what was merged or dropped.

**Step 3 — build123d reconstruction.** `<part_name>.py` (named to match the folder) derives its base directory from its own location (no hardcoded paths), prints the path and size of every CSV on first read, auto-detects each sketch plane (axis-aligned or SVD-fit), and rebuilds the part across numbered geometry guidelines added incrementally. **G3 is always the final export step** and is not counted in the guideline range. The script tracks cumulative surface area / volume per guideline and supports per-guideline checkpointing to the OCP viewer (`VIEW_AT`). The export is **watertight and deterministic**: `.clean()` alone isn't enough (the boolean history leaves zero-area sliver faces), so G3 round-trips the solid through STEP, re-meshes deterministically (`BRepMesh parallel=False`), removes the slivers and repairs with `manifold3d`/`trimesh`, and verifies the exported STL reloads strictly watertight (falling back to a raw export with a warning if a repair dependency is missing). The final deliverable is a stable `<part_name>.stl` plus a build summary. Build conventions and recurring solutions are codified in `TEMPLATE.md` and `COOKBOOK.md` (repo root).

> **Watertight-export dependencies:** the repair path needs `trimesh`, `manifold3d` **and `networkx`** installed in the same environment that runs the build. If any is missing, G3 silently falls back to a raw (non-watertight) STL and the validator drops to surface mode.

**Step 4 — validation.** `validation.py` compares the build STL against the upstream `source_<part_name>.stl`, auto-selecting volume or surface mode (see above) and grading against the FDM thresholds. The report is written to `<part_name>_validation.txt`.
