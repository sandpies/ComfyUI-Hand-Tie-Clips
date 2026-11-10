"""Write a plan into a ComfyUI workflow, by widget NAME.

    python build_graph.py TEMPLATE.json OUT.json --shot shot_plan.json --ref ref_plan.json \
        --set master_audio_file=song.wav master_audio_start_s=0.25 aspect="16:9 landscape" \
        --save-prefix video/HANDTIECLIPS/my_mv --sla-heavy

The template is any saved workflow holding one `HandTieClips` (H3 Ref2VA Chain)
node, normally the user's own graph or the pack's `workflows/HandTieClips_Starter.json`.
Everything else in the graph (models, LoRAs, sampler, seed) is left exactly as
the user had it.

`widgets_values` is positional, so names are mapped to slots from the node's own
INPUT_TYPES (sockets take no slot; `seed` is followed by a hidden
`control_after_generate` slot). If the template's slot count does not match, the
template is from another node version and nothing is written.

Use `--list` to print every widget name with its current value.

**The audit gate.** With --shot/--ref, nothing is written until `check_plan.py` has
run on the plan with the scene map (`--map scene_map.json`) and every error,
warning and lint it prints is either fixed or waived in writing:

    --waivers waivers.json   [{"match": "text from the flagged line", "why": "proven safe because ..."}]

A flagged line is waived when it contains a waiver's `match`; every waiver needs a
`why`. The checker must run its part 1 (the node's own validator); if it cannot,
nothing is written. `--no-mv` is passed when the graph has no master_audio_file.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _htc  # noqa: E402

SCALARS = ("INT", "FLOAT", "STRING", "BOOLEAN")
SLA_LEVELS = ("Off", "Light", "Medium", "Heavy Enforcement")


def widget_names(pack):
    src = (pack / "h3_ref_chain.py").read_text(encoding="utf-8")
    i = src.index("def INPUT_TYPES")
    body = src[i:src.index("RETURN_TYPES", i)]
    items = re.findall(r'^\s{8,16}"([a-z_0-9]+)":\s*\(\s*(\[|"[A-Z_]+"|[A-Za-z_\.\(\)]+)', body, re.M)
    names, types = [], {}
    for n, t in items:
        tt = t.strip('"')
        if t == "[" or tt in SCALARS or not tt.isupper():  # combos and scalars are widgets
            names.append(n)
            types[n] = tt if tt in SCALARS else "COMBO"
            if n == "seed":
                names.append("control_after_generate")
                types["control_after_generate"] = "COMBO"
    return names, types


def lora_path(pack, name):
    """The name ComfyUI lists for a LoRA: its path under models/loras.

    A bare filename that sits in a subfolder (`some_folder/loras/x.safetensors`)
    loads as a red "missing" entry, so it is looked up and written with the
    subfolder, in the OS separator ComfyUI lists it with. Not found: as given.
    """
    root = Path(pack).resolve().parents[1] / "models" / "loras"
    if not root.is_dir() or (root / name).is_file():
        return name
    hits = sorted(h for h in root.rglob(Path(name).name)
                  if h.is_file() and ".cache" not in h.relative_to(root).parts)
    if not hits:
        print(f"  warning: LoRA {name} not found under {root}; written as given")
        return name
    return os.sep.join(hits[0].relative_to(root).parts)


def coerce(kind, raw):
    """By the widget's declared type: a FLOAT saved as 0 is still a float."""
    if kind == "BOOLEAN":
        return raw.lower() in ("1", "true", "on", "yes")
    if kind == "INT":
        return int(float(raw))
    if kind == "FLOAT":
        return float(raw)
    return raw


def save_prefix_slot(pack):
    """Index of filename_prefix among HTCSaveVideo's widgets (sockets take no slot)."""
    src = (pack / "save_video.py").read_text(encoding="utf-8")
    i = src.index("class HTCSaveVideo")
    body = src[src.index("def INPUT_TYPES", i):src.index("RETURN_TYPES", i)]
    items = re.findall(r'^\s{12,20}"([a-z_0-9]+)":\s*\(\s*(\[|"[A-Z_]+"|[A-Za-z_\.\(\)]+)', body, re.M)
    widgets = [n for n, t in items if t == "[" or t.strip('"') in SCALARS or not t.strip('"').isupper()]
    return widgets.index("filename_prefix") if "filename_prefix" in widgets else None


