"""Where a run's time goes: one summary in the console at the end of each run.

Nothing in the chain measured itself, so "why is this run slow" was a guess.
The obvious suspect for a single, simple generation is not sampling but the
swap around it -- Qwen3-VL 32B and the 33B DiT cannot both sit on a 32 GB card,
so a run that changed its prompt loads one, evicts it, loads the other -- and a
guess about that is cheap to settle with a clock.

What it records, all wall clock:

  * `stage(label)` blocks, opened at the chain's choke points (`_core_call`, the
    offloads, the reference prewarm, the VAE decodes). Inclusive: a stage that
    triggers a model load counts that load too.
  * every `comfy.model_management.load_models_gpu` call made by the run's own
    thread, labelled by model class. That is the swap, measured on its own.

`other` is the run's total minus its outermost stages: saving, previews, glue.

It is inert outside a run. The load hook is installed for the run and removed
after it, and only records calls from the thread that started the run, so a
route that loads something meanwhile is neither timed nor slowed. CUDA is
synchronised at stage edges, or an async kernel would be billed to whatever
stage happened to block on it next.
"""

from __future__ import annotations

import functools
import threading
import time
from contextlib import contextmanager

_state = threading.local()
MIN_SHOWN_S = 0.1   # rows faster than this are folded into `other`


def _sync():
    try:
        import torch  # noqa: PLC0415
        if torch.cuda.is_available():
            torch.cuda.synchronize()
    except Exception:  # noqa: BLE001 -- timing must never break a run
        pass


def _rec():
    return getattr(_state, "rec", None)


@contextmanager
def stage(label):
    """Time a block into the current run. A no-op when no run is being timed."""
    rec = _rec()
    if rec is None:
        yield
        return
    _sync()
    top = rec["depth"] == 0
    rec["depth"] += 1
    t0 = time.perf_counter()
    try:
        yield
    finally:
        _sync()
        dt = time.perf_counter() - t0
        rec["depth"] -= 1
        book = rec["loads"] if label.startswith("load ") else rec["stages"]
        tot, n = book.get(label, (0.0, 0))
        book[label] = (tot + dt, n + 1)
        if top:
            rec["top"] += dt


def timed(label):
    """Decorator form of `stage`."""
    def deco(fn):
        @functools.wraps(fn)
        def inner(*a, **kw):
            with stage(label):
                return fn(*a, **kw)
        return inner
    return deco


def _model_name(m):
    inner = getattr(m, "model", m)
    return type(inner).__name__


def _hook_loads():
    """Wrap `load_models_gpu` for this run. -> undo function."""
    try:
        import comfy.model_management as mm  # noqa: PLC0415
    except Exception:  # noqa: BLE001
        return lambda: None
    orig = mm.load_models_gpu
    owner = threading.get_ident()

    @functools.wraps(orig)
    def timed_load(models, *a, **kw):
        if threading.get_ident() != owner or _rec() is None:
            return orig(models, *a, **kw)
        try:
            names = "+".join(sorted({_model_name(m) for m in models})) or "?"
        except Exception:  # noqa: BLE001
            names = "?"
        with stage(f"load {names}"):
            return orig(models, *a, **kw)

    mm.load_models_gpu = timed_load

    def undo():
        # Only put ours back if nobody wrapped it after us.
        if mm.load_models_gpu is timed_load:
            mm.load_models_gpu = orig
    return undo


def _fmt(rows, total):
    out = []
    for label, (s, n) in sorted(rows.items(), key=lambda kv: -kv[1][0]):
        if s < MIN_SHOWN_S:
            continue
        pct = 100.0 * s / total if total > 0 else 0.0
        out.append(f"  {s:8.1f} s {pct:5.1f}%  {label}" + (f"  (x{n})" if n > 1 else ""))
    return out


def summary(rec, total, tag, status):
    lines = [f"[{tag}] timing: {total:.1f} s total{status}"]
    lines += _fmt(rec["stages"], total)
    other = max(0.0, total - rec["top"])
    lines.append(f"  {other:8.1f} s {100.0 * other / total if total > 0 else 0.0:5.1f}%  "
                 "other (saving, previews, glue)")
    if rec["loads"]:
        ls = sum(s for s, _n in rec["loads"].values())
        lines.append(f"  model loads/swaps, {ls:.1f} s, already inside the stages above:")
        lines += _fmt(rec["loads"], total)
    return "\n".join(lines)


def timed_run(fn, tag):
    """Wrap a node's FUNCTION so each call prints where its time went.

    A nested call (a run inside a run) is timed by the outer one only.
    """
    @functools.wraps(fn)
    def inner(*a, **kw):
        if _rec() is not None:
            return fn(*a, **kw)
        _state.rec = {"stages": {}, "loads": {}, "depth": 0, "top": 0.0}
        undo = _hook_loads()
        t0 = time.perf_counter()
        status = " (failed or cancelled)"
        try:
            out = fn(*a, **kw)
            status = ""
            return out
        finally:
            total = time.perf_counter() - t0
            rec, _state.rec = _state.rec, None
            undo()
            try:
                print(summary(rec, total, tag, status), flush=True)
            except Exception:  # noqa: BLE001
                pass
    return inner
