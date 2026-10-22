"""Build the viewer data: scan -> reduced point cloud, CMMS export -> indicators, procedures -> checked.

    python -m armaint.build [--points 250000]

Writes web/data/cell.ply and web/data/scene.json, and results/build_report.json.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd

from . import cmms, procedures
from .scene import EQUIPMENT, budget_downsample, scan_cell, write_ply

ROOT = Path(__file__).resolve().parent.parent


def build(max_points: int = 250_000, raw_points: int = 600_000, seed: int = 0) -> dict:
    t = time.time()
    hist_path = ROOT / "data" / "cmms_history.csv"
    if not hist_path.exists():
        cmms.generate_history(seed=seed).to_csv(hist_path, index=False)
    hist = pd.read_csv(hist_path)
    kpis = cmms.equipment_kpis(hist)

    procs = procedures.load(ROOT / "data" / "procedures.yaml")
    errors = procedures.validate(procs)
    if errors:
        raise ValueError("procedures not publishable:\n" + "\n".join(errors))

    pts, refl, _ = scan_cell(raw_points, seed=seed)
    (small, refl_s), voxel = budget_downsample(pts, max_points, refl)
    grey = (40 + 200 * refl_s).astype(np.uint8)
    rgb = np.c_[grey, grey, (grey * 1.05).clip(0, 255).astype(np.uint8)]
    (ROOT / "web" / "data").mkdir(parents=True, exist_ok=True)
    write_ply(ROOT / "web" / "data" / "cell.ply", small, rgb)

    k = kpis.set_index("tag")
    scene = {
        "title": "Cellule de soudure robotisée (démonstrateur)",
        "units": "m",
        "up": "z",
        "data_as_of": str(pd.to_datetime(hist["start"]).max().date()),
        "equipment": [{
            "tag": e.tag, "name": e.name, "kind": e.kind, "center": e.center, "size": e.size, "shape": e.shape,
            "energy": list(e.energy),
            "kpis": {c: (None if (isinstance(v, float) and np.isnan(v)) else v)
                     for c, v in k.loc[e.tag].drop("name").to_dict().items()},
            "history": cmms.last_interventions(hist, e.tag),
        } for e in EQUIPMENT],
        "procedures": procs,
    }
    (ROOT / "web" / "data" / "scene.json").write_text(json.dumps(scene, ensure_ascii=False, indent=1, default=str),
                                                      encoding="utf-8")
    report = {
        "raw_points": int(len(pts)), "web_points": int(len(small)), "voxel_m": round(voxel, 4),
        "ply_mb": round((ROOT / "web" / "data" / "cell.ply").stat().st_size / 1e6, 2),
        "work_orders": int(len(hist)), "open_orders": int((hist["status"] == "OPEN").sum()),
        "equipment": len(EQUIPMENT), "procedures": len(procs),
        "procedure_steps": sum(len(p["steps"]) for p in procs),
        "status_count": kpis["status"].value_counts().to_dict(),
        "build_s": round(time.time() - t, 1),
    }
    (ROOT / "results").mkdir(exist_ok=True)
    (ROOT / "results" / "build_report.json").write_text(json.dumps(report, indent=2))
    return report


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--points", type=int, default=250_000, help="point budget of the target device")
    print(json.dumps(build(ap.parse_args().points), indent=2))
