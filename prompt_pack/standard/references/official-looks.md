Source: MiniMax-AI/MiniMax-H3 style skills (`skills/` on GitHub). Hub
generation, canvas nodes, Seedance, and negative-prompt blocks are not
ported. Prompt-only. Official fields stay in `base-en.md` / `ref-en.md`,
or `multishot.md` when that chain is on. Grid / panel-sheet reproduction
is `failures.md`. Canvas size is `canvas.md`.

# Official looks

Load after the mode guides when the user names one of these MiniMax looks.
Do not auto-apply because a scene could be an ad or an explainer. Stack
director only if they also asked for cinematic coverage this turn.

No negative-prompt block — write the desired state (`failures.md`).

On-screen copy, lyrics, UI labels, and spoken lines stay user-owned
(SKILL.md). If a look needs a line they did not give, offer 2–3 options
and wait.

## Unspecified duration

User value still wins if it is 4–15 s. Snap in `canvas.md`. Longer than
15 s → sequential clips (`planning.md`).

| Look | Unspecified |
|---|---|
| product-ad | `10.13` (243) |
| handdrawn, game-intro | `15.08` (362) |
| collage (per segment) | `5.17` (124) |
| papercraft, promo, mv, pixar3d | skill default `6.58`, or Plan if the story is longer |

## product-ad

Minimalist / Apple-style product film, ecommerce launch. Not talking-head
KOC, not a screen-demo.

Ref2VA with **three separate** product stills: hero silhouette, material
or mechanism detail, closing composition. Never one 4-panel or grid
sheet (`failures.md`). The original packshot is for analysis; if the
three anchors exist, do not also wire the packshot as a video ref.

Lock body color, accent, material, and finish from the user image.
Apple-style is negative space, light, and camera — not a white/silver
recolor.

Templates (background only): white-tech, dark rim light, brand color
field, light lifestyle. White-tech is a simple white field, not a
mirrored floor.

One product action per beat (lid opens, crown rotates, magnet snaps).
A secondary element enters only after that action is readable. Include
one or two intensity peaks, then a quiet brake for material detail,
readable copy, and the final hold. Transitions come from product edges,
highlights, mechanisms, or silhouette — not flashes, particles, fake
HUDs, generic glass cards, or repeated easing. Opening beat is already
an attractive angle or action, not empty white.

In-frame copy: 3–5 English words, one line, composition zone (not a
lower subtitle bar). Two colors only: first half black/dark gray
(white-tech) or white (dark rim); second half the **actual** product
color. First half enters, then the second half on the same line while
the first half shifts slightly. At most one mid-film copy beat plus a
stable final copy beat on a 10 s film. Spell every line and its time
window in the multimodal body. No invented logo.

Score: ~100 BPM tech instrumental — block chords, pluck, airy noise,
kick and sub, wooden percussion, sudden cutoff leaving a pluck tail —
or `N/A`.

Do not end on a grid, split, product wall, or storyboard board.

Header: `· product-ad`.

## papercraft

Handmade papercraft stop-motion explainer: miniature diorama, layered
cardboard with visible thickness, fibers, folds, seams, cut edges,
physical drop shadows, 4–7 depth planes, macro miniature photography.

Motion is stepped and hand-moved: tiny pauses, rebounds, hinged joints,
pull-tabs, sliders, rotating discs, paper settling. Background layers
move as paper mechanisms. Not smooth CG, plastic, or vector.

Stage those layers as foreground, midground, background, and far
background. The action sits in a readable middle plane, with paper
occluders and scenery on rails. Camera: slow push-in, lateral pan with parallax, static medium
for a label beat, macro for texture, a slight top-down cross-section, or
a layer pass-through. Not a high-speed orbit.

Cuts/transitions obey paper physics: page flip, pop-up unfold, pull-tab,
paper wipe, cloud pass, cut-paper door, circular paper mask, layer split,
confetti, tape, or sticker. Carry the mechanism's position across the cut.

Soundscape: paper flip, scissor, cardboard slide, rustle, wooden click,
tape peel, puppet joint. Score: light marimba / pizzicato, or the
topic's instruments; duck under narration.

