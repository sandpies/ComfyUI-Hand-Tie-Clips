# htc-music-video (agent skill)

An agent skill that directs and produces music videos and short films with the Hand-Tie-Clips
node, back and forth with the user: brief → song or script → story, cast and voices → plate
prompts → directed shot plans (camera, multi-shot hops, eyelines, dialogue and silence) →
checked → graph → retakes.

It is for **agent harnesses that load skills** (a folder with a `SKILL.md` plus scripts the agent
can run), with any model behind them, hosted or local. It is not a chat prompt: the agent has to
run the scripts. For a plain chat app, use `prompt_pack/AUTHORING_PROMPT.md` instead.

## Install

The skill is in the GitHub repository (`prompt_pack/skills/htc-music-video/`), not in the
Comfy registry download, which ships the node only. Clone or download it from GitHub.

Copy this whole folder into your harness's skills folder (for example `~/.claude/skills/` for
Claude Code; other harnesses document their own). If the copy no longer sits inside the pack, tell
the scripts where the pack is:

```
HTC_PACK=/path/to/ComfyUI/custom_nodes/ComfyUI-Hand-Tie-Clips
```

or pass `--htc <path>` to each script. The scripts import the pack's own modules (`songmap`,
`mv_solver`, `planner`, the node's widget list), so they stay in step with the installed node.

## Requirements

- The Hand-Tie-Clips pack installed in ComfyUI.
- ComfyUI's own Python for `song_map.py` and `check_plan.py` part 1 (numpy, PyAV, torch).
  Lyrics need the `openai/whisper-small` weights already downloaded, or `--allow-download`.
- Any Python 3.9+ for `fit_cuts.py` and `build_graph.py`.
- Everything runs on the CPU by default.

## Scripts

| script | does |
|---|---|
| `song_map.py` | tempo, downbeats, per-bar energy, sung bars, timed lyrics; `--relisten` for missed spans |
| `fit_cuts.py` | hop lengths + `master_audio_start_s` so every cut lands on a downbeat |
| `check_plan.py` | the node's own validator, then the lints learned from renders (`--no-mv` for a film) |
| `build_graph.py` | writes the plans and settings into a saved workflow by widget name |

## Local models

The skill is written as stages with stop points and numbered rules so a smaller model can follow
it literally. Give the model a context of 32k+ (the references are read on demand, one per stage),
and a low temperature (0.3-0.5) so the JSON stays strict.
