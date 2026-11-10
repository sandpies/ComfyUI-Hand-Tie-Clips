# Performance: sentences, verbs, faces and the moving camera

[Continuity](continuity.md) decides where everyone is. This page decides how a shot reads once it
is there: how each sentence is built, which verbs move a body, how a face plays the moment, and
how the camera moves with a reason. These come from single-clip writing, where a clip can end
anywhere. In a chain every hop also hands its last frame to the next, so each scale below is
turned down at the joins.

## The sentence

- **A beat is a few timed windows,** each `At mm:ss.mmm-mm:ss.mmm,` then who does what, in one
  sentence. About one window per 3 s: 3 windows in a 6-11 s hop, 4 in 12 s and up, none shorter
  than a second. A speaking window gets the line's real length (about 2.5 words a second, plus
  half a second).
- **Inside a window, order the sentence:** who, then the body impulse, then what the hands do,
  then the face it lands on, then the sound. "@a leans back into the chair, turns the glass once on
  the armrest, and lets a slow smile reach her eyes, the ice clicking."
- **One to three physical actions per window,** chained with *and / while / as*. A single clip can
  pack three into every window; in a chain, the last window before a join carries one, and it
  comes to rest (the hand-off pose).
- **The summary is one sentence** of action, turn and camera; the soundscape a steady bed for the
  place plus the foley of the actions, in time order. Keep each place's bed in the same words in
  every hop set there, so the sound continues across cuts as well as the picture.

## Verbs

- **Never a filler verb:** interacts, engages, reacts, moves, talks, gestures, stands there. Each
  says "do something" and the model picks what.
- **Impulse verbs** start a change: freezes, snaps, jolts, pivots, sinks, leans halfway across,
  straightens.
- **Hand verbs** name the grip and the direction: hooks a finger over, pulls slowly down, slaps
  one hand flat on, holds up one finger, grips and lifts, sets down with a click.
- **Hold verbs** keep a state across a window and a join: stays, keeps, holds, rests, plants her
  feet, lets the glass rest on her knee. Every continuation opens with them.
- **Hands that hold something keep holding it.** A hand on a rail, a glass, a wheel stays in that
  job; don't hand it a new gesture in the same window, or the prop is dropped or doubled.
- **Someone seen from behind stays facing away;** a glance back is the chin turning over one
  shoulder, never the body twisting round.

## Say what is there (the additive rule, as rewrites)

Every word adds (fact 1), so write the state that *is*. Rewrites that hold their meaning:

| Not | Write |
|---|---|
| without looking away | holding unbroken eye contact |
| without moving | holding steady in place |
| without speaking / stops talking | with her lips pressed shut |
| without stopping | in one continuous, unbroken motion |
| never turns around | keeps facing forward |
| not visible / out of sight | stays out of the frame, or name what fills the space |
| no sound / silence | the low hum of the fridge (a named, narrow sound) |
| no longer | now |
| no other | only |

Don't swap the word blindly ("never" → "always"); rewrite the sentence so it names the state.
Spoken lines may say anything; the rule is for stage directions. Your own notes and rules are
written the same way: a writer that reads "no X" in its instructions copies X.

## Faces and bodies: three scales

Choose a scale for each per scene and keep it. **Default in a chain: life small, energy small to
medium, expression small to medium.**

| | Small | Medium | Large |
|---|---|---|---|
| **Life** (bodies at rest) | blink, visible breath, a weight shift; one or two small things move behind them each window | hands busy with a prop, eyes and breath active, the place moving softly | props, hair and drinks handled all the time |
| **Energy** (pace) | unhurried, deliberate, lingering looks, soft delivery | crisp, decisive gestures, posture shifts between windows | sudden freezes, whip turns, leans toward the lens |
| **Expression** (faces) | understated: eyes, brows and lips shift when the moment turns | one readable change per window: a slow smirk, a double take, a brow up | big contrasting states |

- **Large energy and large life break chains:** whip turns and leans toward the lens flip screen
  direction and eyelines, and a body that never settles hands the next hop a blur. Keep large for a
  restart's middle, never its last two seconds.
- **At a join, pose-locked:** only breath in the shoulders and the place moving. That is the
  frame the next hop holds.
- **A face turned away acts with the body:** shoulders drop, spine straightens, a hand closes.
- **Each change of face is tied to a turn** in the scene (a line lands, something is seen), not
  spread evenly through the hop.
- **Each speaker keeps one voice for the whole piece:** a delivery, an accent, the small filler
  words they use. Written once, repeated wherever they speak.

## The moving camera

A move is a sentence about what the lens does, never a film term on its own. Write where the
camera starts, which way and how fast it goes, what stays fixed, and where it stops.

- **One move per hop,** otherwise a calm, slightly breathing camera. A move has a meaning: push
  in for pressure, pull back for a reveal or isolation, an arc for two people circling, a rise for
  release, a track along a threat, a rack focus to hand the moment to another face. No meaning, no
  move.
- **Name what stays still.** An arc: "her feet stay planted, facing the same way, while the
  camera circles her and the city slides past behind." A dolly zoom: "she stays the same size in
  the frame while the room stretches behind her."
- **Define the move by its first and last frame:** "opens on both of them waist up; the camera
  travels slowly in until only her eyes and brows fill the frame". The last frame of a move that
  ends a hop is the first frame of the next.
- **Pace the move over the windows:** hold, then move, then hold. A slow rise stops at the
  shoulders for a window, then reaches the face. A snap lands on the window where the turn
  happens. Establish the people cleanly in the first half of a hop before anything big moves.
- **Shot sizes are screen descriptions:** close = the face from chin to hairline; medium = waist
  up, hands in view; two-shot = both faces clear; profile, three-quarter, eye level, low looking
  up. Write the description, not only the name.

## Plan, write, audit

The strongest results come from separate passes, each doing one job:

1. **Plan** a beat skeleton the user can edit: per window, who, the impulse, the hands, the face,
   the sound, the camera.
2. **Write** the beat from the approved plan.
3. **Audit** it against the rules that are actually active for this piece (the scales chosen,
   the camera move, the continuity sheet row), slowly and literally: change what fails, keep
   everything that passes word for word.
4. **Read the assembled prompt** the node will send (dry run) before anyone renders.
