# Pipelines: who does the hands-on work

The stages, stop points, rules and [before every render](../SKILL.md#before-every-render)
questions are the same for every model. What changes is **who runs the scripts, how much of the
skill fits in the model's context, and how work moves between the model and ComfyUI.** A smaller
model does not get looser rules; it gets smaller steps and the user's hands.

Ask once, in the brief, and write the answer into the [project state](#the-project-state):

> "What runs me? (a) a hosted or frontier model in a harness that can run commands,
> (b) a local model in a harness that can run commands (Qwen, Llama, Gemma in an agent CLI),
> or (c) a chat window with no commands (LM Studio, Open WebUI, a llama.cpp chat)?"

| | `agent` | `local-agent` | `local-chat` |
|---|---|---|---|
| Who runs scripts | you | you | the user, from commands you print (optional) |
| What you read | the stage's pages, whole | one page or one section at a time | what the user pastes in |
| How plans reach the node | `shot_plan.json` + `ref_plan.json` files, `build_graph.py` | the same, written one hop at a time | paste blocks for the node's tabs |
| The check | `check_plan.py --map` | `check_plan.py --map` after every hop | the user runs `check_plan.py`, or you answer the 13 questions in writing |
| Dry-run read | you read every hop prompt | you read every hop prompt | the user pastes the `info` text back; you read it |
| Memory | the conversation | `STATE.md` in the project folder | the state block the user keeps and re-pastes |
| Fresh session | rarely | at a stage boundary when context runs past ~60% | at stages 4, 8 and 11, and whenever replies start forgetting |

If you are unsure which applies, test: try to run `python --version`. If it runs, you are an
`agent` or `local-agent`; if you cannot run anything, you are `local-chat`. A small or quantized
model in a harness is `local-agent` even when the harness could hold more.

## The project state

One block, rewritten at every stop point. It is what lets a small model, or a new session, pick
the piece up without the conversation that made it. Fixed phrases live here so they are copied,
never retyped.

```text
PROJECT STATE
project: <name>   form: MV | film   pipeline: agent | local-agent | local-chat
pin_mech: motion_context | hand_tie | sand_tie   aspect: 16:9 | 9:16 | ...
stage done: <n> <name>   next: <n> <name>   waiting for: <what the user owes>
song: <file in h3_refs> start <s>   tempo <bpm>   (MV only)
cast: @tag = <who, one line>  (sheet file, voice file)
plates: @tag = <file> (<camera: where it stands, facing what>)
spots: <fixed phrase> | <fixed phrase> | ...
outfits: @tag: <outfit phrase, defining cut + colour>
hops: n | secs | kind | place | START -> END (one row each)
open flags: <lint or question still open, with its reason>
```

- `agent`: keep it in the conversation; write it to the project folder only if the user asks.
- `local-agent`: write it to `<project>/STATE.md` at every stop, before you show the user
  anything. A new session reads `SKILL.md`, this page and `STATE.md`, nothing else, then the
  page the next stage names.
- `local-chat`: print it in a code block at the end of every stop. Tell the user to keep the
  latest one; a new chat starts with `SKILL.md`, this page and that block.

## agent

The stages exactly as [SKILL.md](../SKILL.md#the-stages) gives them. Nothing on this page
changes them.

## local-agent

You can run the scripts; your context and your output length are the limits. Everything on
[SKILL.md](../SKILL.md) still holds, with these changes to how you work:

1. **Read narrowly.** `SKILL.md` once per session. For each stage, the page it names, and of the
   long pages only the sections below. Never hold more than two reference pages at once; drop
   one (start a fresh session from `STATE.md`) before reading a third.

   | Stage | Read |
   |---|---|
   | 2-3 Song, measure | `song.md` |
   | 4 Treatment, story & cast | `story_cast_plates.md` Story, Cast; MV: `mv.md` section 1; film: `film.md`; `status.md` "Unproven" only, to pick the two or three rules this piece tests |
   | 5 Plates | `story_cast_plates.md` from "Plates" to the end |
   | 6 Fit | `beats.md` sections 1-2 |
   | 7 Map | `directing.md` "The scene map" |
   | 8 Sheet | `continuity.md` sections 1-7 |
   | 9 Plans | `beats.md` sections 3-5, `camera.md` "Writing shots" and "Writing the move", `performance.md`; MV: `mv.md` sections 2-3, `continuity.md` 8; one take: `one_take.md`; adult: `adult.md` |
   | 10 Check | `beats.md` section 6 |
   | 11-12 Graph, retakes | `graph_render_retake.md` |
   | 13 Finish | `post.md`, `camera.md` "Transitions" |
   | any | `techniques.md`: only the heading for the one technique you are looking up |

   Find a section by its heading (`rg -n "^## " <page>`) and read from there to the next `## `.
2. **Write the plan one hop at a time.** At stage 9, write hop 1's shot notes, then its beats into
   `shot_plan.json`, then run `check_plan.py ... --map scene_map.json`. Fix every error that
   names hop 1 before writing hop 2. A long plan written in one reply is where small models drop
   a spot phrase or a closing bracket.
3. **Copy, don't retype.** Spot, outfit and place phrases come out of `STATE.md` character for
   character. If you notice you are paraphrasing one, stop and copy it.
4. **Write files with the file tool, never through the shell.** Quotes and backslashes in an
   `echo` or heredoc break JSON. Keep JSON strict: double quotes, no trailing commas, no comments.
5. **Never invent script output.** When a script fails, show the exact command and error. Never
   call a plan valid if `check_plan.py` printed `SKIPPED` for part 1 (it needs ComfyUI's own
   Python).
6. **Update `STATE.md` at every stop, then show the user.** If the user's next answer changes a
   row, change the state first.

## local-chat

The user is your hands: they click in ComfyUI, run any command, and paste results back. You
cannot open files, so they paste each page you need. Your job is to make every round trip
short and exact.

**Setup.** The user loads `SKILL.md` and this page as the system prompt (or pastes them as the
first message). About 8k tokens; give the model at least 16k context, 32k is comfortable.

**Every stop ends with a hand-off block,** after what the user reads, and then the state block:

```text
DO IN COMFYUI
1. <one click or paste per line, naming the tab, field or button exactly>
2. ...
PASTE BACK
- <exactly what to copy back, and from where>
NEXT PAGE
- paste references/<page>.md (section "<heading>") in your next message
```

Ask for a page before the stage that needs it, one page per message. If the user cannot paste
it, say which rules you are working without.

**Stage by stage, inside the node.** The `⬒ studio` button on the chain node opens the
work area; the tabs and buttons named here are on it.

| Stage | The user does | You get back |
|---|---|---|
| 2 Song | writes or generates the song (studio's song card, or any tool), saves it into `input/h3_refs/` | the file name |
| 3 Measure | studio: pick the song, **Analyze Beats & Solve Cuts** | the section table text (start, end, lyrics). Machine-heard: ask the user to correct the lyrics by ear |
| 5 Plates | paints each plate from your prompt (studio's **+ Location Plate** card, or any image tool), saves it into `input/h3_refs/` | if you can see images, the plate attached; if not, the user's answers to: what is near, far, left, right; camera height; which way it faces; anything not in your prompt |
| 6 Fit | studio: **Lock Song & Cuts → Chain** (writes the song, its start and the hop lengths onto the node) | the hop lengths it wrote |
| 7-8 Map, sheet | reads and vets | corrections |
| 9 Plans | reads and vets each hop as you write it (one hop's JSON object per message); then pastes your final whole `shot_plan` array into the **Script** tab's `JSON` drawer (it replaces the plan) and the whole `ref_plan` into the **Refs** tab's `JSON` drawer | "done", or the error the drawer shows |
| 10 Check | if they can open a terminal: runs the `check_plan.py` command you print, from the folder you name | the full output |
| 11 Graph | loads `workflows/HandTieClips_Starter.json` (or their last working graph for this project), sets the widgets you list, `dry_run` = `on`, queues | the `info` text from the chain preview, all of it |
| 12 Retakes | watches, and says per hop what went wrong and at what second | that description |
| 13 Finish | stitches in their editor, or runs `transitions.py` from your command | - |

**The final plan block** is the hop objects you already showed, copied unchanged into one
array in hop order. Never rewrite a hop while assembling; if one needs a change, change it,
show it, then assemble. If the plan is too long for one reply, say so and send it in two
messages marked "part 1 of 2 - do not paste yet" and "part 2 of 2 - paste both together".

**The check without a terminal.** If the user cannot run `check_plan.py`, you are the check:
before every hand-off at stage 9-11, answer each of the 13 [before every
render](../SKILL.md#before-every-render) questions in one line, per hop, in your reply, and say
plainly that the script check did not run. The dry-run read at stage 11 is then the last line of
defence: read every hop prompt against its sheet row (START = previous END, spot phrases,
eyelines, props, END framing) and list each mismatch with its fix.

**Settings you list at stage 11** name the widget and the value, one per line: `pin_mech`,
`steps` (8 on turbo), `master_audio_file` and its start (MV), aspect and length, and `establish`
and `prompt` cleared or set (a reused graph keeps the last project's). Everything else stays as
the graph has it; say so.

**Commands you print** run from a terminal opened in the skill folder. Write the full line with
the user's own paths, using ComfyUI's Python for `song_map.py` and `check_plan.py`:

```text
<ComfyUI>/python_embeded/python.exe scripts/check_plan.py <project>/shot_plan.json <project>/ref_plan.json --map <project>/scene_map.json
```

For that the user saves your JSON blocks as files: give each block its file name on the line
above it.
