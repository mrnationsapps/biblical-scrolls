# The Content Engine — how a character's feed is generated

The living world is **generated, not hand-written** (except Leads and anything sacred). This is
the recipe an LLM runs per character, per beat. The vertical-slice file
`content/posts_ambient_preflood.json` is this recipe run **by hand** on the Beat 1-3 family
neighborhood, to prove output quality before we automate it.

## Tiers of liveness (depth concentrates where it matters)
- **Lead / Canonical / Sacred** → authored or tightly guided (see `STORY_THREADS.md`). Maximum
  control. The engine never freelances Scripture; Spine content is authored or review-gated.
- **Regular** → semi-procedural: a defined life-situation, reacts to the big events, posts
  periodic life updates.
- **Ambient** (the ~500+ crowd) → fully generated daily-life + reactions. Shallow depth, real
  *presence*. They make the world feel full.

## Inputs (all already exist as data — this is why it's feasible)
1. **The character** — `characters.csv`: Personality, Work_Title, Faction, Era, Gender,
   Voice_Tone, Emoji_Level.
2. **Their friends** — `relationships.csv`: who comments and reacts (in *their* voices).
3. **What's happening this week** — `beats.csv`: the active Beat(s) in the character's window.
4. **Proximity to the Spine event** — near = reacts directly; far = hears it as rumor/news.
5. **Shapes & arcs** — `POST_FORMATS.md` (post types) + `STORY_THREADS.md` (any arc they're on).

## Output (per character, per beat)
A few posts, each: `{ time_of_day, body (in their voice), reactions (population-bounded),
comments (from friends, in THEIR voices) }`.

## Hard rules
- **Period-true** (no anachronism). **Reverent** toward the sacred.
- **Voice = Personality** (sarcastic / blunt / wistful / easygoing…). Friend comments use the
  friend's personality, not a generic one.
- **No spoilers** past the character's clock. **Mortality:** the dead stop posting.
- **Population-bounded reactions.** **No em dashes.** FB-casual. Users never post, only react.
- Ambient **orbits** the Spine as ordinary witnesses ("the Bible through their eyes") — it does
  not retell Scripture.

## Narration balance — characters carry the story, outlets are the frame ⭐
The app's whole moat is **"the Bible through ordinary eyes."** So events are told through the
**people who live them** (first-person witness), not narrated by the News Outlets. The Fall
through Adam & Eve; the Flood through Noah's family and the doomed who watched it come.

Reserve the **outlets** for only four things:
1. **No human witness** — Creation (nobody exists yet), or cosmic scale ("every living thing
   perished" — no one person sees that).
2. **The divine interior** — what only God knows or does ("God grieved," "God remembered Noah,"
   "the LORD shut the door").
3. **The Watchman's prophetic voice** — foreshadowing / ember-keeping ("watch the old man").
4. **Light "breaking" framing** — sparingly.

The engine already delivers any character's Spine post to everyone (non-ambient = guaranteed), so
outlets are NOT needed to carry the plot. Aim: **outlets = the frame, characters = the story.**
(Rebalanced the Flood beat as the worked example: the animals' arrival is now a turning mocker's
post, and the ark resting on Ararat is Noah's own voice, not the Herald.)

## Run modes (for the production engine)
- **Lazy generation:** per beat as the timeline advances, or on first profile visit; cache.
- **Review gate:** anything touching canonical figures or doctrine is checked before release.

## Proof status
Slice 1 (this file): the 6 Inferred siblings + 3 ambient neighbors, Beat 1-3. ~15 posts with
cross-friend banter, run by hand following the recipe above. If the quality holds, the same
recipe automates era-by-era.