Header: `· papercraft`.

## collage

Editorial halftone paper collage: flat bold color field, black-and-white
photographic cut-outs, selective cardstock accents, warm cream keylines,
soft paper shadows, refined torn edges. Controlled fiber — not kraft,
yellowed, or dirty unless they asked.

Default ~4 s segment snapped to `5.17`. Start on the approved field
color. Assemble 3–6 paper groups piece by piece: appear, slide or pop,
rebound, press flat, pause, lock. Main subjects before secondary
objects. Track overlap, orientation, and shadow. Building from an empty
field is not a loss of fidelity. If a final still is anchored, write
every paper step that reaches it. Hold the completed composition.
No camera move, zoom, morph, spin, or scene cut unless they asked.

Audio default: collage SFX only (slide, pop, press, rustle, snap).
BGM, voiceover, and subtitles only if they asked — then `N/A` the
unused layers.

No readable letters, numerals, UI, or logos unless they asked. Metaphor
is objects, not words on screen.

Header: `· collage`.

## handdrawn

15 s 16:9 live-action + rough glowing hand-drawn fusion unless they
named another canvas. Map these buckets onto the official timeline
(still official fields, not a freeform paragraph):

| Time | Beat |
|---|---|
| 0–3 s | Drawn entity clearly contacts a real hand or object |
| 3–6, 6–10, 10–13 | One entity continuously morphs; each form keeps a line, tail, color smear, or motif from the last; delayed handheld chase (entity leaves the frame edge, camera catches up) |
| 13–15 | Space-scale morph onto wall / floor / window / passage + one small cute beat |

The 0–3 s contact names point, pressure, material response, shadow or
glow, and the human reaction. Usable contacts: wrapping a finger,
landing in a palm, escaping a grip, emerging from a fingertip, pulling
a paper edge. The persisting trace can be a line, tail, smear, curve,
dot, or texture. Texture: crayon, chalk, colored pencil, pastel, rough
brush; jitter, uneven fill, frame-by-frame redraw. Photographer
participates (reach, grab, chase, open, catch). Same space or adjacent
rooms — no location cut. Cute / everyday. Avoid plush, uniform vector
lines, smooth neon tubes, giant eyes, split mouths, exposed teeth,
attack motion, sudden black frames, horror anatomy, a jump scare, or a
second character appearing from nowhere.

Header: `· handdrawn`.

## mv

Music video / lyric typography. Locked lyrics are the only source for
`<d>` and visible type — word for word, original language.

Typography is a spatial graphic (foreground, mid, or background; may be
occluded by a shoulder or hand), not a subtitle bar. Never cover eyes
or a critical lip-sync mouth. One main typography event per shot.

Character, scene, and type-packaging refs are separate `<Subject>`s —
a type card must not leak people or rooms.

Each shot names the current vocal or instrumental cue. Hard cuts on beat
(snare, 808, drop, lyric pause / breath). No fades or dissolves. Fast
passages tie a hi-hat, snare, or bass hit to a frame skip, a scale
change, a gesture, or a cut. Preserve mouth shape and motion direction
across a cut that continues a vocal. A vocal that exists only inside a
reused master track follows `ref-en.md` §5.4: cite `<Audio N>`, do not
invent `(Sx)`. Soundscape is room and body, separate from that master.
>15 s: sequential clips; one master `<Audio>` if they feed the song; do
not cut inside an active vowel unless the next shot is a mouth ECU that
continues the shape.

Header: `· mv`.

## pixar3d

Stylized 3D short: Pixar-inspired cartoon, C4D + Octane, Q-version
proportions, warm SSS skin, sculpted hair clumps with flyaways,
squash-and-stretch acting, clear silhouettes. Not photoreal, not flat
2D anime, not plastic toy skin.

Character cards and **environment-only** scene cards as `<Subject>`
refs. Scene cards must not contain people.

