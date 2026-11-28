"""Finish-stage post pass: kinetic text and pixel fx burned onto a rendered film (references/post.md).

  python post.py measure film.mp4 [--ref other_render.mp4]   cuts, kicks, tempo; --ref = audio offset
  python post.py cues plan.json                              -> cues.json next to it, with the drop log
  python post.py burn cues.json START END                    -> post_START_END.mp4 next to cues.json

Text styles: telop (sticker, placed off people and faces), glitch (split slices, dark worlds only),
orbit (a ring of letters round the singer's neck, the back half tucked behind her).
Pixel fx kinds: kaleidoscope, freeze card, rgb hits, bass shake, punch zoom, colour isolation,
light trails, light leak. Each runs only inside its own window.

Needs ffmpeg with libass on PATH, numpy and opencv. Optional: rembg (people mattes: placement off
bodies, orbit tuck, colour isolation) and a YuNet face model (--yunet, or found under
<ComfyUI>/models/facedetection). Without them the pass still runs and says what it skipped.
Run it with the ComfyUI venv python when rembg lives there. CPU only; budget ~10x real time at
48 fps where a matte is needed, much less elsewhere.
"""
from __future__ import annotations

import json
import math
import re
import subprocess
import sys
from pathlib import Path

import numpy as np

try:
    import cv2
except ImportError:  # pragma: no cover
    sys.exit("post.py needs opencv (pip install opencv-python), e.g. the ComfyUI venv python.")

FONTS = {"telop": "Mochiy Pop One", "glitch": "Rubik Glitch", "orbit": "Bungee", "orbit_jp": "Dela Gothic One",
         "base": "Anton", "counter": "DotGothic16", "counter_flash": "Dela Gothic One",
         "osd": "Consolas", "sfx": "Dela Gothic One", "label": "Bebas Neue"}
BLOCKING = ("freeze card", "kaleidoscope", "colour isolation", "bass shake", "tape cut", "crt off")


def visible(a, b, hide):
    """(a, b) minus every hidden window, as a list of spans."""
    out, cur = [], a
    for ha, hb in sorted(w for w in hide if w[0] < b and w[1] > a):
        if ha > cur:
            out.append((cur, ha))
        cur = max(cur, hb)
    if cur < b:
        out.append((cur, b))
    return out


# ================================================================ shared
def ff_audio(video, t0=0.0, dur=None, rate=8000, af=None):
    args = ["ffmpeg", "-v", "error", "-ss", str(t0)]
    if dur:
        args += ["-t", str(dur)]
    args += ["-i", str(video), "-vn", "-ac", "1", "-ar", str(rate)]
    if af:
        args += ["-af", af]
    raw = subprocess.run(args + ["-f", "s16le", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.int16).astype(np.float32)


def probe(video):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                          "stream=width,height,r_frame_rate:format=duration", "-of", "json", str(video)],
                         capture_output=True, check=True, text=True).stdout
    j = json.loads(out)
    s = j["streams"][0]
    num, den = s["r_frame_rate"].split("/")
    return int(s["width"]), int(s["height"]), float(num) / float(den), float(j["format"]["duration"])


def kicks(video, t0, dur, min_gap=0.40):
    """Kick onsets: rises in the energy of the sound under 120 Hz, at least min_gap apart."""
    x = ff_audio(video, t0, dur, af="lowpass=f=120")
    e = np.sqrt(np.convolve(x ** 2, np.ones(80) / 80, "same"))[::80]
    d = np.maximum(np.diff(e, prepend=e[0]), 0)
    thr = d.mean() + 2.0 * d.std()
    out, last = [], -9
    for i in range(1, len(d) - 1):
        if d[i] > thr and d[i] >= d[i - 1] and d[i] >= d[i + 1] and i * 0.01 - last >= min_gap:
            out.append(t0 + i * 0.01)
            last = i * 0.01
    return out


def scene_cuts(video, threshold=0.30):
    # 24 fps first: frame-generated 48 fps films carry blended in-between frames that split one cut in two
    err = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(video), "-an", "-vf",
                          f"fps=24,scale=224:-1,select='gt(scene,{threshold})',showinfo", "-f", "null", "-"],
                         capture_output=True, text=True, errors="replace").stderr
    return [round(float(m), 3) for m in re.findall(r"pts_time:([0-9.]+)", err)]


def audio_offset(film, ref, seconds=60.0, rate=4000):
    """Seconds to ADD to a time in ref to land on the same sound in film, and the correlation (0-1)."""
    x = ff_audio(film, 0, seconds, rate)
    y = ff_audio(ref, 0, seconds, rate)
    n = min(len(x), len(y))
    x, y = x[:n] - x[:n].mean(), y[:n] - y[:n].mean()
    size = 1 << int(math.ceil(math.log2(2 * n)))
    c = np.fft.irfft(np.fft.rfft(x, size) * np.conj(np.fft.rfft(y, size)), size)
    k = int(np.argmax(c))
    corr = float(c[k] / (np.linalg.norm(x) * np.linalg.norm(y) + 1e-9))
    if k > size // 2:
        k -= size
    return k / rate, corr


# ================================================================ measure
def cmd_measure(video, ref=None):
    W, H, fps, dur = probe(video)
    cuts = scene_cuts(video)
    ks = kicks(video, 0, dur)
    res = {"video": str(video), "size": [W, H], "fps": fps, "duration": round(dur, 3), "cuts": cuts,
           "kicks": [round(k, 2) for k in ks]}
    print(f"{W}x{H} {fps:g} fps {dur:.2f} s | {len(cuts)} cuts -> {len(cuts) + 1} shots | "
          f"{len(ks)} kicks (for tempo use the song stage's BPM, not these)")
    if ref:
        off, corr = audio_offset(video, ref)
        res["offset_from_ref"] = round(off, 3)
        res["offset_corr"] = round(corr, 3)
        print(f"offset: add {off:+.3f} s to {Path(ref).name} times (correlation {corr:.3f}"
              f"{'' if corr > 0.8 else ' -- LOW: not the same mix, time words by ear'})")
    out = Path.cwd() / (Path(video).stem + ".measure.json")
    out.write_text(json.dumps(res, indent=1), encoding="utf-8")
    print("wrote", out)


