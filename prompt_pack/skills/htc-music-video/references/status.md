# Which rules are proven

Every rule in this skill came from a render that failed. Some have since held in a later render;
others are written from one failure and have not been tried yet. Lean on the proven ones. For
each new piece, pick two or three unproven ones the story can test, tell the user which, and
move a rule up once a render shows it holding (or rewrite it if it fails). A rule moves up only
when the user has watched the render and says it held; frame grids and audio levels can only
move a rule down.

## Proven (held in at least one render after the rule was written)

**Directing**
- A one-place, one-take MV on `hand_tie` with `master_audio_file`, 15 s hops: lip sync held
  across all 11 joins of a 12-hop film (each later hop locks its own slice of the song).
- The camera directed in the beat's prose, with the node's `camera` and `framing` left empty.
- `[Shot N]` cuts inside a hop with timed action; 3-4 shots in a hop with lines, 7-8 in an action
  hop with no lines.
- Every cut re-places everyone in it; a person not named in a shot is not in it.
- A continuation's `[Shot 1]` continues the pin, with no cut in its first 2 s.
- The gap between two people given as the same number in both shots across a cut.
- A run or walk with an end mark (stops dead, stops at the ledge, leaves past the lens), and a
  leap with a landing ("lands in a crouch ... and stays crouched").
- A person heard but not seen kept behind the camera, and a reverse angle with no plate naming
  its background.
- An arrival through a door the plate shows.
- Moves: hold, arc, rise, push in (rationed), track backward ahead, backs away ahead, tilt up,
  a fast zoom to a close shot, a drone shot from high above, a mounted camera low on the road,
  a helmet-mounted POV, a drone tracking alongside (the last four on subjects with no sheet).
- A person on a flat solid colour background with no plate.

**People and lines**
- Film eyelines: face three-quarter toward the camera, eyes on the other person, in medium and
  wider shots.
- Voiced rows on speaking hops, voiceless rows of the same sheet elsewhere.
- After the last line, the mouth closed and a sound named (the babble came back where it was
  missing).
- Symmetric character designs hold identity across angles.
- A music video where nobody sings on screen.

**Props and places**
- Props fixed in words inside one scene: colour, count and parts ("two brass clasps, one thick
  green folder").
- A prop the plate lacks, counted and owned from its first shot.
- Plates shot from the camera the shot uses; one plate per shot in multi-shot hops.
- Stylised films: the medium named in every plate prompt, `establish` and `prompt_prefix`.
- A small room planned on two plates at most (the view and its reverse).
- A key prop with its own reference picture (one object on plain grey), named by tag in every
  shot: one design held across five hops of inserts.
- Car interiors with no plate, kept medium or close and named in words in every shot; front
  seats placed by the frame from the dashboard (passenger left, driver right) held.
- A vehicle with its own sheet (one generation: front three-quarter, side, rear, interior), its
  tag on every hop it is seen and its plates generated to match it: one car model across seven
  angles, outside and in.
- A high wide from above and behind a moving vehicle with people who have sheets, the plate shot
  from that same height: held at the height asked, with the person in it.
- A small prop passed between people on screen, each handover written as its own timed action
  ("plucks it out of his hand and holds it up"): every handover read, the prop never jumped.

**Rules tested on purpose in one piece (held)**
- A one-sided feature (one earring, a scar) named with its side in `locked`, on a sheet whose
  every view agrees: held in every close shot.
- A picture inside the picture given its own medium ("a rough grey pencil sketch, no colour").
- A mark already on a page ("already circled ... stays exactly as it is"), the hand beside it.
- Seats restated in each shot's own frame (over one shoulder: the back of her head at the right
  edge).
- In close shots, the gaze "passing well to the left of the camera", the camera beside the
  listener: no lens looks.
- The face that ends a hop shot as a close from beside the listener.
- A person starting a few steps into the frame and walking to their mark.
- An orbit kept to half a turn on a referenced character, stopping on the face.

- Three speakers in one hop, a chosen order: each line in its own shot with the speaker alone
  in the frame, every silent face with a closed mouth, the first speaker's mouth free when his
  line starts, a sound bed with no voices. The first line otherwise goes to the most central,
  frontal, free face.

