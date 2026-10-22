"""Maintenance history (CMMS export) and the indicators shown on each equipment in the 3D view.

`generate_history` writes a synthetic two-year work-order log with the columns of a typical CMMS
export (SAP PM, Maximo, Coswin...). `equipment_kpis` only needs those columns, so a real export
can replace the synthetic file.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .scene import EQUIPMENT

COLUMNS = ["wo", "tag", "type", "failure_mode", "start", "end", "status", "description"]
MODES = {
    "robot": ["Buse colmatée", "Tube contact usé", "Faisceau de câbles", "Défaut codeur", "Collision"],
    "positioner": ["Fuite pneumatique", "Capteur de position", "Défaut variateur"],
    "conveyor": ["Bande déportée", "Roulement", "Capteur présence pièce", "Moteur"],
    "hydraulic": ["Fuite flexible", "Filtre colmaté", "Température huile", "Pompe"],
    "cabinet": ["Disjoncteur", "Ventilation armoire", "Carte E/S"],
    "power": ["Dévidoir", "Refroidissement torche", "Carte de commande"],
    "extraction": ["Filtre saturé", "Courroie ventilateur", "Débit insuffisant"],
}
# mean time between failures (h of calendar time) and median repair time (h), per kind
RELIABILITY = {"robot": (420, 1.2), "positioner": (900, 1.5), "conveyor": (300, 0.8), "hydraulic": (650, 2.0),
               "cabinet": (2500, 1.0), "power": (1100, 0.7), "extraction": (800, 1.0)}
PM_EVERY_H = {"robot": 500, "positioner": 1000, "conveyor": 500, "hydraulic": 750, "cabinet": 2000,
              "power": 1000, "extraction": 750}


def generate_history(start="2024-10-01", days=730, seed=0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    t0 = pd.Timestamp(start)
    horizon = days * 24.0
    rows, wo = [], 100000
    for e in EQUIPMENT:
        mtbf, mttr = RELIABILITY[e.kind]
        t = rng.exponential(mtbf)
        while t < horizon:
            dur = float(rng.lognormal(np.log(mttr), 0.6))
            mode = rng.choice(MODES[e.kind])
            rows.append([wo, e.tag, "CORRECTIVE", mode, t0 + pd.Timedelta(hours=t),
                         t0 + pd.Timedelta(hours=t + dur), "CLOSED", f"{mode} sur {e.name.lower()}"])
            wo += 1
            t += dur + rng.exponential(mtbf)
        t = PM_EVERY_H[e.kind] * rng.uniform(0.2, 1.0)
        while t < horizon:
            dur = float(rng.uniform(0.5, 2.0))
            rows.append([wo, e.tag, "PREVENTIVE", "", t0 + pd.Timedelta(hours=t), t0 + pd.Timedelta(hours=t + dur),
                         "CLOSED", f"Visite préventive {e.name.lower()}"])
            wo += 1
            t += PM_EVERY_H[e.kind]
    df = pd.DataFrame(rows, columns=COLUMNS).sort_values("start").reset_index(drop=True)
    end = t0 + pd.Timedelta(days=days)
    # a few open orders at the extraction date
    for tag in rng.choice([e.tag for e in EQUIPMENT], 4, replace=False):
        e = next(x for x in EQUIPMENT if x.tag == tag)
        mode = rng.choice(MODES[e.kind])
        df.loc[len(df)] = [wo, tag, "CORRECTIVE", mode, end - pd.Timedelta(hours=float(rng.uniform(2, 60))), pd.NaT,
                           "OPEN", f"{mode} sur {e.name.lower()}"]
        wo += 1
    return df


def equipment_kpis(df: pd.DataFrame, as_of: pd.Timestamp | None = None, window_days: int = 365) -> pd.DataFrame:
    """MTBF, MTTR, availability, failure count, top failure modes, open orders, last and next preventive."""
    df = df.copy()
    df["start"], df["end"] = pd.to_datetime(df["start"]), pd.to_datetime(df["end"])
    as_of = as_of or df["start"].max()
    since = as_of - pd.Timedelta(days=window_days)
    out = []
    for e in EQUIPMENT:
        d = df[df["tag"] == e.tag]
        corr = d[(d["type"] == "CORRECTIVE") & (d["status"] == "CLOSED") & (d["start"] >= since)]
        down = ((corr["end"] - corr["start"]).dt.total_seconds() / 3600).sum()
        period = window_days * 24.0
        n = len(corr)
        mtbf = (period - down) / n if n else float("inf")
        mttr = down / n if n else 0.0
        prev = d[d["type"] == "PREVENTIVE"]
        last_pm = prev["start"].max() if len(prev) else pd.NaT
        pm_gap = prev["start"].sort_values().diff().median() if len(prev) > 1 else pd.NaT
        modes = corr["failure_mode"].value_counts().head(3)
        out.append({
            "tag": e.tag, "name": e.name, "failures_12m": n,
            "mtbf_h": round(mtbf, 1) if np.isfinite(mtbf) else None, "mttr_h": round(mttr, 2),
            "availability": round(1 - down / period, 4),
            "open_orders": int(((d["status"] == "OPEN")).sum()),
            "last_preventive": None if pd.isna(last_pm) else last_pm.strftime("%Y-%m-%d"),
            "next_preventive": None if pd.isna(last_pm) or pd.isna(pm_gap) else (last_pm + pm_gap).strftime("%Y-%m-%d"),
            "top_modes": [{"mode": m, "count": int(c)} for m, c in modes.items()],
        })
    k = pd.DataFrame(out)
    # red: chronic failures (20 or more in 12 months); orange: open work order or availability under 99.8%
    k["status"] = np.select([k["failures_12m"] >= 20, (k["open_orders"] > 0) | (k["availability"] < 0.998)],
                            ["red", "orange"], "green")
    return k


def last_interventions(df: pd.DataFrame, tag: str, n: int = 5) -> list[dict]:
    d = df[df["tag"] == tag].copy()
    d["start"] = pd.to_datetime(d["start"])
    d = d.sort_values("start", ascending=False).head(n)
    return [{"wo": int(r.wo), "date": r.start.strftime("%Y-%m-%d"), "type": r.type, "status": r.status,
             "description": r.description} for r in d.itertuples()]
