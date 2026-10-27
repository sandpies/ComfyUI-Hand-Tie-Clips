# Camera: directing the shot

The camera is written in the beat. Leave the shot's `camera` and `framing` directives empty: a
`camera` value is one stock sentence with no speed or reason, and `hold` stands the camera still
for the whole hop. `join` still matters (`continuous` on a continuation, `hard_cut` on a restart);
the first hop ignores it.

## Three questions before every shot

1. **What changes?** The camera moves when the meaning changes; a hold is a choice for tension,
   never the default.
2. **Who has the power?** The camera drifts toward whoever gains it. Low looking up makes someone
   big; high looking down makes them small.
3. **What must the viewer discover?** Move or cut to show it at the moment it matters.

| The moment is about | The camera |
|---|---|
| Someone arriving and owning the space | backs away ahead of them |
| Power moving to someone | a slow push in while they speak |
| A reveal | follows the object, settles on the face it hits |
| Panic | handheld, closer than comfortable |
| A threat being prepared | a slow track along it |
| Two people circling each other | a slow arc, the speaker centred |
| Energy, a crowd, a performance | moves with the lead: alongside, orbiting, rising |
| An ending, isolation | pulls back until the people are small |

## The shape of a hop

- **One take** when the tension is in the continuity (a walk-and-talk, a slow threat, a reveal
  reached by moving). A move can do a cut's job.
- **Cuts inside the hop** when the viewer needs what this angle cannot show: action and
  reaction, shot and reverse shot, an insert, a jump in place or time.
