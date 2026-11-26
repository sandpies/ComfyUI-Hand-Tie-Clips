# Which rules are proven

One line per finding: what to lean on, what failed, what is still a guess. The renders behind each
line are in [the evidence log](status_log.md); read it only when a verdict is in doubt.

**How a line moves.** For each piece, pick two or three unproven lines the story can test and tell
the user which. A line moves up only when the user has watched the render and says it held. Your own
frame stats and audio levels can move a line down, never up. Write the evidence in the log first,
then change the line here.

## Proven: lean on these

**Joins and form**
- `hand_tie` one take for a one-place song: 12 hops x 15 s, lip sync held on every join, when every hop opens on the same framing sentence and the join windows are calm.
- `motion_context`: three continuations in a row in one scene; a 2.5-minute film of cuts, tracks and arcs written from a scene map.
- `sand_tie` fixed-camera take with no lines, five windows, three position changes: held as one shot.
- Every new place on an MV as a hard-cut continuation (no anchor), the hop before ending on her face at a new size and angle: seven in a row held.
- Retaking one hop and locking every hop after it (`locked: true`): the locked hops came from cache, and the join read as a cut.

**Camera and cuts**
- The camera written in the beat's prose, `camera` and `framing` left empty.
- `[Shot N]` cuts with timed action: 3-4 per hop with lines, 4-8 per hop without (73 shots in 15 hops held).
- Every cut re-places everyone; a continuation's `[Shot 1]` does not cut for 2 s.
- Moves that held: hold, arc (half a turn, stopping on the face), rise, push in (rationed), track or back away ahead, tilt up, crash zoom, drone high wide, low mount, helmet POV, whip pan landing dead still, eye macro, worm's-eye, fisheye close, Dutch tilt per beat, top-down from its own plate, flat white or black void shots inside a plated hop.
- A restart that cuts on an action into a clearly new angle and size reads as a cut; the same framing reads as a jump.
- An entrance, an exit or a vanish played as one take with the camera moving; a vanish revealed by a move, not by a cut.
- A match cut on a small object; a flashback in its own light, with white dips in and out.

**People, faces and lines**
- Film eyelines three-quarter toward the camera, eyes on the other person; closes from beside the listener with the gaze "passing well to the left of the camera".
- Closes written "alone in the frame, nobody else is in the frame", with a short place, not the wide's full spot phrase.
- Three speakers in a chosen order, each line its own shot with the speaker alone; after the last line, the mouth closed and a sound named.
- Voiced rows on speaking hops only; five voiced characters across a film, at most three per hop, about two words a second.
- A lower-face skull half-mask that sings or speaks through the jaw ("the jaw ... working with every word"); a masked character masked from the first frame, the phrase naming what shows round the mask.
- Named pose hits that land on the downbeat and freeze, in place of "dances".
- Symmetric character designs hold identity across angles.
- Simultaneous actions bound with "and / while / as / ;", sequence with "then".

**Props, plates and places**
- Plates shot from the shot's camera, one per shot in multi-shot hops, two per set (a view and its reverse).
- Props fixed by colour, count and parts; a key prop with its own picture and tag held one design across five hops; a handover as its own timed action.
- A spot phrase that fits the furniture as the plate draws it; a walk routed over open floor the plate shows.
- An outfit phrase naming the garment's defining cut, in every shot that shows the person.
- A vehicle with its own sheet and matching plates: one car across seven angles. Car interiors with no plate, kept medium or close.
- A person on a flat solid colour background with no plate.
- Stylised films: the medium named in every plate prompt, `establish` and `prompt_prefix`.

**Story, MV energy and finish**
- Three or four turns a minute; a tease held 2-3 s with `tail: hold`.
- An MV written from a half-page treatment (one idea, a hook that grows, five intercut worlds) before any shot table: one piece so far.
- An `fx.json` effect on every MV hop from hop 1, each landing on a named move or beat.
- Objects floating round a still, grounded performer as the hook (can, rain, pegs, sheets, cars), growing each section, with "her feet planted on the ground, her shirt hanging down" on every float shot: "all the gravity stuff worked" (Ue e half-res).
- Post text and fx chosen from samples burned on real frames ([post](post.md)); hero words, not subtitles; reused words carried across renders by a measured audio offset.
- A mono grade in the edit on a colour render, one ffmpeg pass at the source bitrate.

