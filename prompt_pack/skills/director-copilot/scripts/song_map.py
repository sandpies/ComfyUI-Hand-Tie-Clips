"""Measure a song: tempo, downbeats, per-bar energy, sung bars and timed lyrics.

    python song_map.py SONG.wav --out songmap.json            # tempo only, seconds
    python song_map.py SONG.wav --listen --out songmap.json   # + lyrics (Whisper, CPU)
    python song_map.py SONG.wav --relisten 40-66 66-84        # re-transcribe gaps
    python song_map.py SONG.wav --lyrics LYRICS.md --out songmap.json
                                    # KNOWN lyrics: time every line by forced alignment (MMS_FA on
                                    # the vocal stem). Far better than --listen on sung, bilingual
                                    # vocals; prints a section table with bars

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
    # Lyrics can hold Japanese or other non-Latin text; a cp1252 console crashed printing them.
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    ap = argparse.ArgumentParser()
    ap.add_argument("song")
    ap.add_argument("--listen", action="store_true", help="also transcribe lyrics")
    ap.add_argument("--relisten", nargs="*", default=[],
                    help="re-transcribe these spans, e.g. 40-66 (Whisper skips quiet or dense bits)")
    ap.add_argument("--out", help="write the full map here (JSON)")
    ap.add_argument("--lyrics", help="known lyrics (txt/md): time them by forced alignment")
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

    if a.lyrics:
        return lyrics_mode(a, sm, quiet)

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



def lyrics_mode(a, sm, quiet):
    """Forced alignment of known lyrics on the vocal stem, then a section table on the bar grid."""
    import numpy as np
    text = Path(a.lyrics).read_text(encoding="utf-8")
    m = sm.song_map(a.song, listen=False, status=quiet, allow_download=a.allow_download, device=a.device)
    cache = Path(a.out or a.song).with_suffix("").as_posix() + ".vocals.npz"
    if Path(cache).is_file():
        z = np.load(cache)
        vocal, sr, how = z["v"], int(z["sr"]), "vocal stem from cache " + Path(cache).name
    else:
        audio, sr0 = sm.load_stereo(a.song)
        vocal, sr, how = sm.vocal_stem(audio, sr0, status=quiet, allow_download=a.allow_download, device=a.device)
        if vocal is None:
            sys.exit("no vocal stem: " + how)
        np.savez_compressed(cache, v=np.asarray(vocal, np.float32), sr=sr)
    print(f"file {m['file']}  {m['file_dur']:.2f} s, sound ends {m['dur']:.2f} s")
    print(f"tempo {m['bpm']:.3f} BPM, bar {m['bar_s']:.4f} s, first downbeat {m['first_downbeat_s']:.3f} s")
    print(f"vocals: {how}")
    al, note = sm.align_lyrics(np.asarray(vocal, np.float32), sr, text, status=print,
                               allow_download=a.allow_download, device=a.device)
    print(note)
    if not al:
        sys.exit("no trustworthy alignment: check the lyrics match the song as sung")
    bars = [float(t) for t in m["downbeats"]]

    def bar(t):
        return max(1, sum(1 for d in bars if d <= t + 0.15))
    print()
    print("line-by-line (forced alignment; score 0-1; stacked or gang vocals score low but stay in order -- under 0.12 = check by ear):")
    sec_rows, last = [], None
    for ln in al:
        flag = "  <- CHECK" if ln["score"] < 0.12 else ""
        kj = "  (kanji skipped)" if ln.get("kanji") else ""
        print(f"  {ln['a']:7.2f} {ln['b']:7.2f}  bar {bar(ln['a']):3d}  {ln['score']:.2f}  {ln['text']}{kj}{flag}")
        if ln["section"] != last:
            sec_rows.append([ln["section"], ln["a"], ln["b"]])
            last = ln["section"]
        else:
            sec_rows[-1][2] = ln["b"]
    print()
    print("sections (first word -> last word; snap starts to the downbeat at or just before):")
    for name, s0, s1 in sec_rows:
        db = max([d for d in bars if d <= s0 + 0.15] or [0.0])
        print(f"  {s0:7.2f}-{s1:7.2f}  bar {bar(s0):3d} (downbeat {db:6.2f})  {name}")
    gaps = [(x[2], y[1]) for x, y in zip(sec_rows, sec_rows[1:]) if y[1] - x[2] > 2 * m["bar_s"]]
    for g0, g1 in gaps:
        print(f"  {g0:7.2f}-{g1:7.2f}  no lyrics for {g1 - g0:.1f} s (instrumental or ad-libs)")
    if a.out:
        m["aligned"] = al
        m["aligned_sections"] = sec_rows
        Path(a.out).write_text(json.dumps(m, default=str, indent=1, ensure_ascii=False), encoding="utf-8")
        print("wrote", a.out)


if __name__ == "__main__":
    main()
