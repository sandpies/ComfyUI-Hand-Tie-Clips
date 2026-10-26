# Camera: directing the shot

The camera is written in the beat, never picked from the node. Leave the shot's `camera` and
`framing` directives empty; the node then adds no camera line of its own, and the move you write
is the only one the model sees. A `camera` value is one stock sentence with no speed, distance or
reason, and `hold` tells the model to stand still for the whole hop. A film of holds plays as a
row of separate scenes.

`join` still matters, because it is how the hop is made, not how the camera moves: `continuous`
on a continuation, `hard_cut` on a restart (the node refuses a restart with `continuous`). The
first hop ignores `join`.

## Three questions before every shot

1. **What changes in this shot?** The camera moves when the meaning changes and holds when
   nothing does. A hold is a choice, for tension that comes from stillness, never the default.
2. **Who has the power?** The camera drifts toward whoever is gaining it. Low and looking up
   makes someone big; high and looking down makes them small.
3. **What must the viewer discover?** The camera moves or cuts to show it, at the moment it
   matters, not before.

## The moment decides the move

| The moment is about | The camera |
|---|---|
| Someone arriving and owning the space | backs away ahead of them as they walk toward it |
| Power moving to someone | a slow push in on that person while they speak |
| A reveal that changes things | follows the object, then settles on the face it hits |
| Panic, loss of control | handheld, closer than is comfortable |
| A threat being prepared | a slow track along it (the tools, the weapon, the door) |
| Someone made small | low behind the strong one looking up past him, or high over the weak one |
| Two people circling each other | a slow arc around them, the speaker kept centred |
| Energy, a crowd, a performance | moves with the lead: rides alongside, orbits, rises over the crowd |
| An ending, isolation, aftermath | pulls back until the people are small in the place |

## Journeys: keep the goal ahead

- **A run away from the camera says "her back to the camera".** Without it, "runs away from the
  camera" can come out as someone facing the lens and moving backward, like a reversed clip.
