# Director co-pilot (agent skill)

An agent skill that directs and produces short films, microdramas, dialogue scenes and music
videos with the Hand-Tie-Clips node, back and forth with the user. It reasons like a director
and a script supervisor before it writes: the scene's want and turn, the set read from the plate,
blocking as fixed position phrases, coverage, a cut list where every cut has a reason, and a
START → END row per hop that the user vets. Beats are then written from that sheet, checked, and
read back as the node will send them: brief → song or script → story, cast and voices → plates →
continuity sheet → directed shot plans → check → graph → retakes.

It runs three ways, chosen in the brief ([pipelines](references/pipelines.md)):

| pipeline | for | how |
|---|---|---|
| `agent` | a hosted or frontier model in an agent harness | the model runs every script and builds the graph |
| `local-agent` | a local model (Qwen, Llama, Gemma...) in an agent harness that can run commands | the same scripts, read one page at a time, one hop written and checked at a time, progress kept in `STATE.md` |
| `local-chat` | a chat window with no commands (LM Studio, Open WebUI, llama.cpp chat) | you are the hands: the model says exactly what to click and paste in ComfyUI's studio, and what to paste back |

For a one-shot prompt with no stages at all, `prompt_pack/AUTHORING_PROMPT.md` is still there.

## Install

The skill is in the GitHub repository (`prompt_pack/skills/director-copilot/`), not in the
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
| `transitions.py` | dips to black or white and flashes on a rendered film |
| `post.py` | finish pass: measure cuts, kicks and soundtrack offset; cue sheet; kinetic text and fx burned onto the film (needs ffmpeg with libass and opencv; rembg and a YuNet face model optional) |

## Local models

The skill is written as stages with stop points, each naming the pages to read, so a smaller model
can follow it literally. Rules that `check_plan.py` enforces live in the checker, not in the pages,
and form rules sit on their own page (`mv.md`, `film.md`, `one_take.md`), so a session reads only
its own. Give the model a context of 32k+ (16k is the floor for `local-chat`), and a low
temperature (0.3-0.5) so the JSON stays strict.

- **`local-agent`:** install the folder as for any agent. The model reads `SKILL.md`, then only
  the page or section each stage names, and writes `STATE.md` in the project folder at every
  stop. When its context fills, start a new session; it picks up from `STATE.md`.
- **`local-chat`:** put `SKILL.md` and `references/pipelines.md` in the system prompt (about 8k
  tokens). The model asks for each further page when a stage needs it; paste it in. Keep the
  `PROJECT STATE` block it prints at every stop, and start a new chat with it at stages 4, 8
  and 11. If you can open a terminal, run the `check_plan.py` command it gives you and paste
  the output back; that check catches what a small model misses.
