"""Fit hop lengths so every cut lands on a downbeat.

    python fit_cuts.py songmap.json --kinds R,C,C,R,R,R,C,R,C \
        --cuts 8.75:2 20.92 28.44:1 39.72 52.88 64.16:1 73.56 79.2:1 \
        --end 87.0-89.2

--kinds   one letter per hop: R = start or restart (its whole length plays),
          C = continuation (its first overlap frames are the previous hop's and
          are dropped, so it delivers `frames - 22`). Hop 1 is always R.
--cuts    the song time where each hop after hop 1 should start (one fewer than
          the hops). Each is snapped to the nearest downbeat; `t:N` lets the cut
          land up to N bars either side (use it inside a section, never at the
          start of a hook).
--end     the window the last hop must end in (usually just after the last sound).

Prints the best arrangements: hop lengths, `master_audio_start_s`, the song time
each cut lands on and its error in frames. Under ~8 frames reads as on the beat.
Hop lengths come from the pack (mv_solver.DURATION_FRAMES), so they always match
the node's duration widget.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _htc  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("songmap")
    ap.add_argument("--kinds", required=True)
    ap.add_argument("--cuts", nargs="+", required=True)
    ap.add_argument("--end", required=True, help="e.g. 112.5-117.5")
    ap.add_argument("--min-s", type=int, default=5)
    ap.add_argument("--max-s", type=int, default=15)
    ap.add_argument("--min-continuation-s", type=int, default=6)
    ap.add_argument("--tol", type=float, default=8.0, help="max cut error in frames")
    ap.add_argument("--max-offset", type=float, default=0.5)
    ap.add_argument("--top", type=int, default=5)
    ap.add_argument("--htc")
    a = ap.parse_args()

    pack = _htc.find_pack(a.htc)
    ms = _htc.import_pure(pack, "mv_solver")
    D, OV, FPS = ms.DURATION_FRAMES, ms.OVERLAP_FRAMES, ms.FPS

    m = json.loads(Path(a.songmap).read_text(encoding="utf-8"))
    db = [float(x) for x in m["downbeats"]]
    kinds = [k.strip().upper() for k in a.kinds.split(",")]
    if kinds[0] != "R":
        sys.exit("hop 1 must be R")
    if len(a.cuts) != len(kinds) - 1:
        sys.exit(f"{len(kinds)} hops need {len(kinds) - 1} cuts, got {len(a.cuts)}")

    def window(spec):
        t, _, k = spec.partition(":")
        i = min(range(len(db)), key=lambda j: abs(db[j] - float(t)))
        k = int(k or 0)
        return db[max(0, i - k):i + k + 1]

    targets = [window(c) for c in a.cuts]
    end_lo, end_hi = (float(x) for x in a.end.split("-"))
    labels = [lab for lab in D if a.min_s <= int(lab.split()[0]) <= a.max_s]
    res = []

    steps = int(round(a.max_offset / 0.01))
    for o in range(steps + 1):
        off = o / 100.0

        def rec(i, pos, plan, err):
            for lab in labels:
                if kinds[i] == "C" and int(lab.split()[0]) < a.min_continuation_s:
                    continue
                n = D[lab]
                b = pos + (n if kinds[i] == "R" else n - OV)
                s = b / FPS + off
                if i < len(targets):
                    e = min(abs(s - t) for t in targets[i]) * FPS
                    if e > a.tol or max(err, e) > (res[a.top - 1][0] if len(res) >= a.top else 1e9):
                        continue
                    rec(i + 1, b, plan + [(lab, pos / FPS + off, s, e)], max(err, e))
                elif end_lo <= s <= end_hi:
                    res.append((round(err, 2), off, plan + [(lab, pos / FPS + off, s, None)]))
                    res.sort(key=lambda r: r[0])
                    del res[a.top * 4:]

        rec(0, 0, [], 0.0)

    if not res:
        sys.exit("No arrangement fits. Widen --tol, add :N flex to cuts inside sections, "
                 "change a kind, or widen --end.")
    seen = set()
    shown = 0
    for err, off, plan in res:
        key = tuple(p[0] for p in plan) + (off,)
        if key in seen:
            continue
        seen.add(key)
        print(f"\nworst cut {err:.1f} f   master_audio_start_s = {off:.2f}")
        for n, (lab, a_s, b_s, e) in enumerate(plan, 1):
            tail = "" if e is None else f"  cut err {e:.1f} f"
            print(f"  hop {n:2d} {kinds[n - 1]} {lab:>5}  song {a_s:7.2f} -> {b_s:7.2f}{tail}")
        shown += 1
        if shown >= a.top:
            break


if __name__ == "__main__":
    main()
