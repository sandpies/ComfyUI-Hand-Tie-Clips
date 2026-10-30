"""Windowed hand-tie previs: one previs for a whole take, past PREVIS_MAX.

PREP ONLY (2026-10-30). Nothing imports this yet. The core half needs ComfyUI with
Comfy-Org/ComfyUI#17425 (MiniMax H3 context windows, merged 2026-10-30 as 6651247);
`available()` says whether this core has it.

Why. A hand-tie previs is one H3 generate, so it stops at PREVIS_MAX (362 frames, about
5 hops of 8 s) and a longer take is cut into CHAINED sections: section s is pinned on
section s-1's closing latent. That chain is where previs 3 snapped at f22 (Tokyo, 10-28)
and where section 2 drifted to a close-up (HMA, LD Studio). Core's context windows denoise
one latent in one trajectory, running the model on overlapping windows at every step and
fusing them, so a whole take can be ONE previs with no chain and no pin between previs.

The layout (`plan`). The film's previs keeps hand_tie's geometry unchanged: join window k
at W_k (hop k's head, hop k-1's tail), 68 previs frames per 8 s hop, closing window after
the last hop. Context window j covers hops j..j+per_window-1 and steps one hop:

    W0      W1      W2      W3      W4 (closing)
    |-hop0--|-hop1--|-hop2--|-hop3--|--|
    [ window 0      +22]
            [ window 1      +22]
                    [ window 2      +22]

* every join window W_k (0 < k < n) sits in the MIDDLE of window k-1, where the pyramid
  fuse weight peaks: it is drawn by the window that sees both hops it ties;
* every overlap is a whole hop that both windows describe with the same moment, so the
  fuse never averages two different prompts over a stretch of picture;
* every window starts on the 17-frame grid and is 17n+5 frames (5n+2 latents), so its
  first latent is a 1-frame token like any clip's: core's causal_window_fix stays off;
* no window is longer than PREVIS_MAX, so no forward is bigger than today's previs
  (hand_tie's cost rule: nothing bigger than one hop's generate per forward).

Each window gets its own text (`window_texts`): the film's ONE compiled previs text, cut to
the window and re-clocked from 00:00.000. A window that opens inside the previous beat's
range opens on `carry_text` for that 22-frame join window (as `chain_previs_text` does for
a chained section), not on a beat it would restart.

Only `anchor=restart` splits a take (a cut). `extend` and the PREVIS_MAX split go away.
A take that fits PREVIS_MAX gets one window: the caller renders it as today.

Not here yet (integration, after core is updated): encoding one conditioning per window,
the per-window sound pins (window_speaks / song_windows), and the hops reading their
windows out of the one previs.
"""

import re

try:
    from . import hand_tie as _ht
except ImportError:          # loaded standalone by tools/check_ht_windows.py
    import hand_tie as _ht

TAG = "HandTieClips"
PER_WINDOW = 2               # hops per context window


