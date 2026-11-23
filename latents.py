"""Reading and rebuilding H3 sampler latents, without importing ComfyUI.

Split out of `h3_ref_chain.py` so `tools/texture_probe.py` can measure a cached
latent -- the same reason `plan.py`, `refs.py` and `tone.py` carry no ComfyUI
imports. The node file cannot be imported without a running server, and an
instrument that has to guess at the container it is measuring is not an
instrument.

The guessing is the point. H3 hands back a `comfy.nested_tensor.NestedTensor`
-- the video and audio latents in one object -- and it is not a Tensor. It has
no `.std()`, and the attributes it *does* expose are traps: `.shape` returns
`tensors[0].shape`, i.e. the video component's shape while silently speaking
for both. A caller that trusts `.shape` sizes its work to the video and
broadcasts that onto the audio, and nothing raises. Reading the components is
the only honest way to touch the numbers.
"""
from __future__ import annotations

import torch


def parts(x):
    """The component tensors inside a sampler `samples`, as a flat list.

    Returns None for anything unrecognised, which callers treat as "leave this
    latent alone" -- never a silently-wrong single-component guess.
    """
    if isinstance(x, torch.Tensor):
        return [x]
    if getattr(x, "is_nested", False) and hasattr(x, "unbind"):
        got = list(x.unbind())
        if got and all(isinstance(t, torch.Tensor) for t in got):
            return got
    return None


def rebuild(x, new_parts):
    """Put conditioned components back into the container they came from."""
    if isinstance(x, torch.Tensor):
        return new_parts[0]
    return type(x)(new_parts)


def from_dict(lat):
    """`parts()` of a `{"samples": ...}` latent dict. -> list or None."""
    if not isinstance(lat, dict) or "samples" not in lat:
        return None
    return parts(lat["samples"])


def _gauss1d(sigma, device, dtype):
    r = max(1, int(round(3.0 * float(sigma))))
    x = torch.arange(-r, r + 1, dtype=torch.float32, device=device)
    k = torch.exp(-(x * x) / (2.0 * float(sigma) ** 2))
    return (k / k.sum()).to(dtype)


def band_split(t, sigma=2.0):
    """Separable Gaussian low/high split over the last two dims. -> (lo, hi).

    Returns None when the tensor has no spatial extent to speak of -- an audio
    component is a different object and blurring across it means nothing.

    Replicate padding, not reflect: a latent's spatial dims are small (a
    736x1280 frame is 46x80 here) and reflect needs the pad to be smaller than
    the dimension, which stops being true for a large sigma on a small latent.
    """
    if t.dim() < 2 or t.shape[-1] < 8 or t.shape[-2] < 8:
        return None
    import torch.nn.functional as F  # noqa: PLC0415
    h, w = int(t.shape[-2]), int(t.shape[-1])
    flat = t.reshape(-1, 1, h, w)
    k = _gauss1d(sigma, t.device, t.dtype)
    pad = k.numel() // 2
    lo = F.conv2d(F.pad(flat, (pad, pad, 0, 0), mode="replicate"),
                  k.view(1, 1, 1, -1))
    lo = F.conv2d(F.pad(lo, (0, 0, pad, pad), mode="replicate"),
                  k.view(1, 1, -1, 1))
    lo = lo.reshape(t.shape)
    return lo, t - lo


def band_ratio(t, sigma=2.0):
    """High-band sigma as a fraction of total sigma. -> float, or None.

    This is the statistic the texture ratchet actually moves. Measured across a
    3-hop chain it went 0.3643 -> 0.3673 -> 0.3702, monotone, while the total
    sigma it is normalised by FELL 1.2% -- which is why matching total sigma
    cannot see this and, worse, corrects the wrong way.
    """
    got = band_split(t, sigma)
    if got is None:
        return None
    tot = float(t.float().std())
    if not tot or tot != tot:
        return None
    return float(got[1].float().std()) / tot


