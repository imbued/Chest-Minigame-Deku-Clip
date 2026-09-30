import time
############################################################################## claude wrote this to help check for solutions
"""
Continuous membership queries over discretely-sampled Yes/No grids in the x-z plane.

Interpretation (no assumptions beyond what the samples justify):
  * a Yes sample is a valid point
  * two adjacent Yes samples => the whole segment between them is valid
  * four Yes samples forming a grid cell => the whole rectangle is valid
  * a Yes with no Yes neighbours stays a single (float-exact) point

Every grid file carries two parameters in its FILE NAME:  a movement angle and a number of walking steps,
e.g.   angle_0x4A30_steps_12.csv
Every file in the directory must match the pattern (otherwise loading fails loudly), and no two files may
share the same (angle, steps) pair.

Usage:
    solutions = RegionSet.from_directory("solution_grids")
    solutions.contains(x, z)        # bool, fast (use in the DFS)
    solutions.matches(x, z)         # every region containing the point -> .movement_angle / .walking_steps
"""
import re
from bisect import bisect_left
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

# Named groups "angle" (int, 0x-hex or decimal) and "steps" (int). Matched against the file name WITHOUT ".csv".
DEFAULT_NAME_PATTERN = r"angle_(?P<angle>0x[0-9A-Fa-f]+)_steps_(?P<steps>\d+)"


def load_grid(path, sep: Optional[str] = "\t", corner: Optional[str] = "z \\ x"):
    """Load one file -> (zs, xs, V), axes ascending, V[j, i] True where (zs[j], xs[i]) is 'Yes'.

    sep="\\t" uses pandas' fast C parser. sep=None sniffs the delimiter (much slower).
    """
    df = pd.read_csv(
        path, sep=sep, index_col=0, dtype=str, keep_default_na=False,
        engine="python" if sep is None else "c",
    )
    # Guards: a wrong-delimiter or non-grid csv (e.g. one of the movement csvs) would otherwise parse into
    # garbage (or an empty grid that gets silently skipped) instead of failing loudly.
    if corner is not None and str(df.index.name).replace(" ", "") != corner.replace(" ", ""):
        raise ValueError(f"{path}: top-left header cell is {df.index.name!r}, expected {corner!r} "
                         f"(wrong file or wrong delimiter?)")
    if df.shape[0] == 0 or df.shape[1] == 0:
        raise ValueError(f"{path}: grid has shape {df.shape}")
    zs = df.index.to_numpy(dtype=float)
    xs = df.columns.to_numpy(dtype=float)
    V = np.char.lower(np.char.strip(df.to_numpy(dtype=str))) == "yes"
    zo, xo = np.argsort(zs, kind="stable"), np.argsort(xs, kind="stable")
    return zs[zo], xs[xo], V[np.ix_(zo, xo)]


def _span_many(axis: np.ndarray, q: np.ndarray, atol: float):
    """Vectorized: for each q, the sample indices (i0, i1) bracketing it.
    i0 == i1 when q sits on a sample. ok is False when q is outside the sampled range."""
    n = len(axis)
    hi = np.searchsorted(axis, q, side="left")  # first sample >= q
    hi_c, lo_c = np.minimum(hi, n - 1), np.maximum(hi - 1, 0)
    on_hi = (hi < n) & (axis[hi_c] - q <= atol)
    on_lo = (hi > 0) & (q - axis[lo_c] <= atol) & ~on_hi
    ok = on_hi | on_lo | ((hi > 0) & (hi < n))
    i0 = np.where(on_hi, hi, hi - 1)
    i1 = np.where(on_lo, hi - 1, hi)
    return np.clip(i0, 0, n - 1), np.clip(i1, 0, n - 1), ok


class ZXRegion:
    """A single grid file (plus the two parameters that go with it)."""

    __slots__ = ("zs", "xs", "V", "atol", "_zl", "_xl", "name", "movement_angle", "walking_steps")

    def __init__(self, zs: np.ndarray, xs: np.ndarray, V: np.ndarray, atol: float = 0.0,
                 name: str = "", movement_angle: Optional[int] = None, walking_steps: Optional[int] = None):
        self.zs, self.xs, self.V, self.atol = zs, xs, V, atol
        self._zl, self._xl = zs.tolist(), xs.tolist()  # plain lists: fast bisect in the scalar path
        self.name, self.movement_angle, self.walking_steps = name, movement_angle, walking_steps

    def describe(self) -> str:
        """Human-readable parameters, e.g. 'movement angle 0x4A30, 12 walking steps'."""
        if self.movement_angle is None:
            return self.name
        return f"movement angle {hex(self.movement_angle)}, {self.walking_steps} walking steps"

    def __repr__(self):
        return f"ZXRegion({self.name!r}, {self.describe()})"

    @property
    def bbox(self):
        a = self.atol
        return (self.xs[0] - a, self.xs[-1] + a, self.zs[0] - a, self.zs[-1] + a)

    @staticmethod
    def _span(axis: list, q: float, atol: float):
        n = len(axis)
        hi = bisect_left(axis, q)
        if hi < n and axis[hi] - q <= atol:
            return hi, hi
        if hi > 0 and q - axis[hi - 1] <= atol:
            return hi - 1, hi - 1
        if 0 < hi < n:
            return hi - 1, hi
        return None

    def contains(self, x: float, z: float) -> bool:
        sx = self._span(self._xl, x, self.atol)
        if sx is None:
            return False
        sz = self._span(self._zl, z, self.atol)
        if sz is None:
            return False
        (i0, i1), (j0, j1), V = sx, sz, self.V
        return bool(V[j0, i0] and V[j0, i1] and V[j1, i0] and V[j1, i1])

    def contains_many(self, x: np.ndarray, z: np.ndarray) -> np.ndarray:
        i0, i1, okx = _span_many(self.xs, x, self.atol)
        j0, j1, okz = _span_many(self.zs, z, self.atol)
        V = self.V
        return okx & okz & V[j0, i0] & V[j0, i1] & V[j1, i0] & V[j1, i1]


class RegionSet:
    """Many regions; a point is a solution if it lies in ANY of them."""

    def __init__(self, regions: list, skipped: tuple = ()):
        self.regions = list(regions)
        self.skipped = tuple(skipped)  # names of grid files that had no Yes cells at all
        self.names = [r.name or str(i) for i, r in enumerate(self.regions)]
        bb = np.array([r.bbox for r in self.regions], dtype=float).reshape(-1, 4)
        self._xmin, self._xmax, self._zmin, self._zmax = (np.ascontiguousarray(c) for c in bb.T)
        # bounding box of ALL regions (plain floats, for an O(1) first-level reach test)
        if self.regions:
            self._gxmin, self._gxmax = float(self._xmin.min()), float(self._xmax.max())
            self._gzmin, self._gzmax = float(self._zmin.min()), float(self._zmax.max())
        else:  # empty set: everything is infinitely far away
            self._gxmin = self._gzmin = float("inf")
            self._gxmax = self._gzmax = float("-inf")

    @classmethod
    def from_directory(cls, directory, pattern: str = "*.csv", sep: Optional[str] = "\t",
                       atol: float = 0.0, corner: Optional[str] = "z \\ x",
                       name_pattern: Optional[str] = DEFAULT_NAME_PATTERN) -> "RegionSet":
        """Load every grid csv in `directory` (point this at a directory containing ONLY grid files).

        name_pattern: regex with named groups `angle` and `steps`, fullmatched against each file's stem.
        Pass None to skip parameter parsing (regions then have movement_angle = walking_steps = None).
        """
        paths = sorted(Path(directory).glob(pattern))
        if not paths:
            raise FileNotFoundError(f"no files matching {pattern!r} in {str(directory)!r}")

        # Parse + validate ALL file names before reading any grid (fail fast, fail loudly).
        params = {}
        if name_pattern is not None:
            rx = re.compile(name_pattern)
            bad, seen = [], {}
            for path in paths:
                m = rx.fullmatch(path.stem)
                if m is None:
                    bad.append(path.name)
                    continue
                key = (int(m.group("angle"), 0), int(m.group("steps")))
                if key in seen:
                    raise ValueError(f"{path.name} and {seen[key]} have the same parameters "
                                     f"(angle {hex(key[0])}, steps {key[1]})")
                seen[key] = path.name
                params[path] = key
            if bad:
                raise ValueError(f"{len(bad)} file(s) in {str(directory)!r} don't match the name pattern "
                                 f"{name_pattern!r}, e.g. {bad[:5]}")

        regions, skipped = [], []
        for path in paths:
            zs, xs, V = load_grid(path, sep, corner)
            if not V.any():  # region with no Yes can never match; don't carry it
                skipped.append(path.stem)
                continue
            angle, steps = params.get(path, (None, None))
            regions.append(ZXRegion(zs, xs, V, atol, name=path.stem, movement_angle=angle, walking_steps=steps))
        if not regions:
            raise ValueError(f"all {len(paths)} grids in {str(directory)!r} contain no Yes cells")
        return cls(regions, skipped)

    def __len__(self):
        return len(self.regions)

    def _candidates(self, x, z):
        return (self._xmin <= x) & (x <= self._xmax) & (self._zmin <= z) & (z <= self._zmax)

    def contains(self, x: float, z: float) -> bool:
        """Scalar hot path (use this inside the DFS). Stops at the first matching region."""
        for k in np.flatnonzero(self._candidates(x, z)):
            if self.regions[k].contains(x, z):
                return True
        return False

    def matches(self, x: float, z: float) -> list:
        """EVERY region containing the point (a point can lie in several, with different parameters).
        Slower than contains(): call it only once you already know the point is a solution."""
        return [self.regions[k] for k in np.flatnonzero(self._candidates(x, z))
                if self.regions[k].contains(x, z)]

    def which(self, x: float, z: float) -> list:
        """Names of every region containing the point (handy for debugging)."""
        return [r.name for r in self.matches(x, z)]

    def min_distance_to_any_bbox(self, x: float, z: float) -> float:
        """Euclidean distance from (x, z) to the nearest region bounding box (0 if inside one).
        This is a LOWER bound on the distance to the nearest actual solution point."""
        dx = np.maximum(np.maximum(self._xmin - x, x - self._xmax), 0.0)
        dz = np.maximum(np.maximum(self._zmin - z, z - self._zmax), 0.0)
        if dx.size == 0:
            return float("inf")
        return float(np.sqrt((dx * dx + dz * dz).min()))

    def within_reach(self, x: float, z: float, reach: float) -> bool:
        """False only if NO region can possibly be within `reach` of (x, z) (safe to prune on).
        Two levels: an O(1) test against the box around all regions, then a numpy scan of
        per-region boxes only for points that pass it."""
        r2 = reach * reach
        dx = max(self._gxmin - x, x - self._gxmax, 0.0)
        dz = max(self._gzmin - z, z - self._gzmax, 0.0)
        if dx * dx + dz * dz > r2:
            return False
        dx = np.maximum(np.maximum(self._xmin - x, x - self._xmax), 0.0)
        dz = np.maximum(np.maximum(self._zmin - z, z - self._zmax), 0.0)
        return bool(((dx * dx + dz * dz) <= r2).any())

    def contains_many(self, x, z) -> np.ndarray:
        x, z = np.broadcast_arrays(np.asarray(x, float), np.asarray(z, float))
        out = np.zeros(x.shape, dtype=bool)
        for r in self.regions:
            xmin, xmax, zmin, zmax = r.bbox
            m = (~out) & (x >= xmin) & (x <= xmax) & (z >= zmin) & (z <= zmax)
            if m.any():
                out[m] = r.contains_many(x[m], z[m])
        return out