# ================================================================ cues
def cmd_cues(plan_path):
    plan_path = Path(plan_path)
    p = json.loads(plan_path.read_text(encoding="utf-8"))
    video = Path(p["video"])
    if not video.is_absolute():
        video = plan_path.parent / video
    W, H, fps, dur = probe(video)
    cuts = p.get("cuts")
    if cuts is None:
        print("measuring cuts ...")
        cuts = scene_cuts(video)
    edges = [0.0] + list(cuts) + [dur]
    worlds = p.get("worlds") or [""] * (len(edges) - 1)
    if len(worlds) != len(edges) - 1:
        sys.exit(f"{len(worlds)} worlds for {len(edges) - 1} shots: give one world per shot")
    shots = [dict(n=i + 1, a=edges[i], b=edges[i + 1], world=worlds[i]) for i in range(len(worlds))]

    def shot_at(t):
        return next((s for s in shots if s["a"] <= t < s["b"]), shots[-1])

    fx = [dict(a=f[0], b=f[1], kind=f[2], **(f[3] if len(f) > 3 else {})) for f in p.get("fx", [])]
    baked = p.get("baked", [])
    blocking = [(a, b, n) for a, b, n in baked] + [(f["a"], f["b"], f["kind"]) for f in fx if f["kind"] in BLOCKING]
    orbit, glitch = set(p.get("orbit", [])), set(p.get("glitch", []))
    glitch_worlds = set(p.get("glitch_worlds", []))
    gap = float(p.get("min_gap", 1.3))
    off = float(p.get("offset", 0.0))
    text, dropped, last = [], [], -9.0
    for t, word in sorted(((float(w[0]) + off, w[1]) for w in p["words"]), key=lambda q: q[0]):
        t = round(t, 2)
        style = "orbit" if word in orbit else ("glitch" if word in glitch else "telop")
        shot = shot_at(t)
        if style == "glitch" and glitch_worlds and shot["world"] not in glitch_worlds:
            style = "telop"
        hit = next((n for a, b, n in blocking if a - 0.3 <= t <= b + 0.2), None)
        if hit:
            dropped.append((t, word, f"clashes with {hit}"))
            continue
        if t - last < gap:
            dropped.append((t, word, "too close to the previous word"))
            continue
        text.append(dict(t=t, word=word, style=style, shot=shot["n"], world=shot["world"]))
        last = t
    keep = {k: v for k, v in p.items() if k not in ("words", "fx", "cuts", "worlds")}
    cues = dict(keep, video=str(video), size=[W, H], fps=fps, duration=dur, shots=shots, fx=fx, text=text,
                dropped=dropped)
    out = plan_path.parent / "cues.json"
    out.write_text(json.dumps(cues, ensure_ascii=False, indent=1), encoding="utf-8")
    n = {s: sum(1 for x in text if x["style"] == s) for s in ("telop", "glitch", "orbit")}
    print(f"{len(text)} text hits {n} | {len(dropped)} dropped")
    for d in dropped:
        print("  drop", d)
    print("wrote", out)


