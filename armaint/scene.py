"""Equipment of the demonstration cell and a synthetic laser scan of it.

The real use case starts from a terrestrial laser scan (LiDAR) of a workshop. Here a robot welding
cell is described by simple shapes and sampled the way a scanner would see it: denser near the
scanner positions, with range noise and a reflectance value per point. Replace `scan_cell` by a
reader of the real scan (E57/PLY/LAS export) and keep the rest of the pipeline.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class Equipment:
    tag: str
    name: str
    kind: str
    center: tuple[float, float, float]   # metres, z up
    size: tuple[float, float, float]     # box size, or (diameter, diameter, height) for cylinders
    shape: str = "box"
    energy: tuple[str, ...] = ("electrical",)  # energies to isolate before intervention


EQUIPMENT = [
    Equipment("R1", "Robot de soudure 1", "robot", (-1.6, 0.8, 0.9), (0.6, 0.6, 1.8), "cyl"),
    Equipment("R2", "Robot de soudure 2", "robot", (1.6, 0.8, 0.9), (0.6, 0.6, 1.8), "cyl"),
    Equipment("TT1", "Table tournante", "positioner", (0.0, 0.9, 0.45), (1.6, 1.6, 0.9), "cyl",
              ("electrical", "pneumatic")),
    Equipment("CV1", "Convoyeur d'entrée", "conveyor", (0.0, -1.8, 0.45), (5.0, 0.8, 0.9)),
    Equipment("HPU", "Centrale hydraulique de bridage", "hydraulic", (-3.4, -0.4, 0.6), (1.0, 0.8, 1.2), "box",
              ("electrical", "hydraulic")),
    Equipment("ARM", "Armoire électrique", "cabinet", (3.5, -0.6, 1.0), (1.2, 0.6, 2.0)),
    Equipment("WLD", "Générateurs de soudage", "power", (3.3, 1.6, 0.5), (0.8, 0.7, 1.0)),
    Equipment("FUM", "Aspiration des fumées", "extraction", (-3.3, 1.8, 1.2), (0.9, 0.9, 2.4), "cyl"),
]
BY_TAG = {e.tag: e for e in EQUIPMENT}
SCANNERS = np.array([[-4.5, -3.5, 1.6], [4.5, 3.5, 1.6]])


def _box_surface(rng, center, size, n):
    c, s = np.asarray(center), np.asarray(size)
    areas = np.array([s[1] * s[2], s[1] * s[2], s[0] * s[2], s[0] * s[2], s[0] * s[1]])  # no bottom face
    face = rng.choice(5, size=n, p=areas / areas.sum())
    u = rng.uniform(-0.5, 0.5, (n, 3)) * s
    axis, sign = np.array([0, 0, 1, 1, 2])[face], np.array([-1, 1, -1, 1, 1])[face]
    u[np.arange(n), axis] = sign * s[axis] / 2
    return c + u


def _cyl_surface(rng, center, size, n):
    c = np.asarray(center)
    r, h = size[0] / 2, size[2]
    side = int(n * (2 * np.pi * r * h) / (2 * np.pi * r * h + np.pi * r * r))
    th = rng.uniform(0, 2 * np.pi, side)
    z = rng.uniform(-h / 2, h / 2, side)
    pts = np.c_[r * np.cos(th), r * np.sin(th), z]
    m = n - side
    rr, th2 = r * np.sqrt(rng.uniform(0, 1, m)), rng.uniform(0, 2 * np.pi, m)
    top = np.c_[rr * np.cos(th2), rr * np.sin(th2), np.full(m, h / 2)]
    return c + np.vstack([pts, top])


def scan_cell(n_points: int = 600_000, noise_mm: float = 4.0, seed: int = 0):
    """Return points (N, 3) in metres, reflectance (N,) in 0..1 and an equipment index (-1 for background)."""
    rng = np.random.default_rng(seed)
    parts, labels = [], []
    n_eq = int(n_points * 0.55)
    areas = []
    for e in EQUIPMENT:
        sx, sy, sz = e.size
        areas.append(np.pi * sx * sz + np.pi * sx * sx / 4 if e.shape == "cyl" else 2 * (sx + sy) * sz + sx * sy)
    areas = np.array(areas)
    for i, e in enumerate(EQUIPMENT):
        k = int(n_eq * areas[i] / areas.sum())
        surf = _cyl_surface if e.shape == "cyl" else _box_surface
        parts.append(surf(rng, e.center, e.size, k))
        labels.append(np.full(k, i))
    n_floor = int(n_points * 0.35)
    parts.append(np.c_[rng.uniform(-5, 5, n_floor), rng.uniform(-3.5, 3.5, n_floor), np.zeros(n_floor)])
    labels.append(np.full(n_floor, -1))
    n_fence = n_points - sum(len(p) for p in parts)
    side = rng.integers(0, 2, n_fence)
    x = np.where(side == 0, rng.uniform(-4.2, 4.2, n_fence), rng.choice([-4.2, 4.2], n_fence))
    y = np.where(side == 0, 2.8, rng.uniform(-0.8, 2.8, n_fence))
    fence = np.c_[x, y, rng.uniform(0, 2.0, n_fence)]
    keep = (np.floor(fence[:, 2] / 0.05) % 2 == 0) | (fence[:, 2] < 0.3)   # wire mesh rows
    parts.append(fence[keep])
    labels.append(np.full(int(keep.sum()), -1))
    pts, lab = np.vstack(parts), np.concatenate(labels)
    # scanner range noise along the line of sight of the nearest scanner, and range-dependent reflectance
    d = np.linalg.norm(pts[:, None, :] - SCANNERS[None], axis=2)
    near = SCANNERS[d.argmin(1)]
    ray = pts - near
    rng_m = np.linalg.norm(ray, axis=1, keepdims=True)
    pts = pts + ray / np.maximum(rng_m, 1e-6) * rng.normal(0, noise_mm / 1000, (len(pts), 1))
    refl = np.clip(0.75 - 0.05 * rng_m[:, 0] + rng.normal(0, 0.05, len(pts)), 0.05, 1.0)
    refl[lab == -1] *= 0.6
    return pts.astype(np.float32), refl.astype(np.float32), lab.astype(np.int16)


def voxel_downsample(pts: np.ndarray, voxel_m: float, *extra: np.ndarray):
    """Keep one point per voxel (the first one met). Returns the reduced arrays."""
    keys = np.floor(pts / voxel_m).astype(np.int64)
    _, idx = np.unique(keys, axis=0, return_index=True)
    idx.sort()
    return (pts[idx], *[x[idx] for x in extra])


def budget_downsample(pts, max_points: int, *extra, start_voxel_m: float = 0.005):
    """Smallest voxel size (x1.25 steps) that brings the cloud under a headset point budget."""
    v = start_voxel_m
    out = (pts, *extra)
    while len(out[0]) > max_points:
        out = voxel_downsample(pts, v, *extra)
        if len(out[0]) <= max_points:
            return out, v
        v *= 1.25
    return out, 0.0


def write_ply(path, pts: np.ndarray, rgb: np.ndarray):
    """Binary little-endian PLY with float32 xyz and uchar rgb (readable by three.js, CloudCompare, Unity)."""
    n = len(pts)
    header = ("ply\nformat binary_little_endian 1.0\n"
              f"element vertex {n}\nproperty float x\nproperty float y\nproperty float z\n"
              "property uchar red\nproperty uchar green\nproperty uchar blue\nend_header\n").encode()
    rec = np.zeros(n, dtype=[("x", "<f4"), ("y", "<f4"), ("z", "<f4"), ("r", "u1"), ("g", "u1"), ("b", "u1")])
    rec["x"], rec["y"], rec["z"] = pts[:, 0], pts[:, 1], pts[:, 2]
    rec["r"], rec["g"], rec["b"] = rgb[:, 0], rgb[:, 1], rgb[:, 2]
    with open(path, "wb") as f:
        f.write(header)
        f.write(rec.tobytes())


def read_ply(path):
    with open(path, "rb") as f:
        data = f.read()
    end = data.index(b"end_header\n") + len(b"end_header\n")
    n = int([l for l in data[:end].decode().splitlines() if l.startswith("element vertex")][0].split()[-1])
    rec = np.frombuffer(data[end:], dtype=[("x", "<f4"), ("y", "<f4"), ("z", "<f4"), ("r", "u1"), ("g", "u1"),
                                            ("b", "u1")], count=n)
    return np.c_[rec["x"], rec["y"], rec["z"]], np.c_[rec["r"], rec["g"], rec["b"]]
