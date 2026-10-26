# Graph, render order and retakes

## Graph

Start from **the user's own graph** if they have one (their models, LoRAs, sampler and seed stay as
they are; their sampler/scheduler choice is not a bug). Otherwise the pack's
`workflows/HandTieClips_Starter.json`.

```
python scripts/build_graph.py TEMPLATE.json --list          # see every widget
python scripts/build_graph.py TEMPLATE.json OUT.json \
    --shot shot_plan.json --ref ref_plan.json \
    --set pin_mech=motion_context "aspect=16:9 landscape" master_audio_file=<song file> \
          master_audio_start_s=<from fit_cuts> cache_hops=on \
          "prompt_prefix=<one line of look, e.g. Cinematic heist film music video, moody teal and amber lighting>" \
    --save-prefix video/HANDTIECLIPS/<project> --sla-heavy --title "<project> (MV)"
```

- `prompt_prefix` sets the look for every hop (cinematic grade, anime style line, ...). Keep it to
  a sentence, and to the look only: grade, medium, lens, era. Weather and places in it ("steady
  rain, wet reflective streets") reach every hop, interiors included: an indoor plate came out
  with a rainy street behind the counter. Put night and rain in the beats of the outdoor shots. The `prompt` widget can hold a one-line description of the video.
- `cache_hops=on` is what makes retakes cheap.
- `aspect` options include "16:9 landscape", "9:16 portrait", "1:1 square". Ask; don't assume.
- Save a copy of the graph next to the plans, and write a **board**: a markdown file with the
  section table, the hop table (song time, length, R/C, place, who sings, everyone else), the
  settings, and what to check.

## Render order (tell the user)

1. `dry_run = on`: builds every prompt without rendering. Read them on the node's `info` output.
2. `render_through = <a few hops>`: a short first render covering the first continuation, all
   characters and the lip sync.
3. The full run.

## Retakes

With `cache_hops` on, a hop whose inputs did not change loads from disk instead of re-rendering.
So to retake one hop, change only that shot. A **continuation after the changed hop also
re-renders**, because it starts from the changed frames. `locked: true` on a shot forces its old
render to be reused even when its inputs changed (needs a stable `id`); its join with a changed
neighbour was then never generated, so lock continuations with care.

When the user won't reload the graph, give the replacement text to paste into each shot card,
plus any field changes (refs, pace) as a short list.

### Symptom → cause → fix

| The user sees | Likely cause | Fix |
|---|---|---|
| The hop opens on the empty plate, then people pop in | first sentence is about the place | lead with a person acting; place inside that line |
| The camera snaps to the plate's view; faces hidden | plate angle fights the beat's camera | new plate from the beat's camera, or drop the plate from that hop and describe the place in words |
| Camera placed oddly (dashcam facing out) | camera line without a direction | name position + facing + whose faces fill the frame |
| A hard cut at the start of a continuation | first sentence states a new pose or place | open by moving from the previous hop's last pose |
| A different face after a continuation | previous hop ended wide or from behind | end that hop on a face to camera, medium or closer |
| Mouths moving over an instrumental | a singing beat over a part with no vocals | rewrite as action only; check the section table |
| One person stands idle during a verse | the beat gave only the singer an action | give the non-singer a concrete action per half |
| Two people from one character | "they" for one person | use the tag or he/she |
| The picture shows the character sheet layout itself | the beat names no place | name a depicted place in the action line |
| Too much dancing, too little singing | choreography beats | storyline beats; singing to the camera leads each hop |
| People warp through bars, a gate or glass | the beat never fixed which side of the barrier the camera and each person are on, or a person walked into it | name the barrier's place in frame, each side, "stays fixed"; hands on it, never through it |
| Two people both strike, or the one held gets hit | the struck thing is on someone's body and nobody else is held still | one striker, the target away from every body, the others busy with their own business well clear of it |
| A confused, mushy hop | too many actions or conflicting camera/plate | one camera, one clear position per person, one action per person |

### Film symptoms (dialogue, staging, props)

| The user sees | Likely cause | Fix |
|---|---|---|
| A character talks to the audience | "facing the camera" with no eyeline, or a line with no listener | face three-quarter toward the camera, eyes on the other person in a named direction (camera.md, Eyelines) |
| A few words of babble after a line | the hop's last line has no closed mouth and no sound after it | "presses his lips shut", then name a sound (the `after-line` lint) |
| Speech nobody wrote, mid-hop | a face on screen with no mouth state, a voice riding a silent hop, a line said to someone off screen | mouth state on every silent face; voiceless row on silent hops; a visible listener |
| The listener appears beside the lens, staring into it | the camera sits in the listener's seat and the eyes go "just left of the lens" | the camera beside the listener; "eyes on @a, who sits off the frame to the left, his gaze passing well to the left of the camera" |
| Someone turns to the lens in a side-on shot | "face toward the camera" written into a profile framing | "in profile, facing @a"; end the hop on a close shot from beside the listener |
| Two people swap seats or sides | seats given by the frame from one end ("nearer the camera") and read the same from the other end | restate the seating in each shot's own frame |
| A person jumps back between cuts | the gap differs between shots, or a sprint needs room the gap lacks | the same gap as a number in both shots; a short run-up written into the action |
| Someone overshoots into the lens | a run toward the camera with no stop (`no-stop` lint) | where they stop, against a person or a thing in the plate, or "out of frame past the lens" |
| A second copy of a character in a doorway | footsteps or a voice behind a door that is in frame, on a hop carrying one sheet | the source behind the camera, or the newcomer's row on the hop and named |
| A prop doubles, changes or appears from nowhere | introduced after a cut without a count, its shape never fixed, or no picture for a key prop | count and own it from its first shot; fix shape and parts; a key prop gets its own picture |
| A mark draws itself on a page | a hand touches the mark in the shot | the mark "already there and unchanged", the hand beside it |
| Someone climbs out of the boot | a car exit asked for | start them beside the open door, or side-on with the door named |
| A close-up of a body passing the lens | an entrance "from behind the camera" | start them a few steps into the frame, or enter through a door the plate shows |
| A non-singer lip-syncs the song (MV) | their solo shot sits over vocals | move it to an instrumental bar, or keep the singer in frame; closed mouth |
| The passenger ends up at the wheel | a lone person in a car shot | keep the driver's hands in frame, or name the empty driver's side |
| The street outside runs backwards | motion outside written without the car's direction | the car drives forward, lights coming toward the camera and sliding back past the side windows |
| A stranger in a mirror or window | a mirror or glass in frame with nobody named in it | name who is reflected, or turn the mirror away |
| A person warps during a camera circle | a full orbit around a referenced character | half a turn at most, stopping on the face |

Believe what the user reports. Diagnose from the beat, the plate and the settings; give the
replacement; one change per retake so the next render tells you something.
