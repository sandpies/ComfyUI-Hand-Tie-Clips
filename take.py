"""Take = shot: one prompt layout for every window of a sand_tie take (2026-11-01).

A take is one continuous shot (pin_mech=sand_tie: one latent, its hops are context
windows). Two layers per window:

- SHOT layer, the same words in every window of the take: the take's first beat's lead
  (its untimed opening sentences: framing, place, camera) and its directives. Nothing
  tells a window it is a new shot.
- ACTION layer, on the TAKE's clock: every timed sentence ("At 00:02.000-00:06.000,
  ...") of every beat is placed on one timeline. The overlap between two windows is the
  same frames, so it is described ONCE: it belongs to the earlier beat (whose window
  draws it; the next window holds it). Each window gets its slice, re-clocked to the
  window.

Pure Python; no torch, no ComfyUI.
"""
import copy
import re

WINDOW_TAIL = "window"   # a tail value with no sentence in directives.VOCAB

_TIMED = re.compile(
    r"\bAt\s+(\d+):(\d+(?:\.\d+)?)\s*[-–]\s*(\d+):(\d+(?:\.\d+)?)\s*,\s*")


def parse_beat(text):
    """-> (lead, [(t0, t1, sentence)]) or None when the beat carries no timed sentence."""
    text = str(text or "").strip()
    ms = list(_TIMED.finditer(text))
    if not ms:
        return None
    lead = text[:ms[0].start()].strip()
    events = []
    for k, m in enumerate(ms):
        end = ms[k + 1].start() if k + 1 < len(ms) else len(text)
        t0 = int(m.group(1)) * 60 + float(m.group(2))
        t1 = int(m.group(3)) * 60 + float(m.group(4))
        body = text[m.end():end].strip()
        if body and t1 > t0:
            events.append((t0, t1, body))
    return lead, events


def _clock(t):
    t = max(0.0, float(t))
    return f"{int(t // 60):02d}:{t - 60 * int(t // 60):06.3f}"


def _render(lead, events):
    parts = [lead.strip()] if lead.strip() else []
    for t0, t1, body in events:
        parts.append(f"At {_clock(t0)}-{_clock(t1)}, {body}")
    return " ".join(parts)


def takes(shots):
    """Hop indices per take; a take starts at hop 0 and at every anchor=restart."""
    out = []
    for i, s in enumerate(shots):
        if i == 0 or str((s or {}).get("anchor") or "") == "restart" or not out:
            out.append([])
        out[-1].append(i)
    return out


def compile_take(shots, hop_frames, overlap_frames, fps=24, log=None):
    """Rewrite every hop's beat as its window of the take. -> new list of shots.

    A take whose beats are not all timed is left as written (logged): there is no
    clock to put them on. Hop k's window covers its own frames; window k starts
    (len_{k-1} - overlap) frames after window k-1.
    """
    say = log or (lambda _m: None)
    out = [copy.deepcopy(s) for s in shots]
    ov = float(overlap_frames) / float(fps)
    for idx in takes(shots):
        parsed = [parse_beat((shots[i] or {}).get("beat")) for i in idx]
        if any(p is None for p in parsed):
            bad = [idx[j] + 1 for j, p in enumerate(parsed) if p is None]
            say(f"take hop(s) {idx[0] + 1}-{idx[-1] + 1}: hop(s) {bad} have no 'At mm:ss-mm:ss,' "
                "timing, so the take keeps each hop's own beat")
            continue
        lead0 = parsed[0][0]
        dirs0 = dict((shots[idx[0]] or {}).get("directives") or {})
        starts, s = [], 0.0
        for j, i in enumerate(idx):
            starts.append(s)
            s += float(hop_frames[i]) / float(fps) - ov
        # one timeline: hop j owns its local time from its head's end (0 for the first)
        line = []
        for j, i in enumerate(idx):
            if parsed[j][0] and parsed[j][0] != lead0:
                say(f"hop {i + 1}: its lead differs from the take's ('{parsed[j][0][:60]}'); a take "
                    "is one shot, so it uses hop "
                    f"{idx[0] + 1}'s. Write a framing/place change as a cut (anchor = restart)")
            own0 = ov if j > 0 else 0.0
            for t0, t1, body in parsed[j][1]:
                a, b = max(t0, own0), t1
                if b - a > 1e-6:
                    line.append((starts[j] + a, starts[j] + b, body))
        line.sort(key=lambda e: e[0])
        for j, i in enumerate(idx):
            w0 = starts[j]
            w1 = w0 + float(hop_frames[i]) / float(fps)
            ev = []
            for t0, t1, body in line:
                a, b = max(t0, w0), min(t1, w1)
                if b - a > 1e-6:
                    if ev and ev[-1][2] == body and abs(ev[-1][1] - (a - w0)) < 1e-3:
                        ev[-1] = (ev[-1][0], b - w0, body)   # same moment across the seam
                    else:
                        ev.append((a - w0, b - w0, body))
            sh = out[i] if out[i] is not None else {}
            sh["beat"] = _render(lead0, ev)
            d = dict(dirs0)
            tail = ((shots[i] or {}).get("directives") or {}).get("tail")
            if j + 1 < len(idx):
                # a window's end is mid-take: no closing sentence ("still underway as the
                # clip ends" made every window invent action after its calm edge). Its own
                # timeline says how it ends. Only the take's last window keeps its tail.
                d["tail"] = WINDOW_TAIL
            elif tail is not None:
                d["tail"] = tail
            d.pop("join", None)
            sh["directives"] = d
            out[i] = sh
        say(f"take hop(s) {idx[0] + 1}-{idx[-1] + 1}: one shot, {len(line)} timed moment(s) on the "
            f"take clock, overlaps described once")
    return out
