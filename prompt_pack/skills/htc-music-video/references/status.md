# Which rules are proven

Every rule here came from a render that failed. Lean on the proven ones. For each piece, pick two
or three unproven ones the story can test, tell the user which, and move a rule up once the user
has watched the render and says it held (or rewrite it if it failed). Frame stats and audio levels
can only move a rule down.

## Proven (held in at least one render after the rule was written)

**Join modes and form**
- `hand_tie` one-take rap MV, every hop opening on one framing sentence (size, person, place tag)
  and the plate carrying the room: all four joins held at native-like motion (user-watched, 10-28).
- `hand_tie` + `master_audio_file` for a one-place, one-take MV: 12 hops x 15 s (2:51), lip sync
  held across all 11 joins.
- `hand_tie` join windows kept calm (hands resting on the armrests, the camera holding, the same
  framing sentence every hop): a 5-hop one-take rap MV held its framing and joins across three
  previs sections (an earlier MV with hands moving at the joins blurred at three of them).
- A music video where nobody sings on screen.
- Three `motion_context` continuations in a row in one scene; a 12-hop, 2.5-minute film of cuts,
  tracks, arcs and holds written from a scene map.

**Directing**
- The camera in the beat's prose, `camera` and `framing` left empty.
- `[Shot N]` cuts with timed action: 3-4 shots in a hop with lines; 7-8 in a no-line action hop,
  also with two character sheets on it.
- Every cut re-places everyone; a continuation's `[Shot 1]` continues the pin, no cut for 2 s.
- The same gap as a number in both shots of a cut; seats restated in each shot's own frame.
- An end mark on every run or walk; a leap with a landing ("lands in a crouch and stays crouched");
  a person starting a few steps into the frame and walking to the mark.
- Someone heard but not seen kept behind the camera; a reverse angle naming its background; an
  arrival through a door the plate shows; someone behind a lit shop window, the camera outside.
- Moves: hold, arc, rise, push in (rationed), track or back away ahead, tilt up, a fast zoom to a
  close, a drone high wide, a low mounted camera, a helmet POV, a drone alongside (the last four on
  subjects with no sheet); an orbit kept to half a turn, stopping on the face.
- A person on a flat solid colour background with no plate.
- A match cut on a small object; a daylight flashback in a night film with the look in the style
  line and the time of day in the beats.
- A look behind written as the turn ("looks up over her shoulder at the clock").
- One named extra who acts on cue.
- Simultaneous actions bound with "and / while / as / ;", sequence with "then".

**People and lines**
- Film eyelines: three-quarter toward the camera, eyes on the other person, in medium and wider.
- In close shots: the camera beside the listener, the gaze "passing well to the left of the
  camera"; a close closed with "alone in the frame ... nobody else is in the frame".
- The face that ends a hop shot as a close from beside the listener.
- Voiced rows on speaking hops, voiceless rows elsewhere.
- After the last line, the mouth closed and a sound named.
- Three speakers in a chosen order: each line its own shot, the speaker alone, every silent face
  closed, the first speaker's mouth free.
- A sting written on the reveal cut (lands about half a second early).
- Symmetric character designs hold identity across angles; a one-sided feature named with its
  side in `locked`, on a sheet that agrees.
- A watcher alone in the frame, far off the path of someone "already gone"; a phone dialled with
  the receiver down; a low score note across a quiet hop.

**Props and places**
- Props fixed in words inside one scene by colour, count and parts.
- A prop the plate lacks, counted and owned from its first shot.
- A key prop with its own picture, named by tag in every shot: one design across five hops.
- A small prop handed over on screen, each handover its own timed action.
- A picture inside the picture given its own medium; a mark "already circled ... stays exactly as
  it is", the hand beside it.
- A person seen only in a photo given a prop picture of that photo: the same face, no bleed; a
  person meeting her own photo.
- Plates shot from the shot's camera; one plate per shot in multi-shot hops; a small room on two
  plates at most.
- Stylised films: the medium named in every plate prompt, `establish` and `prompt_prefix`.
- Car interiors with no plate, kept medium or close and named in words; front seats placed by the
  frame from the dashboard.
- A vehicle with its own sheet, its tag on every hop, its plates made to match: one car model
  across seven angles.
- A high wide from above a moving vehicle with sheeted people, the plate shot from that height.

**Story**
- Three or four turns per minute; a tease held 2-3 s with `tail: hold`.

## Failed (tried on purpose; do not rely on it)

- A hop's end state in its own short last window ("At 00:15.800-00:17.000, @kyo stands with her lips
  closed in a cold smirk"): a hard cut there. Fold it into the window before (lint `end-state-window`).
- A plate's contents listed in every beat ("in the middle of the narrow night alley in @alley, the
  wet asphalt ..., the shopfronts and steam on the left, the vending machine on the right, neon
  signs ..., red lanterns ..."): the previs went wide to show it all, then drifted back in. The
  same plan with one sentence ("A medium shot of @kyo standing in @alley from her knees up; the
  camera holds") held a steady medium, with the same LoRA on (user's previs A/B).
- "Raps into the camera" as a hop's ending: on a one-take rap MV the camera moved forward at the
  end of hops 1 and 2, both ending on it (user-watched). "Into" reads as travel toward the lens.
  Write "her eyes on the lens" (rule 18).
- A recurring prop held by words alone: the gist held, the design changed every appearance.
- A run away from the camera without "her back to the camera": it played in reverse.
- A run toward a place, shot from in front: the place came out behind her.
- "From beside @b" with the two apart: @b drawn at the speaker's shoulder, twice.
- A masked face with no mouth state on a speaking hop: the mask "spoke". A masked face that nods
  in a close on a hop with lines: its mouth moved with speech.
- A person still in the scene left off a continuation: her look landed on her twin (lint
  `cast-missing`).
- A close whose eyeline named someone beside her, with no "alone in the frame": his head popped
  in (lint `pull-in`).
- "Toward the camera" in nearly every shot: far more lens looks than needed (lint `no-eye-target`).
- A story readable only with the plot in hand: a showcase opening with no want, an untriggered
  flashback, a cut from a yes to a new place.

## Unproven (from one failure; test before a piece depends on it)

- `dialogue_lock` on a `motion_context` film: safe so far (lip sync and sound bed held), never yet
  seen removing babble. Does nothing under `hand_tie`.
- A prop sheet for a prop that changes state.
- A reveal kept dry by naming the room sound across the cut.
- A high angle over sheeted people with no plate from that height (eye level twice).
- A view that turns round with every person given a side again.
- A score across a no-line hop in a busy place, against crowd speech.
- A background figure kept to a pose, against an unwritten insert.
- Cutting between two places inside one hop (the plates swapped once).
- Look-alike hair: one took the other's glasses on a hop without the owner. Cause unknown.
- A hand action on a prop written step by step.
- A masked character kept still on speaking hops, his reactions moved to no-line hops.
- Busy frames stay quiet: silent faces given business with its own sound.
- A chase covered from many camera places, screen direction fixed.
- A camera device into a memory, mirrored on the way back.
- A different reaction for every face, and blinks written.
- No body turn in a `hand_tie` one-take hop: "turning his shoulders toward the microphone" at
  2.0 s came with a cut there (the previs had also drifted closer; fixed in the node 10-28).
- Any hand task finished 2 s before a performer's first vocal: with faders worked until 1 s before
  the first line, the lip sync started a second or two late.
