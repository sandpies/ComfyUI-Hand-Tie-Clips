# Continuity: the director's sheet

A plan can pass every check and still fall apart on screen: people sit in one shot and stand in
the next, swap sides of a table, look the wrong way, walk through furniture, cut for no reason.
The checker reads words. Only you hold the scene. This page is how you hold it: one sheet for the
whole piece, reasoned the way a director and a script supervisor would, agreed with the user
**before any beat is written**, and then executed word for word.

The order that has held up best:

> script → plate read → **continuity sheet + cut list** → user vets → beats written from the sheet
> → check → dry-run read against the sheet → render → diagnose against the sheet

Why it matters more here than on a film set: every restart and every `[Shot N]` cut redraws every
person from words alone (fact 5). A position written two different ways in two shots is two
different positions. A position not written at all is wherever the model guesses.

## 1. Read the plate as a set

Before anything else, write the plate down as a floor plan in screen terms:

- **Near → far:** what stands between the camera and the back wall, in order ("low glass table →
  sofa facing the camera → windows").
- **Left / right:** what is on each side of the frame.
- **Which way each piece faces:** a piece facing the camera, or side-on along a wall? Standing
  free, or pushed against a wall? Open the plate image itself and look; do not write this from
  the plate's prompt or from memory.
- **What each piece lets people do:** sit behind it, lean on it, walk round which end of it. A
  piece that touches a wall at both ends has no way round it; a piece pushed against a wall has no
  way behind it.
- **Where the open floor is:** a walk over floor the plate shows reads cleanly; a walk over
  furniture comes back as someone climbing over it.
- **What it lacks:** no door, no top edge, the back of a photo frame (the `lacks` list).
- **Which angles it gives you.** The plate is one camera position. List every angle the story
  needs (a reverse on someone facing away from the plate camera, an insert, a view from the far
  end). An angle with no plate is a **weak spot**: give it a fixed named background used every
  time, keep it close, or make another plate. Write the weak spots down and show them to the user.
- **Shoot the coverage from the plate's side of the room.** A close that looks at a wall the
  plate never shows (a single whose background is a wall the plate does not include) makes the model
  invent that part of the room, and a restart that opens on it builds a whole new room that the
  continuation after it keeps, until a wide brings the plate back. Keep every camera on the plate
  camera's side, looking the same general way: singles in three-quarter with the plate's far wall
  behind them, two-shots in profile against it. That is also the 180-degree line kept for free.
- **A second plate of the same place works when it adds nothing the first one lacks.** A door, a
  window or a piece of furniture that only the close plate shows appears in the closes and is
  missing in the wides, and the viewer sees the room change at every cut. Before using a second
  plate, compare it with the first: anything new in it is either in the first too, or the shot
  never shows it. Often the cheaper answer is no second plate: keep the closes on the first
  plate and name a plain background (a dim wall) for the angles it does not show, and route
  exits through what the first plate has (out of the frame toward the camera).

## 2. Spots: fixed position phrases

Give every place a person stands or sits in the scene a code and **one phrase**, and use that
phrase word for word in every shot that shows them, like wardrobe:

| Code | Phrase |
|---|---|
| A-SEAT | seated in the middle of the sofa, behind the low table |
| B-NEAR | standing on the near side of the low table, between the table and the camera, at the right of the frame |
| B-COUNTER | leaning back against the front edge of the counter that runs along the right wall, halfway along it, her back to it, facing the room |

**Fit the spot to the room as the plate draws it.** "Behind the counter, facing the camera"
only exists if the counter faces the camera. If it runs side-on along a wall, the model cannot
put anyone behind it facing the lens, so it moves the furniture to fit the words. When the
phrase and the plate disagree, the plate loses. Write the spot from the piece's real
orientation, and name that orientation in the phrase ("the counter that runs along the right
wall") so every shot redraws the room the same way.

**Say which way the person faces the piece.** A side named loosely ("on the room side of it")
can still be drawn behind it. "In front of it, her back to it, facing the room" cannot. A shot
framed "across" a piece of furniture tends to put it between the people, so when both stand on
the same side, "beside" or "in front of" it says what you mean.

**A spot needs open floor the plate shows, and contact pins it best.** A spot named by an
object that sits in a corner (the end of a piece where it meets a wall or a window) has no floor
in front of it; the model puts the person inside the furniture, then behind it. Put the spot
where the plate shows floor, and tie the body to the piece by touch ("leaning back against the
front edge of the counter, halfway along it"): a person touching the front edge cannot be drawn
behind it. Keep the props and backgrounds of those shots from naming the bad corner again; place
props by the person ("on the counter behind her"), not by the corner's objects.

A phrase always gives **both** sides: depth (near or far side of the set piece it relates to) and
screen side (left or right of the frame) in wides. In a close single, keep the depth side and
drop the frame side. "Across the table from him", "by the end of the table", "in front of the
windows" are not positions: each can be drawn on either side.

**Eyelines follow from the spots.** If B stands to A's right in the wide, A looks off frame right
in every single of A, and B off frame left in every single of B. Check every close-up's eyeline
side against where that person stands in the wide: on a pull-back the model draws the person
where the eyeline points.

**Wardrobe phrases name the defining cut, not just the colour.** "Her black dress" leaves the
neckline, length and fit open, and every restart (above all a close one) redraws the
garment from the words plus the sheet. Look at the sheet and put what makes this garment this
garment into the fixed phrase: the neckline, the slit, the length, the collar. Change it once, in
every shot, or not at all.

## 3. Routes and props

- **Every walk is spot to spot, routed round a named end of a named set piece** ("round the left
  end of the table and along its near side"). An unrouted walk goes through the furniture. A route
  over floor the plate does not have (behind a bed pushed against a wall) also goes
  through it: the model makes the person climb over. If the place the story wants is unreachable,
  move the destination to open floor you can see, not the route.
- **Paths do not cross** unless the crossing is the point. Choose entrances and spots so they
  don't need to.
- **Every step has an end mark** ("one small step back and plants her feet there"). A step with
  no end keeps stepping. Never close a shot on the sound of footsteps after a step; the sound adds
  steps.
- **Props get a row each:** where it is in every hop, who moves it, and the move happens on
  screen. A prop that pays off later is **planted**: seen, or glanced at, before it matters. A
  reveal with no plant reads as coming from nowhere.

## 4. START → END, per hop

One row per hop: type (restart or continuation), the START (posture, spot code, facing, what each
holds), what happens (every change on screen), the END, and the END framing.

- **Each START is the previous END,** exactly. Posture and spot changes happen on screen inside a
  hop: never sit in one hop and stand at the start of the next.
- **The END framing is the next hop's first frame** on a continuation. Before a continuation it
  is a face at medium or closer (rule 8).
- **Read the rows as the audience would:** does every hop give a reason for the next? A line
  that asks a question gets its answer, or its refusal, on screen.

## 5. The cut list

List every cut, both joins between hops and `[Shot N]` cuts inside hops, with three things:

| Cut | Before → after | Why it cuts | What matches |
|---|---|---|---|
| 2→3 | front medium two-shot, B in profile at the right → low three-quarter medium close from B's front right, A soft behind her | B folds her arms as she sets terms: cut on that action | same postures, same spots, A still at B's left |

- **A cut has a reason:** a look (cut to what is seen), a line (cut to the speaker or the
  listener), a sound (cut to its source), an action that needs another angle, a reaction.
  A cut with no reason is the one the viewer calls jumpy.
- **Open a restart on a clearly different framing from the previous hop's end.** A big change of
  angle (the other side of the person, a low or a high angle, a three-quarter view instead of a
  profile) and of size reads as a cut. A small change reads as the picture skipping, not as a cut: an over-the-shoulder
  shot from the same side as the wide it follows sits on nearly the same axis, so it jumps.
- **When the scene stays put, cut to a new subject first.** A restart that opens on the same two
  people in the same spot, only a size tighter or wider, still reads as the picture skipping. The
  clean way back into an unchanged setup is an insert of whatever motivates the moment (the phone
  buzzing on the table, a hand on the dial, the object someone is looking at), held a second or
  two, then the cut back to the faces: the eye takes the insert as the reason for the cut, and the
  return lands as a fresh angle. The reaction to a sound plays best after its source has been seen.
- **Cut on an action.** The best restart opener starts a move the moment it opens: arms folding, a
  hand picking a prop up, a turn. The eye follows the move across the cut and does not check the
  framing. A camera move (tracking alongside the person to their next spot) is a good restart
  opener too.
- **A continuation is one take:** it holds the pinned framing, then the camera moves (pull back,
  drift, arc) to reach the next framing. Cuts belong in restarts. (Unproven as a rule; see
  [status](status.md).)
- **What matches** is what the viewer checks across the cut: posture, spot, what is in whose hand,
  eyeline side. Write it so you can read it back.

## 6. Lines and performance on the sheet

- One line per window with its own seconds; a lone short line in a long window is often said
  twice. Give the window the line plus an action, or make the line longer.
- The camera does not "ease onto" or "find" a person: the person moves to meet it. Say the
  camera holds, or name exactly where it stops.
- Faces play the moment in small moves (see [performance](performance.md)); the sheet says what
  each face is doing at every END.

## 7. The user vets the sheet

Hand over the sheet (spots, props, START → END, cut list, weak spots) in plain words, with one
layout line per scene, **and the plate image with every spot drawn on it** (a ring where each
person's feet are, labelled with the spot and its hops). Draw it from the plate itself, not from
the sheet's words: a spot with no floor under it, inside a piece of furniture, or tight against
another piece shows at a glance. Wait. A wrong side caught here costs a sentence; caught in a render it
costs the machine for an hour.

## 8. Execute from the sheet, not from memory

- **Phrases become constants** in the plan builder (or a block you paste from): spots, wardrobe,
  backgrounds for weak-spot angles. Never retype a position.
- **Spots become states** in `scene_map.json` (`who`, `phrase`, `hops`), next to wardrobe. The
  checker then refuses any shot that shows the person without the phrase. That turns the sheet
  into something checked, not just something written.
- **Write each beat from its row:** START, the timed changes, END, in that order. Nothing in the
  beat that is not on the sheet; a change you want goes into the sheet first, then the beat.
- **Check** (`build_graph.py --map --waivers`), then a **dry run** through the real node
  (`dry_run` on) and **read every assembled hop prompt against its row**: START = previous END,
  spot phrases present, eyeline sides, routes, props, END framing. Say which rows you checked.

## 9. After a render

Every slip the user reports maps to a row: a wrong side, a missing route, an unplanted reveal, a
cut with no reason. Fix the row, re-derive the beats from it, check and read again. Never patch
one phrase in a beat without asking which row it came from; patching one at a time is how a plan
drifts away from its own blocking.

## A worked sheet, short

Two people in a kitchen plate (camera at the doorway; near → far: island counter → stove → back
window; fridge on the left).

- Spots: A-STOVE "standing at the stove, behind the island counter, facing the camera"; B-ISLAND
  "standing on the near side of the island counter, between the counter and the camera, at the
  left of the frame". So A looks off frame left in singles; B looks off frame right.
- Prop: a letter. B brings it in (hop 1), lays it on the counter (1), A picks it up (3). Planted:
  A glances at it in hop 2 before reaching for it.
- Rows: 1 R: A at the stove, stirring; B enters from the left edge to B-ISLAND, lays the letter
  down; END close on A, eyes off left. 2 C: pull back to a two-shot; A's eyes drop to the letter;
  END two-shot. 3 R: opens on an insert of the letter (new size, not the two-shot); A comes round
  the right end of the island to read it; END close on B, eyes off right.
- Cuts: 2→3 cut on A's look (to what is seen); 3 insert → close A: her reaction.
- Weak spot: B's reverse close looks back toward the doorway, no plate: "the dim hallway soft
  behind him", every time.