- **Both:** a moving take into the action, then a cut to the aftermath.
- Two or three shots per 12-15 s hop with lines, each at least 2 s. A hop with no lines can hold
  7-8 (see [action hops](#action-hops-with-no-lines)).
- Under `hand_tie` a hop is one take: no `[Shot N]` cuts, one framing for the whole piece, the
  join windows calm (SKILL.md rule 15).

### Writing shots

H3's own shot form: `[Shot N]`, where the camera is and what fills the frame, then the action with
times counted from the hop's start.

> [Shot 1] @a is already seated in the leather chair across the table in @room, facing the
> camera, lips pressed shut, in a medium shot at chest height from the doorway. At
> 00:00.000-00:05.000, he sets his glass down while the camera pushes slowly in until his head
> and shoulders fill the frame. [Shot 2] At 00:05.000 a cut to the reverse angle in @room_reverse:
> a medium close shot from behind @a's shoulder, which stays at the near left, looking across
> the table at @b in the wooden chair, facing the camera. At 00:05.000-00:12.000, @b's grin
> slowly fades, lips pressed shut, and he swallows.

- **Every shot names its plate.** A cut to another angle holds when that angle has a plate and
  the shot names it. A continuation can open on the pin and cut to another room
  (`At 00:03.000 a cut to @kitchen`). No plate for the angle: keep it close.
- **Every cut re-places everyone,** including who sits still. A person not named is not there;
  one who moves between shots without being shown gets dragged and warps.
- **Seats and gaps belong to the frame.** "@a nearer the camera" reads differently from the other
  end of the room, and the two swap seats: translate the seating into each shot's frame. Keep a
  gap as the same number in both shots ("five steps in front of @b"). An action that needs room
  makes the model make it (the person jumps back): write a short run-up instead of a long sprint.
- **Someone heard but not seen stays behind the camera** ("footsteps echoing from behind the
  camera"). A sound behind a door in the frame draws a person there, a copy of whoever's sheet
  rides the hop.
- **A small background figure gets a pose, not a task,** or the model cuts in to show the task.
- **A person someone watches leave is drawn beside the watcher.** Say they are already gone, put
  the watcher far off their path, alone in the frame.
- **A reverse angle with no plate names its background** ("only the dark sky behind her; the hut
  behind the camera"), or the plate comes in behind the face.
- **Words that name a plate feature put the action on it** ("climbs the stairs" uses the plate's
  stairs).
- **Say a camera height twice when it matters** ("the camera stays low").
- **Inserts are their own shot,** and name whose hands.
- **A multi-shot beat runs long** (200-300 words for 3 shots in 12 s); the node's length warning
  is for one-take beats.

### Shots inside a chain

- A restart can cut anywhere; it opens on its own refs.
- A `motion_context` continuation's `[Shot 1]` continues the pin: same place, angle and pose, no
  cut in its first 2 s. The hop before it ends on a face (rule 8). Angle changes happen inside
  hops; the seams stay quiet.
- Plan each hop's last frame: it is the next hop's first.

## Journeys

- **A run away from the camera says "her back to the camera",** or it plays like a reversed clip.
- **The plate decides the direction.** If the plate shows the goal in the distance, a run to the
  goal is a run away from the camera. A front view of that run needs a plate from the other end,
  or no goal plate on the hop; otherwise stay behind or side-on with one screen direction.
- **Every run or walk has an end mark** against a person or a fixed thing ("stops an arm's length
  in front of @b"), or leaves on purpose ("out of frame past the lens"). "Slows to a walk" is not
  a stop.
- **Nobody enters from behind the camera;** that renders a body passing the lens. Start them a few
  steps into the frame, or through a door the plate shows.
- **Cutting between two places inside one hop swaps their plates.** Give each place its own hop,
  or keep the second place to faces and hands.
- **A chase is covered from many places, not one angle,** chosen from what this place offers, with
  the screen direction fixed and written in every shot. Not yet proven.

## Props the model would otherwise invent

- **Count, design and place every prop in every shot** ("two cards face down on the felt in front
  of each man"); say what it is after it changes. A prop first named after a cut is multiplied:
  own it ("one black backpack, the only bag on the roof, at @b's feet").
- **A prop that comes back across hops gets its own picture** (one object on plain grey, no
  hands, no text), a tag, and a row on every hop it is in. Words alone keep the gist and change
  the rest every time. One that changes state (opens, lights up) needs a prop sheet of every state
  (story_cast_plates.md).
- **A picture inside the picture** (a drawing, photo, screen) takes the film's medium unless named
  ("a rough grey pencil sketch on white paper, no colour"). A person in a photo is best a prop
  picture of that photo, not their sheet.
- **A hand action gets every step:** "lifts the stopper out ..., then pours". Not yet proven.
- **A mark already on a page is drawn on camera if a hand touches it.** Say it is already there,
  keep the hand beside it.

## Action

- **Fast body contact warps.** Near misses, or one grab that holds still, in a shot of 3-4 s.
- **One contact at a time, never one action at a time:** everyone else keeps their own business
  clear of it.
- **Phone calls end with the call ending** ("the call clicks off, only the rain"), or the other
  end gets a voice.

## Eyelines

A face turned toward the camera is not a look into the lens.

- **Music video:** the performer may sing into the lens.
- **Film:** nobody looks into the lens. Face three-quarter toward the camera, eyes on the person
  dealt with, with a direction ("his eyes on @b just left of the lens"); in a reverse shot, name
  where the listener is ("who stands just off the frame to the left").
- **The camera never sits in the listener's place.** From the listener's seat, "just left of the
  lens" pulls the listener in beside the lens and turns the look into the lens. Put the camera
  beside the listener and send the look "well to the left of the camera". In close shots "just
  left of the lens" reads as a lens look; keep it for medium and wider.
- **In a side-on shot, keep people "in profile, facing @a".** "Toward the camera" there turns them
  to the lens. End such a hop on a close from beside the listener.
- **"From beside @b" puts @b in the frame** unless the two are side by side. Place the camera by
  the room and close the frame: "@a alone in the frame ...; nobody else is in the frame" (lints
  `beside-tag`, `pull-in`). Read the distance off the scene map, never guess it.
- **Every face turned to the camera needs a target off the lens,** and "toward the camera" only
  where the face must be seen (lint `no-eye-target`). Every line has a listener in a named
  direction. Never write "into the lens" in a scene unless breaking the fourth wall, once.

## Bodies in vehicles and rows

- **Seats fix which way a body faces; say it in every shot** ("in the passenger seat facing the
  windscreen, the back of his head and his right cheek to the camera"). A plate from behind the
  seats shows backs of heads; faces need a shot from the front.
- **Car exits are unreliable.** Start him beside the car with the door open, or show the side of
  the car and name the door.
- **A lone person in a car becomes the driver:** keep the driver's hands in frame, or name the
  empty side.
- **Name everyone in the car in every shot of its seats or windows.**
- **Tie the outside motion to the car** ("the street lights coming toward the camera through the
  windscreen and sliding past the side windows"), or the street runs backwards.
- **Describe a dashboard part by look and place,** or cut the insert. **Mirrors show a person:**
  name who, or turn it away.

## Writing the move

One move per shot: **type + amount + speed + what stays in frame + where it stops.**

> The camera arcs slowly left around the table, about thirty degrees, keeping @a centred, until
> @b slides out of frame on the right.

- Name the start (height, side, facing) and the end framing. Name who the camera keeps: a push in
  on two can push the speaker out, and his line comes out of the other mouth.
- Tie the move to a person or a moment ("as he leans in").
- **Ration the push in:** one per scene, stopped at a framing, or it ends staring into the lens.
  Reach for arcs, tracks, rises, drops and holds.
- **Half a turn at most** around a person, stopping on the face; past their back they warp.
- Proven: holds, arcs, backs away ahead, rises, starts low tilted up, push in, draws back, tracks
  backward ahead, handheld, cuts, tilt up, a fast zoom to a close, drone high wide, a mounted low
  camera, a helmet POV, a drone alongside. Truck, pedestal and roll are unproven: try one at low
  resolution first.

## Action hops with no lines

A 15 s hop with no dialogue holds 7-8 shots, a cut every ~2 s, with extreme cameras (held in
three renders of three sports, and with two character sheets on the hop). A shape that worked: a
sensory extreme close (1-1.5 s), a wide for scale, a mounted or POV camera for immersion, a fast
tracking shot for speed, one slowed peak with the sound dropping to a breath and snapping back, a
pull-back release, a silhouette to end.

- Every shot opens with its own camera and timed sub-beats; pair every picture beat with a sound
  beat and write the music's shape against the cuts.
- Spend the density on spectacle that can be wrong and still read; put story shots on proven
  moves, and expect to reroll a dense hop.
- Shots in one space can merge into one move: give each a clearly different camera position.
- A high angle over people with sheets came out at eye level, unless a plate was shot from that
  height. A "cut to black" at the end of a hop did not render; do it in the edit.
- Unusual body positions drift to familiar ones: restate the position in every shot.

## Across the film

- Get closer as tension rises, release with a wide. No two hops in a row with the same move.
- End on a tease held 2-3 s, not a tidy pull back to nothing. Rhyme images (the same insert at
  the start and the end).
- Under SLA Heavy the plate fixes the opening view: a move that starts elsewhere says so first; an
  angle the plate lacks gets its own plate.

## Transitions

A jump in time or a flashback reads better through a dip than a plain cut.

- **In the edit (exact, the default):** `scripts/transitions.py film.mp4 out.mp4 12:white:0.6
  36:black:1.0` dips on each restart seam (a seam's time is the sum of the hop lengths before it).
  Put it on the board so the user knows it is not in the render.
- **In the render, only with a cause in the picture:** a camera flash, a door shutting out the
  light, headlights into the lens, a blow to a first-person camera, written with its sound. Not
  proven. Never end the hop before a continuation on a black or white frame.
- **A camera device into a memory** (a push into the eyes, the camera sinking into water), mirrored
  on the way back to the face that remembered. Invent it from the film. Not yet proven.
- White for memory, dream or a flash of light; black for time passing, an ending, a blackout; a
  0.2-0.4 s flash for a hit. One or two per film.

## The read-through before a long render

The checker reads words, not space. Read every shot once against these:

1. Can each person see what she looks at? ("looks up over her shoulder at the clock behind her")
2. Do the sides hold? Someone who leaves one view on the right enters its reverse from the left;
   a person on someone's right is on the screen's left in a shot facing them.
3. Does every shot facing away from the plate name what is behind the person?
4. Does every face have a mouth state in every shot, wides included (lint `mouth`)?
5. Is every prop the same words in every shot, and does it travel only on screen?
6. Does a person keep her place when the scene moves on?
7. Does any small background figure have a task?
