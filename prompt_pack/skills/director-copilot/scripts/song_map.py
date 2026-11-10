"""Measure a song: tempo, downbeats, per-bar energy, sung bars and timed lyrics.

    python song_map.py SONG.wav --out songmap.json            # tempo only, seconds
    python song_map.py SONG.wav --listen --out songmap.json   # + lyrics (Whisper, CPU)
    python song_map.py SONG.wav --relisten 40-66 66-84        # re-transcribe gaps

Run it with ComfyUI's Python (it needs numpy, PyAV and, for --listen, torch and
transformers). Listening runs on the CPU unless --device cuda is passed: a render
may be using the GPU, and taking it silently has OOM'd renders before.

Nothing is downloaded unless --allow-download is given. Without the Whisper
weights on disk the map is tempo-only and says so.
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
    ap.add_argument("song")
    ap.add_argument("--listen", action="store_true", help="also transcribe lyrics")
    ap.add_argument("--relisten", nargs="*", default=[],
                    help="re-transcribe these spans, e.g. 40-66 (Whisper skips quiet or dense bits)")
    ap.add_argument("--out", help="write the full map here (JSON)")
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--allow-download", action="store_true")
    ap.add_argument("--htc")
    a = ap.parse_args()

    pack = _htc.find_pack(a.htc)
    sm = _htc.import_pure(pack, "songmap")
    quiet = lambda *x: None  # noqa: E731

    if a.relisten:
        mono, sr, _ = sm.load_mono(a.song)
        for span in a.relisten:
            lo, hi = (float(x) for x in span.split("-"))
            lines, how = sm.transcribe(mono[int(lo * sr):int(hi * sr)], sr, status=quiet,
                                       allow_download=a.allow_download, device=a.device)
            print(f"== {lo:.1f}-{hi:.1f} s ({how})")
            for ln in lines:
                print(f"  {ln['a'] + lo:7.2f} {ln['b'] + lo:7.2f}  {ln['text']}")
        return

    m = sm.song_map(a.song, listen=a.listen, status=quiet,
                    allow_download=a.allow_download, device=a.device)
    if a.out:
        Path(a.out).write_text(json.dumps(m, default=str, indent=1), encoding="utf-8")

    print(f"file {m['file']}  {m['file_dur']:.2f} s, sound ends {m['dur']:.2f} s")
    print(f"tempo {m['bpm']:.3f} BPM, {m['beats_per_bar']} beats/bar, bar {m['bar_s']:.4f} s, "
          f"first downbeat {m['first_downbeat_s']:.3f} s")
    print(f"listening: {m.get('path')} ({m.get('how') or 'tempo only'})")
    for w in m.get("warnings") or []:
        print("WARNING", w)
    if int(m["beats_per_bar"]) != 4:
        print("CHECK: bars are not 4/4. Most pop/rap is 4/4; a 6- or 3-beat reading is usually a "
              "misread. Confirm with the user before fitting cuts.")
    print("\nbar  time   energy sung")
    sung = m.get("sung") or []
    for i, (t, e) in enumerate(zip(m["downbeats"], m["energy"])):
        s = ("*" if i < len(sung) and float(sung[i]) > 0.5 else " ")
        print(f"{i + 1:3d} {float(t):7.2f}  {float(e):5.2f}  {s}")
    if m.get("lines"):
        print("\nlyrics (machine-heard; names and slang are often wrong):")
        for ln in m["lines"]:
            print(f"  {ln['a']:7.2f} {ln['b']:7.2f}  {ln['text']}")
    if m.get("sections"):
        print("\nsuggested sections (a guess; confirm against the lyrics):")
        for s in m["sections"]:
            print(f"  bar {s['bar']:3d} {float(s['s']):7.2f} s  {s['kind']}")


if __name__ == "__main__":
    main()
