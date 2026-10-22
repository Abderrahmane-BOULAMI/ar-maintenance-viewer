"""Measure the added value of the 3D/AR viewer for maintenance teams (evaluation protocol, docs/).

Inputs collected during field trials:
- session logs exported by the viewer (button 'Journal'), one JSON per session;
- a timing sheet comparing the current way of working (paper / CMMS screens) with the viewer;
- the 10 answers of the System Usability Scale (SUS) per participant.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import mannwhitneyu


def sus_score(answers) -> float:
    """System Usability Scale: 10 answers from 1 to 5 -> score from 0 to 100."""
    a = np.asarray(answers, float)
    if a.shape != (10,) or a.min() < 1 or a.max() > 5:
        raise ValueError("SUS needs 10 answers between 1 and 5")
    odd, even = a[0::2] - 1, 5 - a[1::2]
    return float((odd.sum() + even.sum()) * 2.5)


def sus_grade(score: float) -> str:
    """Adjective scale commonly used with SUS (Bangor et al.)."""
    for limit, word in ((85, "excellent"), (72, "bon"), (52, "correct"), (38, "médiocre")):
        if score >= limit:
            return word
    return "inacceptable"


def log_to_rows(path: str | Path, participant: str) -> pd.DataFrame:
    """Viewer session log -> one row per procedure step with its duration."""
    ev = json.loads(Path(path).read_text(encoding="utf-8"))["events"]
    rows = [{"participant": participant, "procedure": e["id"], "step": e["step"], "seconds": e["seconds"]}
            for e in ev if e["event"] == "step_done"]
    return pd.DataFrame(rows)


def compare(timings: pd.DataFrame, baseline: str = "papier", tool: str = "3D") -> pd.DataFrame:
    """Per task: median time with each method, change, error rate and a Mann-Whitney test.

    timings columns: participant, method, task, seconds, errors.
    """
    out = []
    for task, d in timings.groupby("task"):
        a, b = d[d.method == baseline], d[d.method == tool]
        if len(a) < 2 or len(b) < 2:
            continue
        p = mannwhitneyu(a.seconds, b.seconds, alternative="two-sided").pvalue
        out.append({"task": task, "n": f"{len(a)} / {len(b)}",
                    f"median_s_{baseline}": float(a.seconds.median()), f"median_s_{tool}": float(b.seconds.median()),
                    "change_pct": float((b.seconds.median() / a.seconds.median() - 1) * 100),
                    f"errors_{baseline}": float(a.errors.mean()), f"errors_{tool}": float(b.errors.mean()),
                    "p_value": float(p)})
    return pd.DataFrame(out)


def report(timings: pd.DataFrame, sus: pd.DataFrame) -> str:
    """Markdown summary for the evaluation report (numbers only, conclusions are written by the team)."""
    c = compare(timings)
    scores = sus.drop(columns=["participant"]).apply(sus_score, axis=1)
    lines = ["| Tâche | Médiane actuelle (s) | Médiane outil (s) | Écart | Erreurs actuelle | Erreurs outil | p |",
             "|---|---|---|---|---|---|---|"]
    for r in c.itertuples(index=False):
        lines.append(f"| {r.task} | {r[2]:.0f} | {r[3]:.0f} | {r.change_pct:+.0f} % | {r[5]:.2f} | {r[6]:.2f} | "
                     f"{r.p_value:.3f} |")
    lines += ["", f"SUS : moyenne {scores.mean():.1f} / 100 ({sus_grade(scores.mean())}), "
                  f"n = {len(scores)}, min {scores.min():.0f}, max {scores.max():.0f}."]
    return "\n".join(lines)
