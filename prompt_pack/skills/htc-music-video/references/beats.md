# Fitting the cuts and writing the plans

## 1. Choose hop kinds

- **R** = start (hop 1) or **restart**: a cut to a new setup; its whole length plays. Use one at
  every section change and every new place.
- **C** = **continuation**: carries straight on from the previous hop's last frames (one unbroken
  take); its first 22 frames are the previous hop's and are dropped. Use one when a section is
  longer than 15 s, or to show travel (out of the hotel, down the steps, into the car).
- Hops are 5-15 s. A continuation is at least 6 s. Avoid two continuations in a row; identity and
  texture degrade along a run of continuations.

## 2. Fit

```
python scripts/fit_cuts.py songmap.json --kinds R,R,C,R,... --cuts <t2> <t3:1> ... --end <lo>-<hi>
```

- One cut per hop boundary, from the section table. `t:N` lets the cut slide up to N bars
  inside a section; keep section starts (hooks, drops) at 0 flex.
- `--end`: just after the last sound to a second or two later.
- Take the best result: its `master_audio_start_s` and hop lengths go into the plan and graph.
  A worst cut under ~8 frames reads as on the beat.
- If nothing fits: add flex inside sections, change a kind (R/C), widen `--tol`, or split a section.

## 3. Shot plan

The authority on fields, directives and word budgets is the pack's `prompt_pack/SYSTEM_PROMPT.md`.
Read its `shot_plan` and "How long a beat has to be" sections. The shape:

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

Directive values: `join` continuous | match_cut | hard_cut; `pace` slow | steady | brisk;
`tail` ongoing | settle | hold. Leave `camera` and `framing` out: the camera is written in the beat
(SKILL.md rule 6, [camera](camera.md)). The node still accepts them, but each is one stock line,
and `hold` adds "the camera holds its position throughout". The last hop of the film: `tail: "settle"`.

## 4. Writing a beat

Each beat is an **arc**: an opening move → a change mid-hop → a definite end move. One action
plus scenery reads as a static slideshow. Use the top of the word budget (`prompt_pack/SYSTEM_PROMPT.md` has the table: 35-60 words
for 8 s, 45-75 for 10 s, 70-100 for 15 s; `check_plan.py` enforces it).

Write it as what the camera sees (SKILL.md, the keynote): fix the camera's place and facing, put
each person and object in the frame (left/right, near/far, which side of what), and give every
move a screen direction. "@a is trapped and @b comes for him" gives the model no layout;
"@a stands at the left of frame by the wall, @b walks in from the far end toward the lens" does.

Order inside a beat:
1. **A person acting, with the place in that line** (SKILL.md rule 1).
2. **Who sings, to where, and the mouth:** "raps fast and low straight into the camera, his
   lips shaping every word".
3. **Everyone else's action** while that happens.
4. **The change** (the beat hits harder, a door opens, the lights go out).
5. **No section names** ("the hook", "the second verse", "the last line"): the video model
   does not know them. Say how it is delivered: fast, low, full voice, long notes, one line each.
6. **The end move**, ending on what the next hop needs (a face to camera before a continuation).

Templates:

- Restart, one singer + crew:
  > `@a <does X> in/through @place, <light detail>, and <raps fast / sings at full voice> straight into the
  > camera, <his/her> lips shaping every word. Behind <him/her> @b <action> while @c <action>.
  > <Change>. @a <end move>, <face to the lens>.`
- Trade between two singers:
  > `... @a and @b take turns rapping into the camera, one line each, their lips shaping every word.
  > While @a raps, @b <action>; while @b raps, @a <action>. <end move>.`
- Continuation (first sentence moves from the previous end pose):
  > `@a turns from <where the last hop left him> and <new move>, still rapping into the camera ...`
- Instrumental hop (drop, intro, outro tail): only action and sound, no singing words, faces
  reacting.

Barriers (bars, a gate, glass, a railing, a fence) render as something people melt through unless the
beat pins them down. Name the barrier's place in the frame (matching the plate), which side the
camera is on and which side each person is on, say it "stays fixed", and keep hands on it, never
through it. Don't have a person walk up to a barrier that was not already between them and the
camera; put it beside them instead. Two people on opposite sides: profile, both hands on the same
bars from their own side.

Strikes and breaks (smashing chains, a lock, glass, a door): name the one person who strikes, put
the thing struck away from anyone's body ("the chain where it lies on the floor, far from @b"),
hold everyone else still ("@b stays kneeling, arms still, face turned away"), and say "only @a
strikes". "@a smashes @b's chains" made @b swing at them too and get hit. Movement comes after
the break.

Time every movement before writing it into a window: it plays in real time, and a window too
short for it squeezes it, skips it or doubles the people doing it. A step is about half a second,
sitting down or standing up 2 s, opening a door and getting in 3 s, walking round a car 4-5 s.
One travel movement per person per window; if the seconds are not there, drop the movement or
give it its own shot.

Write the camera exactly, one move per hop chosen from what the moment is about ([camera](camera.md)): position, facing, what fills the frame ("the camera rides alongside the
car at window height, both men leaning out toward it").

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

- Characters ride every hop they appear in. Plates ride only the hop that opens in their place
  (hop 1 and restarts); a continuation in the same place needs no plate.
- At most 9 pictures per hop. Plate descs are a few words.
- Every restart's `refs` lists its characters and its plate.

## 6. Check

```
<comfy-python> scripts/check_plan.py shot_plan.json ref_plan.json            # add --no-mv for a film
```

Fix every **error**. For every **lint**, fix it or tell the user why it is safe (e.g. the
opens-on-place exception). Known noise: the node's "@x is a new place" warning on hard-cut restarts.
Then do the "review by reading" items yourself and report them.
