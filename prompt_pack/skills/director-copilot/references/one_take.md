# One take: hand_tie and sand_tie

Read this when the brief picks `pin_mech: hand_tie` or `sand_tie` ([join modes](../SKILL.md#one-take-or-many-places)).
In both, the joins hold; a take breaks where the writing gives the model a reason to redraw the
frame.

## hand_tie: calm joins

A low-res previs of each section is rendered first, and every hop is tied to it at both ends. The
first and last 1.3 s of every hop are join windows that two hops share.

- **The same framing sentence opens every hop:** size, person, place tag and nothing else ("A
  medium shot of @a standing in @alley from her knees up; the camera holds"). The plate carries
  the room.
- **Calm join windows:** hands at rest on something (knees, a stand, a table), the camera still,
  no gesture, body turn or move crossing them. A hand or camera moving through a join blurs there
  (lint `join-calm`). A shoulder turn inside a hop came with a cut.
- One framing, one place, no `[Shot N]` cuts and no restarts. `dialogue_lock` does nothing here;
  set `last_frame_guide=off` and `dialogue_lock=off` on the graph.

## sand_tie: one video, drawn in windows

Each take is one video; its hops are overlapping windows drawn in order and finished together. A
take ends only at `anchor: restart`, the one real cut. Every take:

- **Opens on the camera, nothing else.** Every hop of the take opens with the same sentence, word
  for word: framing, camera movement, who is in shot. No place in it if the place changes during
  the take, no time of day if the light changes. Only the take's first opening is used (lint
  `take-lead`).
- **Puts the action on a timeline,** `At mm:ss-mm:ss,` sentences, each hop's times its own (0 to
  the hop's length) (lint `untimed`).
- **Has few timed sentences.** Every sentence boundary is a place the picture can jump: a handful
  across a minute holds, one per hop does not.
- **Ends every hop but the take's last on an action with no line in it,** and gives each line its
  own timed sentence. The next window opens by restating the hop's last timed sentence; if that
  sentence holds lines, they are spoken again (lints `carry-line`, `stacked-lines`). A take with
  no lines does not hit this.
- **Names a place in the same words in every sentence set there,** time of day included. A new
  background detail in one sentence redraws the place at that boundary. No arc in one sentence
  ("first walks, then stops"): a sentence is given whole to every window it spans, and each window
  replays it (lint `arc`).
- **Changes place as a crossing of 5-6 seconds seen from the camera:** the new place opens up
  around and beside the people while the old one stays behind them. A camera backing away ahead
  of someone reaches the new place first; a quick "walks into" renders as a cut.
- **Says which way stairs and slopes rise relative to the camera,** or a person facing the camera
  climbs backwards (lint `slope`).
- **Gives a long walk through one place that place's plate on every hop,** shot from where the
  camera is, named in the opening sentence. Words alone let each window invent its own place.
- **With a master song,** describes delivery, not lyrics, and gives whoever is not singing
  something to do.

Needs overlap 0.9 s and a ComfyUI with H3 context windows.
