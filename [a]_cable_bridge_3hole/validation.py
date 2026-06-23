#!/usr/bin/env python3
"""
validation.py — geometry validation with automatic metric selection.

Compares  <component>.stl   (build123d output)
against    source_<component>.stl   (reference),
where <component> is the name of the folder this script lives in.
Writes a human-readable report next to itself.

REFERENCE RESOLUTION (priority order):
  1. Current GitHub raw  : raw.githubusercontent.com/avajones081196/zaphod-bot/main/<component>/source_<component>.stl
  2. Post-transfer owner : same path with 'avajones081196' replaced by 'sft-01'
  3. Local folder        : source_<component>.stl already sitting next to this script
A network hit is cached locally (only if no local copy exists) so later runs
work offline. If all three fail, validation errors out clearly.

STRATEGY (graceful degradation):
  1. VOLUME MODE — used when BOTH meshes can be built into a valid solid by
     manifold3d (merges coincident vertices, tolerates minor non-manifold
     defects). Reports:
        - Volumetric difference %       = |Vb - Vr| / Vr * 100
        - Symmetric volume difference % = (Va + Vb - 2*Vi) / Vr * 100
  2. SURFACE MODE — used when either mesh genuinely cannot form a closed solid
     (real holes / open surfaces). Reports surface-area % error + Hausdorff +
     mean point-to-point distance.
  3. ALWAYS — bounding box (per axis) and centroid, plus the chosen mode + why.
"""

import os
import sys
import urllib.request

BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
COMPONENT = os.path.basename(BASE_DIR)
BUILD_STL = os.path.join(BASE_DIR, f"{COMPONENT}.stl")
REPORT    = os.path.join(BASE_DIR, f"{COMPONENT}_validation.txt")

# Reference-resolution config -------------------------------------------------
GITHUB_OWNERS = ["avajones081196", "sft-01"]  # current owner first, then post-transfer owner
GITHUB_REPO   = "zaphod-bot"
GITHUB_BRANCH = "main"
NET_TIMEOUT_S = 10

BBOX_TOL_MM, CENTROID_TOL_MM = 0.1, 0.1
VOL_PCT_EXCELLENT, VOL_PCT_GOOD, VOL_PCT_ACCEPTABLE = 1.0, 3.0, 5.0
SYM_PCT_EXCELLENT, SYM_PCT_GOOD, SYM_PCT_ACCEPTABLE = 2.0, 5.0, 10.0
AREA_PCT_EXCELLENT, AREA_PCT_GOOD, AREA_PCT_ACCEPTABLE = 0.5, 2.0, 5.0
HAUS_EXCELLENT_MM, HAUS_GOOD_MM, HAUS_ACCEPTABLE_MM = 0.1, 0.5, 1.0
HAUSDORFF_N_SAMPLES = int(os.environ.get("VALIDATION_SAMPLES", "50000"))

import trimesh  # loading + surface measurement only


def resolve_reference():
    """Return a path to source_<COMPONENT>.stl using GitHub-first, local-fallback."""
    fname = f"source_{COMPONENT}.stl"
    local = os.path.join(BASE_DIR, fname)
    for owner in GITHUB_OWNERS:
        url = (f"https://raw.githubusercontent.com/{owner}/{GITHUB_REPO}/"
               f"{GITHUB_BRANCH}/{COMPONENT}/{fname}")
        try:
            with urllib.request.urlopen(url, timeout=NET_TIMEOUT_S) as r:
                data = r.read()
            if data:
                if not os.path.exists(local):           # cache, never clobber a local copy
                    with open(local, "wb") as f:
                        f.write(data)
                print(f"  Reference resolved from GitHub ({owner})")
                return local if os.path.exists(local) else _spool(data, fname)
        except Exception:
            continue
    if os.path.exists(local):
        print("  Reference resolved from local folder")
        return local
    return local  # not found -> downstream error


def _spool(data, fname):
    import tempfile
    p = os.path.join(tempfile.gettempdir(), fname)
    with open(p, "wb") as f:
        f.write(data)
    return p