def frames_to_latents(frames):
    """H3's latent length for a clip of `frames` (core's video_latent_t)."""
    f = int(frames)
    return 2 if f <= 5 else ((f - 5) // _ht.GRID) * 5 + 2


def frame_to_latent(f):
    """Latent index of a frame on the 17-frame grid."""
    f = int(f)
    if f % _ht.GRID:
        raise ValueError("ht_windows: frame %d is off the %d-frame grid" % (f, _ht.GRID))
    return f // _ht.GRID * 5


def takes(shots):
    """[[hop index, ...], ...]: hop 0 and every anchor=restart open a take."""
    out = []
    for i, sh in enumerate(shots or []):
        if i == 0 or str((sh or {}).get("anchor") or "") == "restart":
            out.append([])
        out[-1].append(i)
    return out


def plan(hop_frames, per_window=PER_WINDOW):
    """The windowed previs of ONE take.

    -> {"joins": [W0..Wn], "spacings": [...], "previs": frames, "latents": n,
        "windowed": bool,
        "windows": [{"hops": [j, ..], "f0": int, "f1": int, "l0": int, "l1": int,
                     "joins": [local join starts]}, ...]}
    `windowed` is False when the take fits one generate (PREVIS_MAX): one window, the
    caller renders it as today.
    """
    hop_frames = [int(f) for f in (hop_frames or [])]
    if not hop_frames:
        raise ValueError("ht_windows: a take needs at least one hop")
    lay = _ht.layout(hop_frames, max_frames=10 ** 9)      # always with a closing window
    joins, total = list(lay["windows"]), int(lay["previs"])
    n = len(hop_frames)
    windowed = total > _ht.PREVIS_MAX and n > 1
    if not windowed:
        spans = [list(range(n))]
    else:
        m = max(1, int(per_window))
        # A window of m long hops can pass PREVIS_MAX: fewer hops per window, never fewer than 1.
        while m > 1 and any(joins[j + m] + _ht.WINDOW - joins[j] > _ht.PREVIS_MAX
                            for j in range(0, n - m + 1)):
            m -= 1
        if m == 1:
            raise ValueError("ht_windows: hops this long leave no room for two in one window; "
                             "a window must hold both hops a join window ties")
        spans = [list(range(j, j + m)) for j in range(0, n - m + 1)]
    windows = []
    for hops in spans:
        f0 = joins[hops[0]]
        f1 = joins[hops[-1] + 1] + _ht.WINDOW
        if f1 - f0 > _ht.PREVIS_MAX and windowed:
            raise ValueError("ht_windows: window over hops %s is %d frames, past PREVIS_MAX"
                             % (hops, f1 - f0))
        l0 = frame_to_latent(f0)
        windows.append({"hops": hops, "f0": f0, "f1": f1,
                        "l0": l0, "l1": l0 + frames_to_latents(f1 - f0),
                        "joins": [joins[k] - f0 for k in range(hops[0], hops[-1] + 2)]})
    return {"joins": joins, "spacings": list(lay["spacings"]), "previs": total,
            "latents": frames_to_latents(total), "windowed": windowed, "windows": windows}


# --- the text -------------------------------------------------------------------

_ROW = re.compile(r"At (\d\d):(\d\d\.\d{3})-(\d\d):(\d\d\.\d{3}), (.*?)(?=\s+At \d\d:\d\d\.\d{3}-|\s*$)",
                  re.S)


def _rows(text, fps):
    """compile_previs's text back to [(f0, f1, text)]."""
    out = []
    for m in _ROW.finditer(str(text or "")):
        a = int(round((int(m.group(1)) * 60 + float(m.group(2))) * fps))
        b = int(round((int(m.group(3)) * 60 + float(m.group(4))) * fps))
        out.append((a, b, m.group(5).strip()))
    return out


def window_texts(shots, hop_frames, pl, fps=_ht.FPS):
    """One previs text per window of `pl` (from `plan`), for one take's `shots`.

    The take's text is compiled ONCE over all its hops; each window gets the rows it
    covers, clipped and re-clocked to start at 00:00.000, with the take's framing
    sentence in front. A frame two windows share is described by the same beat in both.
    -> [str] per window, and [str] notes.
    """
    text, _lay = _ht.compile_previs(shots, hop_frames, fps, max_frames=10 ** 9)
    rows = _rows(text, fps)
    frame_sent, size = _ht.previs_framing(shots)
    out, notes = [], []
    for i, w in enumerate(pl["windows"]):
        f0, f1 = w["f0"], w["f1"]
        segs = []
        for a, b, t in rows:
            a2, b2 = max(a, f0), min(b, f1)
            if b2 <= a2:
                continue
            if a < f0:
                if _ht._spoken_s(t) > 0:
                    # A crossing line led in ahead of its window: this window says it from
                    # its first frame, the window before from the lead. Same words, later.
                    notes.append("window %d: a line starts %d frames before the window; "
                                 "it is spoken from the window's first frame" % (i + 1, f0 - a))
                else:
                    # Without the framing sentence: carry_text names everyone a moment
                    # tags, and the framing sentence tags the place as well.
                    t = _ht.carry_text(t.replace(frame_sent, "") if frame_sent else t, size)
            segs.append((a2 - f0, b2 - f0, t))
        body = " ".join("At %s-%s, %s" % (_ht._stamp(a / float(fps)), _ht._stamp(b / float(fps)), t)
                        for a, b, t in segs)
        out.append(_ht.with_framing(body, shots))
    return out, notes


# --- the core half (needs Comfy-Org/ComfyUI#17425) --------------------------------

def available():
    """True when this ComfyUI can window an H3 latent (core 6651247 or later)."""
    try:
        import comfy.model_base as mb
        import comfy.context_windows  # noqa: F401
    except Exception:
        return False
    h3 = getattr(mb, "MiniMaxH3", None)
    return h3 is not None and callable(getattr(h3, "map_context_window_to_modalities", None))


def make_handler(pl, fuse="pyramid", freenoise=False):
    """A context handler that runs exactly `pl`'s windows and gives window i the i-th
    entry of the positive conditioning list (one encoded `window_texts` entry each).

    Core's own split_conds_to_windows picks a cond by the window's centre over equal
    slices of the clip (IndexListContextWindow.get_region_index), which does not follow
    hop lengths; here the window -> cond map is the plan's.
    """
    import comfy.context_windows as cw

    wins = [list(range(w["l0"], w["l1"])) for w in pl["windows"]]
    total = int(pl["latents"])
    by_start = {lst[0]: i for i, lst in enumerate(wins)}
    overlaps = [0] + [max(0, wins[i - 1][-1] + 1 - wins[i][0]) for i in range(1, len(wins))]

    class _HopWindows(cw.IndexListContextHandler):
        def get_context_windows(self, model, x_in, model_options):
            full = x_in.size(self.dim)
            if full != total:
                raise RuntimeError("[%s] hand-tie windows: the previs latent is %d long, "
                                   "the plan is %d" % (TAG, full, total))
            return [cw.IndexListContextWindow(lst, dim=self.dim, total_frames=full,
                                              context_overlap=ov)
                    for lst, ov in zip(wins, overlaps)]

        def get_resized_cond(self, cond_in, x_in, window, device=None):
            if cond_in is not None and len(cond_in) == len(wins):
                cond_in = [cond_in[by_start[window.index_list[0]]]]
            return super().get_resized_cond(cond_in, x_in, window, device)

    return _HopWindows(
        context_schedule=cw.get_matching_context_schedule(cw.ContextSchedules.STATIC_STANDARD),
        fuse_method=cw.get_matching_fuse_method(fuse),
        context_length=max(len(lst) for lst in wins),
        context_overlap=max(overlaps), dim=2, freenoise=bool(freenoise),
        causal_window_fix=False)


def install(model, pl, fuse="pyramid", freenoise=False):
    """A clone of `model` that samples the previs latent in `pl`'s windows. The clone
    keeps the user's model untouched. Pass the windows' conditionings as ONE positive
    list, in window order (each a one-entry list from its own text encode, added up)."""
    import comfy.context_windows as cw

    if not available():
        raise RuntimeError("[%s] hand-tie windows need ComfyUI with MiniMax H3 context "
                           "windows (Comfy-Org/ComfyUI#17425)" % TAG)
    m = model.clone()
    m.model_options["context_handler"] = make_handler(pl, fuse, freenoise)
    cw.create_prepare_sampling_wrapper(m)        # VRAM estimate per window, not per film
    if freenoise:
        cw.create_sampler_sample_wrapper(m)      # without it freenoise=True does nothing
    return m