##############################################################################
"""
In order to get accurate trig computations that reflect those in the game, we need to use the lookup table below
because the game just does an approximation because it was efficient. Here are the relevant files from decomp
which I modified below for python:
https://github.com/zeldaret/mm/blob/main/src/libultra/gu/sins.c
https://github.com/zeldaret/mm/blob/main/src/libultra/gu/coss.c
https://github.com/zeldaret/mm/blob/56fa21dd0031a17cfc9e355f609542617598a265/src/code/z_lib.c#L37
"""

SINTABLE = (
    0x0000, 0x0032, 0x0064, 0x0096, 0x00C9, 0x00FB, 0x012D, 0x0160, 0x0192, 0x01C4, 0x01F7, 0x0229, 0x025B, 0x028E,
    0x02C0, 0x02F2, 0x0324, 0x0357, 0x0389, 0x03BB, 0x03EE, 0x0420, 0x0452, 0x0484, 0x04B7, 0x04E9, 0x051B, 0x054E,
    0x0580, 0x05B2, 0x05E4, 0x0617, 0x0649, 0x067B, 0x06AD, 0x06E0, 0x0712, 0x0744, 0x0776, 0x07A9, 0x07DB, 0x080D,
    0x083F, 0x0871, 0x08A4, 0x08D6, 0x0908, 0x093A, 0x096C, 0x099F, 0x09D1, 0x0A03, 0x0A35, 0x0A67, 0x0A99, 0x0ACB,
    0x0AFE, 0x0B30, 0x0B62, 0x0B94, 0x0BC6, 0x0BF8, 0x0C2A, 0x0C5C, 0x0C8E, 0x0CC0, 0x0CF2, 0x0D25, 0x0D57, 0x0D89,
    0x0DBB, 0x0DED, 0x0E1F, 0x0E51, 0x0E83, 0x0EB5, 0x0EE7, 0x0F19, 0x0F4B, 0x0F7C, 0x0FAE, 0x0FE0, 0x1012, 0x1044,
    0x1076, 0x10A8, 0x10DA, 0x110C, 0x113E, 0x116F, 0x11A1, 0x11D3, 0x1205, 0x1237, 0x1269, 0x129A, 0x12CC, 0x12FE,
    0x1330, 0x1361, 0x1393, 0x13C5, 0x13F6, 0x1428, 0x145A, 0x148C, 0x14BD, 0x14EF, 0x1520, 0x1552, 0x1584, 0x15B5,
    0x15E7, 0x1618, 0x164A, 0x167B, 0x16AD, 0x16DF, 0x1710, 0x1741, 0x1773, 0x17A4, 0x17D6, 0x1807, 0x1839, 0x186A,
    0x189B, 0x18CD, 0x18FE, 0x1930, 0x1961, 0x1992, 0x19C3, 0x19F5, 0x1A26, 0x1A57, 0x1A88, 0x1ABA, 0x1AEB, 0x1B1C,
    0x1B4D, 0x1B7E, 0x1BAF, 0x1BE1, 0x1C12, 0x1C43, 0x1C74, 0x1CA5, 0x1CD6, 0x1D07, 0x1D38, 0x1D69, 0x1D9A, 0x1DCB,
    0x1DFC, 0x1E2D, 0x1E5D, 0x1E8E, 0x1EBF, 0x1EF0, 0x1F21, 0x1F52, 0x1F82, 0x1FB3, 0x1FE4, 0x2015, 0x2045, 0x2076,
    0x20A7, 0x20D7, 0x2108, 0x2139, 0x2169, 0x219A, 0x21CA, 0x21FB, 0x222B, 0x225C, 0x228C, 0x22BD, 0x22ED, 0x231D,
    0x234E, 0x237E, 0x23AE, 0x23DF, 0x240F, 0x243F, 0x2470, 0x24A0, 0x24D0, 0x2500, 0x2530, 0x2560, 0x2591, 0x25C1,
    0x25F1, 0x2621, 0x2651, 0x2681, 0x26B1, 0x26E1, 0x2711, 0x2740, 0x2770, 0x27A0, 0x27D0, 0x2800, 0x2830, 0x285F,
    0x288F, 0x28BF, 0x28EE, 0x291E, 0x294E, 0x297D, 0x29AD, 0x29DD, 0x2A0C, 0x2A3C, 0x2A6B, 0x2A9B, 0x2ACA, 0x2AF9,
    0x2B29, 0x2B58, 0x2B87, 0x2BB7, 0x2BE6, 0x2C15, 0x2C44, 0x2C74, 0x2CA3, 0x2CD2, 0x2D01, 0x2D30, 0x2D5F, 0x2D8E,
    0x2DBD, 0x2DEC, 0x2E1B, 0x2E4A, 0x2E79, 0x2EA8, 0x2ED7, 0x2F06, 0x2F34, 0x2F63, 0x2F92, 0x2FC0, 0x2FEF, 0x301E,
    0x304C, 0x307B, 0x30A9, 0x30D8, 0x3107, 0x3135, 0x3163, 0x3192, 0x31C0, 0x31EF, 0x321D, 0x324B, 0x3279, 0x32A8,
    0x32D6, 0x3304, 0x3332, 0x3360, 0x338E, 0x33BC, 0x33EA, 0x3418, 0x3446, 0x3474, 0x34A2, 0x34D0, 0x34FE, 0x352B,
    0x3559, 0x3587, 0x35B5, 0x35E2, 0x3610, 0x363D, 0x366B, 0x3698, 0x36C6, 0x36F3, 0x3721, 0x374E, 0x377C, 0x37A9,
    0x37D6, 0x3803, 0x3831, 0x385E, 0x388B, 0x38B8, 0x38E5, 0x3912, 0x393F, 0x396C, 0x3999, 0x39C6, 0x39F3, 0x3A20,
    0x3A4D, 0x3A79, 0x3AA6, 0x3AD3, 0x3B00, 0x3B2C, 0x3B59, 0x3B85, 0x3BB2, 0x3BDE, 0x3C0B, 0x3C37, 0x3C64, 0x3C90,
    0x3CBC, 0x3CE9, 0x3D15, 0x3D41, 0x3D6D, 0x3D99, 0x3DC5, 0x3DF1, 0x3E1D, 0x3E49, 0x3E75, 0x3EA1, 0x3ECD, 0x3EF9,
    0x3F25, 0x3F50, 0x3F7C, 0x3FA8, 0x3FD3, 0x3FFF, 0x402B, 0x4056, 0x4082, 0x40AD, 0x40D8, 0x4104, 0x412F, 0x415A,
    0x4186, 0x41B1, 0x41DC, 0x4207, 0x4232, 0x425D, 0x4288, 0x42B3, 0x42DE, 0x4309, 0x4334, 0x435F, 0x4389, 0x43B4,
    0x43DF, 0x4409, 0x4434, 0x445F, 0x4489, 0x44B4, 0x44DE, 0x4508, 0x4533, 0x455D, 0x4587, 0x45B1, 0x45DC, 0x4606,
    0x4630, 0x465A, 0x4684, 0x46AE, 0x46D8, 0x4702, 0x472C, 0x4755, 0x477F, 0x47A9, 0x47D2, 0x47FC, 0x4826, 0x484F,
    0x4879, 0x48A2, 0x48CC, 0x48F5, 0x491E, 0x4948, 0x4971, 0x499A, 0x49C3, 0x49EC, 0x4A15, 0x4A3E, 0x4A67, 0x4A90,
    0x4AB9, 0x4AE2, 0x4B0B, 0x4B33, 0x4B5C, 0x4B85, 0x4BAD, 0x4BD6, 0x4BFE, 0x4C27, 0x4C4F, 0x4C78, 0x4CA0, 0x4CC8,
    0x4CF0, 0x4D19, 0x4D41, 0x4D69, 0x4D91, 0x4DB9, 0x4DE1, 0x4E09, 0x4E31, 0x4E58, 0x4E80, 0x4EA8, 0x4ED0, 0x4EF7,
    0x4F1F, 0x4F46, 0x4F6E, 0x4F95, 0x4FBD, 0x4FE4, 0x500B, 0x5032, 0x505A, 0x5081, 0x50A8, 0x50CF, 0x50F6, 0x511D,
    0x5144, 0x516B, 0x5191, 0x51B8, 0x51DF, 0x5205, 0x522C, 0x5253, 0x5279, 0x52A0, 0x52C6, 0x52EC, 0x5313, 0x5339,
    0x535F, 0x5385, 0x53AB, 0x53D1, 0x53F7, 0x541D, 0x5443, 0x5469, 0x548F, 0x54B5, 0x54DA, 0x5500, 0x5525, 0x554B,
    0x5571, 0x5596, 0x55BB, 0x55E1, 0x5606, 0x562B, 0x5650, 0x5675, 0x569B, 0x56C0, 0x56E5, 0x5709, 0x572E, 0x5753,
    0x5778, 0x579D, 0x57C1, 0x57E6, 0x580A, 0x582F, 0x5853, 0x5878, 0x589C, 0x58C0, 0x58E5, 0x5909, 0x592D, 0x5951,
    0x5975, 0x5999, 0x59BD, 0x59E1, 0x5A04, 0x5A28, 0x5A4C, 0x5A6F, 0x5A93, 0x5AB7, 0x5ADA, 0x5AFD, 0x5B21, 0x5B44,
    0x5B67, 0x5B8B, 0x5BAE, 0x5BD1, 0x5BF4, 0x5C17, 0x5C3A, 0x5C5D, 0x5C7F, 0x5CA2, 0x5CC5, 0x5CE7, 0x5D0A, 0x5D2D,
    0x5D4F, 0x5D71, 0x5D94, 0x5DB6, 0x5DD8, 0x5DFA, 0x5E1D, 0x5E3F, 0x5E61, 0x5E83, 0x5EA5, 0x5EC6, 0x5EE8, 0x5F0A,
    0x5F2C, 0x5F4D, 0x5F6F, 0x5F90, 0x5FB2, 0x5FD3, 0x5FF4, 0x6016, 0x6037, 0x6058, 0x6079, 0x609A, 0x60BB, 0x60DC,
    0x60FD, 0x611E, 0x613E, 0x615F, 0x6180, 0x61A0, 0x61C1, 0x61E1, 0x6202, 0x6222, 0x6242, 0x6263, 0x6283, 0x62A3,
    0x62C3, 0x62E3, 0x6303, 0x6323, 0x6342, 0x6362, 0x6382, 0x63A1, 0x63C1, 0x63E0, 0x6400, 0x641F, 0x643F, 0x645E,
    0x647D, 0x649C, 0x64BB, 0x64DA, 0x64F9, 0x6518, 0x6537, 0x6556, 0x6574, 0x6593, 0x65B2, 0x65D0, 0x65EF, 0x660D,
    0x662B, 0x664A, 0x6668, 0x6686, 0x66A4, 0x66C2, 0x66E0, 0x66FE, 0x671C, 0x673A, 0x6757, 0x6775, 0x6792, 0x67B0,
    0x67CD, 0x67EB, 0x6808, 0x6825, 0x6843, 0x6860, 0x687D, 0x689A, 0x68B7, 0x68D4, 0x68F1, 0x690D, 0x692A, 0x6947,
    0x6963, 0x6980, 0x699C, 0x69B9, 0x69D5, 0x69F1, 0x6A0E, 0x6A2A, 0x6A46, 0x6A62, 0x6A7E, 0x6A9A, 0x6AB5, 0x6AD1,
    0x6AED, 0x6B08, 0x6B24, 0x6B40, 0x6B5B, 0x6B76, 0x6B92, 0x6BAD, 0x6BC8, 0x6BE3, 0x6BFE, 0x6C19, 0x6C34, 0x6C4F,
    0x6C6A, 0x6C84, 0x6C9F, 0x6CBA, 0x6CD4, 0x6CEF, 0x6D09, 0x6D23, 0x6D3E, 0x6D58, 0x6D72, 0x6D8C, 0x6DA6, 0x6DC0,
    0x6DDA, 0x6DF3, 0x6E0D, 0x6E27, 0x6E40, 0x6E5A, 0x6E73, 0x6E8D, 0x6EA6, 0x6EBF, 0x6ED9, 0x6EF2, 0x6F0B, 0x6F24,
    0x6F3D, 0x6F55, 0x6F6E, 0x6F87, 0x6FA0, 0x6FB8, 0x6FD1, 0x6FE9, 0x7002, 0x701A, 0x7032, 0x704A, 0x7062, 0x707A,
    0x7092, 0x70AA, 0x70C2, 0x70DA, 0x70F2, 0x7109, 0x7121, 0x7138, 0x7150, 0x7167, 0x717E, 0x7196, 0x71AD, 0x71C4,
    0x71DB, 0x71F2, 0x7209, 0x7220, 0x7236, 0x724D, 0x7264, 0x727A, 0x7291, 0x72A7, 0x72BD, 0x72D4, 0x72EA, 0x7300,
    0x7316, 0x732C, 0x7342, 0x7358, 0x736E, 0x7383, 0x7399, 0x73AE, 0x73C4, 0x73D9, 0x73EF, 0x7404, 0x7419, 0x742E,
    0x7443, 0x7458, 0x746D, 0x7482, 0x7497, 0x74AC, 0x74C0, 0x74D5, 0x74EA, 0x74FE, 0x7512, 0x7527, 0x753B, 0x754F,
    0x7563, 0x7577, 0x758B, 0x759F, 0x75B3, 0x75C7, 0x75DA, 0x75EE, 0x7601, 0x7615, 0x7628, 0x763B, 0x764F, 0x7662,
    0x7675, 0x7688, 0x769B, 0x76AE, 0x76C1, 0x76D3, 0x76E6, 0x76F9, 0x770B, 0x771E, 0x7730, 0x7742, 0x7754, 0x7767,
    0x7779, 0x778B, 0x779D, 0x77AF, 0x77C0, 0x77D2, 0x77E4, 0x77F5, 0x7807, 0x7818, 0x782A, 0x783B, 0x784C, 0x785D,
    0x786E, 0x787F, 0x7890, 0x78A1, 0x78B2, 0x78C3, 0x78D3, 0x78E4, 0x78F4, 0x7905, 0x7915, 0x7925, 0x7936, 0x7946,
    0x7956, 0x7966, 0x7976, 0x7985, 0x7995, 0x79A5, 0x79B5, 0x79C4, 0x79D4, 0x79E3, 0x79F2, 0x7A02, 0x7A11, 0x7A20,
    0x7A2F, 0x7A3E, 0x7A4D, 0x7A5B, 0x7A6A, 0x7A79, 0x7A87, 0x7A96, 0x7AA4, 0x7AB3, 0x7AC1, 0x7ACF, 0x7ADD, 0x7AEB,
    0x7AF9, 0x7B07, 0x7B15, 0x7B23, 0x7B31, 0x7B3E, 0x7B4C, 0x7B59, 0x7B67, 0x7B74, 0x7B81, 0x7B8E, 0x7B9B, 0x7BA8,
    0x7BB5, 0x7BC2, 0x7BCF, 0x7BDC, 0x7BE8, 0x7BF5, 0x7C02, 0x7C0E, 0x7C1A, 0x7C27, 0x7C33, 0x7C3F, 0x7C4B, 0x7C57,
    0x7C63, 0x7C6F, 0x7C7A, 0x7C86, 0x7C92, 0x7C9D, 0x7CA9, 0x7CB4, 0x7CBF, 0x7CCB, 0x7CD6, 0x7CE1, 0x7CEC, 0x7CF7,
    0x7D02, 0x7D0C, 0x7D17, 0x7D22, 0x7D2C, 0x7D37, 0x7D41, 0x7D4B, 0x7D56, 0x7D60, 0x7D6A, 0x7D74, 0x7D7E, 0x7D88,
    0x7D91, 0x7D9B, 0x7DA5, 0x7DAE, 0x7DB8, 0x7DC1, 0x7DCB, 0x7DD4, 0x7DDD, 0x7DE6, 0x7DEF, 0x7DF8, 0x7E01, 0x7E0A,
    0x7E13, 0x7E1B, 0x7E24, 0x7E2C, 0x7E35, 0x7E3D, 0x7E45, 0x7E4D, 0x7E56, 0x7E5E, 0x7E66, 0x7E6D, 0x7E75, 0x7E7D,
    0x7E85, 0x7E8C, 0x7E94, 0x7E9B, 0x7EA3, 0x7EAA, 0x7EB1, 0x7EB8, 0x7EBF, 0x7EC6, 0x7ECD, 0x7ED4, 0x7EDB, 0x7EE1,
    0x7EE8, 0x7EEE, 0x7EF5, 0x7EFB, 0x7F01, 0x7F08, 0x7F0E, 0x7F14, 0x7F1A, 0x7F20, 0x7F25, 0x7F2B, 0x7F31, 0x7F36,
    0x7F3C, 0x7F41, 0x7F47, 0x7F4C, 0x7F51, 0x7F56, 0x7F5B, 0x7F60, 0x7F65, 0x7F6A, 0x7F6F, 0x7F74, 0x7F78, 0x7F7D,
    0x7F81, 0x7F85, 0x7F8A, 0x7F8E, 0x7F92, 0x7F96, 0x7F9A, 0x7F9E, 0x7FA2, 0x7FA6, 0x7FA9, 0x7FAD, 0x7FB0, 0x7FB4,
    0x7FB7, 0x7FBA, 0x7FBE, 0x7FC1, 0x7FC4, 0x7FC7, 0x7FCA, 0x7FCC, 0x7FCF, 0x7FD2, 0x7FD4, 0x7FD7, 0x7FD9, 0x7FDC,
    0x7FDE, 0x7FE0, 0x7FE2, 0x7FE4, 0x7FE6, 0x7FE8, 0x7FEA, 0x7FEC, 0x7FED, 0x7FEF, 0x7FF1, 0x7FF2, 0x7FF3, 0x7FF5,
    0x7FF6, 0x7FF7, 0x7FF8, 0x7FF9, 0x7FFA, 0x7FFB, 0x7FFB, 0x7FFC, 0x7FFD, 0x7FFD, 0x7FFE, 0x7FFE, 0x7FFE, 0x7FFE,
    0x7FFE, 0x7FFF,
)