def match_band(t, target_ratio, sigma=2.0, clamp=(0.5, 2.0)):
    """Rescale t's high band so its high-band fraction becomes `target_ratio`.

    -> (tensor, k), or (t, None) when the tensor has no bands to match.

    Only the high half is scaled, so the low-frequency structure that carries
    the scene is bit-identical and the correction is one scalar. It cannot blur,
    sharpen unevenly, or invent detail; the worst it can do is get the gain
    wrong, which is why `clamp` exists.

    Note the fraction is against the tensor's own sigma, so restoring the ratio
    does move total sigma a little. That is deliberate: the ratio is the drifting
    statistic and sigma is the one that lies.
    """
    got = band_split(t, sigma)
    if got is None or not target_ratio:
        return t, None
    lo, hi = got
    cur_hi = float(hi.float().std())
    if not cur_hi or cur_hi != cur_hi:
        return t, None

    # The naive `k = target * sigma / hi_sigma` is wrong, and quietly so:
    # scaling the high band changes the sigma it is a fraction OF, so the
    # target moves as you apply it. Measured, it undershot by 5% on a
    # latent-shaped tensor -- a correction that silently does most, but not
    # all, of its job is the worst kind to ship.
    #
    # First guess solves the fixed point assuming lo and hi are orthogonal:
    # k*H / sqrt(L^2 + k^2*H^2) = r, so k = r*L / (H*sqrt(1 - r^2)) ...
    r = min(float(target_ratio), 0.999)
    lo_sd = float(lo.float().std())
    k = (r * lo_sd) / (cur_hi * max(1e-6, (1.0 - r * r) ** 0.5))
    # ... then refine against the statistic as actually measured, because a
    # difference of Gaussians is not an exact orthogonal projection. Two or
    # three passes converge, and a latent is small enough that this is free.
    for _ in range(4):
        k = min(max(k, clamp[0]), clamp[1])
        got_r = band_ratio(lo + hi * k, sigma)
        if not got_r:
            break
        if abs(got_r - r) <= 1e-4 * max(r, 1e-6):
            break
        k *= r / got_r
    k = min(max(k, clamp[0]), clamp[1])
    return lo + hi * k, k


def motion_overload_score(video_latent, warn_ratio=2.4):
    """Lightweight temporal jitter / overload metric over an H3 video latent.

    Accepts a `[B,C,T,H,W]` tensor, `NestedTensor`, or `{"samples": ...}` dict.
    Measures peak-to-median frame-step velocity (`spike_ratio`) and second-order
    acceleration relative to spatial variance (`accel_index`). -> dict or None.
    """
    v = None
    if isinstance(video_latent, dict):
        ps = from_dict(video_latent)
        v = ps[0] if ps else None
    elif isinstance(video_latent, torch.Tensor):
        v = video_latent
    else:
        ps = parts(video_latent)
        v = ps[0] if ps else None
    if v is None or not isinstance(v, torch.Tensor) or v.ndim != 5 or int(v.shape[2]) < 4:
        return None
    vf = v.detach().float()
    dv = vf[:, :, 1:] - vf[:, :, :-1]
    step_rms = dv.pow(2).mean(dim=(0, 1, 3, 4)).sqrt()
    med = float(step_rms.median())
    peak_val, peak_idx = step_rms.max(dim=0)
    spike_ratio = float(peak_val) / max(med, 1e-6)
    ddv = dv[:, :, 1:] - dv[:, :, :-1]
    base_sd = float(vf.std())
    accel_index = float(ddv.pow(2).mean().sqrt()) / max(base_sd, 1e-6)
    score = min(1.0, max(0.0, 0.45 * max(0.0, spike_ratio - 1.0) / 2.0 + 0.55 * max(0.0, accel_index - 0.35) / 0.85))
    overloaded = bool(spike_ratio >= float(warn_ratio) or accel_index >= 0.85)
    status = "overload" if overloaded else ("elevated" if score >= 0.45 else "smooth")
    note = (
        f"motion {status} (score {score:.2f}, spike {spike_ratio:.2f}x at step {int(peak_idx) + 1}, "
        f"accel {accel_index:.2f})"
    )
    return {
        "score": round(score, 3),
        "spike_ratio": round(spike_ratio, 2),
        "accel_index": round(accel_index, 3),
        "peak_step": int(peak_idx) + 1,
        "overloaded": overloaded,
        "status": status,
        "note": note,
    }


