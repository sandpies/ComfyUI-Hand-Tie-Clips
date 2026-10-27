# Fitting the cuts and writing the plans

## 1. Choose hop kinds

**`motion_context`:**
- **R** = hop 1 or a **restart**: a cut to a new setup; its whole length plays. One at every
  section change and every new place.
- **C** = **continuation**: carries straight on from the previous hop's last frames; its first 22
  frames are the previous hop's and are dropped. For a section over 15 s, or to show travel.
- Hops 5-15 s, a continuation at least 6 s. Avoid two continuations in a row; restart every 4-5.

**`hand_tie`:** hop 1 is R, every other hop is C, all in one place and one framing. 15 s hops
keep the render count low; the node pairs them two per previs by itself. Each later hop's first
0.92 s is the join and is dropped.

## 2. Fit (MV)

```
python scripts/fit_cuts.py songmap.json --kinds R,R,C,R,... --cuts <t2> <t3:1> ... --end <lo>-<hi>
```

- One cut per hop boundary, from the section table. `t:N` lets a cut slide up to N bars inside a
  section; keep section starts (hooks, drops) at 0 flex.
- `--end`: just after the last sound to a second or two later.
- Take the best result: its `master_audio_start_s` and hop lengths go into the plan and graph.
  A worst cut under ~8 frames reads as on the beat. Nothing fits: add flex, change a kind, widen
  `--tol`, or split a section.
- Under `hand_tie` with equal hops, the film is `n x hop - (n - 1) x 0.92 s`: pick the start so
  the film ends on the song's last sound, and say what of the intro is cut.

## 3. Shot plan

The authority on fields, directives and word budgets is the pack's `prompt_pack/SYSTEM_PROMPT.md`
(its `shot_plan` and "How long a beat has to be" sections).

```json
{"shots": [
  {"id": "01_arrival", "duration": "10 s",
   "directives": {"pace": "slow", "tail": "ongoing"},
   "beat": "..."},
  {"id": "02_floor", "duration": "12 s", "anchor": "restart", "refs": ["kai", "mira", "floor"],
   "directives": {"join": "hard_cut", "pace": "steady", "tail": "ongoing"},
   "beat": "..."},
  {"id": "03_floor", "duration": "6 s",
   "directives": {"join": "continuous", "pace": "steady", "tail": "ongoing"},
   "beat": "..."}
]}
```

`join` continuous | match_cut | hard_cut; `pace` slow | steady | brisk; `tail` ongoing | settle |
hold. Leave `camera` and `framing` out (SKILL.md rule 6). The film's last hop: `tail: "settle"`
(a tease: `hold`).

## 4. Writing a beat

Each beat is an **arc**: an opening move, a change mid-hop, a definite end. Use the top of the word
budget (35-60 words for 8 s, 45-75 for 10 s, 70-100 for 15 s; `check_plan.py` enforces it), written
from the shot notes as what the camera sees.

Order inside a beat:
1. **A person acting, the place in that line** (rule 1).
2. **Who sings, to where, and the mouth:** "raps fast and low, his eyes on the lens, his lips
   shaping every word" (never "into the camera", which pulls the shot in). The first line starts on a free body: finish any hand task at least 2 s
   before the first vocal, or the model runs the task late and the lips start a second or two
   after the words.
3. **Everyone else's action** at the same time.
4. **The change** (the beat hits harder, a door opens, the lights go out).
5. **How it is delivered,** never section names: fast, low, full voice, long notes, one line each.
6. **The end,** on what the next hop needs: a face before a `motion_context` continuation; hands
   at rest and the camera still before a `hand_tie` join.

Templates:

- Restart, one singer + crew:
  > `@a <does X> in/through @place, <light detail>, and <raps fast / sings at full voice>, <his/her>
  > eyes on the lens, <his/her> lips shaping every word. Behind <him/her> @b <action> while @c
  > <action>. <Change>. @a <end move>, <face to the lens>.`
- Trade between two singers:
  > `... @a and @b take turns rapping to the lens, one line each, their lips shaping every
  > word. While @a raps, @b <action>; while @b raps, @a <action>. <end move>.`
- Continuation: the first sentence moves from the previous end pose:
  > `@a turns from <where the last hop left him> and <new move>, still rapping, his eyes on the lens ...`
- `hand_tie` one-take hop: the same framing sentence every hop, then timed windows clear of the
  first and last 1.3 s:
  > `The same medium close shot, @a still seated on the stool at the microphone in @studio, <the
  > place laid out by side>, <her hands where the last hop left them>; the camera holds. At
  > 00:01.300-00:07.000, @a <sings / acts>. At 00:07.000-00:13.700, @a <sings / acts>, <hands
  > back at rest>.`
- Instrumental hop: only action and sound, no singing words, faces reacting, mouths closed.

**Barriers** (bars, gate, glass, railing): name the barrier's place in the frame as the plate has
it, which side the camera and each person are on, that it "stays fixed", and keep hands on it,
never through it. Don't walk anyone up to a barrier that was not already between them and the
camera. Two people on opposite sides: profile, both hands on the same bars from their own side.

**Strikes and breaks:** name the one person who strikes, put the target away from every body ("the
chain where it lies on the floor, far from @b"), keep everyone else busy clear of it, and say "only
@a strikes". Movement comes after the break.

## 5. Ref plan

```json
{"subjects": {
   "1": {"name": "the woman in the red leather jacket", "locked": "...", "context": "..."}},
 "refs": [
   {"tag": "kai", "file": "kai_sheet.jpg", "subject": 1, "retention": "fully_preserved",
    "shots": [1, 2, 3], "desc": "character reference sheet"},
   {"tag": "floor", "file": "casino_floor.jpg", "retention": "reference", "shots": [2],
    "desc": "casino gaming floor"}]}
```

- Characters ride every hop they appear in. Under `motion_context`, plates ride the hops that open
  in their place (hop 1 and restarts); under `hand_tie`, the plate rides every hop.
- At most 9 pictures per hop. Plate descs are a few words. Every restart lists its characters and
  its plate.

## 6. Check

```
<comfy-python> scripts/check_plan.py shot_plan.json ref_plan.json --map scene_map.json
#   add --no-mv for a film, --pin-mech hand_tie for a one-take piece
```

Fix every **error**. For every **lint**, fix it or tell the user why it is safe. Known noise: the
node's "@x is a new place" warning on hard-cut restarts, and `pin-face` under `hand_tie` (the
previs, not the last face, carries identity there). Then do the "review by reading" items.