def sins(x: int) -> int:
    x >>= 4

    if x & 0x400:
        val = SINTABLE[0x3FF - (x & 0x3FF)]
    else:
        val = SINTABLE[x & 0x3FF]

    if x & 0x800:
        return -val

    return val

def coss(x: int) -> int:
    return sins(x + 0x4000)

def Math_SinS(x: int) -> float:
    return sins(x) / 32767.0

def Math_CosS(x: int) -> float:
    return coss(x) / 32767.0

"""
In order to compute the x and z velocities, we need to know:
    1) The linear velocity during every frame of the movement
    2) The movement angle during every frame of the movement
Then we can do:
    x_velocity = linear_velocity * Math_SinS(movement_angle)
    z_velocity = linear_velocity * Math_CosS(movement_angle)

I will record the linear velocities and movement angles for movements at camera angle 0x0000 and then I can get the camera angle associated
with whatever facing angle we have (using a lookup table that maps "facing angle" to "camera angle while holding target on flat ground while 
not too close to walls") and then I can add on whatever the movement angle at 0x0000 was to the current camera angle to get the current
movement angle.
"""

VELOCITY_SCALE = 1.5 # if moving with a velocity of 1 for 1 frame, you move 1.5 position units
TOTAL_ANGLES = 0x10000

def _to_int(v):
    """CSV cells may be hex strings like '0x0010' or plain numbers."""
    return int(v, 16) if isinstance(v, str) else int(v)


def _check_all_bins(keys, filename):
    expected = set(range(0, TOTAL_ANGLES, 0x10))
    got = set(keys)
    if got != expected:
        missing = sorted(expected - got)
        unexpected = sorted(got - expected)
        raise ValueError(
            f"{filename}: expected all {len(expected)} angle bins. "
            f"Missing {len(missing)} (first few: {[hex(m) for m in missing[:5]]}), "
            f"unexpected {len(unexpected)} (first few: {[hex(u) for u in unexpected[:5]]})"
        )