# --- carry anchor (tone_compensate = "anchor+carry", 11-22) -----------------
# The pixel anchor (tone.anchor_pull) repaints each hop's decoded frames, but a
# motion_context continuation is pinned from the previous hop's SAMPLER latent,
# so the drift that anchor removed from the master still feeds the next hop.
# This pulls the carried latent itself back to the scene's first hop: per video
# channel, the mean all the way and the spread within CARRY_STD_CLAMP. Only the
# global level per channel moves; frame-to-frame content is untouched. The idea
# (anchor the carry, not the output, to a source no drift has touched) was
# measured independently by two community packs; this is HTC's own code.
CARRY_STRENGTH = 1.0
CARRY_MATCH_STD = True
CARRY_STD_CLAMP = (0.85, 1.18)   # the sand_tie tone_lock clamp (walk_night_mv_00004)


def _video_5d(lat):
    """(parts, index of the 5-D video part) of a latent dict, or (None, None)."""
    ps = from_dict(lat)
    if not ps:
        return None, None
    return (ps, 0) if ps[0].ndim in (4, 5) else (None, None)


def channel_stats(lat):
    """Per-channel (mean [C], std [C]) of a latent dict's video part, float32 CPU. -> tuple or None."""
    ps, k = _video_5d(lat)
    if ps is None or k is None:
        return None
    v = ps[k]
    v = (v.unsqueeze(0) if v.ndim == 4 else v).float()
    dims = (0, 2, 3, 4)
    return (v.mean(dim=dims).cpu(), v.std(dim=dims).clamp_min(1e-6).cpu())


def carry_pull(lat, ref, strength=None, match_std=None, std_clamp=None):
    """`lat` (a sampler latent dict) with its video part pulled toward `ref` =
    channel_stats() of the scene's first hop. The audio part is never touched.
    -> (new dict, note) ; (lat, None) when nothing could be done."""
    k_s = CARRY_STRENGTH if strength is None else float(strength)
    m_std = CARRY_MATCH_STD if match_std is None else bool(match_std)
    lo, hi = CARRY_STD_CLAMP if std_clamp is None else std_clamp
    ps, k = _video_5d(lat)
    if ps is None or k is None or ref is None or k_s <= 0.0:
        return lat, None
    v0 = ps[k]
    v = (v0.unsqueeze(0) if v0.ndim == 4 else v0).float()
    m0, s0 = (t.to(v.device).float() for t in ref)
    if m0.numel() != v.shape[1]:
        return lat, None
    dims = (0, 2, 3, 4)
    m = v.mean(dim=dims)
    s = v.std(dim=dims).clamp_min(1e-6)
    gain = (s0 / s).clamp(lo, hi) if m_std else torch.ones_like(s)
    shp = (1, -1, 1, 1, 1)
    target = (v - m.view(shp)) * gain.view(shp) + m0.view(shp)
    out = v + k_s * (target - v)
    out = (out.squeeze(0) if v0.ndim == 4 else out).to(dtype=v0.dtype, device=v0.device)
    new_parts = list(ps)
    new_parts[k] = out
    new = dict(lat)
    new["samples"] = rebuild(lat["samples"], new_parts)
    shift = float(((m - m0).abs() / s0.clamp_min(1e-6)).mean())
    note = (f"carry pulled to the scene's first hop (mean gap {shift:.3f} sd"
            + (f", spread x{float(gain.min()):.2f}-{float(gain.max()):.2f}" if m_std else "")
            + f", strength {k_s:g})")
    return new, note
