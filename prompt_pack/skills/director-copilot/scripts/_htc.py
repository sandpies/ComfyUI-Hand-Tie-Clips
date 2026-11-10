"""Find the Hand-Tie-Clips pack and the ComfyUI checkout it lives in.

Every script in this skill reuses the pack's own modules (songmap, mv_solver,
planner) instead of carrying copies, so a rule fixed in the pack is fixed here
too. That needs two paths:

  pack   the ComfyUI-Hand-Tie-Clips folder (holds h3_ref_chain.py)
  comfy  the ComfyUI root (holds the `comfy` package the validator imports)

Resolution order: --htc / HTC_PACK, then walking up from this file (the skill
ships inside the pack at prompt_pack/skills/), then COMFYUI_ROOT/custom_nodes.
"""
from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path

PACK_MARKER = "h3_ref_chain.py"


def find_pack(explicit=None):
    cands = []
    if explicit:
        cands.append(Path(explicit))
    if os.environ.get("HTC_PACK"):
        cands.append(Path(os.environ["HTC_PACK"]))
    here = Path(__file__).resolve()
    cands.extend(here.parents)
    root = os.environ.get("COMFYUI_ROOT")
    if root:
        cands.extend(sorted((Path(root) / "custom_nodes").glob("*Hand-Tie-Clips*")))
    for c in cands:
        if (c / PACK_MARKER).is_file():
            return c
    sys.exit("Hand-Tie-Clips pack not found. Pass --htc <path to ComfyUI-Hand-Tie-Clips> "
             "or set HTC_PACK / COMFYUI_ROOT.")


def import_pure(pack, name):
    """A ComfyUI-free module of the pack (songmap, mv_solver, plan, refs)."""
    sys.path.insert(0, str(pack))
    return importlib.import_module(name)


def import_package_module(pack, name):
    """A module that needs the pack imported as a package (planner)."""
    comfy = pack.parent.parent
    for p in (str(comfy), str(pack.parent)):
        if p not in sys.path:
            sys.path.insert(0, p)
    return importlib.import_module(f"{pack.name}.{name}")


def refs_dir(pack):
    return pack.parent.parent / "input" / "h3_refs"
