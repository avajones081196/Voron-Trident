# Voron-Trident Reconstruction

Reconstruction of the [Voron-Trident](https://github.com/VoronDesign/Voron-Trident) printed STL parts in [build123d](https://github.com/gumyr/build123d), each part rebuilt **parametrically from extracted Fusion 360 coordinates** and validated against the original upstream STL.

**Reference (source STLs):** https://github.com/VoronDesign/Voron-Trident
**This repo:** https://github.com/avajones081196/Voron-Trident

Every part is rebuilt **from scratch in build123d** — not converted from the mesh — so the result is a clean parametric model that matches the original geometry as closely as the source data allows.

> **Progress: 1 of 145 parts reconstructed.** The first part, `[a]_cable_bridge_3hole`, is built end-to-end (G1–G7); validation against the upstream STL is pending. The remaining 144 parts are listed as **Pending** in the status section below.

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
├── <part_name>_build123d.py       # build123d reconstruction script
├── <part_name>_G_1_<n>.stl        # build123d output (mesh)
├── <part_name>_G_1_<n>.step       # build123d output (B-rep)
├── <part_name>_summary_G_1_<n>.txt        # per-guideline build summary
├── <part_name>_area_history_G_1_<n>.txt   # cumulative area/volume per guideline
├── source_<part_name>.stl         # reference STL from the upstream Voron-Trident repo
├── validation.py                  # build-vs-source comparison (auto volume / surface mode)
└── <part_name>_validation.txt     # validation report
```

The build script runs end to end and writes the STL/STEP for the guideline range it covers; the CSV preprocessor reads `csv_data_<part_name>/` and writes `csv_merged/`.

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

| # | Part | Status | Guidelines | Metrics |
|---|------|--------|-----------|---------|
| 1 | `[a]_cable_bridge_3hole` | 🔨 Built — validation pending | G1, G2, G4, G5, G6, G7 (G3 = export) | *to be filled after validation.py* |

> **Any not-yet-built component** carries the placeholder *"discuss structure, methodology and validation script details"* in place of its metrics until it is reconstructed and validated.

### Pending (144 parts, grouped by subsystem)

**[a] assembly group**
`[a]_btt_knob_light_shield`, `[a]_cable_bridge_2hole`, `[a]_cover_bearing_x2`, `[a]_cover_logo_x2`, `[a]_d2f_cover`, `[a]_exhaust_fan_grill`, `[a]_exhaust_filter_mount_x2`, `[a]_exhaust_grill`, `[a]_fan_grill_a_x2`, `[a]_fan_grill_b_x2`, `[a]_fan_grill_open_optional_x2`, `[a]_fan_grill_retainer_x2`, `[a]_filter_access_cover`, `[a]_idler_carrier_a_x2`, `[a]_idler_carrier_b_x2`, `[a]_idler_front_x2`, `[a]_keystone_blank_insert_x2`, `[a]_mini12864_case_front_insert`, `[a]_mini12864_case_hinge`, `[a]_skirt_corner_a_x2`, `[a]_skirt_corner_b_x2`, `[a]_skirt_logo_x2`, `[a]_xy_left`, `[a]_xy_right`, `[a]_xy_right_d2f`, `[a]_y_bumper`, `[a]_y_endstop_pod`, `[a]_z_carriage_left`, `[a]_z_carriage_rear`, `[a]_z_carriage_right`, `[a]_z_cover_left`, `[a]_z_cover_rear`, `[a]_z_cover_right`, `[a]_z_rail_stop_x2`

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

The first part. A cable-bridge cover built from a single in-plane sketch (S1) plus four auxiliary sketches (S2–S6). It runs to **G7 — six geometry guidelines** (`G1, G2, G4, G5, G6, G7`, with G3 the final export step), and is the first part in the repo to finish as **two separate solids**.

- **G1 — tray (S1, Z=0 plane).** The S1 sketch is a soup of 76 lines/arcs that assemble into one outer outline, one inner_base outline, and six oval openings (four small + two larger). The inner outline is open in the CSV — its dangling end sits exactly on the outer edge — so the inner_base is closed against a segment of the outer outline. The outer-wall region is extruded **15 mm** (+Z), the inner_base floor **3 mm** (+Z), and the six ovals are left as through-holes. Built as: full 15 mm block, pocket the inner region down to 3 mm, then pierce the six ovals. Volume ≈ 8645.7 mm³.
- **G2 — outer chamfer (sweep cut).** A 0.4 mm equal (45°) chamfer on the bottom outer-wall edges at z=0. OCCT's edge-chamfer refused this solid, so the chamfer is applied as a **swept S2-profile cut** along each edge.
- **G4 — oval chamfer (sweep cut).** The same 0.4 mm swept chamfer applied to the six oval rims at z=0 (countersink direction).
- **G5 — bosses + holes (S3).** Two cylindrical mounting bosses lofted on the −Y wall (outer circle r3.8 @ Y88.5 → r4.8 @ Y89.5), each drilled with an r2.7 hole (+10 mm / −1 mm along Y) and given a 0.4 mm countersink chamfer at the y=94.5 exit face.
- **G6 — slots (S4).** Two enclosed S4 profiles on the y=94.5 plane, extrude-cut through the body (13 mm along −Y, 1 mm along +Y to avoid coincident surfaces).
- **G7 — intersected body (S5 ∩ S6).** S5 (Y=126.5 plane) and S6 (X=87.85 plane) are extruded along their normals and **intersected** to form a new solid, kept separate from the G1–G6 part — so the model holds two bodies.

*Validation against `source_[a]_cable_bridge_3hole.stl` is pending; metrics will be recorded here once `validation.py` is run.*

---

## Methodology

The reconstruction pipeline is the same for every part. The comparison metrics differ by validation mode (volume vs surface — see *Validation & metric selection*); everything else is identical.

**Step 1 — Coordinate extraction in Fusion 360.** The reference STL is imported into Fusion 360. A custom Fusion add-in writes each sketch profile's line / arc / circle / spline endpoints to a CSV (`Fusion_Coordinates_S<N>.csv`), one logical sketch per file, in world-space millimetres.

**Step 2 — CSV preprocessing.** `0_preprocess_csvs.py` reads `csv_data_<part_name>/`, removes duplicate primitives, and writes cleaned files to `csv_merged/`. A summary log records what was merged or dropped.

**Step 3 — build123d reconstruction.** `<part_name>_build123d.py` derives its base directory from its own location (no hardcoded paths), prints the path and size of every CSV on first read, auto-detects each sketch plane (axis-aligned or SVD-fit), and rebuilds the part across numbered geometry guidelines. **G3 is always the final export step** and is not counted in the guideline range. The script tracks cumulative surface area / volume per guideline, supports per-guideline checkpointing to the OCP viewer (`VIEW_AT`), runs `.clean()` before export, and writes STL, STEP, a build summary, and an area-history file.

**Step 4 — validation.** `validation.py` compares the build STL against the upstream `source_<part_name>.stl`, auto-selecting volume or surface mode (see above) and grading against the FDM thresholds. The report is written to `<part_name>_validation.txt`.