- **The plate decides the direction of a run.** The plate is the camera: if it shows the goal in
  the distance (a ship at the far end of a pier), a run toward the goal is a run away from
  the camera, seen from behind. A shot from in front of that runner ("running toward the
  camera, the terminal behind her") on the same hop still gets the plate's view behind her, so
  the ship came out at her back and she seemed to run away from it. A front view of the run
  needs its own plate from the other end (looking back at the land), or a hop without the
  goal's plate; otherwise stay behind her, or side-on with one fixed screen direction.

## Cutting between two places

Cutting back and forth between two places inside one hop (a runner on a pier, someone waiting
on a ship) lets the two plates swap: the runner's second shot, "running toward the camera down
the pier, the dark terminal behind her", came out on the ship's deck with the lifeboats behind
her. The match cut and the flashback held; the place did not. Give each place its own hop (a
restart per place, short hops are fine), or keep the second place's shots to faces and hands
with nothing of the place in them.

## The shape of a hop: one take, or cuts inside it

A hop does not have to be one continuous take. Up to 15 s can hold one moving take, several
shots cut like an edited scene, or both. Choosing which is the directing.

- **One take** when the tension is in the continuity: a walk-and-talk, a slow threat, a reveal
  the camera reaches by moving, stillness the viewer cannot escape. A move can do a cut's job
  (the camera arcs until the man in the doorway comes into view).
- **Cuts inside the hop** when the viewer needs what the current angle cannot show: an action
  and its reaction, shot and reverse shot in a dialogue, an insert of the object that matters,
  the power flipping, a jump in place or time.
- **Both:** a moving take into the action, then a cut to the aftermath.

Two or three shots per 12-15 s hop is a good pace; give each shot at least 2 s.

### Writing shots

Use H3's own shot form. Each shot opens with `[Shot N]`, says where the camera is and what fills
the frame, then gives the action with times counted from the hop's own start:

> [Shot 1] @a is already seated in the leather chair across the table in @room, facing the
> camera, lips pressed shut, in a medium shot at chest height from the doorway. At
> 00:00.000-00:05.000, he sets his glass down while the camera pushes slowly in until his head
> and shoulders fill the frame. [Shot 2] At 00:05.000 a cut to the reverse angle in @room_reverse:
> a medium close shot from behind @a's shoulder, which stays at the near left, looking across
> the table at @b in the wooden chair, facing the camera. At 00:05.000-00:12.000, @b's grin
> slowly fades, lips pressed shut, and he swallows.

- **Lead `[Shot 1]` with a person acting** (hard rule 1): `[Shot 1] @a is already seated in
  @room ...`, never `[Shot 1] A wide shot of @room ...`, or the hop opens on the empty plate.
- **Every shot names the plate it is in.** A cut to another angle of the same place holds when
  that angle has its own plate and the shot names it (`a cut to the reverse angle in
  @room_reverse`). Plates can change inside a hop, and so can places: a continuation can open on
  the pin in one room and cut to another (`At 00:03.000 a cut to @kitchen`). A shot from an angle
  no plate shows is less certain; keep it close (a face, hands, an object) so little background
  has to be invented.
- **Every cut re-places everyone.** Each shot is a new frame: name every person in it, where
  they are in that frame and what they are doing, including the one who sits still ("@a is
  still seated in the leather chair on the left, in profile, facing right"). A person not named
  in a shot is not in it, even if they never moved. Keep each person in the same place across
  the cut; one who moves between shots without being shown moving gets dragged and warps.
- **Seats are placed by the frame, not by the room.** "@a nearer the camera, @b nearer the
  window" from the aisle becomes "@a nearer the camera" again from the window end, and the two
  swap seats. Every shot that shows them translates the seating into its own frame ("from the
  window end: @b nearest the camera, @a beyond him by the aisle"). A sit-down or an arrival inside
  a close shot can widen into a shot nobody wrote and seat people by habit: keep that action
  "in the same medium shot, alone in the frame".
- **Keep the gap between people the same across a cut, as a number in both shots** ("five
  steps in front of @b"). A place word like "halfway down the corridor" reads differently from
  each camera, and a close shot of one person with the other "just off the frame" puts them
  side by side. An action that needs room (a sprint at someone, a slide, a run-up) makes the
  model make the room: the person jumps back to start it. Write a short run-up into the action
  ("takes two quick steps and drops into a slide") instead of a sprint over a short gap.
- **Someone heard but not seen stays out of the frame.** Footsteps, a voice or a knock behind a
  door that is in the frame gets a person drawn in the doorway, and on a hop whose refs carry
  only one character, that person comes out as a copy of the one character. Put the source
  behind the camera and say so ("the stairwell door behind the camera, footsteps echoing from
  behind the camera"), or put the newcomer's row on the hop and name them in the shot.
- **A small figure in the background gets a pose, not a task.** A fiddly hand action given to
  someone small behind glass ("her finger turning the dial of the phone") got its own unwritten
  insert: the film cut inside to a close of her hands, with the person walking past the lens
  still crossing the foreground. Keep a background figure to a pose ("stands behind the counter,
  the phone beside her hand"), or give the action a `[Shot]` of its own. Not yet proven.
- **A person someone watches leave is drawn into the watcher's shot.** "Her eyes follow @a, who
  walks off the frame to the left" put @a right beside the watcher, shoulder to shoulder, and the
  two of them, close together with no lines, filled the shot with chatter. Say the person is
  already gone and give the watcher a distance and a place off that person's path: "@b alone in
  the frame, far across the street from the shop, her eyes on the corner where @a has just
  disappeared; nobody else is in the frame".
- **A reverse angle with no plate says what is behind the person.** With the place's plate on
  the hop, a close shot "from the other side" still pulls the plate in behind the face. Name
  the background ("only the dark sky and the city lights behind her") and where the plate's
  features are now ("the hut behind the camera").
- **Words that name a plate feature put the action on it.** "Climbs the stairs" when the
  plate shows an outside staircase puts the climber on those stairs. Describe action in terms
  the plate actually shows, or keep it off screen.
- **Say a camera height twice when it matters.** "A low angle just above the floor, looking up
  at him" can still come out near eye level; repeat it in the action ("the camera stays low").
- **Inserts are their own shot.** Hands, a phone, a stack of bills: `[Shot 2] At 00:04.000 a cut
  to a close shot from just above the table, looking down: @a's hands ...`. Name whose hands.
- **Beat length.** A multi-shot beat runs well past the node's one-take word budget (a 3-shot
  12 s hop is often 200-300 words). That is expected; the node's length warning is for one-take
  beats.

### Shots inside a chain

- **A restart** can be cut anywhere; it opens on its own refs.
- **A continuation's `[Shot 1]` continues the pin:** the same place, angle and pose as the
  previous hop's last shot, with no cut in its first 2 seconds (the first second is the dropped
  overlap). After that it may cut anywhere.
- **The last shot decides the next hop.** Before a continuation, the hop's last shot ends on a
  face toward the camera, medium or closer (hard rule 8). The angle changes happen inside hops;
  the seams stay quiet.

### Props the model would otherwise invent

Cards, chips, money, papers and screens are drawn fresh in every shot unless the beat fixes them.
Name how many, what they show and where they lie, every shot they are in: "two cards face down
on the felt in front of each man, one neat stack of black chips beside them", "the two black aces
face up". When an object changes (cards turned over, chips pushed in), say what it is now. A prop
left vague turns into a pile of different objects from cut to cut.

A prop the plate does not have, first mentioned after a cut, gets multiplied: one backpack "at
her feet" in a two-person wide came out as one bag per person. Count it and own it ("one black
backpack, the only bag on the roof, at @b's feet") from the first shot it is in, or put it in the
plate.

An object that is itself a picture (a drawing, a photo, a screen) is drawn in the film's own
medium unless the beat says otherwise; a "pencil drawing" in an anime film came out as a full
colour illustration. Name the medium of the object too ("a rough grey pencil sketch on white
paper, no colour").

An invented prop with no picture does not hold across hops: the same full description pasted
into every shot keeps the gist (eight sides, a blue lid) and changes everything else in each
appearance. A prop that appears in more than one hop gets its own picture (one object on plain
grey), a tag and a row on every hop it is in. A person in a photo is
best a prop picture of that photo, which held the same face on every hop with no bleed.

A prop the plates do not show gets redrawn in each insert unless its shape is fixed: "one small
key glowing cyan" was a key in the vault and a glowing fob in a later close-up of a palm. Within
one hop, give it a shape and parts in every shot it is in ("a small cyan glowing key with a
round head and a short notched blade"); across hops, give it a picture.

A hand action on a prop gets every step written, in order, or the model skips the ones it was
not told: "pours from the decanter" poured from a decanter that kept its stopper on. Write
"lifts the glass stopper out of the decanter and sets it on the table, then pours". The same
goes for a cap, a lid, a zip, a lighter, a phone lock: open it before using it. Not yet proven.

A mark that is already on a page or a screen (a circled line, a stamp, a crossed-out name) gets
drawn on camera if a hand touches it in the shot: a finger tapping "the line circled in red ink"
drew the circle as it tapped. Say the mark is already there before the shot starts and does not
change, and keep the hand beside it, not on it ("taps the margin next to the circled line").

Words held a briefcase and two folders steady through several inserts inside one scene when each
had a colour, a count and parts (two brass clasps, one thick green folder, one thin red folder).
A prop the story turns on (it recurs across hops, gets close inserts, changes hands) gets its own
reference picture, the way a character does: one object, centred, on a plain neutral background,
lit evenly, no hands, no text. Give it a tag (`@key`), put its row on every hop it appears in, and
name it by tag in every shot ("@mika lifts @key out of the case"). Words alone let it change
design from insert to insert. Not yet proven.

A person shown inside a screen, photo or drawing is still a person: name them, and give the
model their likeness. Prefer a prop picture of the photo itself (the polaroid with their face,
made as an image) over their character sheet: a sheet with no body in the shot bleeds onto the
nearest person of the same build. "A small figure in a red jacket" on a monitor, on a hop carrying only the
watcher's sheet, came out as a man.

### Action

- **Body contact warps when it is fast.** A shoulder ram or a punch landing in a few seconds
  renders bodies melting into each other. Prefer near misses ("ducks under his arm without
  touching him") or one grab that then holds still ("grabs the back of his jacket and pins him
  to the counter"), and give it a shot of its own with at least 3-4 s.
- **Every run or walk has an end mark.** A run "toward the camera" with no stop keeps going: the
  runner overshoots everyone in the shot and ends up in the lens. Give the start point and the
  stop point against a person or a fixed thing in the plate ("runs in from the far end of the
  platform and stops an arm's length in front of @b, facing her"), or end it on purpose ("runs
  out of frame past the lens"). A camera backing away ahead of the runner also holds the
  distance. "Slows to a walk" is not a stop.
- **Nobody enters from behind the camera.** "Walks in past the camera from behind it" renders the
  body passing the lens in a close shot (hips and hands filling the frame) before the wide shot
  returns. Start the person already a few steps into the frame ("is already walking away from
  the camera across the floor"), or have them enter from a side or a door the plate shows.
- **One contact at a time, never one action at a time** (hard rule 5): when someone strikes,
  grabs or breaks something, nobody else touches that person or thing, but everyone else keeps
  doing their own thing clear of it. A frame where one person moves and the rest freeze plays
  like a slideshow.
- **Phone calls end with the call ending** ("the call clicks off, and the only sound is the
  rain"), or the model gives the other end a voice.

## Eyelines

A face turned toward the camera is not a person looking into the lens. Keep the two apart in
every beat.

- **Music video:** the performer may sing straight into the lens; that is the form.
- **Film or story scene:** nobody looks into the lens. Turn the face toward the camera,
  three-quarter, so it can be seen, and put the eyes on the person they are dealing with, with
  a direction: "facing the camera three-quarter, his eyes on @b just left of the lens". In a
  reverse shot the listener is off frame, so name where: "looking up at @a, who stands just off
  frame to the left". **When the camera sits where the listener sits** (their seat, their side of
  a table, a shot "from" their bench), "eyes on @a just left of the lens" pulls @a into the frame
  beside the lens, facing straight into it, and the speaker looking at @a looks into the lens too.
  Put the camera beside the listener, not in their place, and send the look clearly past it:
  "eyes on @a, who sits off the frame to the left, his gaze passing well to the left of the
  camera". "Just left of the lens" is barely off the axis in a close shot and reads as a look
  into the lens; keep it for medium and wider shots. Or place @a in the shot with a facing
  ("the back of @a's head at the left edge").
- **"Face toward the camera" in a side-on shot turns the person to the lens.** When the people
  face each other in profile (a booth from the aisle, a table side-on), a face "three-quarter
  toward the camera" turns away from the other person and into the lens. Keep them "in profile,
  facing @a" there. When a hop must end on a face for the next continuation, end it with a cut
  to a close shot taken from beside the listener, not by turning the person in the wide shot.
- **"From beside @b" can put @b in the frame.** With @b's sheet on the hop, a close of someone
  standing across a room "from beside @b" drew @b at her shoulder, and she jumped across the
  room between cuts. When the two are not close together, place the camera by the room ("from
  across the table") and close the frame: "@a alone in the frame, still standing by the window
  ..., her eyes on @b across the table, off the frame to the right; nobody else is in the frame"
  (lint `beside-tag`). This failed twice in one scene; never dismiss the lint by
  guessing the distance, read it off the scene map.
  Never
  write "into the lens", "at the lens" or "toward the lens" in a
  scene unless breaking the fourth wall is the point, once, on purpose.
- **Not yet render-proven:** "looks down at @b" alone still came out as eyes in the lens on a
  face turned to the camera; the explicit "eyes on @b just left of the lens" form is the fix to
  test first.
- **Every line has a listener in a named direction.** A line spoken to nobody in particular
  turns into a line spoken to the audience.
- **Every face turned to the camera needs something to look at.** A face "facing the camera" in
  a group shot, on a walk toward the camera, or posing, with no target for the eyes, looks into
  the lens; a film with "toward the camera" in every shot came out with far more lens looks than
  it needed. Give each face a target off the lens (the guests on the left, the falling card, the
  door), and say "toward the camera" only where the face must be seen (lint `no-eye-target`).
- **A close shot pulls in whoever its eyeline names.** A close of one person at a railing, "her
  eyes on @b, who stands off the frame to the right", drew @b's head into the edge of the close,
  because @b stood right beside her. Every close with someone named off the frame gets "@a alone
  in the frame ...; nobody else is in the frame" (lint `pull-in`; the same fix as `beside-tag`).

## Bodies in vehicles and rows

Seats fix which way a body faces, and the model does not know it. Say it in every shot:
"seated in the passenger seat facing forward toward the windscreen, the back of his head and
his right cheek to the camera". A close shot that shows a face from the front drags the body
round to the camera in the next wide shot unless that shot names the direction again. A plate
from behind the seats shows the backs of heads; faces need a plate or a shot from the front
(from the dashboard looking back).
Getting out of a car is unreliable: "steps out of the backseat of the black car" still came out of
the boot. Avoid the exit when you can: start him already standing beside the car, the rear side door
open behind him, and let him shut it ("swings the open rear side door shut behind him"). If the
exit must be seen, show the side of the car to the camera and name the door: "the rear side door
nearest the camera swings open and he climbs out of the back seat".

- **A lone person in a car shot becomes the driver.** A close shot of the passenger alone came out
  with him at the wheel. Keep the driver in the frame (his hands on the wheel at the edge), or
  name the empty side ("the driver's side off the frame to the right, no steering wheel in front
  of him").
- **Name everyone in the car in every shot that shows its seats or windows.** A side-on shot that
  named the two in front had an empty back seat; the third man then popped up at the window in
  the next shot.
- **Say which way the world moves outside.** "Neon lights streak past" came out with the street
  running backwards. Tie it to the car: "the car drives forward, the street lights coming toward
  the camera through the windscreen and sliding past the side windows toward the back".
- **Dashboard parts are interchangeable to the model.** "Turns the radio dial" came out as a hand
  on the speedometer. Describe the part by its look and place ("the small chrome knob of the radio
  in the middle of the dashboard, below the gauges"), or cut the insert.
- **Mirrors show a person.** A rear-view mirror in a close shot showed a stranger's face. Say who is
  in it ("the mirror showing @ana's eyes") or turn it away ("the mirror tilted up at the roof").

## Writing the move

One move per shot, written as **type + amount + speed + what stays in frame + where it stops**:

> The camera starts low, just above the wet floor, tilted up at him, then rises slowly to his
> eye level and levels off as he halts in a medium shot.

> The camera arcs slowly left around the table, about thirty degrees, keeping @a centred,
> until @b slides out of frame on the right.

- Name where it starts (height, side, facing) and where it ends (the framing: "head and
  shoulders fill the frame", "the two men small at the far end").
- Say what stays in frame during the move. A push in on two people can push the speaker out;
  name who the camera keeps. The speaker must stay in frame for his line.
- Tie the move to a person or a moment ("as he leans in", "as the photo stops in front of him").
- **Ration the push in.** It is the easiest move to write and the first to wear out: at most one
  per scene, and stop it at a framing ("until his head and shoulders fill the frame"), or it ends
  in an extreme close-up staring into the lens. For variety reach for an arc around the people,
  a track alongside a walk, a rise or a drop in height, a hold that lets the action come to the
  camera.
- Proven words: holds, arcs, backs away ahead of him, rises, starts low tilted up, pushes in,
  draws back, tracks backward ahead of him, handheld, cuts. Held in one render each: "tilts
  slowly up" (an empty establishing shot), "zooms in fast to a close shot of her face" (a crash
  zoom), a person on a flat solid colour background with no plate. Truck, pedestal, POV and roll
  are not yet proven; try one at low resolution before a film leans on it.
- **No full circles.** A camera circling all the way around a person warps them once it passes
  behind: the model has to invent their back and the reverse background as it goes. Keep an orbit
  to a half turn or less ("circles halfway around her, from her left side to her right"), and
  stop it on her face.

## Stressing the camera: action hops with no lines

A single 15 s generation holds 7-8 shots (a cut every ~2 s, sub-beats of half a second) with
extreme cameras, when the hop has no dialogue and no lip sync to protect. The three-to-four-shot
budget is for hops with lines and close acting; an action hop with nobody talking can cut twice
as fast.

**The shape that works** (one 15 s hop, held in three renders of three different sports):

1. A sensory extreme close-up: fingers on frost, wet eyes, a glove on asphalt; one small action
   in it (a breath, crystals crumbling), 1-1.5 s.
2. A wide for scale: "a wide drone shot from high above", the person tiny in a huge place.
3. Immersion: a mounted or point-of-view camera ("a helmet-mounted POV skimming low over the
   ridge, the gloved hands at the edges of the frame", "a camera mounted inches above the
   asphalt, facing the rider's feet").
4. Speed: "a drone tracking shot flying low beside him", a fast push in as the space narrows.
5. The peak: one beat where the motion slows, the sound drops to a breath or a heartbeat, then
   "normal speed snaps back with a heavy bass impact".
6. Release: a wide pulling back, or a slow arc level with the person revealing the landscape.
7. Resolution: a silhouette against the sun, moving away.

**With character sheets on the hop** (two people, no lines), 7 shots in 15 s still held, faces
and cut times included. A high angle did not: "a high shot from above the lanterns, looking
straight down the lane" came out at eye level, as a drone shot did on an earlier sheet hop. A high
angle over referenced people is unproven; keep the scale shot level, or try it on a hop of its own.

**How to write it:**
- Every shot opens with a camera of its own ("cuts to a low static shot inside the gap, looking
  out toward the opening") and gets timed sub-beats ("At 00:07.000-00:07.500, ...").
- Pair every picture beat with a sound beat, and write the music's shape against the cuts (builds,
  drops out at the peak, returns with a hit, stops dead at the end).
- Speed words: "at fast speed", "the motion slows to slow motion", "normal speed snaps back".
- Cut times land within about half a second of what is written.

**The price of that density:** some shots come out with the camera in the wrong place or moving
the wrong way (a POV that tilts off, a move that drifts instead of cutting, an object that
appears before it should). Spend the stress on spectacle shots that can be wrong and still read;
put the shots the story depends on (the face, the prop, the turn) on proven moves, and expect to
reroll a dense hop.

**What these renders also showed:**
- Shots in the same space can merge into one continuous move: seven written shots on one wave
  came out as three hard cuts with the camera flying between the rest. Give each shot a clearly
  different camera position (drone, water level, inside the barrel) if every cut must be hard.
- A final "cut to black, held in silence" for the last half second did not render in any of the
  three; the last shot just holds. Do the black in the edit.
- An unusual body position drifts toward a familiar one: a street-luge rider lying feet-first
  came up kneeling on the board in the hairpin. Re-state the body position in every shot.
- These subjects had no reference sheet. With a sheet and SLA Heavy on, the full arc behind a
  person is still the warp risk above; keep it to a half turn on a referenced character.

**Cover a chase from many places, not one.** A runner coming at the lens is one angle; a
chase that only uses it plays as the same shot repeated. Every cut moves the camera somewhere
new, chosen from what this chase's place offers: the rooftops give a drone, a market gives a
camera behind the stalls, a train gives the window beside the runner. A tracking shot
alongside, a camera on the ground at the feet or the chaser's view over his shoulder are
examples, not a set to repeat in every chase. Keep the chase's screen direction fixed across those cuts (the runner
always crossing left to right, the chaser always behind her on the left) and write it in
every shot, or the cut reads as her turning back. Not yet proven.

## Across the film

- **Get closer as tension rises, then release with a wide.** Wide, medium, close builds a
  scene; a wide lets it breathe.
- **No two hops in a row with the same move.** Contrast between cuts is what makes it feel
  edited rather than a string of scenes.
- **Budget the story against the running time.** Every story turn (an arrival, a deal, a trick,
  a discovery, a payoff) needs at least one hop of its own, plus room for the reactions around
  it. A minute holds three or four turns comfortably; five turns in a minute plays rushed. Cut a
  turn or add hops rather than squeeze.
- **End on a tease, not a full stop.** Resolve the story, then open one small new thread in
  the last shot (a phone buzzing with an unknown number, a figure in the doorway, a smile that
  fades) and hold that image 2-3 s before the end. A tidy pull back to nothing reads as abrupt.
- **Rhyme images.** The same insert at the start and the end (a hand counting money, a door
  closing) tells the story without a line explaining it.
- **Plan each hop's last frame.** It is the next hop's first frame: the move must stop where
  the next shot can start.
- **The plate must allow the move.** Under SLA Heavy the plate fixes the opening view. A move
  that starts somewhere else (low, high, side) says so in its first camera sentence; an angle the
  plate does not show gets its own plate.

## Transitions: flashes, blackouts, whiteouts

A jump in time or a flashback reads better through a dip than a plain cut: a white flash into a
memory, a fade through black out of it, a hard white flash for a shock. There are two ways.

- **In the edit (exact, free, the default).** A seam between restart hops is a hard cut at a
  known time (the sum of the hop lengths before it). `scripts/transitions.py film.mp4 out.mp4
  12:white:0.6 36:black:1.0` dips to white or black centred on each cut; the sound is untouched.
  Plan it on the board ("hop 2 opens through a white flash") so the user knows it is not in the
  render.
- **In the render, only with a cause in the picture.** A light in the scene that fills the frame:
  a camera flash, a door closing out the last light, headlights into the lens, a blow to a
  first-person camera ("the frame goes black, a thin high ringing"). Write the cause
  and the sound together. The next hop can open on the same state as a restart ("the black
  slowly fades up, blurred, then sharp"). Not proven. A plain "cut to black" or "fade to white"
  with no cause in the picture has not rendered, and never end the hop before a continuation on
  a black or white frame: the continuation has nothing to rebuild the people from.

**A camera device into a memory.** A dip alone is a cut; a move that carries the face into
the past reads as remembering. Invent the move from what this film is about: a push into the
eyes for a memory of a face, the camera sinking into the water for a drowning, a turn of the
object in the hand that becomes the same object years before. The way back mirrors the way in,
ending on the face that remembered. Not
yet proven.

Match the dip to the meaning: white for memory, dream or a shock of light; black for time
passing, an ending or a loss of consciousness; a quick flash (0.2-0.4 s) for a hit or a camera
flash. Use them sparingly: one or two a film keeps them meaningful.

## The read-through before a long render

First run every shot through the six facts ([directing](directing.md#part-2-the-method)) and
`check_plan.py --map`. Then:

The checker reads words, not space. Before a render of more than a few hops, read every shot
once against these questions; each was a mistake the checker passed.

1. **Can each person see what she looks at?** A clock "behind her" that her eyes "rise to" is
   behind her head. Write the turn ("looks up over her shoulder at the clock behind her").
2. **Do the sides hold?** Write one line per scene: who is on the left in the side-on shot, which
   way each looks in her close. Every close and every entrance follows it; someone who enters
   from behind a person cannot be seen coming by that person. Someone who leaves one view on the right enters
   its reverse angle from the left. A person on someone's right is on the left of the screen in a shot
   facing that someone.
3. **Does every shot facing away from the plate name what is behind the person?** A reverse
   angle with no background named pulls the plate in behind the face.
4. **Does every face on screen have a mouth state,** in every shot of a hop with lines, wide
   shots included (lint `mouth`)?
5. **Is every prop the same full words in every shot it is in, and does it travel?** Follow
   each prop from hop to hop: who holds it, where it goes. A card one person keeps cannot turn
   up in another's hand at the end unless a shot hands it over.
7. **Does a person keep her place when the scene moves on?** Someone who walks to the other side
   of a chair in one hop is still there in the next.
6. **Does any small background figure have a task?** Give it a pose, or a shot of its own.

## Failures this page prevents

- Every hop on `hold` or a stock `push_in`: the film reads as a row of separate scenes.
- A restart with a push in and close framing on a wide plate: it opened on the empty plate,
  then zoomed in.
- A push in on two men pushed the speaker out of frame, and his line came out of the other
  man's mouth.
- A cut to a side angle that did not name the seated man: he vanished from the room.
- A fast shoulder ram: both bodies warped.
- "Facing the camera" and "into the lens" in every shot of a story: every character talked to the
  audience.
- A car seen from the back seat after a frontal close-up of the passenger: he sat facing backward.
- Push in after push in: one ended in an extreme close-up staring into the lens.