- A sting written on the reveal cut ("a single low dramatic sting as the camera cuts to her
  face"): a low hit came in about half a second before the cut and rang out over the close.
- A person seen only in a photo, given a prop picture of that photo instead of a character sheet:
  the same face on both hops, and no bleed onto anyone else on screen.
- Someone inside behind a window, the camera outside: "seen through the big lit shop window, the
  window frame around her and rain streaking the glass between her and the camera".
- 7 shots in 15 s on a hop carrying two character sheets, no lines: cuts and faces held.

- A watcher alone in the frame, far off the path of the person she watches, who is "already gone"
  and not named in the shot; a phone dialled with the receiver down instead of a call with no
  line; a low score note across a quiet hop. The shoulder-to-shoulder pair and its chatter went
  away.

- A match cut: an extreme close of a small object, then a cut to the same object in a new
  place ("the same small silver key sliding into the lock").
- A daylight flashback inside a night film, with the style line holding only the look and the
  time of day in the beats.
- A person meeting her own photo: the sheet matched the polaroid made earlier.
- A look at something behind her, written as the turn ("looks up over her shoulder at the clock").
- One named extra ("one gate attendant, a man in a yellow rain jacket, the only other person
  there") who waves and steps aside on cue.
- Three continuation hops in a row in one scene.
- A 12-hop, 2.5-minute film of cuts, tracks, arcs and holds written from a scene map: camera
  cuts and moves mostly landed as written (user-watched).

- A close shot closed with "alone in the frame ... nobody else is in the frame", the camera
  placed by the room, not beside the listener: the listener stayed out (user-watched).

- Simultaneous actions bound with "and / while / as / ;" and sequence with "then": H3 weighs these
  words strongly for several people in one scene (taught from the user's own renders).

**Story**
- Three or four turns per minute; a tease held 2-3 s with `tail: hold`.

## Failed (tried on purpose; do not rely on it)

- A recurring prop held by words alone: the same full description in every shot kept the gist
  (eight sides, a blue lid) but the box looked different in every appearance across two films.
  Every prop that comes back gets its own picture.
- A run away from the camera written without "her back to the camera": it played like a run in
  reverse.
- A run toward a place, shot from in front of the runner: the place in the plate came out
  behind her, so she seemed to run away from it.

- A close placed "from beside @b" when the two are apart (across a long table, across a room):
  @b was drawn at the speaker's shoulder twice in one scene. Only use "from beside" when the two
  are side by side or across a small table.
- A masked face on a hop where others speak, with no mouth state: the mask "spoke". Write "his
  mouth hidden behind the mask, his jaw still" and a sound under his shot.

- A person still in the scene left off a continuation hop (no row, not named): her look (two
  buns, a choker) landed on her silver-haired twin in the next shot. Everyone in the room rides
  every continuation hop of the scene (map `cast`, lint `cast-missing`); restarts start fresh.

- A masked face that moves (a nod) in a close shot on a hop with lines: the mask's mouth moved
  with speech, after a question and again after a statement with a loud chord over his shot.

- A close of one person whose eyeline named someone standing right beside her "off the frame
  to the right", with no "alone in the frame": his head popped into the edge of the close (lint
  `pull-in`).
- "Toward the camera" or "facing the camera" in nearly every shot, often with no target for the
  eyes: far more lens looks than the film needed (lint `no-eye-target`).
- A story that read only with the plot in hand: an opening catwalk with no want (a
  showcase), a flashback placed straight after it with no trigger in the present, and a cut from
  a yes straight to a new place with no first step shown. Viewers could not tell why each scene
  came next (film.md, The viewer knows only what the screen shows).

## Unproven (written from one failure; test before a piece depends on it)

- Hands at rest on a surface at every join (rule 8). From a 12-hop one-take MV on `hand_tie`
  with a master song: lip sync held on all 11 joins, but the three joins with a hand on the
  chest or moving on the stand blurred; the joins with hands on the knees were clean. Under
  `hand_tie` both hops at a join are tied to the same previs frames, so the pose at the join
  comes from the previs, which reads the beats.
- One framing for a whole one-take piece: the beats asked for one medium close shot every hop;
  one previs section (two hops) came out a tight close-up. Under `hand_tie` the previs sets
  each section's framing.

- `dialogue_lock` (`lines+hold`, or `full`) on a film with lines, the beats keeping each
  line word for word, quoted or `<d>` (with `dialogue_audio_file`, the words of that
  recording): meant to stop invented words and babble after a line. Safe so far: lip sync and
  the sound bed held in three tests (one a real film's two hops), even with a whole hop frozen. Not yet seen removing babble:
  neither test babbled with the lock off, so keep it for a hop that babbles without it. Under hand_tie it
  does nothing: tried there, one take cut and another said a line twice.

- A prop sheet (every state the story shows, plus the part a hand works) for a prop that opens or
  changes: with one picture of the closed state, the prop looked right but opened differently
  every time.

- A reveal kept dry by naming the room sound across the cut: quieter than the written sting, but
  a small hit may still have come in on the cut.
- A high angle (drone, "from above") over people with character sheets and no plate from that
  height: came out at eye level in two renders. With a plate shot from the height, it held
  (see Proven).
- A view that turns round (from behind, then from in front) with every person given a side in
  the new frame: once a person was left without one ("his hair in the dark behind the driver")
  and came out twice, once on each side of the one in the middle.
- A score across a whole no-line hop in a busy place, so the model does not fill it with crowd
  speech.
- A background figure kept to a pose, so the model does not cut in to show her task.
- Cutting between two places inside one hop: the plates swapped once (see camera.md); prefer a
  hop per place.
- Two people with the same black bob: one took the other's glasses on a continuation where the
  glasses' owner was not on the hop. Cause not known; watch features on look-alike hair.
- A hand action on a prop written step by step ("lifts the stopper out ..., then pours"); a bare
  "pours" kept the stopper on.
- A masked character kept still in the background of a speaking hop, his reactions moved to a
  hop with no lines.
- Busy frames stay quiet: silent faces given business with its own sound (footsteps, a glass set
  down) instead of stillness, so empty time does not fill with speech. Every babble so far came in
  an empty window; test it on purpose.
- A chase covered from many camera places (alongside, ground mount, the chaser's shoulder,
  drone, half orbit on a vault) with the screen direction fixed and written in every shot.
- A camera device into a memory (a push into the eyes, a fast half orbit to an extreme close)
  before the white, mirrored on the way back.
- A different reaction written for every face in frame (smug, wary, amused) and blinks written
  where a face holds the screen; one unprompted render showed the varied reactions working.