Plan each beat as five facts — action or expression, camera, position and
held objects, synced audio, and the state handed to the next beat — then
write them as motion-clock ranges inside the shot (`field-craft.md`), not
as per-second headings. If a landmark changes screen place because the
camera moved, say so. Track a character who leaves frame into the next
shot. One line of action, with anticipation, squash, overshoot, and
follow-through where the action stays readable. Dutch angle only for
imbalance, chase, surprise, or slapstick. Do not force this stylized-3D
default over a medium they named. Alternate close-ups with other sizes.
Longer than 15 s → Plan sequential clips; restyle each Write with this lock.

Header: `· pixar3d`.

## promo

Brand / product / app reel. Logo, UI, packaging, mascot, and claims
come from user assets only. Do not invent a mark, metric, or slogan.
If identity assets are missing, stop and ask.

One action per beat. A 15 s reel uses about five to eight beats; shorter
reels use fewer. Each beat has an owner, one proof, a readable-copy
interval, a color state, and a transition. Pace as setup, anticipation,
commitment, impact, brake, and settle, without printing those words as
labels. Keep two to five color states taken from the brand evidence.
Show the user action and the concrete result. Transitions from product
motion, cursor, UI flow, or matched geometry. Hold logo clear space.
Visible copy from brand materials, held long enough to read. Final beat
is product + supplied lockup.

Header: `· promo`.

## game-intro

Two-player co-op menu intro. Ref2VA: approved menu still as
composition/UI `<Subject>`; player photos as identity `<Subject>`s
restyled into the chosen look (keep face, hair, glasses, proportions —
not the photo's lighting or camera).

Requested on-screen labels (quote them): `PLAYER 1` / `PLAYER 2`, user
nicknames, `READY`, `START NEW GAME`, `CONTINUE`, `SETTINGS`,
`EXIT GAME`, plus the game title. Single-line, no wrap. Palette ≤5
colors; red only for danger/exit. P1 left, P2 right — do not swap.

Player 1 stays left, taller or more agile, with light precise gear and
the functional accent color. Player 2 stays right, shorter or broader,
with heavier gear and the warm strength color. Write sleeve, rail,
joint, lock, and finger articulation. In a close view, account for the
off-screen player. A height-comparison still is its own picture role.

Unspecified 15.08 s, continuous (no hard cut): 0–2 menu; 2–4 P1 right-arm
config; 4–7 P2 heavy-arm config; 7–8.5 confirm; 8.5–10 load bar;
10–15 enter the world in the chosen style (do not force cyberpunk).
The menu becomes the world through geometry, color, and UI motion, then
lands in a stable third-person co-op view. Hover tones and clicks sync
to the controls. No copied branded interface.

Header: `· game-intro`.

## Self-check

Fix before showing if the active look fails:

- product-ad: combined sheet as the only product ref; product recolored
  to generic Apple silver/white; two rows of copy; invented logo; ending
  on a grid or product wall; a secondary element enters before the
  product action is readable; fake HUD, glass card, or repeated easing
- papercraft: smooth CG / plastic / vector; no paper thickness, fibers,
  or layer shadows; high-speed orbit; the action has no readable middle
  plane; a cut drops the mechanism's position
- collage: kraft/dirty paper they did not ask for; camera move; BGM or
  VO they did not ask for; readable letters; pieces jump to the final
  arrangement
- handdrawn: no 0–3 s contact; contact has no point, pressure, or
  material response; a second entity appears; horror anatomy; plush,
  vector tube, giant eyes, split mouth, teeth, attack motion, or a
  sudden black frame; camera neatly centers instead of lagging
- mv: invented or paraphrased lyrics; subtitle-bar type covering eyes
  or mouth; fade transition; a shot names no musical cue; mouth shape
  resets across a cut that continues a vocal
- pixar3d: photoreal or 2D anime language; people inside a scene-card
  subject; per-second headings instead of motion-clock ranges; a Dutch
  angle with no imbalance, chase, surprise, or slapstick; stylized 3D
  forced over a medium they named
- promo: invented logo or claim; a beat has no concrete proof
- game-intro: swapped players; players equalized in height or gear
  weight; wrapped UI text; hard cut; loading hidden by smoke