# ================================================================ burn
class Burn:
    def __init__(self, cues_path, yunet=None):
        self.dir = Path(cues_path).parent
        self.c = json.loads(Path(cues_path).read_text(encoding="utf-8"))
        c = self.c
        self.V = c["video"]
        self.W, self.H = c["size"]
        self.FPS = c["fps"]
        self.FB = self.W * self.H * 3
        self.BEAT = 60 / float(c.get("bpm", 120))
        self.BAR = 4 * self.BEAT
        self.fonts = dict(FONTS, **c.get("font_names", {}))
        self.fontsdir = c.get("fonts", "fonts")
        self.glow = c.get("glow", {})
        self.cuts = [s["a"] for s in c["shots"]] + [c["shots"][-1]["b"]]
        self.work = self.dir / "_post"
        self.work.mkdir(exist_ok=True)
        self.STAMP = "\\fscx128\\fscy128\\t(0,80,\\fscx94\\fscy94)\\t(80,150,\\fscx100\\fscy100)"
        self._size = {}
        self._sessions = None
        self.yn = self._yunet(yunet)

    # ---------------------------------------------------------- optional models
    def _yunet(self, path):
        if path is None:
            for parent in Path(__file__).resolve().parents:
                hit = sorted((parent / "models" / "facedetection").glob("face_detection_yunet*.onnx"))
                if hit:
                    path = hit[-1]
                    break
        if not path or not Path(path).is_file():
            print("no YuNet face model found (--yunet): text placement ignores faces, orbit sits mid-frame")
            return None
        return cv2.FaceDetectorYN.create(str(path), "", (self.W, self.H), 0.7)

    def sessions(self):
        if self._sessions is None:
            try:
                from rembg import new_session
                self._sessions = (new_session("isnet-general-use"), new_session("u2net_human_seg"))
            except Exception as e:  # rembg missing or a model it cannot fetch
                print(f"rembg unavailable ({e.__class__.__name__}): no people matte; placement uses faces and "
                      "detail only, orbit is not tucked, colour isolation is skipped")
                self._sessions = False
        return self._sessions

    def mattes(self, fr, need_wide=True):
        s = self.sessions()
        if not s:
            return None, None
        from rembg import remove
        rgb = cv2.cvtColor(fr, cv2.COLOR_BGR2RGB)
        tight = np.array(remove(rgb, session=s[0], only_mask=True)).astype(np.float32) / 255
        wide = np.array(remove(rgb, session=s[1], only_mask=True)).astype(np.float32) / 255 if need_wide else None
        return tight, wide

    def faces(self, fr):
        if self.yn is None:
            return []
        _, f = self.yn.detect(fr)
        return [] if f is None else [tuple(map(int, r[:4])) for r in f]

    # ---------------------------------------------------------- frames
    def grab(self, t):
        cap = cv2.VideoCapture(self.V)
        cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
        ok, fr = cap.read()
        cap.release()
        return fr

    def busy_map(self, fr):
        """[people (faces weigh 3), detail] -- where text must not go, and where it would be hard to read."""
        W, H = self.W, self.H
        tight, wide = self.mattes(fr)
        if tight is None:
            people = np.zeros((H, W), np.float32)
        else:
            people = ((tight > 0.4) | (wide > 0.35)).astype(np.uint8)
            people = cv2.dilate(people, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (49, 49))).astype(np.float32)
        g = cv2.cvtColor(fr, cv2.COLOR_BGR2GRAY).astype(np.float32)
        lap = np.abs(cv2.Laplacian(cv2.GaussianBlur(g, (0, 0), 1.2), cv2.CV_32F))
        edge = np.clip(cv2.GaussianBlur(lap, (0, 0), 10) / (np.percentile(lap, 99) * 0.25 + 1e-3), 0, 1)
        for x, y, w, h in self.faces(fr):
            cv2.rectangle(people, (x - w // 2, y - h // 2), (x + w + w // 2, y + h + h // 2), 3.0, -1)
        return np.stack([people, edge])

    def shot_at(self, t):
        return next((s for s in self.c["shots"] if s["a"] <= t < s["b"]), self.c["shots"][-1])

    def next_cut(self, t):
        return next((c for c in self.cuts if c > t + 1e-3), self.cuts[-1])

    # ---------------------------------------------------------- ASS
    @staticmethod
    def ts(t):
        t = max(0.0, t)
        return "%d:%02d:%05.2f" % (int(t // 3600), int(t % 3600 // 60), t % 60)

    def ev(self, a, b, tags, txt, layer=0):
        return f"Dialogue: {layer},{self.ts(a)},{self.ts(b)},B,,0,0,0,,{{{tags}}}{txt}"

    def head(self):
        return (f"[Script Info]\nScriptType: v4.00+\nPlayResX: {self.W}\nPlayResY: {self.H}\nWrapStyle: 2\n"
                "ScaledBorderAndShadow: yes\n\n[V4+ Styles]\n"
                "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, "
                "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
                "Alignment, MarginL, MarginR, MarginV, Encoding\n"
                f"Style: B,{self.fonts['base']},80,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,"
                "1,0,0,5,0,0,0,1\n\n[Events]\n"
                "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")

    def telop_events(self, a, b, txt, x, y, r, s, anim=True):
        st = self.STAMP if anim else ""
        base = f"\\an5\\pos({x},{y})\\frz{r}\\fn{self.fonts['telop']}\\fs{s}{st}"
        return [self.ev(a, b, base + "\\bord24\\3c&HFFFFFF&\\1c&HFFFFFF&\\shad9\\4c&H301010&\\4a&H40&", txt, 0),
                self.ev(a, b, base + "\\bord11\\3c&H2A10D8&\\1c&HFFFFFF&\\shad0", txt, 1),
                self.ev(a, b, base + f"\\bord0\\1c&H00F6FF&\\shad0\\clip(0,0,{self.W},{y})", txt, 2)]

    def glitch_events(self, a, b, txt, x, y, s):
        W, H, ev = self.W, self.H, self.ev
        out = []
        base = f"\\an5\\fn{self.fonts['glitch']}\\fs{s}\\bord0\\shad0"
        rng = np.random.default_rng(int(a * 100))
        f = 1 / self.FPS
        for i in range(4):                                  # 4 jitter frames on the hit
            dx, dy = rng.integers(-30, 30), rng.integers(-8, 8)
            t0, t1 = a + i * f, a + (i + 1) * f
            out += [ev(t0, t1, base + f"\\pos({x - 18 + dx},{y + dy})\\1c&H3020FF&\\alpha&H20&", txt, 0),
                    ev(t0, t1, base + f"\\pos({x + 18 - dx},{y - dy})\\1c&HFFE020&\\alpha&H20&", txt, 1),
                    ev(t0, t1, base + f"\\pos({x + dx // 2},{y})\\1c&HFFFFFF&", txt, 2)]
        t = a + 4 * f
        k = 0
        while t < b:                                        # settled split, slice band jumps every beat
            t1 = min(b, t + self.BEAT)
            band = y - s // 3 + (k * 37) % max(1, s // 2)
            out += [ev(t, t1, base + f"\\pos({x - 8},{y})\\1c&H3020FF&\\alpha&H30&", txt, 0),
                    ev(t, t1, base + f"\\pos({x + 8},{y + 2})\\1c&HFFE020&\\alpha&H30&", txt, 1),
                    ev(t, t1, base + f"\\pos({x},{y})\\1c&HFFFFFF&\\clip(0,0,{W},{band})", txt, 2),
                    ev(t, t1, base + f"\\pos({x + 24},{y})\\1c&HFFFFFF&\\clip(0,{band},{W},{band + 16})", txt, 2),
                    ev(t, t1, base + f"\\pos({x},{y})\\1c&HFFFFFF&\\clip(0,{band + 16},{W},{H})", txt, 2)]
            t, k = t1, k + 1
        return out

    def ass_filter(self, name):
        return f"ass=_post/{name}:fontsdir={self.fontsdir}"

    def text_box(self, kind, txt, s, r=0):
        """Rendered size of a word: burned once over black and measured."""
        W, H = self.W, self.H
        key = (kind, txt, s, r)
        if key not in self._size:
            if kind == "telop":
                evs = self.telop_events(0, 1, txt, W // 2, H // 2, r, s, anim=False)
            elif kind == "sfx":
                evs = self.sfx_events(0, 1, txt, W // 2, H // 2, r, s, "&HFFFFFF&", anim=False)
            else:
                evs = [self.ev(0, 1, f"\\an5\\pos({W // 2},{H // 2})\\fn{self.fonts['glitch']}\\fs{s}\\bord0", txt, 0)]
            (self.work / "_m.ass").write_text(self.head() + "\n".join(evs) + "\n", encoding="utf-8")
            raw = subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", f"color=black:s={W}x{H}:d=0.1",
                                  "-vf", "format=bgr24," + self.ass_filter("_m.ass"), "-frames:v", "1",
                                  "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], cwd=self.dir, capture_output=True,
                                 check=True).stdout
            im = np.frombuffer(raw, np.uint8).reshape(H, W, 3)
            ys, xs = np.where(im.max(axis=2) > 20)
            if not len(xs):
                print(f"  WARNING: '{txt}' rendered blank -- is the {kind} font in {self.fontsdir}?")
            self._size[key] = (int(xs.max() - xs.min() + 24), int(ys.max() - ys.min() + 24)) if len(xs) else (200, 100)
        return self._size[key]

    def place(self, kind, txt, s, r, busy, taken, prefer):
        """Grid search for the clearest slot; shrinks 1.0 / 0.82 / 0.68 when nothing is clear."""
        W, H = self.W, self.H
        best = None
        for scale in (1.0, 0.82, 0.68):
            sz = int(s * scale)
            w, h = self.text_box(kind, txt, sz, r)
            b = busy[0].copy()
            for (x0, y0, x1, y1) in taken:
                b[max(0, y0):y1, max(0, x0):x1] = 3.0
            ii = cv2.integral(b)
            ie = cv2.integral(busy[1])
            for cy in range(h // 2 + 20, H - h // 2 - 20, 12):
                for cx in range(w // 2 + 20, W - w // 2 - 20, 12):
                    x0, y0 = cx - w // 2, cy - h // 2
                    m = (ii[y0 + h, x0 + w] - ii[y0, x0 + w] - ii[y0 + h, x0] + ii[y0, x0]) / (w * h)
                    e = (ie[y0 + h, x0 + w] - ie[y0, x0 + w] - ie[y0 + h, x0] + ie[y0, x0]) / (w * h)
                    bias = cy / H if prefer == "top" else 1 - cy / H
                    sc = m + 0.15 * e + 0.05 * bias - 0.04 * abs(cx - W / 2) / W
                    if best is None or sc < best[0]:
                        best = (sc, cx, cy, sz, m, w, h)
            if best is None:
                continue
            if best[4] < 0.03:
                break
        return best

    def build_text(self, start, end):
        front, log, taken_windows = [], [], []
        hits = [h for h in self.c["text"] if start <= h["t"] < end - 0.5]
        max_overlap = float(self.c.get("max_overlap", 0.12))
        for i, h in enumerate(hits):
            t, word, style = h["t"], h["word"], h["style"]
            if style == "orbit":
                continue
            dur = max(0.9, 2 * self.BEAT) if style == "telop" else 1.2
            a = t
            nc = self.next_cut(a)
            b = min(a + dur, nc) if nc - a >= 0.5 else a + dur
            samples = sorted({a + 0.05, (a + b) / 2, b - 0.05})
            busy = np.max([self.busy_map(self.grab(x)) for x in samples], axis=0)
            taken = [box for (wa, wb, box) in taken_windows if wa < b and wb > a]
            n = len(word)
            if style == "telop":
                s = 112 if n <= 6 else (92 if n <= 10 else 76)
                r = (-7, 6, -5, 7)[i % 4]
            else:
                s = 150 if n <= 6 else 118
                r = 0
            best = self.place(style, word, s, r, busy, taken, "top" if i % 2 == 0 else "bottom")
            if best is None or best[4] > max_overlap:
                ov = best[4] if best else 1.0
                log.append(f"{t:7.2f} {style:6s} {h['world']:8s} {word:16s} DROPPED: frame too crowded "
                           f"(overlap {ov:.3f})")
                continue
            sc, x, y, sz, ov, w, hh = best
            rel_a, rel_b = a - start, b - start
            front += self.telop_events(rel_a, rel_b, word, x, y, r, sz) if style == "telop" else \
                self.glitch_events(rel_a, rel_b, word, x, y, sz)
            taken_windows.append((a, b, (x - w // 2, y - hh // 2, x + w // 2, y + hh // 2)))
            log.append(f"{t:7.2f} {style:6s} {h['world']:8s} {word:16s} ({x},{y}) fs{sz} overlap {ov:.3f}")
        return front, log

    def build_counter(self, start, end):
        """A floor counter in a corner: a small dark LED panel whose readout changes on given times
        (plan "counter": {"floors": [[t, "1F"], ...], "flash": [t, ...], "flash_text": "うえ!", "corner": "tl"}).
        Hidden during blocking fx. Times are in film time (the plan offset is not applied)."""
        cfg = self.c.get("counter")
        if not cfg or not cfg.get("floors"):
            return [], []
        W, H, ev = self.W, self.H, self.ev
        floors = sorted((float(t), str(lab)) for t, lab in cfg["floors"])
        hide = [(f["a"], f["b"]) for f in self.c["fx"] if f["kind"] in BLOCKING] +                [(a, b) for a, b, _n in self.c.get("baked", [])]
        bw, bh = int(W * 0.17), int(H * 0.085)
        mx, my = int(W * 0.035), int(H * 0.05)
        corner = cfg.get("corner", "tl")
        x0 = mx if corner in ("tl", "bl") else W - mx - bw
        y0 = my if corner in ("tl", "tr") else H - my - bh
        amber, dim = "&H28AAFF&", "&H1A4A80&"
        fs = int(bh * 0.92)
        r = int(bh * 0.18)
        box = (f"m {r} 0 l {bw - r} 0 b {bw} 0 {bw} 0 {bw} {r} l {bw} {bh - r} b {bw} {bh} {bw} {bh} {bw - r} {bh} "
               f"l {r} {bh} b 0 {bh} 0 {bh} 0 {bh - r} l 0 {r} b 0 0 0 0 {r} 0")
        # visible spans: from each change to the next, minus hidden windows
        spans = []
        for i, (t, lab) in enumerate(floors):
            t1 = floors[i + 1][0] if i + 1 < len(floors) else float(self.c["duration"])
            a, b = max(t, start), min(t1, end)
            if b <= a:
                continue
            cuts = sorted([(ha, hb) for ha, hb in hide if ha < b and hb > a])
            cur = a
            for ha, hb in cuts:
                if ha > cur:
                    spans.append((cur, ha, lab, t >= start and cur == t))
                cur = max(cur, hb)
            if cur < b:
                spans.append((cur, b, lab, t >= start and cur == t))
        out, log = [], []
        for a, b, lab, fresh in spans:
            ra, rb = a - start, b - start
            out.append(ev(ra, rb, f"\\an7\\pos({x0},{y0})\\p1\\bord3\\3c{amber}\\1c&H0A0808&\\1a&H38&\\shad0", box, 4))
            tag = f"\\an4\\pos({x0 + int(bw * 0.08)},{y0 + bh // 2})\\fn{self.fonts['counter']}\\fs{fs}\\bord1\\3c{amber}\\shad0\\1c{amber}"
            if fresh:   # two dim frames, then lit: the readout ticking over
                f = 1 / self.FPS
                out.append(ev(ra, min(rb, ra + 2 * f), tag.replace(amber, dim), "▲ " + lab, 5))
                out.append(ev(min(rb, ra + 2 * f), rb, tag, "▲ " + lab, 5))
            else:
                out.append(ev(ra, rb, tag, "▲ " + lab, 5))
        flash_txt = cfg.get("flash_text", "うえ!")
        fz = int(H * 0.085)
        for t in cfg.get("flash", []):
            t = float(t)
            if not (start <= t < end) or any(ha - 0.2 <= t <= hb for ha, hb in hide):
                continue
            ra = t - start
            tag = (f"\\an7\\pos({x0},{y0 + bh + int(H * 0.015)})\\fn{self.fonts['counter_flash']}\\fs{fz}"
                   f"\\bord5\\3c&H0A0A0A&\\1c{amber}\\shad0{self.STAMP}\\t(500,800,\\alpha&HFF&)")
            out.append(ev(ra, ra + 0.8, tag, flash_txt, 6))
            log.append(f"{t:7.2f} counter  flash {flash_txt}")
        log.append(f"counter: {len(spans)} readout spans in {start:.1f}-{end:.1f}")
        return out, log

    # ---------------------------------------------------------- VCR on-screen display
    def build_osd(self, start, end):
        """A VCR on-screen display (plan "osd": {"states": [[t, "play"|"pause"], ...], "date": "AM 7:00  NOV.28",
        "play_hold": 2.5}). PAUSE stays up while paused; PLAY shows for play_hold s after each play. The tape
        counter (bottom right) runs only while playing. Top line hides in blocking fx; the bottom line also in
        baked windows. Film time (the plan offset is not applied)."""
        cfg = self.c.get("osd")
        if not cfg or not cfg.get("states"):
            return [], []
        W, H, ev = self.W, self.H, self.ev
        dur = float(self.c["duration"])
        states = sorted((float(t), s) for t, s in cfg["states"])
        block = [(f["a"], f["b"]) for f in self.c["fx"] if f["kind"] in BLOCKING]
        hide_bottom = block + [(a, b) for a, b, _n in self.c.get("baked", [])]
        fs = int(H * 0.06)
        mx, my = int(W * 0.036), int(H * 0.052)
        font = self.fonts["osd"]

        def txt(a, b, x, y, an, s, body, draw=False):
            out = []
            for a2, b2 in visible(max(a, start), min(b, end), hide):
                ra, rb = a2 - start, b2 - start
                base = f"\\an{an}\\fn{font}\\b1\\fs{s}\\bord0" + ("\\p1" if draw else "")
                for dx, dy, col, al, lay in ((3, 3, "&H000000&", "&H60&", 7), (-2, 0, "&H4646FF&", "&H50&", 8),
                                             (2, 0, "&HFFDC46&", "&H50&", 8), (0, 0, "&HFFFFFF&", "&H00&", 9)):
                    out.append(ev(ra, rb, base + f"\\pos({x + dx},{y + dy})\\1c{col}\\alpha{al}", body, lay))
            return out

        out, log = [], []
        icon_h = int(fs * 0.8)
        pause_icon = (f"m 0 0 l {icon_h // 4} 0 l {icon_h // 4} {icon_h} l 0 {icon_h} "
                      f"m {icon_h // 2} 0 l {icon_h // 2 + icon_h // 4} 0 l {icon_h // 2 + icon_h // 4} {icon_h} "
                      f"l {icon_h // 2} {icon_h}")
        play_icon = f"m 0 0 l {int(icon_h * 0.85)} {icon_h // 2} l 0 {icon_h}"
        hold = float(cfg.get("play_hold", 2.5))
        play_spans, played = [], 0.0
        for i, (t, s) in enumerate(states):
            t1 = states[i + 1][0] if i + 1 < len(states) else dur
            hide = block
            if s == "pause":
                out += txt(t, t1, mx, my, 7, 0, pause_icon, draw=True)
                out += txt(t, t1, mx + int(icon_h * 1.2), my - int(fs * 0.12), 7, fs, "PAUSE")
            else:
                b = min(t1, t + hold)
                out += txt(t, b, mx, my, 7, 0, play_icon, draw=True)
                out += txt(t, b, mx + int(icon_h * 1.2), my - int(fs * 0.12), 7, fs, "PLAY")
                play_spans.append((t, t1))
            log.append(f"{t:7.2f} osd      {s.upper()}")
        # bottom line: date + a tape counter that runs only while playing
        hide = hide_bottom
        fsb = int(fs * 0.75)
        yb = H - my
        if cfg.get("date"):
            out += txt(0, dur, mx, yb, 1, fsb, cfg["date"])

        def counter(t):
            return sum(max(0.0, min(t, b) - a) for a, b in play_spans)

        marks = sorted({0.0, dur} | {a for a, b in play_spans} | {b for a, b in play_spans})
        for a, b in play_spans:                          # every counter second ticks over while playing
            k = math.floor(counter(a)) + 1
            while True:
                tt = a + (k - counter(a))
                if tt >= b:
                    break
                marks.append(tt)
                k += 1
        marks = sorted(set(m for m in marks if 0 <= m <= dur))
        for a, b in zip(marks, marks[1:]):
            if b <= start or a >= end:
                continue
            c = int(counter(a + 1e-4))
            out += txt(a, b, W - mx, yb, 3, fsb, "SP %d:%02d:%02d" % (c // 3600, c % 3600 // 60, c % 60))
        log.append(f"osd: {len(states)} states, tape counter runs {sum(b - a for a, b in play_spans):.1f} s")
        return out, log

    def reserve_osd(self, busy):
        """Keep words and labels off the OSD's top-left readout and its bottom line."""
        if self.c.get("osd"):
            busy = busy.copy()
            busy[0, :int(self.H * 0.15), :int(self.W * 0.24)] = 3.0
            busy[0, int(self.H * 0.86):, :] = 3.0
        return busy

    # ---------------------------------------------------------- manga sound-effect words
    def sfx_events(self, a, b, txt, x, y, r, s, col, anim=True):
        st = self.STAMP if anim else ""
        base = f"\\an5\\pos({x},{y})\\frz{r}\\fn{self.fonts['sfx']}\\fs{s}{st}"
        return [self.ev(a, b, base + "\\bord16\\3c&H101010&\\1c&H101010&\\shad7\\4c&H000000&\\4a&H70&", txt, 0),
                self.ev(a, b, base + f"\\bord0\\1c{col}\\shad0", txt, 1)]

    def build_sfx(self, start, end, taken_windows):
        """Plan "sfx": [[t, "シーン", {"vertical": true, "color": "&HFFFFFF&", "size": 130, "rot": 0, "dur": 1.4}]].
        Placed like a telop: never over people or faces; dropped when the frame is too crowded. Film time."""
        out, log = [], []
        for item in self.c.get("sfx", []):
            t, word = float(item[0]), item[1]
            o = item[2] if len(item) > 2 else {}
            if not (start <= t < end - 0.3):
                continue
            txt = "\\N".join(word) if o.get("vertical") else word
            a = t
            nc = self.next_cut(a)
            b = min(a + float(o.get("dur", 1.2)), nc) if nc - a >= 0.5 else a + float(o.get("dur", 1.2))
            busy = self.reserve_osd(np.max([self.busy_map(self.grab(x)) for x in sorted({a + 0.05, (a + b) / 2, b - 0.05})],
                                           axis=0))
            taken = [box for (wa, wb, box) in taken_windows if wa < b and wb > a]
            r = float(o.get("rot", 0 if o.get("vertical") else 8))
            best = self.place("sfx", txt, int(o.get("size", 130)), r, busy, taken, o.get("prefer", "top"))
            if best is None or best[4] > float(self.c.get("max_overlap", 0.12)):
                log.append(f"{t:7.2f} sfx      {word:16s} DROPPED: frame too crowded")
                continue
            sc, x, y, sz, ov, w, hh = best
            out += self.sfx_events(a - start, b - start, txt, x, y, r, sz, o.get("color", "&H00E6FF&"))
            taken_windows.append((a, b, (x - w // 2, y - hh // 2, x + w // 2, y + hh // 2)))
            log.append(f"{t:7.2f} sfx      {word:16s} ({x},{y}) fs{sz} overlap {ov:.3f}")
        return out, log

    # ---------------------------------------------------------- museum labels on frozen people
    def track_labels(self, start, end):
        """Plan "labels": [{"a": 22.1, "b": 24.6, "items": [["MID-YAWN", "No.1 / FROZEN", 108], ...]}] where the
        number is the face's x at "a" (from a still). Boxes sit still in space clear of people over the whole
        window; the leader line follows each tracked head. Returns per-frame draw lists keyed by frame index."""
        from PIL import ImageFont
        W, H, FPS = self.W, self.H, self.FPS
        frames, log = {}, []
        fdir = self.dir / self.fontsdir

        def font(names, size):
            for n in names:
                for p in list(fdir.glob(n)) + [Path("C:/Windows/Fonts") / n]:
                    if p.is_file():
                        return ImageFont.truetype(str(p), size)
            return ImageFont.load_default()
        big = font(["BebasNeue-Regular.ttf"], int(H * 0.044))
        small = font(["consolab.ttf", "consola.ttf"], int(H * 0.021))
        for L in self.c.get("labels", []):
            a, b = float(L["a"]), float(L["b"])
            if b <= start or a >= end:
                continue
            cap = cv2.VideoCapture(self.V)
            cap.set(cv2.CAP_PROP_POS_MSEC, a * 1000)
            n = int(round((b - a) * FPS))
            pos = {i: None for i in range(len(L["items"]))}
            tracks, lost = [], {i: 0 for i in pos}
            for k in range(n):
                ok, fr = cap.read()
                if not ok:
                    break
                if k % 2 == 0:
                    fs = [(x + w / 2, y + h / 2, w) for x, y, w, h in self.faces(fr)]
                    for i, it in enumerate(L["items"]):
                        ref = pos[i] if pos[i] is not None else (float(it[2]), None, 0)
                        cand = [f for f in fs if abs(f[0] - ref[0]) < (90 if pos[i] is not None else 120)
                                and (ref[1] is None or abs(f[1] - ref[1]) < 120)]
                        if cand:
                            f = min(cand, key=lambda q: abs(q[0] - ref[0]))
                            pos[i] = f if pos[i] is None else tuple(0.5 * p + 0.5 * q for p, q in zip(pos[i], f))
                            lost[i] = 0
                        else:
                            lost[i] += 2
                tracks.append({i: (pos[i] if pos[i] is not None and lost[i] < 0.3 * FPS else None) for i in pos})
            cap.release()
            bw_ = {i: int(max(big.getlength(it[0]), small.getlength(it[1])) + 28) for i, it in enumerate(L["items"])}
            bh = int(H * 0.044 + H * 0.021 + 22)
            found = {i for tr in tracks for i, v in tr.items() if v is not None}
            for i, it in enumerate(L["items"]):
                log.append(f"{a:7.2f} label    {it[0]:16s} " + ("pinned above the tracked head" if i in found else
                                                                 f"DROPPED: face never found near x={it[2]}"))
            f0 = int(round((a - start) * FPS))
            top = int(H * 0.15)
            for k, tr in enumerate(tracks):
                items, placed = [], []
                for j, i in enumerate(sorted(found)):
                    head = tr[i]
                    t_in = k / FPS - 0.12 * j
                    if head is None or t_in < 0:
                        continue
                    hx, hy, fw = head
                    bw = bw_[i]
                    x0 = int(min(max(hx - bw / 2, 16), W - bw - 16))
                    y0 = int(hy - 0.55 * fw - 30 - bh)               # a short stub above the head
                    if x0 < W * 0.24 and y0 < top:
                        y0 = top                                     # clear of the PAUSE readout
                    if y0 < 8 or y0 + bh > H * 0.86:
                        continue
                    box = (x0, y0, bw, bh)
                    faces_hit = any(abs(f[0] - (x0 + bw / 2)) < bw / 2 + f[2] / 2 and y0 < f[1] + f[2] * 1.2
                                    and y0 + bh > f[1] - f[2] * 0.2 for f in tr.values() if f is not None)
                    if faces_hit or any(x0 < q[0] + q[2] and q[0] < x0 + bw and y0 < q[1] + q[3] and q[1] < y0 + bh
                                        for q in placed):
                        continue
                    placed.append(box)
                    al = min(1.0, t_in / 0.08, (b - a - k / FPS) / 0.2)
                    items.append((box, (hx, hy - 0.55 * fw), L["items"][i][0], L["items"][i][1], al))
                frames[f0 + k] = items
        return frames, (big, small), log

    def draw_labels(self, fr, items, fonts):
        from PIL import Image, ImageDraw
        big, small = fonts
        ov = Image.new("RGBA", (self.W, self.H), (0, 0, 0, 0))
        d = ImageDraw.Draw(ov)
        alpha = max(al for *_, al in items)
        for (x0, y0, bw, bh), head, t1, t2, al in items:
            A = int(255 * al)
            if head is not None:
                hx, hy = int(head[0]), int(head[1] - 6)
                ex = min(max(hx, x0 + 8), x0 + bw - 8)
                ey = y0 + bh if y0 + bh < hy else y0
                d.line([(hx, hy), (ex, ey)], fill=(255, 255, 255, A), width=3)
                d.ellipse([hx - 6, hy - 6, hx + 6, hy + 6], fill=(255, 255, 255, A), outline=(0, 0, 0, A))
            d.rectangle([x0, y0, x0 + bw, y0 + bh], fill=(250, 248, 240, A), outline=(20, 20, 20, A), width=2)
            d.text((x0 + 12, y0 + 4), t1, font=big, fill=(20, 20, 20, A))
            d.text((x0 + 12, y0 + bh - small.size - 6), t2, font=small, fill=(120, 30, 30, A))
        if alpha <= 0:
            return fr
        o = np.array(ov).astype(np.float32)
        m = o[..., 3:4] / 255
        rgb = o[..., [2, 1, 0]]
        return (fr.astype(np.float32) * (1 - m) + rgb * m).astype(np.uint8)

    # ---------------------------------------------------------- tape fx
    def tape_cut(self, fr, t, a, b, seed):
        """VHS head-switch on a cut: rows wobble, a noisy band at the bottom, chroma slips, a small vertical jump.
        Strongest at the window's middle (put the cut there)."""
        W, H = self.W, self.H
        p = (t - a) / (b - a)
        k = math.sin(math.pi * min(max(p, 0), 1))
        rng = np.random.default_rng(seed + int(t * 1000))
        ys = np.arange(H, dtype=np.float32)
        dx = k * (14 * np.sin(ys * 0.045 + t * 60) + 5 * rng.standard_normal(H))
        band = ys > H * (1 - 0.08 * k - 0.02)
        dx[band] += k * (60 + 40 * rng.random())
        mapx = (np.arange(W, dtype=np.float32)[None, :] - dx[:, None]).astype(np.float32)
        mapy = np.repeat(((ys + k * H * 0.03 * (rng.random() - 0.3)) % H)[:, None], W, axis=1).astype(np.float32)
        out = cv2.remap(fr, mapx, mapy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)
        bb, gg, rr = cv2.split(out)
        s = int(round(8 * k))
        out = cv2.merge([np.roll(bb, s, axis=1), gg, np.roll(rr, -s, axis=1)])
        o = out.astype(np.float32)
        o[band] = o[band] * 0.6 + rng.random((int(band.sum()), W, 1)) * 170 * k
        for _ in range(int(6 * k)):
            y = int(rng.integers(0, H - 3))
            o[y:y + int(rng.integers(1, 4))] = o[y:y + 3].mean() * 0.3 + 200 * rng.random((1, W, 1))
        g = o.mean(axis=2, keepdims=True)
        o = o * (1 - 0.35 * k) + g * 0.35 * k
        return np.clip(o * (1 + 0.15 * k * math.sin(t * 90)), 0, 255).astype(np.uint8)

    def crt_off(self, fr, t, a, b):
        """The set switching off: the picture squashes to a bright line, the line to a dot, the dot fades."""
        W, H = self.W, self.H
        p = (t - a) / (b - a)
        out = np.zeros_like(fr, dtype=np.float32)
        if p < 0.45:
            q = p / 0.45
            h = max(3, int(H * (1 - q) ** 2.2))
            gain = 1 + 1.6 * q
            sq = cv2.resize(fr, (W, h), interpolation=cv2.INTER_AREA).astype(np.float32) * gain
            y0 = (H - h) // 2
            out[y0:y0 + h] = sq
        elif p < 0.72:
            q = (p - 0.45) / 0.27
            w = max(6, int(W * (1 - q) ** 1.8))
            x0 = (W - w) // 2
            out[H // 2 - 2:H // 2 + 2, x0:x0 + w] = 255
            out = cv2.GaussianBlur(out, (0, 0), 3) * 1.6 + out
        elif p < 1.0:
            q = (p - 0.72) / 0.28
            r = max(1, int(7 * (1 - q)))
            cv2.circle(out, (W // 2, H // 2), r, (255, 255, 255), -1)
            out = (cv2.GaussianBlur(out, (0, 0), 6) * 2.5 + out) * (1 - q)
        return np.clip(out, 0, 255).astype(np.uint8)

    def build_orbits(self, start, end):
        """Per-frame ring events round the singer's neck: (front, back, frame ranges that need a matte)."""
        W, H, FPS, BAR, ev = self.W, self.H, self.FPS, self.BAR, self.ev
        front, back, ranges = [], [], []
        hooks = [h for h in self.c["text"] if h["style"] == "orbit" and start <= h["t"] < end - 0.5]
        words = [h["word"] for h in self.c["text"] if h["style"] == "orbit"]
        ring = list(self.c.get("ring") or (" " + " ・ ".join(dict.fromkeys(words)) + " ・ "))
        n = len(ring)
        for h in hooks:
            t0 = h["t"]
            nc = self.next_cut(t0)
            if nc - t0 < 0.35:
                t0 = nc                                     # snap the ring onto the new shot
            t1 = min(t0 + 2 * BAR, end)
            glow = self.glow.get(self.shot_at(t0 + 0.1)["world"], "&HFFFFFF&")
            cap = cv2.VideoCapture(self.V)
            cap.set(cv2.CAP_PROP_POS_MSEC, t0 * 1000)
            fx = None
            for k in range(int((t1 - t0) * FPS)):
                ok, fr = cap.read()
                if not ok:
                    break
                if k % 4 == 0:
                    fs = self.faces(fr)
                    if fs:
                        x, y, w, hh = max(fs, key=lambda q: q[2] * q[3])
                        c = (x + w / 2, y + hh * 1.15, max(w * 3.0, 240))     # neck height, ~3 faces wide
                        fx = c if fx is None else tuple(0.7 * p + 0.3 * q for p, q in zip(fx, c))
                if fx is None:
                    fx = (W / 2, H * 0.42, 260)
                cx, cy, rx = fx
                tt = k / FPS
                grow = min(1.0, tt / 0.15)
                out_t = (t1 - t0) - tt
                exitk = 1.0 if out_t > 0.25 else out_t / 0.25
                rxx = rx * (0.6 + 0.4 * grow) * (1 + 0.5 * (1 - exitk))
                ry = rxx * 0.17
                phase = 2 * math.pi * tt / BAR * 0.5
                a_ = (t0 - start) + tt
                b_ = a_ + 1 / FPS
                for i, ch in enumerate(ring):
                    if ch == " ":
                        continue
                    ang = math.pi - 2 * math.pi * (i + 0.5) / n + phase     # reads left to right across the front
                    x = cx + rxx * math.cos(ang)
                    y = cy + ry * math.sin(ang)
                    fr_side = math.sin(ang)
                    s = int(max(30, (52 + 30 * fr_side) * (rxx / 260) ** 0.5) * (0.5 + 0.5 * grow))
                    if s < 8:
                        continue
                    dx, dy = -rxx * math.sin(ang), ry * math.cos(ang)
                    rot = max(-30.0, min(30.0, -math.degrees(math.atan(dy / dx)) if abs(dx) > 1e-6 else 0.0))
                    al = max(int(255 * (1 - exitk)), 0x00 if fr_side > -0.05 else 0x50)
                    font = self.fonts["orbit_jp"] if ord(ch) > 255 else self.fonts["orbit"]
                    tags = f"\\an5\\pos({x:.0f},{y:.0f})\\fn{font}\\fs{s}\\frz{rot:.1f}\\alpha&H{al:02X}&"
                    tgt = front if fr_side > -0.05 else back
                    tgt.append(ev(a_, b_, tags + f"\\bord5\\blur6\\3c{glow}\\1c{glow}", ch, 0))
                    tgt.append(ev(a_, b_, tags + f"\\bord2\\3c{glow}\\1c&HFFFFFF&", ch, 1))
            cap.release()
            ranges.append((t0, t1))
        return front, back, ranges

    # ---------------------------------------------------------- pixel fx
    def kaleido(self, fr, t, zoom=2.3, spin=0.6):
        W, H = self.W, self.H
        big = cv2.resize(fr, (int(W * zoom), int(H * zoom)))
        M = cv2.getRotationMatrix2D((big.shape[1] / 2, big.shape[0] / 2), math.degrees(spin * t), 1.0)
        big = cv2.warpAffine(big, M, (big.shape[1], big.shape[0]))
        y0, x0 = (big.shape[0] - H) // 2, (big.shape[1] - W) // 2
        q = big[y0:y0 + H, x0:x0 + W][:H // 2, :W // 2]
        top = np.hstack([q, q[:, ::-1]])
        return np.vstack([top, top[::-1]])

    def warp(self, fr, scale, dx=0.0, dy=0.0):
        M = cv2.getRotationMatrix2D((self.W / 2, self.H / 2), 0, scale)
        M[0, 2] += dx
        M[1, 2] += dy
        return cv2.warpAffine(fr, M, (self.W, self.H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)

    def isolate(self, fr, tight, wide, k, keep_hue):
        """Grey the world, keep the subject (tight matte, eroded) plus her keep-hue pixels inside the loose one."""
        hsv = cv2.cvtColor(fr, cv2.COLOR_BGR2HSV)
        hue = np.zeros(fr.shape[:2], bool)
        for lo, hi in keep_hue:
            hue |= (hsv[..., 0] >= lo) & (hsv[..., 0] <= hi)
        keep = hue & (hsv[..., 1] > 90) & (hsv[..., 2] > 40)
        t_ = cv2.erode((tight > 0.5).astype(np.uint8), np.ones((3, 3), np.uint8)) > 0
        m = cv2.GaussianBlur((t_ | ((wide > 0.5) & keep)).astype(np.float32), (0, 0), 0.8)[..., None]
        g = cv2.cvtColor(cv2.cvtColor(fr, cv2.COLOR_BGR2GRAY), cv2.COLOR_GRAY2BGR).astype(np.float32) * 0.8
        m = 1 - k * (1 - m)
        return (fr * m + g * (1 - m)).astype(np.uint8)

    def proc(self, args):
        return subprocess.Popen(args, cwd=self.dir, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                bufsize=self.FB * 2)

    def text_stream(self, name, dur, bg):
        return self.proc(["ffmpeg", "-v", "error", "-f", "lavfi", "-i",
                          f"color={bg}:s={self.W}x{self.H}:r={self.FPS}:d={dur}",
                          "-vf", "format=bgr24," + self.ass_filter(name), "-f", "rawvideo", "-pix_fmt", "bgr24", "-"])

    def read(self, p):
        b = p.stdout.read(self.FB)
        return None if len(b) < self.FB else np.frombuffer(b, np.uint8).reshape(self.H, self.W, 3)

    @staticmethod
    def layer(black, white):
        """Text burned over black and over white -> alpha and premultiplied colour."""
        a = 1.0 - (white.astype(np.float32) - black.astype(np.float32)).mean(axis=2, keepdims=True) / 255.0
        return np.clip(a, 0, 1), black.astype(np.float32)

    def windows(self, kind):
        return [f for f in self.c["fx"] if f["kind"] == kind]

    def run(self, start, end):
        W, H, FPS, ev = self.W, self.H, self.FPS, self.ev
        dur = end - start
        print("placing text ...", flush=True)
        front, log = self.build_text(start, end)
        of, back, orbit_ranges = self.build_orbits(start, end)
        front += of
        cf, clog = self.build_counter(start, end)
        front += cf
        log += clog
        of2, olog = self.build_osd(start, end)
        front += of2
        log += olog
        sf, slog = self.build_sfx(start, end, [])
        front += sf
        log += slog
        label_frames, label_fonts, llog = self.track_labels(start, end) if self.c.get("labels") else ({}, None, [])
        log += llog
        freeze = [f for f in self.windows("freeze card") if start <= f["a"] < end]
        for f in freeze:
            a, b = f["a"], f["b"]
            card, sub = f.get("card"), f.get("sub")
            sz = int(f.get("size", 140))
            x, y = int(f.get("x", W * 0.17)), int(f.get("y", H * 0.65))
            if card:
                front += self.telop_events(a - start, b - start, card, x, y, -6, sz)
            if sub:
                tags = (f"\\an5\\pos({x + 10},{y + int(sz * 0.78)})\\frz-6\\fn{self.fonts['telop']}"
                        f"\\fs{int(sz * 0.36)}{self.STAMP}")
                front += [ev(a - start + 0.12, b - start, tags + "\\bord6\\3c&H101010&\\1c&H00F6FF&\\shad0", sub, 3)]
            log.append(f"{a:7.2f} freeze   {card} at ({x},{y})")
        for name, evs in (("_front.ass", front), ("_back.ass", back or [ev(0, 0.01, "", " ")])):
            (self.work / name).write_text(self.head() + "\n".join(evs) + "\n", encoding="utf-8")
        print("\n".join(log), flush=True)

        def wins(kind):
            return [(f["a"], f["b"]) for f in self.windows(kind)]

        def inside(t, ws):
            return any(a <= t < b for a, b in ws)

        # kicks measured over the whole song, so a sample burn hits the same kicks as the full burn
        ks = [k for k in kicks(self.V, 0, self.c["duration"]) if start - 1 <= k < end]
        rgbw, zoomw, isow = wins("rgb hits"), wins("punch zoom"), wins("colour isolation")
        shakes = [a for a, b in wins("bass shake")]
        kal = self.windows("kaleidoscope")
        leakw, trailw = wins("light leak"), wins("light trails")
        tapew, crtw = wins("tape cut"), wins("crt off")
        iso_hue = {(f["a"], f["b"]): f.get("keep_hue", [[0, 8], [165, 180]]) for f in self.windows("colour isolation")}
        if isow and not self.sessions():
            isow = []
        need_matte = orbit_ranges + isow

        src = self.proc(["ffmpeg", "-v", "error", "-ss", str(start), "-t", str(dur), "-i", self.V, "-f", "rawvideo",
                         "-pix_fmt", "bgr24", "-"])
        fb_, fw_ = self.text_stream("_front.ass", dur, "black"), self.text_stream("_front.ass", dur, "white")
        bb_, bw_ = self.text_stream("_back.ass", dur, "black"), self.text_stream("_back.ass", dur, "white")
        out = self.dir / f"post_{int(start)}_{int(end)}.mp4"
        # Keep the render's quality: the source's own video bitrate, not a CRF (CRF 18 on a 16 Mbps
        # render came out at 5 Mbps, user 11-29 Tomare), the soundtrack copied untouched.
        br = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=bit_rate",
                             "-of", "csv=p=0", self.V], capture_output=True, text=True).stdout.strip()
        rate = ["-b:v", br, "-maxrate", str(int(int(br) * 1.25)), "-bufsize", str(int(br) * 2)]             if br.isdigit() else ["-crf", "12"]
        enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s",
                                f"{W}x{H}", "-r", str(FPS), "-i", "-", "-ss", str(start), "-t", str(dur), "-i", self.V,
                                "-map", "0:v", "-map", "1:a?", "-c:v", "libx264", "-preset", "slow", *rate,
                                "-pix_fmt", "yuv420p", "-c:a", "copy", "-movflags", "+faststart",
                                "-shortest", str(out)], stdin=subprocess.PIPE)
        held = trail = None
        cache = (-1, None, None)
        for i in range(int(round(dur * FPS))):
            t = start + i / FPS
            fr = self.read(src)
            lf, lw, lb, lbw = self.read(fb_), self.read(fw_), self.read(bb_), self.read(bw_)
            if fr is None or lf is None:
                break
            fr = fr.copy()
            # freeze card: the picture holds, the song runs on
            fz = next(((f["a"], f["b"]) for f in freeze if f["a"] <= t < f["b"]), None)
            if fz:
                if held is None:
                    hsv = cv2.cvtColor(fr, cv2.COLOR_BGR2HSV).astype(np.float32)
                    hsv[..., 1] = np.clip(hsv[..., 1] * 1.25, 0, 255)
                    held = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)
                fr = held.copy()
                if t - fz[0] < 1 / FPS:
                    fr = cv2.addWeighted(fr, 0.4, np.full_like(fr, 255), 0.6, 0)
            else:
                held = None
            for f in kal:
                if f["a"] <= t < f["b"]:
                    mix = 1.0 if t < f["b"] - 0.6 else (f["b"] - t) / 0.6
                    fr = cv2.addWeighted(self.kaleido(fr, t - f["a"], f.get("zoom", 2.3), f.get("spin", 0.6)), mix,
                                         fr, 1 - mix, 0)
            if inside(t, zoomw):
                z = sum(0.06 * math.exp(-12 * (t - k)) for k in ks if k <= t and inside(k, zoomw))
                if z > 0.002:
                    fr = self.warp(fr, 1 + z)
            for T in shakes:
                if T <= t < T + 0.6:
                    amp = 14 * math.exp(-7 * (t - T))
                    fr = self.warp(fr, 1.04, amp * math.sin(t * 71), amp * math.cos(t * 53))
            if inside(t, rgbw) and any(k <= t < k + 0.09 for k in ks if inside(k, rgbw)):
                b_, g_, r_ = cv2.split(fr)
                fr = cv2.merge([np.roll(b_, 12, axis=1), np.roll(g_, 3, axis=0), np.roll(r_, -12, axis=1)])
            tw = next(((a, b) for a, b in trailw if a <= t < b), None)
            if tw:                                           # bright pixels linger, eased in and out
                env = min(1.0, (t - tw[0]) / 1.0, (tw[1] - t) / 1.5)
                f32 = fr.astype(np.float32)
                trail = f32 if trail is None else np.maximum(f32, trail * (0.93 * env))
                fr = np.maximum(f32, trail).astype(np.uint8)
            else:
                trail = None
            tight = wide = None
            iso = next(((a, b) for a, b in isow if a <= t < b), None)
            if inside(t, need_matte):                        # one matte per pair of frames at 48 fps
                if i - cache[0] <= 1 and (cache[2] is not None or not iso):
                    tight, wide = cache[1], cache[2]
                else:
                    tight, wide = self.mattes(fr, need_wide=bool(iso))
                    cache = (i, tight, wide)
            if iso and tight is not None:
                k = min(1.0, (t - iso[0]) / 0.06, (iso[1] - t) / 0.06)
                fr = self.isolate(fr, tight, wide, k, iso_hue[iso])
            if label_frames.get(i):
                fr = self.draw_labels(fr, label_frames[i], label_fonts)
            for n_, (a, b) in enumerate(tapew):
                if a <= t < b:
                    fr = self.tape_cut(fr, t, a, b, n_ * 7919)
            base = fr.astype(np.float32)
            ab, cb = self.layer(lb, lbw)
            outf = base * (1 - ab) + cb
            if tight is not None and ab.max() > 0.01:        # back half of the ring goes behind her
                m = cv2.GaussianBlur(tight, (0, 0), 1.0)[..., None]
                outf = outf * (1 - m) + base * m
            af, cf = self.layer(lf, lw)
            outf = outf * (1 - af) + cf
            for a, b in leakw:                               # warm flare drifting across, then fade to black
                if a <= t < b:
                    p = (t - a) / (b - a)
                    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
                    g = np.exp(-((xx - W * (0.2 + 0.5 * p)) ** 2 + (yy - H * 0.3) ** 2) / (2 * (W * 0.35) ** 2))
                    leak = g[..., None] * np.array([40, 150, 255], np.float32) * min(1, p * 2)
                    outf = 255 - (255 - outf) * (255 - leak) / 255
                    outf *= min(1.0, (b - t) / 1.2)
            for a, b in crtw:                                # switch-off: last, over everything
                if t >= a:
                    outf = self.crt_off(np.clip(outf, 0, 255).astype(np.uint8), t, a, b).astype(np.float32) \
                        if t < b else np.zeros_like(outf)
            enc.stdin.write(np.clip(outf, 0, 255).astype(np.uint8).tobytes())
            if i % 240 == 0:
                print(f"  {t:6.1f}s", flush=True)
        enc.stdin.close()
        enc.wait()
        for p in (src, fb_, fw_, bb_, bw_):
            p.kill()
        print("wrote", out)


def main(argv):
    # Words can be Japanese; a cp1252 console crashed printing them.
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    if len(argv) < 2 or argv[0] not in ("measure", "cues", "burn"):
        sys.exit(__doc__)
    if argv[0] == "measure":
        ref = argv[argv.index("--ref") + 1] if "--ref" in argv else None
        cmd_measure(argv[1], ref)
    elif argv[0] == "cues":
        cmd_cues(argv[1])
    else:
        yunet = argv[argv.index("--yunet") + 1] if "--yunet" in argv else None
        pos = [a for i, a in enumerate(argv[1:]) if not a.startswith("--") and argv[i] != "--yunet"]
        if len(pos) < 3:
            sys.exit(__doc__)
        Burn(pos[0], yunet).run(float(pos[1]), float(pos[2]))


if __name__ == "__main__":
    main(sys.argv[1:])