def grade(v, exc, good, acc):
    return "EXCELLENT" if v <= exc else "GOOD" if v <= good else "ACCEPTABLE" if v <= acc else "POOR"


class Tee:
    def __init__(self, path):
        self.term = sys.stdout; self.f = open(path, "w", encoding="utf-8")
    def write(self, m): self.term.write(m); self.f.write(m)
    def flush(self): self.term.flush(); self.f.flush()
    def close(self): self.f.close()


def to_manifold(mesh):
    """Build a manifold3d solid from a trimesh mesh; None if it can't form a valid closed solid."""
    try:
        import numpy as np, manifold3d as m3d
        mm = m3d.Manifold(m3d.Mesh(
            vert_properties=np.asarray(mesh.vertices, dtype=np.float32),
            tri_verts=np.asarray(mesh.faces, dtype=np.uint32)))
        if mm.is_empty() or mm.volume() <= 0:
            return None
        return mm
    except Exception:
        return None


def bbox_centroid(mb, mr):
    print(f"\n  {'-'*64}\n  BOUNDING BOX  (tolerance +/-{BBOX_TOL_MM} mm per axis)\n  {'-'*64}")
    ba, bb = mb.bounds, mr.bounds
    axes = ['X min','X max','Y min','Y max','Z min','Z max']
    va = [ba[0][0],ba[1][0],ba[0][1],ba[1][1],ba[0][2],ba[1][2]]
    vr = [bb[0][0],bb[1][0],bb[0][1],bb[1][1],bb[0][2],bb[1][2]]
    print(f"  {'Axis':<6}{'Build':>12}{'Reference':>12}{'Diff mm':>10}  Status")
    ok = True
    for ax, a, r in zip(axes, va, vr):
        d = a - r; p = abs(d) <= BBOX_TOL_MM; ok = ok and p
        print(f"  {ax:<6}{a:>12.4f}{r:>12.4f}{d:>+10.4f}  {'PASS' if p else 'FAIL'}")
    print(f"  Overall bounding box : {'PASS' if ok else 'FAIL'}")
    print(f"\n  {'-'*64}\n  CENTROID  (tolerance +/-{CENTROID_TOL_MM} mm per axis)\n  {'-'*64}")
    ca, cr = mb.centroid, mr.centroid
    dist = ((ca[0]-cr[0])**2 + (ca[1]-cr[1])**2 + (ca[2]-cr[2])**2) ** 0.5
    cok = dist <= CENTROID_TOL_MM
    print(f"  Build    : ({ca[0]:.4f}, {ca[1]:.4f}, {ca[2]:.4f})")
    print(f"  Reference: ({cr[0]:.4f}, {cr[1]:.4f}, {cr[2]:.4f})")
    print(f"  Centroid distance : {dist:.4f} mm  -> {'PASS' if cok else 'FAIL'}")
    return ok, cok


