import copy
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from armaint import cmms, procedures
from armaint.evaluation import compare, sus_grade, sus_score
from armaint.scene import EQUIPMENT, budget_downsample, read_ply, scan_cell, voxel_downsample, write_ply

ROOT = Path(__file__).resolve().parent.parent


def test_scan_is_deterministic_and_labelled():
    a, ra, la = scan_cell(50_000, seed=1)
    b, _, _ = scan_cell(50_000, seed=1)
    assert np.array_equal(a, b)
    assert ra.min() >= 0.05 and ra.max() <= 1.0
    assert set(np.unique(la)) == set(range(-1, len(EQUIPMENT)))
    assert a[:, 2].min() > -0.05  # nothing under the floor beyond noise


def test_voxel_downsample_one_point_per_voxel():
    pts, refl, _ = scan_cell(50_000, seed=2)
    small, refl_s = voxel_downsample(pts, 0.05, refl)
    keys = np.floor(small / 0.05).astype(int)
    assert len(np.unique(keys, axis=0)) == len(small)
    assert len(small) < len(pts) and len(refl_s) == len(small)


def test_budget_downsample_respects_budget():
    pts, refl, _ = scan_cell(80_000, seed=3)
    (small, _), voxel = budget_downsample(pts, 20_000, refl)
    assert len(small) <= 20_000 and voxel > 0


def test_ply_roundtrip(tmp_path):
    pts = np.random.default_rng(0).normal(size=(100, 3)).astype(np.float32)
    rgb = np.random.default_rng(1).integers(0, 255, (100, 3)).astype(np.uint8)
    write_ply(tmp_path / "a.ply", pts, rgb)
    p2, c2 = read_ply(tmp_path / "a.ply")
    assert np.allclose(p2, pts) and np.array_equal(c2, rgb)


def test_kpis_on_known_history():
    t = pd.Timestamp("2026-01-01")
    rows = []
    for i in range(4):  # 4 failures of 2 h on R1 over the year
        rows.append([i, "R1", "CORRECTIVE", "Collision", t + pd.Timedelta(days=60 * i + 1),
                     t + pd.Timedelta(days=60 * i + 1, hours=2), "CLOSED", ""])
    rows.append([9, "R1", "CORRECTIVE", "Collision", t + pd.Timedelta(days=364), pd.NaT, "OPEN", ""])
    df = pd.DataFrame(rows, columns=cmms.COLUMNS)
    k = cmms.equipment_kpis(df, as_of=t + pd.Timedelta(days=365)).set_index("tag")
    assert k.loc["R1", "failures_12m"] == 4
    assert k.loc["R1", "mttr_h"] == pytest.approx(2.0)
    assert k.loc["R1", "mtbf_h"] == pytest.approx((8760 - 8) / 4)
    assert k.loc["R1", "availability"] == pytest.approx(1 - 8 / 8760, abs=1e-4)
    assert k.loc["R1", "open_orders"] == 1 and k.loc["R1", "status"] == "orange"
    assert k.loc["R2", "failures_12m"] == 0 and k.loc["R2", "status"] == "green"


def test_generated_history_columns_and_open_orders():
    df = cmms.generate_history(days=200, seed=4)
    assert list(df.columns) == cmms.COLUMNS
    assert (df["status"] == "OPEN").sum() == 4
    assert (pd.to_datetime(df["end"]).dropna() >= pd.to_datetime(df.loc[df["end"].notna(), "start"])).all()


def test_shipped_procedures_are_valid():
    assert procedures.validate(procedures.load(ROOT / "data" / "procedures.yaml")) == []


def test_validator_catches_missing_lockout_and_bad_tag():
    procs = procedures.load(ROOT / "data" / "procedures.yaml")
    bad = copy.deepcopy(procs[0])
    bad["id"] = "X"
    del bad["steps"][1]["lockout"]            # forget the lockout step
    bad["steps"][0]["tag"] = "R9"
    errs = procedures.validate([bad])
    assert any("without a lockout" in e for e in errs)
    assert any("unknown tag R9" in e for e in errs)


def test_validator_catches_duration_and_unreleased_energy():
    p = {"id": "Y", "equipment": "HPU", "duration_min": 60,
         "steps": [{"tag": "HPU", "text": "lock", "minutes": 5, "lockout": ["hydraulic"]},
                   {"tag": "HPU", "text": "work", "minutes": 5, "isolate": ["hydraulic"]}]}
    errs = procedures.validate([p])
    assert any("add up to 10" in e for e in errs) and any("still locked out" in e for e in errs)


def test_sus():
    assert sus_score([3] * 10) == 50
    assert sus_score([5, 1] * 5) == 100
    assert sus_grade(80) == "bon"
    with pytest.raises(ValueError):
        sus_score([3] * 9)


def test_compare_detects_faster_tool():
    rng = np.random.default_rng(0)
    rows = [{"participant": i, "method": m, "task": "localiser", "seconds": rng.normal(mu, 10), "errors": 0}
            for i in range(12) for m, mu in (("papier", 120), ("3D", 60))]
    c = compare(pd.DataFrame(rows))
    assert c.loc[0, "change_pct"] < -30 and c.loc[0, "p_value"] < 0.01


def test_scene_json_matches_build():
    s = json.loads((ROOT / "web" / "data" / "scene.json").read_text(encoding="utf-8"))
    assert {e["tag"] for e in s["equipment"]} == {e.tag for e in EQUIPMENT}
    assert all("status" in e["kpis"] for e in s["equipment"])
