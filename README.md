# Biblical Scrolls

A wholesome, Facebook-style "living feed" where the people of the Bible live out the
story **chronologically**, time-compressed, as one shared world. You scroll, react, and
follow the cast, but you cannot post, only the people of Scripture speak. An anti-doomscroll
by design: the story unfolds on your own clock and cannot be binged.

Content currently spans **all of Genesis** (Genesis 1 through 50, 40 beats, 230 posts).

## Run locally

No dependencies, no accounts. Requires Python 3.

```
python app/serve.py
```

Then open http://localhost:8000. Per-user state (friends, reactions, story-clock,
notifications) lives in the browser's localStorage. Use the top-bar controls to change
speed, and turn on "engine view" for the debug Table of Contents (jump to any beat).

## Build the static site (for hosting)

The app is fully static: `/api/feed` is one authored world (identical for everyone) and
each profile is deterministic, so we pre-render everything to `docs/`.

```
python build_static.py
```

This regenerates `docs/` (the site GitHub Pages serves): `index.html`, `api/feed.json`,
`api/profile/<id>.json` for every character, plus the PWA manifest, service worker, and icons.
It reuses the exact logic in `app/serve.py`, so the static output matches the local server.

## Deploy (GitHub Pages)

`docs/` is served directly by GitHub Pages (Settings -> Pages -> Deploy from branch ->
`main` / `/docs`). It is a PWA, so testers can install it to their home screen.

## Project layout

| Path | What it is |
|---|---|
| `app/serve.py` | The whole app: stdlib server + embedded SPA frontend |
| `content/posts_*.json` | The authored feed content (auto-globbed) |
| `characters.csv` | The cast (~1,377 characters) |
| `beats.csv` | The pacing / Beat map (Genesis -> Revelation) |
| `relationships.csv` | The social graph |
| `build_static.py` | Pre-renders the static site into `docs/` |
| `docs/` | The generated static site (what gets hosted) |
| `DESIGN.md`, `STORY_THREADS.md`, `POST_FORMATS.md`, `CONTENT_ENGINE.md` | Design docs |
