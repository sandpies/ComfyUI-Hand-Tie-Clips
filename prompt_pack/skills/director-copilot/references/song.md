# Song: writing it (if needed) and measuring it

## What the user may have

| They have | Do |
|---|---|
| Song file + lyrics | Measure the file; align their lyrics to the timed lines. Best case. |
| Song file only | Measure with `--listen`; machine lyrics are rough (names, slang, ad-libs come out wrong). Ask them to correct the section table. |
| Lyrics only (song not made yet) | Plan the story per section now. Wait for the audio before fitting any timing. |
| Neither | Brainstorm with them, then write lyrics with section tags (below) for whatever music generator or musician they use. |

Do not assume a particular music service. Ask what they make songs with only if it changes the
format they need.

## Writing a song for a video

A song that is easy to film:
- **1:30-2:00.** Long enough for a story, short enough to render.
- **Short intro** (under ~10 s). Intro time is screen time with nobody singing.
- **Clear sections**, each tagged: `[Intro]`, `[Verse 1: Name]`, `[Pre-Hook: Name]`, `[Hook: all]`,
  `[Bridge]`, `[Drop]`, `[Outro: Name]`, `[End]`. Put the singer in the tag for multi-singer songs.
- **Name the characters in the lyrics** when they are the cast; it ties the words to the faces.
- **Verses that describe actions** ("grab chips, grab juice", "cut the wire") give the video its
  beats for free.
- **A breakdown or drop with no vocals** is a natural place for a spectacle shot nobody sings in.
- Style line: genre, BPM, instrumentation, the voices (e.g. "two male rappers, deep baritone and
  gritty mid-range"), "short intro". Generators often use one voice for everything; tell the user
  how to regenerate a section if two singers sound the same.

## Measuring

```
<comfy-python> scripts/song_map.py <song> --listen --out songmap.json
<comfy-python> scripts/song_map.py <song> --relisten 40-66 66-84     # spans the lyrics missed
```

Read the output for:
- **Tempo and bar.** Most songs are 4/4. If it reports 3 or 6 beats per bar, or a tempo that
  does not fit the song's feel, it is probably a misread (a 147 BPM song once read as 110). Ask the
  user, or count bars against the lyric line spacing.
- **Phase drift warning.** Downbeats are then tracked per 20 s; use `downbeats` from the JSON
  (the fitter does).
- **Sung bars** (`*`) and **timed lyric lines**. Whisper often drops dense or quiet stretches. A gap
  of 10+ s inside a sung section is a missed passage, not silence: re-listen that span, then ask.
- **Where the music really ends** (`sound ends`). The film ends just after the last sound.

## The section table

Before any story work, show the user this, and ask them to confirm by ear:

| Song | Section | Who sings | Lyrics (first words) |
|---|---|---|---|
| 0:00-0:11 | Intro | nobody / spoken | ... |
| 0:11-0:28 | Verse 1 | A | "Red jacket..." |

- Section starts land on downbeats; write them to 2 decimals from the downbeat list.
- Mark every instrumental stretch. Those hops get no singing.
- Say plainly which rows you guessed.

The cut times you pass to `fit_cuts.py` come from this table: one per hop boundary.
