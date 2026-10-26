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