## Failed: what the model did instead

- A plate's contents listed in the beat: the shot went wide to show it all.
- "Into the camera": the camera travelled toward the lens. Write "her eyes on the lens".
- A close carrying the wide's full spot phrase: a second full-body copy appeared behind.
- A hop's end state in its own short last window: a hard cut there.
- A recurring prop held by words alone: the design changed every time.
- A run away from the camera without "her back to the camera": played in reverse. A run toward a place shot from in front: the place came out behind her.
- "From beside @b" with the two apart: @b drawn at the speaker's shoulder.
- A masked face with no mouth state, or nodding in a close, on a speaking hop: the mask spoke.
- Someone in the scene left off a continuation: the look landed on someone else.
- "Toward the camera" in nearly every shot: far too many lens looks.
- A story readable only with the plot in hand (no want, an untriggered flashback).
- `sand_tie` lines stacked in one timed sentence ending a window: the lines were spoken again.
- An outfit phrase only in `[Shot 1]`: the garment changed after the cut.
- A prop taken off a hop whose camera sees where it rests: it popped back on the next hop.
- A cut in the middle of one continuous action: read as a jump.
- A cut to a slightly tighter size on the axis where a camera move just stopped: read as a skip, "killed the vibe".
- A floating or changed thing named only in the shot where it changes: gone after the next cut (sheets lifted into the sky vanished at 1:28). Name it in every later shot until it changes back.
- Someone sitting in frame left out of a shot: popped in at the next cut with a new prop.
- A tilt past a counter to the floor behind it: the counter vanished.
- A spot asking for contact the plate cannot give: the person sat on air.
- Three speakers trading lines in one wide; six shots in a 14 s hop with lines: lines went to the wrong faces.
- A swing round a pole with the feet together: the legs merged at the pole.
- A near-photographic plate in an anime piece: the body came out realistic.
- One gesture for a whole window ("slicing one hand on every beat"): it looped. Many short timed windows inside one take: stutter cuts.
- The same to-lens rap clause on every shot of an MV: a slideshow.
- Post: a short speed ramp, a breathing letterbox, colour isolation from a loose matte, a kaleidoscope over a face, a text ring at face height. Edit grade: `colorhold` on flames leaked onto skin.

## Unproven: one failure each, test before a piece depends on it

- Camera placement (floor, body mount, air, whips) over move variety for MV energy.
- A new named move every bar or two; at most two timed windows inside one continuous take.
- A recurring masked or costumed character needs the sheet on every hop he appears on, even far.
- Never writing a masked character unmasked; start him masked.
- A `motion_context` restart on a stack with sheets put the sheet in frame 0; the hard-cut continuation (above) is the alternative, not yet A/B'd.
- `sand_tie` dialogue with one line per timed sentence and every window ending on a line-free action.
- Dialogue at about two words a second without gibberish or swapped mouths.
- Voices kept clearly apart in pitch and texture (close voices swapped timbre).
- Three plates of one room from one floor plan, or edited from one master picture.
- `dialogue_lock` on `motion_context`: safe, never yet seen removing babble.
- A prop sheet for a prop that changes state.
- A continuity sheet vetted before the beats, spots checked as `states`.
- Off-frame eyeline side matching the side in the wide.
- A continuation as one take with the cuts in restarts.
- A footstep sound and an end mark after every step.
- A lone short line in a long window said twice; fill the window.
- The adult page's laws across hops and joins.
- Energy and expression small to medium in chains, pose-locked at joins.
- A reveal kept dry by naming the room sound across the cut.
- A high angle over sheeted people with no plate from that height.
- A view that turns round with every person given a side again.
- A score over a no-line hop in a busy place.
- A background figure kept to a pose.
- Cutting between two places inside one hop.
- Look-alike hair swapping glasses between people.
- A hand action on a prop written step by step.
- A masked character still on speaking hops, his reactions on no-line hops.
- Silent faces given business with its own sound.
- A chase from many camera places, screen direction fixed.
- A camera device into a memory, mirrored on the way back.
- A different reaction for every face; blinks written.
- No body turn in a `hand_tie` hop (a shoulder turn came with a cut).
- Hand tasks finished 2 s before a performer's first vocal.
