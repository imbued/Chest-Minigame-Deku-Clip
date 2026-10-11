import numpy as np
import pandas as pd

TOTAL_ANGLES = 0x10000
ESS_STEP = 0x708      # 1800; one ESS turn. Positive count = Left (adds), negative = Right (subtracts)
DEKU_STEP = 0x1E0     # one Deku spin subtracts this
CARDINALS = [0x0000, 0x4000, 0x8000, 0xC000]
CARD = np.array(CARDINALS, dtype=np.int64)
INF = 10**9

# gcd(0x708, 0x10000) = 8, so the ESS turn count only matters modulo 65536/8 = 8192,
# and the minimal |ESS count| for any reachable offset is at most 4096.
ESS_PERIOD = TOTAL_ANGLES // 8
INV_225 = pow(225, -1, ESS_PERIOD)   # 0x708 = 8 * 225


# ----------------------------------------------------------------------------------------
# Lookup cache loading (unchanged from your script)
# ----------------------------------------------------------------------------------------

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
    Also verifies that no (Initial Angle, Frame) pair is repeated.
    """
    data = pd.read_csv(filename)
    if "Frame" not in data.columns:
        raise ValueError(f"{filename}: no 'Frame' column, so row order can't be verified")
    data = data.sort_values("Frame", kind="stable")
    if data.duplicated(["Initial Angle", "Frame"]).any():
        raise ValueError(f"{filename}: repeated (Initial Angle, Frame) rows")
    return data

def preprocess_untargeted_camera_angle_after_targeting(filename="target_and_untarget_and_let_camera_snap.csv"):
    """
    e.g. if I have angle 0x3C00 and press target, while holding target my camera angle is 0x3C0F, but if I release
    target, then the camera angle will eventually snap to 0x4000 (takes several frames though)
    """
    if filename != "target_and_untarget_and_let_camera_snap.csv":
        raise ValueError(f"{filename=}")
    data = _read_sorted_by_frame(filename)

    cache = {}
    for initial_angle_str, rows in data.groupby("Initial Angle", sort=False):
        last_row = rows.iloc[-1]
        if last_row["Frame"] != rows["Frame"].max():
            raise ValueError(f"{filename}: angle {initial_angle_str} is not sorted by frame")
        cache[_to_int(initial_angle_str)] = _to_int(last_row["Camera Angle"])

    _check_all_bins(cache.keys(), filename)
    return cache

FacingAngleToUntargetedCameraAngleAfterTargeting = preprocess_untargeted_camera_angle_after_targeting(
    filename="target_and_untarget_and_let_camera_snap.csv")


def get_bin(angle):
    """Round down to a multiple of 0x10 (there are only 4096 angle bins in the cache)."""
    return 0x10 * (angle // 0x10)

def get_camera_angles(angle, lookup=FacingAngleToUntargetedCameraAngleAfterTargeting):
    cam_angle = lookup[get_bin(angle)]
    return [(cam_angle + card) % TOTAL_ANGLES for card in CARDINALS]


# ----------------------------------------------------------------------------------------
# Solver
# ----------------------------------------------------------------------------------------
#
# Model
# -----
# A "state" is a facing angle you are standing at right after you picked it (either an initial
# option, or a cardinal of a camera angle after retargeting). From a state you do a "segment":
#     d Deku spins and e ESS turns (e>0 Left, e<0 Right)   ->  facing = state - 0x1E0*d + 0x708*e
# (spins and ESS turns commute for the resulting angle, so only the totals matter).
# A segment ends either at a goal angle, or with a retarget: the camera angle becomes
# lookup[bin(facing)] and your next state is one of its 4 cardinals (free).
#
# Search
# ------
# We keep, for every state angle, the cheapest ESS count for each total Deku count
# (best[angle, deku]) -- a Pareto table -- and expand layer by layer in the number of retargets.
# A state is only expanded if it improved the table, so everything that is written out is
# Pareto-optimal: no listed solution is beaten (or tied) on both ESS and Deku by another one
# for the same goal angle.
#
# Reaching a goal angle from a state needs no enumeration: 0x708*e = goal - state + 0x1E0*d (mod 0x10000)
# is solved directly for the smallest |e|, so the *last* segment can use any number of ESS turns.
# Segments that end in a retarget are enumerated, up to `max_ess_before_retarget` ESS turns each.

def _ess_order(max_e):
    """0, 1, -1, 2, -2, ... so that the first hit for a given result is the cheapest."""
    order = [0]
    for i in range(1, max_e + 1):
        order += [i, -i]
    return np.array(order, dtype=np.int64)

def _fmt(a):
    return f"0x{a:04X}"

def _turns_text(d, e):
    parts = []
    if d:
        parts.append(f"{d} Deku spin{'s' if d != 1 else ''}")
    if e:
        parts.append(f"{abs(e)} {'Left' if e > 0 else 'Right'} ESS turn{'s' if abs(e) != 1 else ''}")
    return " + ".join(parts) if parts else "no turns"

def _unroll(path):
    steps = []
    while path is not None:
        path, item = path
        steps.append(item)
    steps.reverse()
    return steps


def solve_angles(initial_angle, goal_angles, lookup, initial_camera_angle=None,
                 max_deku_spins=10, max_retargets=2, max_ess_before_retarget=200, verbose=True):
    """
    Returns a list of solution dicts (Pareto-optimal in (ESS turns, Deku spins) per goal angle).

    max_deku_spins            total Deku spins allowed over the whole route
    max_retargets             how many times you may retarget (0 = old behaviour, no retargeting)
    max_ess_before_retarget   max |ESS turns| in a segment that is followed by a retarget
                              (the final segment into the goal is NOT limited by this)
    initial_camera_angle      if None, taken from the lookup cache for initial_angle
    """
    if not (isinstance(initial_angle, int) and 0 <= initial_angle < TOTAL_ANGLES):
        raise ValueError(f"{initial_angle=}")
    goals = sorted({int(g) % TOTAL_ANGLES for g in goal_angles})
    if not goals:
        raise ValueError("no goal angles given")

    D = max_deku_spins
    cam_table = np.zeros(TOTAL_ANGLES // 0x10, dtype=np.int64)
    for b, cam in lookup.items():
        cam_table[b >> 4] = cam

    # ---- starting options (all free) ----
    if initial_camera_angle is None:
        initial_camera_angle = lookup[get_bin(initial_angle)]
    starts = {}
    def add_start(a, label):
        starts.setdefault(a % TOTAL_ANGLES, label)
    add_start(initial_angle, "initial facing angle")
    for card in CARDINALS:
        add_start(initial_camera_angle + card,
                  f"initial camera angle {_fmt(initial_camera_angle)} + {_fmt(card)}")
    for card in CARDINALS:
        add_start(card, "always-available cardinal")

    best = np.full((TOTAL_ANGLES, D + 1), INF, dtype=np.int64)   # best[angle, deku] (prefix-min over deku)
    frontier = {}                                                # (angle, deku) -> (ess, path)
    for a, label in starts.items():
        best[a, 0] = 0
        frontier[(a, 0)] = (0, (None, ("start", a, label)))
    best = np.minimum.accumulate(best, axis=1)

    G = np.array(goals, dtype=np.int64)
    ng = len(goals)
    gidx = np.arange(ng)[None, :]
    goal_best = np.full((ng, D + 1), INF, dtype=np.int64)
    goal_path = {}                                               # (goal index, deku) -> (ess, path, (d, e))
    ds_all = np.arange(D + 1, dtype=np.int64)

    E_ARR = _ess_order(max_ess_before_retarget)
    ABS_E = np.abs(E_ARR)

    def check_goals(s, d0, c0, path):
        nd = D - d0 + 1
        dsl = ds_all[:nd]
        r = (G[None, :] - s + DEKU_STEP * dsl[:, None]) & 0xFFFF         # (nd, ng)
        ok = (r & 7) == 0
        if not ok.any():
            return
        e0 = ((r >> 3) * INV_225) % ESS_PERIOD
        e = np.where(e0 <= ESS_PERIOD // 2, e0, e0 - ESS_PERIOD)          # smallest |e|
        tot_c = c0 + np.abs(e)
        tot_d = np.broadcast_to((d0 + dsl)[:, None], r.shape)
        gi = np.broadcast_to(gidx, r.shape)
        m = ok & (tot_c < goal_best[gi, tot_d])
        if not m.any():
            return
        goal_best[gi[m], tot_d[m]] = tot_c[m]
        for di, g_i in zip(*np.nonzero(m)):
            goal_path[(int(g_i), d0 + int(di))] = (int(tot_c[di, g_i]), path, (int(dsl[di]), int(e[di, g_i])))

    for layer in range(max_retargets + 1):
        if verbose:
            print(f"layer {layer} (retargets used = {layer}): {len(frontier)} states to process")
        for (s, d0), (c0, path) in frontier.items():
            check_goals(s, d0, c0, path)
        if layer == max_retargets:
            break

        by_angle = {}
        for (s, d0), val in frontier.items():
            by_angle.setdefault(s, []).append((d0, val))

        new_states = {}
        for s, items in by_angle.items():
            x = (s - DEKU_STEP * ds_all[:, None] + ESS_STEP * E_ARR[None, :]) & 0xFFFF   # (D+1, nE) facing before retarget
            cams = cam_table[x >> 4]                                                      # camera angle after retarget
            children = (cams[:, :, None] + CARD[None, None, :]) & 0xFFFF                  # (D+1, nE, 4)
            for d0, (c0, path) in items:
                nd = D - d0 + 1
                ch = children[:nd]
                tot = (d0 + ds_all[:nd])[:, None, None]
                keys = (ch * (D + 1) + tot).ravel()
                cost = np.broadcast_to(c0 + ABS_E[None, :, None], ch.shape).ravel()
                u, idx = np.unique(keys, return_index=True)       # first occurrence = fewest ESS (E_ARR is |e|-ordered)
                ang, td, uc = u // (D + 1), u % (D + 1), cost[idx]
                m = uc < best[ang, td]
                if not m.any():
                    continue
                ang, td, uc, idx = ang[m], td[m], uc[m], idx[m]
                best[ang, td] = uc
                di_arr, ei_arr, ki_arr = np.unravel_index(idx, ch.shape)
                for a, t, c, di, ei, ki in zip(ang.tolist(), td.tolist(), uc.tolist(),
                                               di_arr.tolist(), ei_arr.tolist(), ki_arr.tolist()):
                    face = int(ch[di, ei, ki])
                    step = ("seg", di, int(E_ARR[ei]), int(x[di, ei]), int(cams[di, ei]), CARDINALS[ki], face)
                    new_states[(a, t)] = (c, (path, step))

        best = np.minimum.accumulate(best, axis=1)
        frontier = {}
        for (a, t), (c, path) in new_states.items():
            if best[a, t] == c and (t == 0 or best[a, t - 1] > c):
                frontier[(a, t)] = (c, path)

    # ---- Pareto filter per goal, then build readable solutions ----
    solutions = []
    for g_i, goal in enumerate(goals):
        lowest = INF
        for t in range(D + 1):
            if (g_i, t) not in goal_path:
                continue
            c, path, (fd, fe) = goal_path[(g_i, t)]
            if c >= lowest:
                continue
            lowest = c
            steps = _unroll(path)
            start = steps[0]
            segs = steps[1:]
            solutions.append({
                "goal": goal, "ess": c, "deku": t, "retargets": len(segs),
                "start_angle": start[1], "start_label": start[2],
                "segments": segs, "final": (fd, fe),
            })
    return solutions


def format_solution(sol):
    lines = [f"Goal {_fmt(sol['goal'])} = {sol['goal']}: {sol['ess']} ESS turns total, "
             f"{sol['deku']} Deku spins total, {sol['retargets']} retarget(s)",
             f"    start at {_fmt(sol['start_angle'])} ({sol['start_label']})"]
    n = 1
    for (_, d, e, x, cam, card, face) in sol["segments"]:
        lines.append(f"    {n}) {_turns_text(d, e)} -> facing {_fmt(x)}; retarget -> camera angle {_fmt(cam)}; "
                     f"use cardinal {_fmt(cam)} + {_fmt(card)} = {_fmt(face)}")
        n += 1
    fd, fe = sol["final"]
    lines.append(f"    {n}) {_turns_text(fd, fe)} -> facing {_fmt(sol['goal'])} (goal)")
    return "\n".join(lines)


def write_solution_files(solutions, goal_angles, file_by_ess, file_by_deku, header=""):
    goals = sorted({int(g) for g in goal_angles})
    solved = {s["goal"] for s in solutions}
    unsolved = [g for g in goals if g not in solved]

    orderings = [
        (file_by_ess, "sorted by ESS turns, then Deku spins, then retargets",
         lambda s: (s["ess"], s["deku"], s["retargets"], s["goal"])),
        (file_by_deku, "sorted by Deku spins, then ESS turns, then retargets",
         lambda s: (s["deku"], s["ess"], s["retargets"], s["goal"])),
    ]
    for filename, title, key in orderings:
        with open(filename, "w") as f:
            f.write(f"# {title}\n")
            if header:
                f.write(header.rstrip() + "\n")
            f.write(f"# {len(solutions)} solutions for {len(solved)}/{len(goals)} goal angles "
                    f"(Pareto-optimal in ESS turns / Deku spins per goal angle)\n")
            if unsolved:
                f.write(f"# no solution found for: {', '.join(_fmt(g) for g in unsolved)}\n")
            f.write("\n")
            for sol in sorted(solutions, key=key):
                f.write(format_solution(sol) + "\n\n")


def find_solutions(initial_angle, goal_angles, max_deku_spins=10, max_retargets=2,
                   max_ess_before_retarget=200, initial_camera_angle=None,
                   file_by_ess="angle_solutions_by_ess.txt", file_by_deku="angle_solutions_by_deku.txt",
                   lookup=FacingAngleToUntargetedCameraAngleAfterTargeting):
    solutions = solve_angles(initial_angle, goal_angles, lookup,
                             initial_camera_angle=initial_camera_angle,
                             max_deku_spins=max_deku_spins, max_retargets=max_retargets,
                             max_ess_before_retarget=max_ess_before_retarget)
    header = (f"# initial angle {_fmt(initial_angle)}, max_deku_spins={max_deku_spins}, "
              f"max_retargets={max_retargets}, max_ess_before_retarget={max_ess_before_retarget}")
    write_solution_files(solutions, goal_angles, file_by_ess, file_by_deku, header)
    print(f"Done. {len(solutions)} solutions -> {file_by_ess}, {file_by_deku}")
    return solutions


if __name__ == "__main__":
    initial_angle = 0xD53
    # initial_camera_angle = None -> looked up from the cache. Set it (e.g. 0xD53) to override.
    initial_camera_angle = None

    bucket = 0xFEE0
    assert bucket % 0x10 == 0, f"{hex(bucket)=}"
    goal_angle_list = list(range(bucket, bucket + 0x10))

    find_solutions(initial_angle, goal_angle_list,
                   max_deku_spins=10, max_retargets=5, max_ess_before_retarget=200,
                   initial_camera_angle=initial_camera_angle)