def _read_sorted_by_frame(filename):
    """
    Read a csv so that, within every "Initial Angle" group, rows are in Frame order.
    (groupby keeps FILE order inside each group, so this must be enforced explicitly.)
    Also verifies that no (Initial Angle, Frame) pair is repeated and that every angle bin
    recorded exactly the same frames -- differing frame sets usually mean a run was cut short,
    which would make "the last row" NOT the final frame of the movement.
    If your data legitimately has different frame counts per bin, relax the last check.
    """
    data = pd.read_csv(filename)
    if "Frame" not in data.columns:
        raise ValueError(f"{filename}: no 'Frame' column, so row order can't be verified")
    data = data.sort_values("Frame", kind="stable")
    if data.duplicated(["Initial Angle", "Frame"]).any():
        raise ValueError(f"{filename}: repeated (Initial Angle, Frame) rows")
    frame_sets = data.groupby("Initial Angle", sort=False)["Frame"].agg(tuple)
    if frame_sets.nunique() != 1:
        raise ValueError(f"{filename}: angle bins don't all record the same frames (runs cut short?)")
    return data


def preprocess_csv(filename, fp32=True):
    #### this is for everything other than guano shield scoots! for guano, I'll guanowalk for like 30 frames and store a list of all movement angles I get for each angle

    data = _read_sorted_by_frame(filename)

    cache = {}

    if not fp32:

        for initial_angle_str, rows in data.groupby("Initial Angle", sort=False):
            initial_angle = _to_int(initial_angle_str)
            last_row = rows.iloc[-1]  # safe now: rows are in Frame order, so this is the final frame
            cache[initial_angle] = {
                "X Position Change" : rows["X Velocity"].sum() * VELOCITY_SCALE, # how much x position changes from doing this movement starting at this angle
                "Z Position Change" : rows["Z Velocity"].sum() * VELOCITY_SCALE,
                "Initial Angle" : initial_angle,
                "Final Angle" : _to_int(last_row["Angle"]),
                "Final Camera Angle" : _to_int(last_row["Camera Angle"]),
            }
    else:
        # TODO, in principle i could make this a bit closer to reality by not adding on the total position change but instead computing the change each frame to reduce floating point error, but i won't worry about this for now
        for initial_angle_str, rows in data.groupby("Initial Angle", sort=False):
            initial_angle = _to_int(initial_angle_str)
            last_row = rows.iloc[-1]  # safe now: rows are in Frame order, so this is the final frame

            x_position_change = np.float32(0.0)
            z_position_change = np.float32(0.0)

            for x_velocity, z_velocity in zip(rows["X Velocity"], rows["Z Velocity"]):
                x_position_change = np.float32(x_position_change + np.float32(np.float32(x_velocity) * np.float32(VELOCITY_SCALE)))
                z_position_change = np.float32(z_position_change + np.float32(np.float32(z_velocity) * np.float32(VELOCITY_SCALE)))

            cache[initial_angle] = {
                "X Position Change" : x_position_change,
                "Z Position Change" : z_position_change,
                "Initial Angle" : initial_angle,
                "Final Angle" : _to_int(last_row["Angle"]),
                "Final Camera Angle" : _to_int(last_row["Camera Angle"]),
            }

    _check_all_bins(cache.keys(), filename)
    return cache


def preprocess_guano_movement_angles_csv(filename="guanowalk_left.csv"):
    """
    Update: It is important that I test all 65536 angles for this one with current implementation, but might use these notes to not need it:
        https://pastebin.com/ZtapPuRG

        important info from the pastebin:
            - if camera angle < angle then a straight right guanowalk will not walk forward initially, but straight left will
            - if camera angle > angle then a straight left guanowalk will not walk forward initially, but straight right will
            - if camera angle = angle, then straight right and straight left guanowalks will both initially walk forward
        
        also need to be way more careful about guano chain being reset. if he doesnt walk forward, we need to reset chain length
    """
    if filename not in ["guanowalk_left.csv", "guanowalk_right.csv"]:
        raise ValueError(f"{filename=}")

    data = _read_sorted_by_frame(filename)

    cache = {}

    for initial_angle_str, rows in data.groupby("Initial Angle", sort=False):
        # it is important that we start on frame 8 because previous movement angles in the data aren't updated yet
        late = rows.loc[rows["Frame"] >= 8, "Movement Angle"]
        cache[_to_int(initial_angle_str)] = [_to_int(a) for a in late] # list of all movement angles once they start updating 

    _check_all_bins(cache.keys(), filename)
    return cache

def preprocess_targeted_camera_angles(filename="hold_sidehop_left.csv"):

    if filename not in ["hold_sidehop_left.csv", "hold_sidehop_right.csv"]:
        raise ValueError(f"{filename=}")

    data = _read_sorted_by_frame(filename)

    cache = {}

    for initial_angle_str, rows in data.groupby("Initial Angle", sort=False):
        if len(rows) <= 5:
            raise ValueError(f"{filename}: angle {initial_angle_str} has only {len(rows)} rows, need at least 6")
        row = rows.iloc[5]
        if row["Frame"] != 6:
            raise ValueError(f"wrong data!!!")
        cache[_to_int(initial_angle_str)] = _to_int(row["Camera Angle"])

    _check_all_bins(cache.keys(), filename)
    return cache


#############################################################################################################

