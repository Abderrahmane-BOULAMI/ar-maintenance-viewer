"""Load and check step-by-step maintenance procedures before they are published to the viewer."""
from __future__ import annotations

from pathlib import Path

import yaml

from .scene import BY_TAG


def load(path: str | Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def validate(procs: list[dict]) -> list[str]:
    """Return a list of human-readable errors (empty list = publishable).

    Rules: unique ids; every tag exists in the scene; step minutes add up to the announced duration
    (within 20%); a step that needs an energy isolated must come after a lockout of that energy and
    before the release (a step without 'isolate' after a lockout means the equipment is released).
    """
    errors, seen = [], set()
    for p in procs:
        pid = p.get("id", "?")
        if pid in seen:
            errors.append(f"{pid}: duplicated id")
        seen.add(pid)
        if p.get("equipment") not in BY_TAG:
            errors.append(f"{pid}: unknown equipment {p.get('equipment')}")
        total = 0
        locked: set[str] = set()
        for i, s in enumerate(p.get("steps", []), 1):
            if s.get("tag") not in BY_TAG:
                errors.append(f"{pid} step {i}: unknown tag {s.get('tag')}")
            if not s.get("text"):
                errors.append(f"{pid} step {i}: empty text")
            total += s.get("minutes", 0)
            if s.get("lockout"):
                locked |= set(s["lockout"])
                continue
            need = set(s.get("isolate", []))
            missing = need - locked
            if missing:
                errors.append(f"{pid} step {i}: works on {sorted(missing)} energy without a lockout step before")
            if not need:
                locked = set()  # equipment released
        if p.get("duration_min") and abs(total - p["duration_min"]) > 0.2 * p["duration_min"]:
            errors.append(f"{pid}: steps add up to {total} min, announced {p['duration_min']} min")
        if locked:
            errors.append(f"{pid}: ends with energies still locked out {sorted(locked)}")
    return errors
