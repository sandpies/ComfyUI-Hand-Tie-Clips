# Music video: treatment, energy and the song's rules

Read this for any music video, before the story stage and again before writing plans. Measuring
the song is [song](song.md). Films use [film](film.md) instead.

The node's WRITE tab carries the same craft in short form (`prompt_pack/write/mv.md`), and the
Studio's concept step asks for the same treatment. A lesson that changes this page changes that
file too.

## 1. The treatment comes before any table

An MV without a concept turns into a reel of plates with someone walking and doing random things in
front of each one. Before the place-per-section table, write a treatment of half a page and show it:

- **The idea in one line.** What the video is about beyond the lyrics: a device, a game, a world
  rule ("everything spins around her", "she blinks and the city cuts").
- **The visual hook.** One move, image or effect that belongs to this video only, and that comes
  back and grows each chorus.
- **Escalation by section.** What is bigger, stranger or closer in each section than in the last.
  The last chorus pays off what the first one set up.
- **Worlds.** A few designed sets, each with its light and a hero prop or texture. Places can
  intercut inside a section; they do not have to be toured in order.
- **Performance.** Who sings to the lens and where, and what the performer does between lines.

The story table, the plates and every hop come from the treatment. When a note arrives, change
the treatment or the sheet first, then the beats.

## 2. Energy: what real music videos do

Measured on popular MVs: the median shot is about 0.7-0.9 s, cut density follows the song (a
build around 4-5 cuts per 15 s, a drop or chorus 15-20), and the camera moves in most shots, often
on two axes at once, with a lot of handheld on street sets. Choreography wides cut against tight
attitude close-ups about every second. Light design (colour blocks, silhouettes, spotlight pools)
does as much work as the set.

H3 will not cut every 0.8 s, so take the shape, not the numbers:

- **4-7 `[Shot N]` cuts per hop** on high-energy sections (proven), fewer on verses. Change angle
  and size on every cut.
- **Place the camera, don't only move it.** Height, mount and what it looks through decide the
  energy: on the floor, fixed to her body, in the air, behind something, whips landing on the
  beat. `check_plan.py` prints the mix of bold, safe and slow placements; read it before the
  hand-over.
- **A new named move every bar or two, each with an end.** One gesture written for a whole window
  ("slicing one hand on every beat") loops. Quick gestures get their real steps (reach, cover,
  shove, swing back). Named pose hits that land on the downbeat and freeze read as choreography;
  "dances" reads as flapping.
- **Few timed windows inside one continuous take,** at most two, each around 1.7 s or longer, on
  the key moment. Many or short windows render as stutter cuts. Everything else flows with
  "then ... on the beat". Cuts between shots are free.
- **Singing on chosen shots only.** The same to-lens rap clause on every shot reads as "cut, sing,
  cut, sing". Effect and interaction shots carry no mouth line.
- **An effect on every hop from hop 1.** Pick one `fx.json` effect per hop that lands on a named
  move or beat. Effects that start only mid-song leave the opening plain.

## 3. The song's rules

- **No `<d>` lines.** The song drives the mouths. Write who sings and how ("raps fast, his eyes on
  the lens, his lips shaping every word"). A performer may look at the lens; "into the camera"
  reads as travel toward it and pulls the shot in.
- **Sung beats only over sung music;** check the section table. A hand task ends a little before
  the performer's first vocal.
- **Whoever is not singing has something concrete to do.** A non-singer alone on screen over
  vocals mouths the song: put their solos on instrumental bars, or keep the singer in frame and
  give them a closed mouth.
- **A masked or faceless character does not sing,** unless the mask has a jaw the model can move
  (a lower-face skull half-mask sang a whole MV): then the jaw does the singing ("the jaw of the
  skull half-mask working with every word"). A masked character written unmasked, even from behind
  or putting the mask on, gets an invented bare face that every continuation keeps. The mask phrase
  names what shows round it ("his bare forehead, brows and eyes above it").
- **No song-structure words** ("hook", "chorus", "verse", "the last line"): the model has no song
  map. Describe what the mouth and body do (lint `song-words`).