def main():
    if not os.path.exists(BUILD_STL): sys.exit(f"ERROR: build mesh not found: {BUILD_STL}")
    ref_stl = resolve_reference()
    if not os.path.exists(ref_stl):   sys.exit(f"ERROR: reference mesh not found: source_{COMPONENT}.stl")
    tee = Tee(REPORT); sys.stdout = tee
    mode = None
    try:
        print("=" * 66)
        print("  GEOMETRY VALIDATION REPORT")
        print(f"  Component : {COMPONENT}")
        print(f"  Build     : {os.path.basename(BUILD_STL)}")
        print(f"  Reference : {os.path.basename(ref_stl)}")
        print("=" * 66)

        mb = trimesh.load(BUILD_STL); mr = trimesh.load(ref_stl)
        mb_m, mr_m = to_manifold(mb), to_manifold(mr)
        for label, m, mm in (("Build", mb, mb_m), ("Reference", mr, mr_m)):
            v = mm.volume() if mm is not None else float('nan')
            print(f"  {label:<10}: {len(m.faces):,} triangles | solid={mm is not None} | "
                  f"volume={v:.4f} mm^3 | area={m.area:.4f} mm^2")

        results = {}
        if mb_m is not None and mr_m is not None:
            try:
                import manifold3d as m3d
                vb, vr = mb_m.volume(), mr_m.volume()
                inter = m3d.Manifold.batch_boolean([mb_m, mr_m], m3d.OpType.Intersect)
                vi = inter.volume()
                results = {"vol_pct": abs(vb-vr)/vr*100.0, "sym_pct": (vb+vr-2*vi)/vr*100.0,
                           "vb": vb, "vr": vr, "vi": vi}
                mode = "VOLUME"
            except Exception as e:
                print(f"\n  [!] Volume mode chosen but boolean failed: {e}\n      Falling back to SURFACE mode.")
                mode = None
        if mode is None:
            mode = "SURFACE"

        why = ("both meshes form valid closed solids (via manifold3d)" if mode == "VOLUME"
               else f"build solid={mb_m is not None}, reference solid={mr_m is not None}"
                    " -> volume undefined, using surface metrics")
        print(f"\n  >>> MODE: {mode}  ({why})")

        if mode == "VOLUME":
            vp, sp = results["vol_pct"], results["sym_pct"]
            print(f"\n  {'-'*64}\n  VOLUME METRICS\n  {'-'*64}")
            print(f"  Build volume               : {results['vb']:.4f} mm^3")
            print(f"  Reference volume           : {results['vr']:.4f} mm^3")
            print(f"  Intersection volume        : {results['vi']:.4f} mm^3")
            print(f"  Volumetric difference %    : {vp:.4f} %   -> {grade(vp, VOL_PCT_EXCELLENT, VOL_PCT_GOOD, VOL_PCT_ACCEPTABLE)}")
            print(f"  Symmetric volume diff %    : {sp:.4f} %   -> {grade(sp, SYM_PCT_EXCELLENT, SYM_PCT_GOOD, SYM_PCT_ACCEPTABLE)}")
        else:
            ab, ar = mb.area, mr.area
            area_pct = abs(ab-ar)/ar*100.0 if ar else float('nan')
            print(f"\n  {'-'*64}\n  SURFACE METRICS\n  {'-'*64}")
            print(f"  Build surface area         : {ab:.4f} mm^2")
            print(f"  Reference surface area     : {ar:.4f} mm^2")
            print(f"  Surface-area % error       : {area_pct:.4f} %   -> {grade(area_pct, AREA_PCT_EXCELLENT, AREA_PCT_GOOD, AREA_PCT_ACCEPTABLE)}")
            try:
                import numpy as np
                pb = mb.sample(HAUSDORFF_N_SAMPLES); pr = mr.sample(HAUSDORFF_N_SAMPLES)
                _, d1, _ = mr.nearest.on_surface(pb); _, d2, _ = mb.nearest.on_surface(pr)
                alld = np.concatenate([d1, d2]); haus = float(alld.max()); mean = float(alld.mean())
                print(f"  Hausdorff (max) distance   : {haus:.4f} mm   -> {grade(haus, HAUS_EXCELLENT_MM, HAUS_GOOD_MM, HAUS_ACCEPTABLE_MM)}")
                print(f"  Mean point-to-point dist   : {mean:.4f} mm")
                print(f"  95th-percentile distance   : {float(np.percentile(alld,95)):.4f} mm")
            except Exception as e:
                print(f"  Hausdorff/mean distance    : (could not compute: {e}; pip install rtree)")

        bok, cok = bbox_centroid(mb, mr)
        print(f"\n{'='*66}\n  SUMMARY  (mode: {mode})\n{'='*66}")
        if mode == "VOLUME":
            print(f"  Volumetric difference %    : {results['vol_pct']:.4f} %")
            print(f"  Symmetric volume diff %    : {results['sym_pct']:.4f} %")
        else:
            print(f"  Surface-area % error / Hausdorff / mean - see SURFACE METRICS above")
        print(f"  Bounding box               : {'PASS' if bok else 'FAIL'}")
        print(f"  Centroid                   : {'PASS' if cok else 'FAIL'}")
        print("=" * 66)
    finally:
        sys.stdout = tee.term; tee.close()
    print(f"Report written -> {os.path.basename(REPORT)}  (mode: {mode})")


if __name__ == "__main__":
    main()
