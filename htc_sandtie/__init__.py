"""SandTie PromptRig — clean-room MiniMax H3 writer engine inside Hand Tie Clips.

Powers both:
- The reworked `Standard` tab inside `HandTieClips` (`js/editor/standard_writer.js`)
- The standalone plug-and-play `SandTiePromptRig` node (`sandtie_node.py`)
"""
from __future__ import annotations

from . import beat_grid, catalogs, dialogue, director_cards, finisher, refs, vision_cv, writer

__all__ = [
    "beat_grid",
    "catalogs",
    "dialogue",
    "director_cards",
    "finisher",
    "refs",
    "vision_cv",
    "writer",
]
