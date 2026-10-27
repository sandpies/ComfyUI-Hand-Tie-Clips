# Graph, render order and retakes

## Graph

Start from **the user's own graph** if they have one (their models, LoRAs, sampler and seed stay as
they are; their sampler choice is not a bug), else the pack's `workflows/HandTieClips_Starter.json`.

```
python scripts/build_graph.py TEMPLATE.json --list          # every widget and its value
python scripts/build_graph.py TEMPLATE.json OUT.json \
    --shot shot_plan.json --ref ref_plan.json \
    --set pin_mech=motion_context "aspect=16:9 landscape" master_audio_file=<song file> \
          master_audio_start_s=<from fit_cuts> cache_hops=on \
          "establish=" "prompt_prefix=<one line of look, e.g. Cinematic heist film music video, moody teal and amber lighting>" \
    --save-prefix video/HANDTIECLIPS/<project> --sla-heavy --title "<project> (MV)"
```

- `pin_mech`: `motion_context` for many places, `hand_tie` for one take (SKILL.md). Under
  `hand_tie` also set `last_frame_guide=off` and `dialogue_lock=off`.
- `establish` empty (`"establish="`) when `prompt_prefix` carries the look. It is added to hop 1
  and to every `hand_tie` previs, so the same line twice doubles the look and any place words
  in it. Its one job is the medium on hop 1 when nothing else names it.
- `prompt_prefix` is the look only (grade, medium, lens, era), one sentence. Weather and places in
  it reach every hop, interiors included; put them in the beats. `prompt` can hold one line about
  the video.
- `cache_hops=on` makes retakes cheap. `aspect`: "16:9 landscape", "9:16 portrait", "1:1 square";
  ask.
- Save the graph next to the plans with a **board**: section table, hop table (song time, length,
  R/C, place, who sings, everyone else), settings, what to check, and the estimated render time.

## Render order (tell the user)

1. `dry_run = on`: builds every prompt without rendering; read them on the node's `info` output.
2. `render_through = <a few hops>`: a short first render covering the first join, every character
   and the lip sync.
3. The full run. Give the time up front (a 15 s hop at 576p takes roughly 6-9 minutes on a 32 GB
   card). Once the user has queued it, it is a pass or a fail; never plan a re-render of the whole
   piece to fix a few seconds.

## Retakes

With `cache_hops` on, a hop whose inputs did not change loads from disk. To retake one hop, change
only that shot. A `motion_context` continuation after it re-renders too (it starts from the changed
frames); under `hand_tie` a changed beat can re-render its section's previs and every hop tied to it. `locked: true` reuses a
shot's old render even when its inputs changed (needs a stable `id`); its join with a changed
neighbour was never generated, so lock continuations with care.

When the user won't reload the graph, give the text to paste into each shot card plus any field
changes as a short list. One change per retake, so the next render tells you something.

### Symptom, cause, fix

| The user sees | Likely cause | Fix |
|---|---|---|
| The hop opens on the empty plate | first sentence is about the place | lead with a person acting, place inside that line |
| The camera snaps to the plate's view | plate angle fights the beat's camera | a plate from the beat's camera, or drop the plate from that hop |
| A dashcam facing out | camera line without a direction | position + facing + whose faces fill the frame |
| A hard cut at the start of a continuation | the first sentence states a new pose or place | open by moving from the last pose |
| A different face after a continuation | the hop before ended wide or from behind | end it on a face, medium or closer |
| A soft double image at a `hand_tie` join | a hand or the camera moving through the join window | hands at rest, camera still in the first and last 1.3 s (lint `join-calm`) |
| Mouths moving over an instrumental | a singing beat over no vocals | action only; check the section table |
| One person idle during a verse | only the singer has an action | a concrete action for the non-singer |
| Two people from one character | "they" for one person | the tag, or he/she |
| The character sheet layout itself | the beat names no place | a depicted place in the action line |
| People warp through bars or glass | sides of the barrier never fixed | barrier place, each side, "stays fixed", hands on it |
| Two people strike, or the held one is hit | target on someone's body | one striker, target away from every body |
| A confused, mushy hop | too many actions, camera fights plate | one camera, one place and one action per person |
| A character talks to the audience | no eyeline, or a line with no listener | three-quarter, eyes on the other person in a named direction |
| Babble after a line | no closed mouth and sound after the last line | "presses his lips shut", then a sound (lint `after-line`) |
| Speech nobody wrote, mid-hop | a silent face with no mouth state or nothing to do, a voice on a silent hop | mouth state and business; voiceless row |
| The listener beside the lens, staring in | camera in the listener's seat | camera beside the listener, gaze "well to the left of the camera" |
| Someone turns to the lens side-on | "toward the camera" in a profile framing | "in profile, facing @a" |
| Two people swap seats | seating given from one end, read from the other | restate the seating in each shot's frame |
| A person jumps back between cuts | different gap, or a sprint needs room | the same gap as a number; a short run-up |
| Someone overshoots into the lens | a run with no stop (lint `no-stop`) | a stop against a person or thing, or "out of frame past the lens" |
| A copy of a character in a doorway | a sound behind a door in frame | the source behind the camera, or the newcomer's row on the hop |
| A prop doubles, changes or appears | uncounted after a cut, or no picture | count and own it; a key prop gets a picture |
| A mark draws itself on a page | a hand touches it | "already there and unchanged", the hand beside it |
| Someone climbs out of the boot | a car exit | start beside the open door, or side-on with the door named |
| A non-singer lip-syncs (MV) | their solo over vocals | move it to an instrumental bar, or keep the singer in frame |
| The passenger at the wheel | a lone person in a car shot | the driver's hands in frame, or the empty side named |
| The street runs backwards | outside motion not tied to the car | lights coming toward the camera, sliding back past the windows |
| A stranger in a mirror | a mirror with nobody named in it | name who is reflected, or turn it away |
| A person warps during a circle | a full orbit | half a turn at most, stopping on the face |

Believe what the user reports. Diagnose from the beat, the plate and the settings, and give the
replacement.
