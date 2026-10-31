"""Windowed take (pin_mech=windowed): a take is ONE H3 latent, its hops are context windows.

No hop is pinned on another hop's output, so nothing is handed down a chain: every window
is denoised together with its neighbours at every step (ComfyUI's H3 context windows,
Comfy-Org/ComfyUI#17425) and they agree over the overlap. Picture and sound are both in
the one latent. Hop k's window is exactly the hop's own frames, so the per-step work is
the same as a motion_context chain; a take splits only at anchor=restart.

A retake re-draws only the hops whose text/seed/refs changed: their windows are cut out of
the stored take latent with the neighbouring overlaps held (noise_mask 0), sampled, and put
back. Pure geometry here; the sampling lives in h3_ref_chain.
"""
import hashlib
import json

GRID = 17          # frames per H3 latent block
AUDIO_HZ = 40      # audio latent steps per second
FPS = 24


def f2l(frames):
    """Latent length of a clip of `frames` frames (core video_latent_t)."""
    f = int(frames)
    return 2 if f <= 5 else ((f - 5) // GRID) * 5 + 2


def a_index(frame):
    """Audio latent index of a frame (core temporal_shape: round(seconds * 40))."""
    return int(round(int(frame) / float(FPS) * AUDIO_HZ))


def takes(shots):
    """[[hop index, ...], ...]: hop 0 and every anchor=restart open a take."""
    out = []
    for i, sh in enumerate(shots or []):
        if i == 0 or str((sh or {}).get("anchor") or "") == "restart":
            out.append([])
        out[-1].append(i)
    return out


def plan(hop_lens, overlap):
    """Windows of one take. Every hop is 17n+5 frames and every stride (hop - overlap)
    a whole number of 17-frame blocks, so every window starts on the grid and its first
    latent is a clip-start token. -> {"frames", "latents", "audio", "windows": [{"f0", "f1",
    "l0", "l1", "a0", "a1"}]}. Raises ValueError with the reason otherwise."""
    lens = [int(x) for x in hop_lens]
    ov = int(overlap)
    if not lens:
        raise ValueError("a windowed take needs at least one hop")
    for k, n in enumerate(lens):
        if n % GRID != 5:
            raise ValueError(f"hop {k + 1} is {n} frames; windowed hops must be 17n+5")
    starts = [0]
    for k, n in enumerate(lens[:-1]):
        stride = n - ov
        if stride <= 0 or stride % GRID:
            raise ValueError(f"hop {k + 1}: {n} frames minus the {ov}-frame overlap is {stride}, "
                             f"not a multiple of {GRID}; windows would leave the latent grid")
        starts.append(starts[-1] + stride)
    total = starts[-1] + lens[-1]
    wins = []
    for f0, n in zip(starts, lens):
        l0 = f0 // GRID * 5
        wins.append({"f0": f0, "f1": f0 + n, "l0": l0, "l1": l0 + f2l(n),
                     "a0": a_index(f0), "a1": a_index(f0 + n)})
    return {"frames": total, "latents": f2l(total), "audio": a_index(total), "windows": wins}


def digest(block, seed, steps, length, refs):
    """What makes a hop's window what it is: its text, seed, steps, length and the digests
    of its reference pictures. A retake changes one of these."""
    payload = {"block": str(block), "seed": int(seed), "steps": int(steps),
               "len": int(length), "refs": dict(sorted((refs or {}).items()))}
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()[:24]


def take_key(salt, digs):
    """The stored take's key: the chain salt (model, size, sampler...) + every hop's digest."""
    payload = {"windowed_take": 2, "salt": salt, "hops": list(digs)}   # 2 = in-order layout
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode("utf-8")).hexdigest()[:24]


def changed_runs(old, new):
    """Contiguous runs [a, b] of hops whose digest changed. None when the hop count differs
    (a different take: render it whole)."""
    if old is None or len(old) != len(new):
        return None
    runs, a = [], None
    for k, (o, n) in enumerate(zip(old, new)):
        if o != n and a is None:
            a = k
        if o == n and a is not None:
            runs.append((a, k - 1))
            a = None
    if a is not None:
        runs.append((a, len(new) - 1))
    return runs


def sub_plan(pl, a, b, overlap):
    """The part of a take a retake of hops a..b re-draws: windows a..b re-based to 0, and
    the latent/audio ranges held from the neighbours (the overlap shared with hop a-1 and
    with hop b+1). -> {"l0", "l1", "a0", "a1", "plan", "hold_v": [(l0, l1)], "hold_a": [...]}
    in sub-take coordinates."""
    w = pl["windows"]
    L0, L1, A0, A1 = w[a]["l0"], w[b]["l1"], w[a]["a0"], w[b]["a1"]
    F0 = w[a]["f0"]
    sub = {"frames": w[b]["f1"] - F0, "latents": L1 - L0, "audio": A1 - A0,
           "windows": [{"f0": x["f0"] - F0, "f1": x["f1"] - F0, "l0": x["l0"] - L0,
                        "l1": x["l1"] - L0, "a0": x["a0"] - A0, "a1": x["a1"] - A0}
                       for x in w[a:b + 1]]}
    hold_v, hold_a = [], []
    ov_l, ov_a = f2l(overlap), a_index(overlap)
    if a > 0:
        hold_v.append((0, ov_l))
        hold_a.append((0, ov_a))
    if b < len(w) - 1:
        hold_v.append((L1 - L0 - ov_l, L1 - L0))
        hold_a.append((A1 - A0 - ov_a, A1 - A0))
    return {"l0": L0, "l1": L1, "a0": A0, "a1": A1, "plan": sub,
            "hold_v": hold_v, "hold_a": hold_a}