def audit(a, pack, w, slot):
    """Run check_plan.py on the plan and refuse to write while anything is unresolved."""
    import subprocess
    if not (a.shot and a.ref):
        sys.exit("audit gate: give both --shot and --ref (the checker reads them together).")
    if not a.map:
        sys.exit("audit gate: --map scene_map.json is required (references/directing.md, 'The scene map'). "
                 "Write the map before the beats; the checker reads sides, goals, props, states and plate "
                 "geometry from it.")
    pin = str(w[slot["pin_mech"]]) if "pin_mech" in slot else "motion_context"
    mv = bool(str(w[slot["master_audio_file"]]).strip()) if "master_audio_file" in slot else False
    cmd = [sys.executable, str(Path(__file__).resolve().parent / "check_plan.py"), a.shot, a.ref,
           "--pin-mech", pin, "--map", a.map] + ([] if mv else ["--no-mv"]) + (["--htc", a.htc] if a.htc else [])
    cmd += ["--refs-dir", a.refs_dir] if a.refs_dir else []
    out = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8").stdout
    if "SKIPPED: could not import the node's validator" in out:
        sys.exit("audit gate: check_plan.py could not run the node's validator (run with ComfyUI's Python). "
                 "Nothing written.")
    flagged = [ln.strip() for ln in out.splitlines() if re.match(r"^\s{2}[EWL] ", ln)]
    waivers = []
    if a.waivers:
        waivers = json.loads(Path(a.waivers).read_text(encoding="utf-8"))
        bad = [x for x in waivers if not str(x.get("match") or "").strip() or not str(x.get("why") or "").strip()]
        if bad:
            sys.exit(f"audit gate: every waiver needs a 'match' and a 'why'; {len(bad)} do not.")
    open_ = [f for f in flagged if not any(str(x["match"]) in f for x in waivers)]
    errors = [f for f in flagged if f.startswith("E ")]
    if errors or open_:
        print(f"audit gate: {len(open_)} unresolved line(s) from check_plan.py; nothing written.")
        for f in (errors + [x for x in open_ if x not in errors]):
            print("  ", f[:240])
        print("Fix each one, or add a waiver with the reason it is safe (--waivers).")
        sys.exit(3)
    used = [x for x in waivers if any(str(x["match"]) in f for f in flagged)]
    print(f"audit gate: passed ({len(flagged)} flagged line(s), all waived by {len(used)} waiver(s); "
          f"pin_mech {pin}, {'music video' if mv else 'film'}).")
    for x in used:
        print(f"   waived '{x['match'][:60]}': {x['why'][:120]}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("template")
    ap.add_argument("out", nargs="?")
    ap.add_argument("--shot")
    ap.add_argument("--ref")
    ap.add_argument("--set", nargs="*", action="extend", default=[], metavar="name=value")
    ap.add_argument("--save-prefix")
    ap.add_argument("--title")
    ap.add_argument("--sla-heavy", action="store_true",
                    help="set H3SLAAttention reference_protection to Heavy Enforcement")
    ap.add_argument("--lora", nargs="*", action="extend", default=[], metavar="file[:strength]",
                    help="replace the LoRA loader's stack with these LoRAs (in order)")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--htc")
    ap.add_argument("--map", help="scene_map.json; required with --shot/--ref (the audit gate)")
    ap.add_argument("--waivers", help="JSON list of {match, why}: flagged lines proven safe")
    ap.add_argument("--refs-dir", help="reference folder for the checker (default <ComfyUI>/input/h3_refs)")
    a = ap.parse_args()

    pack = _htc.find_pack(a.htc)
    names, types = widget_names(pack)
    g = json.loads(Path(a.template).read_text(encoding="utf-8"))
    chains = [n for n in g.get("nodes", []) if n.get("type") == "HandTieClips"]
    if len(chains) != 1:
        sys.exit(f"template must hold exactly one HandTieClips node, found {len(chains)}")
    node = chains[0]
    w = node["widgets_values"]
    if len(w) != len(names):
        sys.exit(f"template has {len(w)} widget slots, this pack's node has {len(names)}. "
                 f"Re-save the template in the current ComfyUI first.")
    slot = {n: k for k, n in enumerate(names)}

    if a.list:
        for k, n in enumerate(names):
            print(f"{k:3d} {n:28s} {str(w[k])[:60]!r}")
        return
    if not a.out:
        sys.exit("give an output path (or --list)")

    changed = []
    if a.shot:
        text = Path(a.shot).read_text(encoding="utf-8")
        json.loads(text)
        w[slot["shot_plan"]] = text
        if "h3_plan_backup" in (node.get("properties") or {}):
            node["properties"]["h3_plan_backup"] = text  # the editor's Simple-mode stash
        changed.append("shot_plan")
    if a.ref:
        text = Path(a.ref).read_text(encoding="utf-8")
        json.loads(text)
        w[slot["ref_plan"]] = text
        changed.append("ref_plan")
    for kv in a.set:
        k, _, v = kv.partition("=")
        if k not in slot:
            sys.exit(f"no widget named {k!r} (use --list)")
        # the style line reaches every hop, indoor ones too: weather and places belong in the beats
        hit = re.findall(r"\b(rain\w*|snow\w*|fog\w*|storm\w*|night|day|sunset|sunrise|streets?|beach|"
                         r"city|forest|cafe|bar|club|room|indoors?|outdoors?)\b", v, re.I) if k == "prompt_prefix" else []
        if hit:
            print(f"  WARNING prompt_prefix names {', '.join(sorted(set(h.lower() for h in hit)))}: it is sent to every "
                  f"hop. Keep it to the look (medium, grade, lens, era) and put time, weather and place in the beats.")
        w[slot[k]] = coerce(types[k], v)
        changed.append(f"{k}={w[slot[k]]!r}")
    if a.title:
        node["title"] = a.title
    for n in g["nodes"]:
        if a.save_prefix and n.get("type") == "HTCSaveVideo":
            vals = n.get("widgets_values")
            k = save_prefix_slot(pack)
            if isinstance(vals, list) and k is not None and len(vals) > k and isinstance(vals[k], str):
                vals[k] = a.save_prefix
                changed.append("HTCSaveVideo prefix")
        if a.save_prefix and n.get("type") in ("SaveVideo", "VHS_VideoCombine"):
            vals = n.get("widgets_values")
            if isinstance(vals, list) and vals and isinstance(vals[0], str):
                vals[0] = a.save_prefix
                changed.append(f"{n['type']} prefix")
            elif isinstance(vals, dict) and "filename_prefix" in vals:
                vals["filename_prefix"] = a.save_prefix
                changed.append(f"{n['type']} prefix")
        if a.lora and n.get("type") == "LTX_lora_loader":
            stack = []
            for item in a.lora:
                f, _, st = item.partition(":")
                f = lora_path(pack, f)
                stack.append({"on": True, "lora": f, "str": float(st or 1), "v": 1, "a": 1, "t": 1})
            # the loader rebuilds its stack from properties.stack_data, a JSON string, on load
            txt = json.dumps(stack, separators=(",", ":"))
            n.setdefault("properties", {})["stack_data"] = txt
            vals = n.get("widgets_values")
            if isinstance(vals, list) and len(vals) > 1:
                vals[1] = txt
            changed.append(f"LoRA stack: {', '.join(x['lora'] for x in stack)}")
        if n.get("type") == "H3SLAAttention":
            vals = n.get("widgets_values") or []
            hit = [k for k, v in enumerate(vals) if v in SLA_LEVELS]
            cur = vals[hit[0]] if hit else "not found"
            if a.sla_heavy and hit:
                vals[hit[0]] = "Heavy Enforcement"
                changed.append(f"SLA reference_protection {cur} -> Heavy Enforcement")
            else:
                print(f"SLA reference_protection: {cur}")
    if a.shot or a.ref:
        audit(a, pack, w, slot)
    Path(a.out).write_text(json.dumps(g, indent=1, ensure_ascii=False), encoding="utf-8")
    print("wrote", a.out)
    for c in changed:
        print("  set", c)
    for k in ("pin_mech", "aspect", "master_audio_file", "master_audio_start_s", "dry_run", "render_through",
              "cache_hops", "prompt_prefix"):
        if k in slot:
            print(f"  {k} = {str(w[slot[k]])[:70]!r}")


if __name__ == "__main__":
    main()