def get_bin(angle):
    """
    rounds angle such that it's last hex digit is 0 (i.e. rounds down to nearest multiple of 0x10) because there are only 4096 angle bins
    and the caches only store values for each bin, so this is just a helper function to get the bin for when we use the cache
    """
    return 0x10 * (angle // 0x10)

def hold_sidehop(x_pos, z_pos, angle, left=True, fp32=True):
    """
    Just a basic hold sidehop for now. Might do a move general sidehop function in the future where you can hold into guano walk or release early
    would need to account for ending guano early with holding target or without and shield or no shield and if doing this then might as well allow
    releasing control stick and/or early during sidehop, etc.

    Inefficient implementation of computing velocities might look like:
    ```
     sidehop_linear_velocities = [8.5, 8.4, 8.299999, 8.199999, 8.099998, 7.999999, 6.999999]
        movement_angle_offset = 0x4000 if left else -0x4000
        movement_angle = (camera_angle + movement_angle_offset) % 0x10000
        sidehop_movement_angles = [movement_angle for _ in sidehop_linear_velocities] 
    
        # instead of computing the x and z velocities at every frame, we just need the final 
        cumulative_x_velocity = 0
        cumulative_z_velocity = 0
        for v, a in zip(sidehop_linear_velocities, sidehop_movement_angles):
            cumulative_x_velocity += v * Math_SinS(a)
            cumulative_z_velocity += v * Math_CosS(a)
        return (cumulative_x_velocity, cumulative_z_velocity)
    ```
    but I precompute sums to make it a little faster
    """
    # movement_angle_offset = 0x4000 if left else -0x4000
    # movement_angle = (camera_angle + movement_angle_offset) % TOTAL_ANGLES
    # cumulative_linear_velocity = 56.499994 # sum([8.5, 8.4, 8.299999, 8.199999, 8.099998, 7.999999, 6.999999])
    # cumulative_x_velocity = cumulative_linear_velocity * Math_SinS(movement_angle)
    # cumulative_z_velocity = cumulative_linear_velocity * Math_CosS(movement_angle)

    # updated_x_pos = x_pos + VELOCITY_SCALE * cumulative_x_velocity 
    # updated_z_pos = z_pos + VELOCITY_SCALE * cumulative_z_velocity
    # return updated_x_pos, updated_z_pos, angle

    if left:
        data = HoldLeftSidehopCache[get_bin(angle)]
    else:
        data = HoldRightSidehopCache[get_bin(angle)]
    if not fp32:
        updated_x_pos = x_pos + data["X Position Change"]
        updated_z_pos = z_pos + data["Z Position Change"]
    else:
        updated_x_pos = np.float32(x_pos) + np.float32(data["X Position Change"])
        updated_z_pos = np.float32(z_pos) + np.float32(data["Z Position Change"])
    updated_angle = data["Final Angle"]
    return updated_x_pos, updated_z_pos, updated_angle

def guano_shield_scoot(x_pos, z_pos, angle, guano_chain_length=0, left=True, fp32=True):
    """
    linear velocity is 2 for 2 frames

    down-left is the same as cardinal turn down + guano shield scoot right
    down-right is the same as cardinal turn down + guano shield scoot left

    Because of symmetry, I am ignoring those cases to reduce the number of permutations

    - if camera angle < angle then a straight right guanowalk will not walk forward initially, but straight left will
    - if camera angle > angle then a straight left guanowalk will not walk forward initially, but straight right will
    - if camera angle = angle, then straight right and straight left guanowalks will both initially walk forward

    well, i could just do a hacky fix and say if the absolute difference between movement angle and camera angle is < 0x07
    (really i think checking for equality suffices), then we reset guano chain length
    """
    if not fp32:
        cumulative_linear_velocity = 4 # sum([2, 2])
        if left:
            movement_angle_list = FacingAngleToLeftGuanoMovementAngles[get_bin(angle)]
        else:
            movement_angle_list = FacingAngleToRightGuanoMovementAngles[get_bin(angle)]
        if guano_chain_length >= len(movement_angle_list):
            raise NotImplementedError(f"I have only implemented the first {len(movement_angle_list)} movement values, got {guano_chain_length=}")
        movement_angle = movement_angle_list[guano_chain_length]

        cumulative_x_velocity = cumulative_linear_velocity * Math_SinS(movement_angle)
        cumulative_z_velocity = cumulative_linear_velocity * Math_CosS(movement_angle)

        updated_x_pos = x_pos + VELOCITY_SCALE * cumulative_x_velocity 
        updated_z_pos = z_pos + VELOCITY_SCALE * cumulative_z_velocity
    else:
        if left:
            movement_angle_list = FacingAngleToLeftGuanoMovementAngles[get_bin(angle)]
        else:
            movement_angle_list = FacingAngleToRightGuanoMovementAngles[get_bin(angle)]
        if guano_chain_length >= len(movement_angle_list):
            raise NotImplementedError(f"I have only implemented the first {len(movement_angle_list)} movement values, got {guano_chain_length=}")
        movement_angle = movement_angle_list[guano_chain_length]

        v_x, v_z = get_xz_vel_fp32(linear_velocity=2, movement_angle=movement_angle)
        updated_x_pos = np.float32( np.float32(x_pos) + np.float32( np.float32(v_x) * np.float32(VELOCITY_SCALE) ) ) + np.float32( np.float32(v_x) * np.float32(VELOCITY_SCALE) )
        updated_z_pos = np.float32( np.float32(z_pos) + np.float32( np.float32(v_z) * np.float32(VELOCITY_SCALE) ) ) + np.float32( np.float32(v_z) * np.float32(VELOCITY_SCALE) )
    guano_chain_must_be_reset = False
    camera_angle = FacingAngleToTargetedCameraAngle[get_bin(angle)]
    if abs(movement_angle - camera_angle) < 0x07: # really I could check for equality I think, but this is just playing it safe
        guano_chain_must_be_reset = True
    return updated_x_pos, updated_z_pos, angle, guano_chain_must_be_reset

def shield_scoot_forward(x_pos, z_pos, angle, fp32=True): # TODO
    # Note: it is assumed that we're holding target when doing the shield scoot!! Untargeted too annoying to add for now, but I could
    if not fp32:
        cumulative_linear_velocity = 4 # sum([2, 2])
        camera_angle = FacingAngleToTargetedCameraAngle[get_bin(angle)]
        movement_angle = camera_angle
        cumulative_x_velocity = cumulative_linear_velocity * Math_SinS(movement_angle)
        cumulative_z_velocity = cumulative_linear_velocity * Math_CosS(movement_angle)

        updated_x_pos = x_pos + VELOCITY_SCALE * cumulative_x_velocity 
        updated_z_pos = z_pos + VELOCITY_SCALE * cumulative_z_velocity
    else:
        camera_angle = FacingAngleToTargetedCameraAngle[get_bin(angle)]
        movement_angle = camera_angle
        v_x, v_z = get_xz_vel_fp32(linear_velocity=2, movement_angle=movement_angle)
        updated_x_pos = np.float32( np.float32(x_pos) + np.float32( np.float32(v_x) * np.float32(VELOCITY_SCALE) ) ) + np.float32( np.float32(v_x) * np.float32(VELOCITY_SCALE) )
        updated_z_pos = np.float32( np.float32(z_pos) + np.float32( np.float32(v_z) * np.float32(VELOCITY_SCALE) ) ) + np.float32( np.float32(v_z) * np.float32(VELOCITY_SCALE) )
    return updated_x_pos, updated_z_pos, angle

def hold_backflip(x_pos, z_pos, angle, fp32=True):
    """
    backflip_linear_velocities = [6, 5.9, 5.8, 5.7, 5.6, 5.5, 5.400001, 5.300001, 5.200001, 5.100001, 5.000001, 4.000001]
    """
    # movement_angle_offset = 0x8000
    # movement_angle = (camera_angle + movement_angle_offset) % TOTAL_ANGLES
    # cumulative_linear_velocity = 64.500006 # sum([6, 5.9, 5.8, 5.7, 5.6, 5.5, 5.400001, 5.300001, 5.200001, 5.100001, 5.000001, 4.000001])
    # cumulative_x_velocity = cumulative_linear_velocity * Math_SinS(movement_angle)
    # cumulative_z_velocity = cumulative_linear_velocity * Math_CosS(movement_angle)

    # updated_x_pos = x_pos + VELOCITY_SCALE * cumulative_x_velocity 
    # updated_z_pos = z_pos + VELOCITY_SCALE * cumulative_z_velocity
    # return updated_x_pos, updated_z_pos, angle
    data = HoldBackflipCache[get_bin(angle)]
    if not fp32:
        updated_x_pos = x_pos + data["X Position Change"]
        updated_z_pos = z_pos + data["Z Position Change"]
    else:
        updated_x_pos = np.float32(x_pos) + np.float32(data["X Position Change"])
        updated_z_pos = np.float32(z_pos) + np.float32(data["Z Position Change"])
    updated_angle = data["Final Angle"]
    return updated_x_pos, updated_z_pos, updated_angle

def hold_deku_spin(x_pos, z_pos, angle, target=True, fp32=True):
    """
    Original (commented) implementation assumed target is ALWAYS TRUE (i.e. untargeted was not implemented)
    Importantly, this assumes you hold shield at the end of the spin

    deku_spin_linear_velocities = [2, 4, 6, 8, 8.772973, 8.383783, 7.994595, 7.605406, 7.216217, 6.827027, 6.437838, 6.048649, 5.65946, 5.27027, 4.881081, 4.881081] # repeated value at end might be due to holding shield as shield often repeats your last velocity for 1 frame
    """
    # movement_angle_offset = 0x0000
    # movement_angle = (camera_angle + movement_angle_offset) % TOTAL_ANGLES
    # cumulative_linear_velocity = 99.97837999999999 # [2, 4, 6, 8, 8.772973, 8.383783, 7.994595, 7.605406, 7.216217, 6.827027, 6.437838, 6.048649, 5.65946, 5.27027, 4.881081, 4.881081]
    # cumulative_x_velocity = cumulative_linear_velocity * Math_SinS(movement_angle)
    # cumulative_z_velocity = cumulative_linear_velocity * Math_CosS(movement_angle)

    # updated_x_pos = x_pos + VELOCITY_SCALE * cumulative_x_velocity 
    # updated_z_pos = z_pos + VELOCITY_SCALE * cumulative_z_velocity
    # return updated_x_pos, updated_z_pos, angle
    if target:
        data = HoldDekuSpinTargetedCache[get_bin(angle)] # note: this cache assumes that you hold TARGET + Up + A on the first frame, then you hold shield at end of spin
    else:
        data = HoldDekuSpinUntargetedCache[get_bin(angle)]
    if not fp32:
        updated_x_pos = x_pos + data["X Position Change"]
        updated_z_pos = z_pos + data["Z Position Change"]
    else:
        updated_x_pos = np.float32(x_pos) + np.float32(data["X Position Change"])
        updated_z_pos = np.float32(z_pos) + np.float32(data["Z Position Change"])
    updated_angle = data["Final Angle"]
    return updated_x_pos, updated_z_pos, updated_angle

def ess_turn(x_pos, z_pos, angle, num_turns):
    """
    `num_turns` > 0 means ESS turns left, `num_turns` < 0 means ESS turns right
    """
    if num_turns == 0:
        raise ValueError(f"Got {num_turns=}, but it should be positive or negative")
    angle_offset = 0x708

    new_angle = (angle + num_turns * angle_offset) % TOTAL_ANGLES
    return x_pos, z_pos, new_angle

def deku_spin_in_place(x_pos, z_pos, angle, num_spins):
    angle_offset = -0x1E0
    new_angle = (angle + num_spins * angle_offset) % TOTAL_ANGLES
    return x_pos, z_pos, new_angle

def cardinal_turn(x_pos, z_pos, angle, direction):

    camera_angle = FacingAngleToTargetedCameraAngle[get_bin(angle)]

    if direction == "UP":
        angle_offset = 0x0000
    elif direction == "LEFT":
        angle_offset = 0x4000
    elif direction == "DOWN":
        angle_offset = 0x8000
    elif direction == "RIGHT":
        angle_offset = 0xC000
    else:
        raise ValueError(f"invalid direction, got {direction=}")

    new_angle = (camera_angle + angle_offset) % TOTAL_ANGLES
    return x_pos, z_pos, new_angle


def position_is_valid(x_pos, z_pos):

    # this bans some parts of the checkerboard area, but I don't have to worry about checking for moving diagonal through the wall
    if z_pos > 826 or z_pos < 134:
        return False

    if x_pos > 66 or x_pos < -1666:
        return False

    # slanted part of counter near clip location
    if z_pos >= 797 and x_pos <= -174 and x_pos >= -243.7903 and x_pos >= ((-243.7903 - -180.3072)/(826 - 797.6762))* (z_pos - 826) + -243.7903:
        return False

    # slanted part of counter to the left side of the room
    if 15 <= x_pos <= 66 and x_pos <= ((66 - 15)/(818.1763 - 797))*(z_pos - 797) + 15:
        return False

    # # checkboard area, these will never execute in practice so commenting it for now
    # if z_pos > 826 and x_pos > -375:
    #     return False
    # if z_pos < 134 and x_pos > -374:
    #     return False
    # if z_pos < 14:
    #     return False
    # if z_pos > 946:
    #     return False
    return True


# list of 2-tuples: first entry is the camera angle and the second entry is the number os frames it is active for
CameraAngleAndLastingFrames = [
    (0xFE91, 2),
    (0xFEA1, 2),
    (0xFEB1, 2),
    (0xFEC1, 2),
    (0xFED1, 2),
    (0xFEE1, 2),
    (0xFEF1, 2),
    (0xFF01, 1),
    (0xFF11, 2),
    (0xFF21, 2),
    (0xFF31, 2),
    (0xFF41, 1),
    (0xFF51, 2),
    (0xFF61, 2),
    (0xFF71, 1),
    (0xFF81, 1),
    (0xFF91, 2),
    (0xFFA1, 1),
    (0xFFB1, 1),
    (0xFFC1, 1),
    (0xFFD1, 1),
    (0xFFE1, 1),
    (0xFFF1, 1),
    (0x0000, float('inf')),
]

CameraAngleToLastingFrameIndex = {get_bin(a) : i for i, (a, _) in enumerate(CameraAngleAndLastingFrames)}

def build_movement_angle_to_previous_cam_angles_map(CameraAngleAndLastingFrames):
    """
    Given the movement angle on the frame of the clip (linear velocity of 9.94054), we want
    all angles that we could have while walking (while targeted). See diagram in the docstring
    for `preprocess_exodus_csv` for more details.

    The walking camera angle is the movement angle that we have on the linear velocity 6 frames. We also
    want to store the movement angle that we have on the linear velocity 8 frame so we can completely backtrack. 
    """
    ClipMovementAngleToPreviousMovementAngles = {}
    for i, (walking_camera_angle, _) in enumerate(CameraAngleAndLastingFrames[:-2]):

        linear_velocity_8_movement_angle, lasts_for = CameraAngleAndLastingFrames[i+1]
        if lasts_for == 2:
            linear_velocity_994054_movement_angle = linear_velocity_8_movement_angle
        elif lasts_for == 1:
            linear_velocity_994054_movement_angle, _ = CameraAngleAndLastingFrames[i+2]

        if linear_velocity_994054_movement_angle not in ClipMovementAngleToPreviousMovementAngles:
            ClipMovementAngleToPreviousMovementAngles[linear_velocity_994054_movement_angle] = []
        previous_movement_angles = {
            6 : walking_camera_angle,
            8: linear_velocity_8_movement_angle,
        }
        ClipMovementAngleToPreviousMovementAngles[linear_velocity_994054_movement_angle].append(previous_movement_angles)

    return ClipMovementAngleToPreviousMovementAngles

ClipMovementAngleToPreviousMovementAngles = build_movement_angle_to_previous_cam_angles_map(CameraAngleAndLastingFrames)

def get_xz_vel(linear_velocity, movement_angle):
    x_velocity = linear_velocity * Math_SinS(movement_angle)
    z_velocity = linear_velocity * Math_CosS(movement_angle)
    return (x_velocity, z_velocity)

def reverse_clip_position(x_position, z_position, clip_movement_angle):
    """
    `clip_movement_angle` is the movement angle at linear velocity 9.94054. 
    `x_position` and `z_position` are the x and z positions on that frame as well.

    We want to find the position that we can stand in as deku before we begin walking at all in order to achieve the clip position
    and movement angle. However, many solutions exist as we could start walking from far away instead of deku spinning as soon as possible. 
    We want to consider walking up to an additional 75 frames
    """
    if clip_movement_angle not in ClipMovementAngleToPreviousMovementAngles:
        if clip_movement_angle + 1 not in ClipMovementAngleToPreviousMovementAngles:
            raise ValueError(f"clip movement angle not in dictionary, got {hex(clip_movement_angle)}. Additionally, {hex(clip_movement_angle+1)} is not in the dictionary!")
        clip_movement_angle += 1 # to account for the last digit of the camera angle either being a 0 or a 1

    target_positions = []
    for previous_movement_angles in ClipMovementAngleToPreviousMovementAngles[clip_movement_angle]:
        walking_movement_angle = previous_movement_angles[6]
        linear_velocity_8_movement_angle = previous_movement_angles[8]

        for extra_walk_frames in range(76):
            cumulative_walking_linear_velocity = 18 + 6 * extra_walk_frames # (2 + 4 + 6 + 6 + 6*extra_walk_frames) @ walking movement angle
            cumulative_walking_x_velocity, cumulative_walking_z_velocity = get_xz_vel(linear_velocity=cumulative_walking_linear_velocity, movement_angle=walking_movement_angle)

            lin_vel_8_x_velocity, lin_vel_8_z_velocity = get_xz_vel(linear_velocity=8, movement_angle=linear_velocity_8_movement_angle)

            x_pos_change = (cumulative_walking_x_velocity + lin_vel_8_x_velocity) * VELOCITY_SCALE
            z_pos_change = (cumulative_walking_z_velocity + lin_vel_8_z_velocity) * VELOCITY_SCALE

            # note that since we are reverseing the position, we need to actually subtract these changes!
            reversed_position_x = x_position - x_pos_change
            reversed_position_z = z_position - z_pos_change

            target_position = {
                'Walking Angle' : walking_movement_angle, 
                'X Position' : reversed_position_x, 
                'Z Position' :reversed_position_z,
                'Extra Walking Frames' : extra_walk_frames,
                }
            target_positions.append(target_position)
    return target_positions


def get_xz_vel_fp32(linear_velocity, movement_angle):
    x_velocity = np.float32(linear_velocity) * np.float32(Math_SinS(movement_angle))
    z_velocity = np.float32(linear_velocity) * np.float32(Math_CosS(movement_angle))
    return (x_velocity, z_velocity)

# using fp32 works much better, but still not perfect for reversing since there is inherently floating point error
def reverse_clip_position_fp32(x_position, z_position, clip_movement_angle):
    """
    `clip_movement_angle` is the movement angle at linear velocity 9.94054. 
    `x_position` and `z_position` are the x and z positions on that frame as well.

    We want to find the position that we can stand in as deku before we begin walking at all in order to achieve the clip position
    and movement angle. However, many solutions exist as we could start walking from far away instead of deku spinning as soon as possible. 
    We want to consider walking up to an additional 75 frames
    """
    if clip_movement_angle not in ClipMovementAngleToPreviousMovementAngles:
        if clip_movement_angle + 1 not in ClipMovementAngleToPreviousMovementAngles:
            raise ValueError(f"clip movement angle not in dictionary, got {hex(clip_movement_angle)}. Additionally, {hex(clip_movement_angle+1)} is not in the dictionary!")
        clip_movement_angle += 1 # to account for the last digit of the camera angle either being a 0 or a 1

    target_positions = []
    for previous_movement_angles in ClipMovementAngleToPreviousMovementAngles[clip_movement_angle]:
        walking_movement_angle = previous_movement_angles[6]
        linear_velocity_8_movement_angle = previous_movement_angles[8]

        for extra_walk_frames in range(76):

            linear_velocities = [2, 4, 6, 6] + [6 for _ in range(extra_walk_frames)]

            reversed_position_x = np.float32(x_position)
            reversed_position_z = np.float32(z_position)
            for v in linear_velocities:
                v_x, v_z = get_xz_vel_fp32(v, walking_movement_angle)
                reversed_position_x -= np.float32(v_x) * np.float32(VELOCITY_SCALE)
                reversed_position_z -= np.float32(v_z) * np.float32(VELOCITY_SCALE)


            v_x, v_z = get_xz_vel_fp32(8, linear_velocity_8_movement_angle)
            reversed_position_x -= np.float32(v_x) * np.float32(VELOCITY_SCALE)
            reversed_position_z -= np.float32(v_z) * np.float32(VELOCITY_SCALE)

            target_position = {
                'Walking Angle' : walking_movement_angle, 
                'X Position' : reversed_position_x, 
                'Z Position' :reversed_position_z,
                'Extra Walking Frames' : extra_walk_frames,
                }
            target_positions.append(target_position)
    return target_positions



# # TODO I'll delete this later, this is just here for testing purposes!
# targets = reverse_clip_position(x_position=-239.56575, z_position=824.11, clip_movement_angle=0xFEC1)
# targets_fp32 = reverse_clip_position_fp32(x_position=-239.56575, z_position=824.11, clip_movement_angle=0xFEC1)
# import code; code.interact(local=locals())



# def preprocess_exodus_csv(directory):
#     """
#     `directory` is a string corresponding to the directory the .csv files are stored in,
#     these are the .csv files from exodus's google sheet 

#     The files have names in the form e.g. "Treasure Chest Game Deku Spin clip - FEC0.csv"

#     Exodus's .csv files contain "Yes"/"No" entries corresponding to (z, x) positions which
#     indicate whether or not the clip works at that position at the movement angle mentioned
#     in the file name. However, the movement angle used and positions used are actually on the
#     frame of the clip which is when deku has linear velocity 9.94054, so these aren't the actual
#     positions that we want the setup to find. So we have to reverse engineer all possible position
#     setups that we could walk for X frames and then spin from. 
    
#         How Targeted Deku Walk into Deku Spin works for the clip:
#             - We start with a facing angle and it's corresponding targeted camera angle
#             - lin vel 2, 4, 6 @ targeted cam angle
#             - another lin vel 6 @ targeted cam angle (cam potentially updates on this frame) (when you start a deku spin, the 6 lin vel gets repeated for 1 frame)
#             - lin vel 8 @ updated cam angle (if 1-framer, cam updates again)
#             - lin vel 9.94054 @ (potentially new) cam angle -- this movement angle needs to match the one in the filename
#         Summary:
#             - so we do (2 + 4 + 6) * 1.5 units all at the targeted camera movement angle, every time
#             - but we can do an additional k * 6 * 1.5 units for k in {0, 1, ..., 75} roughly -- this is optional, but we need to test all of these
#                 - k=0 corresponds to walking from standstill, k=1 is 1 extra frame of walking from the minimum required, etc.
#             - 6 * 1.5 with SAME MOVEMENT ANGLE but new camera angle if the previous targeted camera angle lasts for 2 or 1 frames (only exception is if they last for float('inf') frames, which might not even happen)
#             - 8 * 1.5 at the NEW MOVEMENT ANGLE (if the camera angle lasts for 1 or 2 frames) (the new movement angle is the same value as the new camera angle we got on the previous frame -- so this is the first step at which the movement angle ever changes!)
#             - if the movement angle on the previous frame is a camera angle that lasts for 1 frame, then we move to the next movement angle on this frame, otherwise we keep the same movement angle as before
#                 - add on 9.94054 * 1.5 at whatever movement angle we have now

#         How do we reverse this? Let Y be some angle and let Y+0x10 be our movement angle of the last frame we have a linear velocity of 6

#             lin vel.   movement angle
#                 0:       Y
#                 0:       Y+0x10 (snaps to camera)
#                 2:       Y+0x10
#                 4:       Y+0x10
#                 6: 	     Y+0x10 <-- 1-framer or 2-framer
#                 -------
#                 8: 	     Y+0x20 <-- 2-framer
#                 9.94054: Y+0x20     (repeated)


#                 0:       Y
#                 0:       Y+0x10 (snaps to camera)
#                 2:       Y+0x10
#                 4:       Y+0x10
#                 6: 	     Y+0x10 <-- 1-framer or 2-framer
#                 -------
#                 8: 	     Y+0x20 <-- 1-framer
#                 9.94054: Y+0x30 <-- 1-framer or 2-framer

#             ### vvvvvvvvvvvv DON'T TRUST THIS STUFF TOO CLOSELY, I WAS SLEEP DEPRIVED AND I'M PRETTY SURE I MADE MISTAKES vvvvvvvvvvvvvvvvvvvvv
#             # If our angle on 9.94054 linear velocity is a 1-frame or a 2-framer, in either case we don't know if the angle on 8 linear velocity
#             # was a 1-framer or a 2-framer, so we don't necessarily know what angle we had while walking.

#             #     Suppose on lin vel 9.94054 we have angle Y and that it is a 2-framer. Suppose Y-0x10 is also a 2-framer. If Y-0x10 were the angle during
#             #     lin vel 8, then it would also be the angle for lin vel 9.94054 because that is what happens with 2-framers (see first diagram above), so
#             #     if Y and Y-0x10 are both 2-framers, then Y-0x10 was the camera angle (i.e. angle for 6 lin vel). This same argument works assuming that
#             #     Y is a 1-framer, so if Y-0x10 is a 2-framer then it was the camera angle.
#             #         Summary:
#             #             Suppose: Y in {1-framer, 2-framer}, Y-0x10 = 2-framer --> Y-0x10 is on lin vel 6 

#             #     Suppose on lin vel 9.94054 we have angle Y and that it is a 1-framer or 2-framer (shouldn't really matter). If Y-0x10 is a 1-framer, then
#             #     it could've been on either lin vel 8 or lin vel 6. We literally don't know.   help me claude??????
                
#             #     Suppose: Y = 1-framer, Y-0x10 = 1-framer, Y-0x20 = 1-framer. In this case, we know lin vel 6 had to be Y-0x20.

#         Example: 
#             for the 0xFEC0 exodus sheet, (x, z) = (-239.5658, 824.112) is a working position in the .csv file, so let's reverse engineer a working position
#             - CameraAngleAndLastingFrames[CameraAngleToLastingFrameIndex[get_bin(0xFEC0)]] = (0xFEC1, 2)
#             - since the movement update from the 9.94054 velocity frame didn't actually happen yet, we can ignore it, but we use its movement angle to compute the previous movement angle
#                 - since the final movement angle is 0xFEC1 (on the 9.94054 frame) 
#         nvm, not finishing this docstring, but clearly there can be multiple different walking angles for a given clip movement angle:

#         examples:
#         hex(linear_velocity_994054_movement_angle)='0xff11', ('0xfef1', '0xff01')
#         hex(linear_velocity_994054_movement_angle)='0xff51', ('0xff31', '0xff41')
#         hex(linear_velocity_994054_movement_angle)='0xff91', ('0xff71', '0xff81')

#     """



########## big copy and paste from claude vvvvvvvvvvvvvvvvvvvvvvvv
# Paste-ready replacement for preprocess_exodus_csv (keep your long explanatory docstring/notes above it if you like).
#
# It uses names that already exist in your file:
#   load_grid                                  (from the RegionSet block)
#   reverse_clip_position_fp32                 (yours)
#   ClipMovementAngleToPreviousMovementAngles  (yours)
# and needs these imports (add `shutil`; the rest you already have):
import re
import shutil
import time
from pathlib import Path

import numpy as np

# "Treasure Chest Game Deku Spin clip - FEC0"  ->  clip movement angle 0xFEC0 (matched against the file stem)
EXODUS_NAME_PATTERN = r".*-\s*(?P<angle>[0-9A-Fa-f]{4})"


def _detect_sep(path):
    """Google-sheet exports are usually comma-separated, but your samples looked tab-separated. Look at the header."""
    with open(path, "r", encoding="utf-8-sig") as f:
        header = f.readline()
    return "\t" if "\t" in header else ","


def _write_grid(path, zs, xs, V):
    """Write a tab-separated z-x Yes/No grid that `RegionSet.from_directory` can read back. Axis values are written
    with repr(), so the float32-derived values round-trip exactly."""
    lines = ["\t".join(["z \\ x"] + [repr(float(x)) for x in xs])]
    for j, z in enumerate(zs):
        lines.append("\t".join([repr(float(z))] + ["Yes" if v else "No" for v in V[j]]))
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def preprocess_exodus_csv(directory, output_directory="solution_grids"):
    """
    Turn exodus's clip-frame grids into walk-start grids that `RegionSet.from_directory` can load.

    For every exodus sheet (clip movement angle F, from the file name) and every walking angle A / extra-walk-frame
    count k that leads to F, one output grid is written to `output_directory`, named
        angle_0x{A:04X}_steps_{k}.csv
    Each output grid has the same Yes/No cells as the sheet; only the axes change (every clip x / z is replaced by
    the start x / z that `reverse_clip_position_fp32` gives for it).

    Why this is equivalent to calling reverse_clip_position_fp32 on every Yes cell: in that function the reversed x
    depends only on x and the reversed z only on z, so it is enough to reverse each distinct x and each distinct z
    once. Rounding is monotone, so the axes stay ordered.

    Safety: the output directory must not exist yet (or be empty). Files are built in "<output_directory>.tmp"
    and renamed only when everything succeeded, so a crash can't leave a half-written solution set behind.

    Returns a summary dict (also printed).
    """
    directory, output_directory = Path(directory), Path(output_directory)

    # ---- validate everything cheap before doing any real work ------------------------------------------------
    paths = sorted(directory.glob("*.csv"))
    if not paths:
        raise FileNotFoundError(f"no .csv files in {str(directory)!r}")
    rx = re.compile(EXODUS_NAME_PATTERN)
    files, bad = {}, []
    for p in paths:
        m = rx.fullmatch(p.stem)
        if m is None:
            bad.append(p.name)
            continue
        angle = int(m.group("angle"), 16)
        if angle in files:
            raise ValueError(f"{p.name} and {files[angle].name} are both for clip angle {hex(angle)}")
        files[angle] = p
    if bad:
        raise ValueError(f"{len(bad)} file(s) don't end in ' - XXXX.csv' (4 hex digits): {bad[:5]}")

    if output_directory.exists():
        if any(output_directory.iterdir()):
            raise FileExistsError(f"{str(output_directory)!r} already has files in it; delete or rename it first "
                                  f"(RegionSet loads EVERY csv in a directory, so stale files would silently mix in)")
        output_directory.rmdir()
    tmp_directory = output_directory.with_name(output_directory.name + ".tmp")
    if tmp_directory.exists():
        raise FileExistsError(f"{str(tmp_directory)!r} exists (left over from an interrupted run?); delete it first")

    # ---- do the work in the temp directory --------------------------------------------------------------------
    start_time = time.time()
    tmp_directory.mkdir(parents=True)
    written = {}  # (walking angle, steps) -> output file name; catches collisions
    skipped_all_no, skipped_no_walking_angle = [], []
    try:
        for clip_angle, path in sorted(files.items()):
            zs, xs, V = load_grid(path, _detect_sep(path))

            if not V.any():
                skipped_all_no.append(path.name)
                print(f"  {path.name}: no Yes cells, skipped")
                continue
            if clip_angle not in ClipMovementAngleToPreviousMovementAngles \
                    and clip_angle + 1 not in ClipMovementAngleToPreviousMovementAngles:
                skipped_no_walking_angle.append(path.name)
                print(f"  {path.name}: no walking angle produces clip angle {hex(clip_angle)}, skipped")
                continue

            # Crop to the bounding box of the Yes cells. Exact: everything outside is No, and a No corner can never
            # make an edge / cell valid, so removing those rows/columns changes nothing about the region.
            rows, cols = np.flatnonzero(V.any(axis=1)), np.flatnonzero(V.any(axis=0))
            zs, xs = zs[rows[0]:rows[-1] + 1], xs[cols[0]:cols[-1] + 1]
            V = V[rows[0]:rows[-1] + 1, cols[0]:cols[-1] + 1]

            # Reverse each distinct x (with a dummy z) and each distinct z (with a dummy x).
            z_dummy, x_dummy = float(zs[0]), float(xs[0])
            x_results = [reverse_clip_position_fp32(float(x), z_dummy, clip_angle) for x in xs]
            z_results = [reverse_clip_position_fp32(x_dummy, float(z), clip_angle) for z in zs]

            # every call returns the same list of (walking angle, extra walking frames) in the same order
            labels = [(r["Walking Angle"], r["Extra Walking Frames"]) for r in x_results[0]]
            for res in x_results + z_results:
                assert [(r["Walking Angle"], r["Extra Walking Frames"]) for r in res] == labels

            X = np.array([[float(r["X Position"]) for r in res] for res in x_results])  # (n_cols, n_entries)
            Z = np.array([[float(r["Z Position"]) for r in res] for res in z_results])  # (n_rows, n_entries)

            for i, (walking_angle, steps) in enumerate(labels):
                new_xs, new_zs = X[:, i], Z[:, i]
                if not (np.all(np.diff(new_xs) > 0) and np.all(np.diff(new_zs) > 0)):
                    raise ValueError(f"{path.name}: walking angle {hex(walking_angle)}, {steps} extra frames: two "
                                     f"neighbouring sheet coordinates collapsed onto the same float32 value")
                name = f"angle_0x{walking_angle:04X}_steps_{steps}.csv"
                if (walking_angle, steps) in written:
                    raise ValueError(f"{name} would be written twice ({path.name} and {written[(walking_angle, steps)]})")
                written[(walking_angle, steps)] = path.name
                _write_grid(tmp_directory / name, new_zs, new_xs, V)

            print(f"  {path.name}: {V.shape[1]} x {V.shape[0]} cropped grid, {len({a for a, _ in labels})} walking "
                  f"angle(s) -> {len(labels)} files")

        if not written:
            raise ValueError("nothing was written (every sheet was skipped)")
        tmp_directory.rename(output_directory)
    except BaseException:
        shutil.rmtree(tmp_directory, ignore_errors=True)  # only ever removes the directory created above
        raise

    summary = {
        "files_written": len(written),
        "skipped_all_no": skipped_all_no,
        "skipped_no_walking_angle": skipped_no_walking_angle,
        "seconds": time.time() - start_time,
    }
    print(f"Wrote {summary['files_written']} grids to {str(output_directory)!r} in {summary['seconds']:.1f}s"
          + (f"; skipped (no Yes cells): {skipped_all_no}" if skipped_all_no else "")
          + (f"; skipped (no walking angle): {skipped_no_walking_angle}" if skipped_no_walking_angle else ""))
    return summary
########## big copy and paste from claude ^^^^^^^^^^^^^^^^^^^^^^^^



if not Path("solution_grids").exists():
    print("PREPROCESSING EXODUS CSV FILES")
    preprocess_exodus_csv("exodus_csvs")
else:
    print("WARNING: SKIPPING preprocess_exodus_csv BECAUSE THE DIRECTORY ALREADY EXISTS")
solutions = RegionSet.from_directory("solution_grids") # directory containing ONLY the z-x grid csvs
# we called it `solutions`, but really they are the `target` positions.

def position_is_solution(x_pos, z_pos):
    return solutions.contains(x_pos, z_pos)

# def position_is_solution(x_pos, z_pos):
#     pass # TODO, need number of frames to walk before spinning!!


def position_str(x, z, angle):
    camera_angle = FacingAngleToTargetedCameraAngle[get_bin(angle)]
    return f"    (X, Z, Angle, Cam)=({x}, {z}, {hex(angle)}, {hex(camera_angle)})"

# def log_solution(x0, z0, a0, sol_x, sol_z, sol_a, action_log, filename):
#     with open(filename, 'a') as f:
#         f.write(f"-"*30)
#         f.write(f"Solution Position: {position_str(sol_x, sol_z, sol_a)}\n")
#         f.write(f"Initial Position: {position_str(x0, z0, a0)}\n")
#         for action in action_log:
#             f.write(f"    {action}\n")
#         # TODO somehow fetch which angle is needed for the solution position
#         # TODO WE ALSO NEED HOW MANY FRAMES OF WALKING FORWARD IS NEEDED FOR THE DEKU SPIN CLIP (assuming you have correct angle)!!!!!!!!!!!!

def log_solution(x0, z0, a0, sol_x, sol_z, sol_a, action_log, filename, matches):
    with open(filename, 'a') as f:
        f.write("-" * 30 + "\n")
        f.write(f"Solution Position: {position_str(sol_x, sol_z, sol_a)}\n")
        f.write(f"Initial Position: {position_str(x0, z0, a0)}\n")
        for m in matches:
            f.write(f"NEEDS: {m.describe()}  ({m.name})\n")
        for action in action_log:
            f.write(f"    {action}\n")
        

"""
To get the targeted camera angle corresponding to a given facing angle (on flat ground and not too close to a wall), I use a lookup table
that I obtain by running a lua script. Also, I use a lookup table for tons of other stuff now because the camera is extremely annoying. This
is a bad and incomplete comment, sorry, but I used a lua script to generate .csv files that cached movement at all 4096 angle bins.
"""



print("Preprocessing .csv files to build caches...")
initial_time = time.time()
FacingAngleToTargetedCameraAngle = preprocess_targeted_camera_angles("hold_sidehop_left.csv")
FacingAngleToLeftGuanoMovementAngles = preprocess_guano_movement_angles_csv("guanowalk_left.csv") # with current data, it is limited to only first ~30 mvoement angles, in reality there are ~54 or so, but in practice we probably wouldn't even use 5 or 10 of them anyway -- I would've done all of them but guanowalking into walls made it annoying to script and not worth the effort
FacingAngleToRightGuanoMovementAngles = preprocess_guano_movement_angles_csv("guanowalk_right.csv")

HoldBackflipCache = preprocess_csv("hold_backflip.csv")
HoldLeftSidehopCache = preprocess_csv("hold_sidehop_left.csv")
HoldRightSidehopCache = preprocess_csv("hold_sidehop_right.csv")
HoldDekuSpinTargetedCache = preprocess_csv("hold_deku_spin_targeted.csv") # assumes holding target when starting the spin
HoldDekuSpinUntargetedCache = preprocess_csv("hold_deku_spin_untargeted.csv") # assumes untargeted when starting the spin
final_time = time.time()
print(f"Caches generated in {final_time-initial_time:.2f} seconds")


MovementCosts = {
    "HoldSidehopLeft" : 1,
    "HoldSidehopRight" : 1,
    "GuanoShieldScootLeft" : 1,
    "GuanoShieldScootRight" : 1,
    "ShieldScootForward" : 1,
    "HoldBackflip" : 1,
    "HoldDekuSpinTargeted" : 1,
    "HoldDekuSpinUntargeted" : 1,
}

AngleCosts = {
    "ESSTurn": 1,
    "CardinalTurn": 0.25,
    "DekuSpinInPlace" : 1,
    "ResetGuanoChain" : 0,
    "NULL": 0,
}


############## TODO double check from claude
import math

def _max_disp(cache):
    return max(math.hypot(v["X Position Change"], v["Z Position Change"]) for v in cache.values())

# scoots: 4 velocity * 1.5, times the largest |(sin, cos)| the game's lookup table can produce
_SCOOT_DISP = 4 * VELOCITY_SCALE * max(math.hypot(Math_SinS(a), Math_CosS(a)) for a in range(0, TOTAL_ANGLES, 0x10))

MaxDisplacement = {
    "HoldSidehopLeft": _max_disp(HoldLeftSidehopCache),
    "HoldSidehopRight": _max_disp(HoldRightSidehopCache),
    "GuanoShieldScootLeft": _SCOOT_DISP,
    "GuanoShieldScootRight": _SCOOT_DISP,
    "ShieldScootForward": _SCOOT_DISP,
    "HoldBackflip": _max_disp(HoldBackflipCache),
    "HoldDekuSpinTargeted": _max_disp(HoldDekuSpinTargetedCache),
    "HoldDekuSpinUntargeted": _max_disp(HoldDekuSpinUntargetedCache),
}
assert MaxDisplacement.keys() == MovementCosts.keys()  # catches a new move missing from one dict
MAX_REACH_PER_COST = max(
    float("inf") if MovementCosts[k] == 0 else MaxDisplacement[k] / MovementCosts[k]
    for k in MovementCosts
)
print(f"{MAX_REACH_PER_COST=}")
############## from claude ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

MAX_COST = 10 # 10
MAX_ESS_TURNS = 8 # e.g. -8, -7, ..., -1, 1, ..., 7, 8 (i.e. do negative and positive but skip 0)
ESS_OPTIONS = [a for a in range(-MAX_ESS_TURNS, MAX_ESS_TURNS+1) if a != 0]
MAX_DEKU_SPINS_IN_PLACE = 3
MAX_GUANO_CHAIN_LENGTH = 5 #20 #5

def find_solutions(x0, z0, a0, filename):
    """
    `x0` initial x position
    `z0` initial z position
    `a0` initial angle
    `filename` of txt file we save solutions to
    """

    success_count = [0]
    failure_count = [0]
    def dfs(x, z, a, angle_turn=True, guano_chain_length=0, action_log=[], cost=0):

        if cost > MAX_COST:
            failure_count[0] += 1
            #print(f"{success_count[0]} Solutions Found, {failure_count[0]} Failures -- exceeds max cost")
            return False
        if guano_chain_length > MAX_GUANO_CHAIN_LENGTH:
            failure_count[0] += 1
            #print(f"{success_count[0]} Solutions Found, {failure_count[0]} Failures -- guano")
            return False
        if not position_is_valid(x, z): # important that this is checked BEFORE solution is valid because preprocess_exodus_csv might give invalid "solution" positions
            failure_count[0] += 1
            #print(f"{success_count[0]} Solutions Found, {failure_count[0]} Failures")
            return False

        if not solutions.within_reach(x, z, (MAX_COST - cost) * MAX_REACH_PER_COST):
            failure_count[0] += 1
            #print(f"{success_count[0]} Solutions Found, {failure_count[0]} Failures -- {cost=}")
            return False

        # if position_is_solution(x, z):
        #     # TODO I need to know which movement angle the solution corresponds to as well as the number of walking frames!!!!!!!
        #     log_solution(x0=x0, z0=z0, a0=a0, sol_x=x, sol_z=z, sol_a=a, action_log=action_log, filename=filename)
        #     success_count[0] += 1
        #     print(f"{success_count[0]} Solutions Found, {failure_count[0]} Failures")
        #     return True # I don't think return value really matters, just terminates the dfs branch

        if position_is_solution(x, z):
            matches = solutions.matches(x, z)
            log_solution(x0=x0, z0=z0, a0=a0, sol_x=x, sol_z=z, sol_a=a, action_log=action_log, filename=filename, matches=matches)
            success_count[0] += 1
            print(f"{success_count[0]} Solutions Found, {failure_count[0]} Failures")
            return True # I don't think return value really matters, just terminates the dfs branch
        
        if angle_turn:
            for angle_option in AngleCosts:
                # if angle_option != "NULL":
                #     guano_chain_length = 0

                if angle_option == "ESSTurn":
                    for num_turns in ESS_OPTIONS:
                        new_x, new_z, new_a = ess_turn(x_pos=x, z_pos=z, angle=a, num_turns=num_turns)
                        action_log.append(f"{num_turns} ESS Turns" + position_str(x=new_x, z=new_z, angle=new_a))
                        dfs(x=new_x, z=new_z, a=new_a, angle_turn=not angle_turn, guano_chain_length=0, action_log=action_log, cost=cost+AngleCosts[angle_option])
                        action_log.pop()
                elif angle_option == "CardinalTurn":
                    for direction in ['LEFT', 'RIGHT', 'DOWN']:
                        new_x, new_z, new_a = cardinal_turn(x_pos=x, z_pos=z, angle=a, direction=direction)
                        action_log.append(f"Cardinal Turn {direction}" + position_str(x=new_x, z=new_z, angle=new_a))
                        dfs(x=new_x, z=new_z, a=new_a, angle_turn=not angle_turn, guano_chain_length=0, action_log=action_log, cost=cost+AngleCosts[angle_option])
                        action_log.pop()
                elif angle_option == "DekuSpinInPlace":
                    for num_deku_spins in range(1, MAX_DEKU_SPINS_IN_PLACE+1):
                        new_x, new_z, new_a = deku_spin_in_place(x_pos=x, z_pos=z, angle=a, num_spins=num_deku_spins)
                        action_log.append(f"{num_deku_spins} Deku Spins In Place" + position_str(x=new_x, z=new_z, angle=new_a))
                        dfs(x=new_x, z=new_z, a=new_a, angle_turn=not angle_turn, guano_chain_length=0, action_log=action_log, cost=cost+AngleCosts[angle_option]*num_deku_spins)
                        action_log.pop()
                elif angle_option == "NULL":
                    dfs(x=x, z=z, a=a, angle_turn=not angle_turn, guano_chain_length=guano_chain_length, action_log=action_log, cost=cost)
                elif angle_option == "ResetGuanoChain":
                    if guano_chain_length == 0: 
                        continue
                    action_log.append(f"{angle_option}" + position_str(x=x, z=z, angle=a))
                    dfs(x=x, z=z, a=a, angle_turn=not angle_turn, guano_chain_length=0, action_log=action_log, cost=cost+AngleCosts[angle_option])
                    action_log.pop()
                else:
                    raise ValueError("typo??")
        else: # if not angle_turn, we pick a movement option instead

            for movement_option in MovementCosts:
                if movement_option in {"HoldSidehopLeft", "HoldSidehopRight"}:
                    new_x, new_z, new_a = hold_sidehop(x_pos=x, z_pos=z, angle=a, left=movement_option=="HoldSidehopLeft")
                    action_log.append(f"{movement_option}" + position_str(x=new_x, z=new_z, angle=new_a))
                    dfs(x=new_x, z=new_z, a=new_a, angle_turn=not angle_turn, guano_chain_length=0, action_log=action_log, cost=cost+MovementCosts[movement_option])
                    action_log.pop()
                elif movement_option in {"GuanoShieldScootLeft", "GuanoShieldScootRight"}:
                    new_x, new_z, new_a = guano_shield_scoot(x_pos=x, z_pos=z, angle=a, guano_chain_length=guano_chain_length, left=movement_option=="GuanoShieldScootLeft")
                    action_log.append(f"{movement_option}" + position_str(x=new_x, z=new_z, angle=new_a))
                    dfs(x=new_x, z=new_z, a=new_a, angle_turn=not angle_turn, guano_chain_length=guano_chain_length+1, action_log=action_log, cost=cost+MovementCosts[movement_option])
                    action_log.pop()
                elif movement_option == "ShieldScootForward":
                    new_x, new_z, new_a = shield_scoot_forward(x_pos=x, z_pos=z, angle=a)
                    action_log.append(f"{movement_option}" + position_str(x=new_x, z=new_z, angle=new_a))
                    dfs(x=new_x, z=new_z, a=new_a, angle_turn=not angle_turn, guano_chain_length=0, action_log=action_log, cost=cost+MovementCosts[movement_option])
                    action_log.pop()
                elif movement_option == "HoldBackflip":
                    new_x, new_z, new_a = hold_backflip(x_pos=x, z_pos=z, angle=a)
                    action_log.append(f"{movement_option}" + position_str(x=new_x, z=new_z, angle=new_a))
                    dfs(x=new_x, z=new_z, a=new_a, angle_turn=not angle_turn, guano_chain_length=0, action_log=action_log, cost=cost+MovementCosts[movement_option])
                    action_log.pop()
                elif movement_option in ["HoldDekuSpinTargeted", "HoldDekuSpinUntargeted"]:
                    new_x, new_z, new_a = hold_deku_spin(x_pos=x, z_pos=z, angle=a, target=movement_option=="HoldDekuSpinTargeted")
                    action_log.append(f"{movement_option}" + position_str(x=new_x, z=new_z, angle=new_a))
                    dfs(x=new_x, z=new_z, a=new_a, angle_turn=not angle_turn, guano_chain_length=0, action_log=action_log, cost=cost+MovementCosts[movement_option])
                    action_log.pop()
                else:
                    raise ValueError("typo???")


            
    dfs(x=x0, z=z0, a=a0, angle_turn=True, guano_chain_length=0, action_log=[], cost=0)

x0 = np.float32(-70)
z0 = np.float32(209.75)
a0 = 0x0000
filename = "cmg-solutions-test.txt"
find_solutions(x0, z0, a0, filename)


