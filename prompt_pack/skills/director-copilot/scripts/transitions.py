"""Add dips to black or white (and flashes) at chosen times of a rendered video.

    python transitions.py film.mp4 out.mp4 12:white:0.5 36:black:1.0 60:flash:0.25

Each item is time:kind:length in seconds. The dip is centred on the time: it fades to black
(or white) over the first half of the length and back over the second half, so put the time on
the cut. `flash` is a short white burst (use 0.2-0.4 s). The sound is copied unchanged.

Seams between restart hops are hard cuts at known times: the sum of the hop lengths before them.
Runs ffmpeg on the CPU; needs ffmpeg on the PATH.
"""
import subprocess
import sys


def main():
    if len(sys.argv) < 4:
        sys.exit(__doc__)
    src, out, items = sys.argv[1], sys.argv[2], sys.argv[3:]
    dark, light = [], []
    for it in items:
        t, kind, length = it.split(":")
        half = float(length) / 2
        ramp = f"max(0,1-abs(t-{float(t)})/{half})"  # 0 away from the cut, 1 on it
        if kind == "black":
            dark.append(ramp)
        elif kind in ("white", "flash"):
            light.append(ramp)
        else:
            sys.exit(f"unknown kind {kind!r}: black, white or flash")
    d = "+".join(dark) or "0"
    w = "+".join(light) or "0"
    # brightness lifts or drops luma; saturation goes to 0 at the peak so white is white, not tinted
    vf = (f"eq=eval=frame:brightness='min(1,{w})-min(1,{d})':"
          f"saturation='1-min(1,{w}+{d})'")
    cmd = ["ffmpeg", "-y", "-v", "error", "-i", src, "-vf", vf, "-c:v", "libx264", "-crf", "16",
           "-preset", "medium", "-c:a", "copy", out]
    print(" ".join(cmd))
    subprocess.run(cmd, check=True)
    print("wrote", out)


if __name__ == "__main__":
    main()
