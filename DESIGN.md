# BibleFeed — Design Specification

> A wholesome, chronological "social media" experience of the Bible.
> Working title: **BibleFeed** (name TBD — see §10.5).
> (See `Initial Idea.txt` for the original vision.)

---

## 1. Vision & North Star

BibleFeed is a mobile app that looks and feels like Facebook, but every person in
the feed is a biblical figure living their life **chronologically**, from Day 1 of
Genesis to the end of Revelation. Users don't post. They **read, scroll, like, and
heart** — experiencing the entire biblical story as a living, breathing social world
that unfolds in real time over roughly one calendar year.

**The North Star (and the twist):** this is an *anti*-doomscroll app. It replaces an
empty, addictive habit with a meaningful one — **not** by slamming a wall in front of
the user, but because **you cannot consume tomorrow's story today.** Each user's personal
story-clock rations new content (§5.1). The scroll can feel infinite and Facebook-true
while still being inherently un-bingeable.

---

## 2. Core Principles (non-negotiables)

1. **Scripture is the Word of God, and we never compromise it.** Every post traces
   back to a real verse or a defensible inference from one. Creative liberty fills
   gaps; it never contradicts, embellishes, or invents doctrine.
2. **Period-true.** The world stays true to its times — culture, geography, work,
   food, relationships. The *language* is modernized; the *world* is not.
3. **Reverent.** Wholesome throughout. Sacred figures handled with maximum care (§3.1).
4. **Facebook-true immersion.** Mimic Facebook's mechanics as closely as possible. No
   feature that breaks the illusion of a real social feed.
5. **Chronological & per-user.** One authored world, experienced on a *personal* clock —
   every user starts at Genesis and lives the whole arc in real time (§5.1).
6. **The NPCs are the lens. ⭐** Most users already know the Bible — so the *freshness* is
   living it through the eyes of ordinary, fictional people. The fictional NPCs are the
   **majority of the cast and the bulk of the feed**; canonical figures are the
   "celebrities" everyone follows but who post mainly at Spine moments. The Bible is the
   *setting*; the NPCs are the *characters you live with* (§6.6). This is the app's moat —
   the reason it can't be replaced by simply reading Scripture.

---

## 3. Key Decisions (resolved)

### 3.1 Portraying God, Jesus, and the divine
- **God the Father:** never a user/profile. His action reaches the feed through
  **events**, through **prophets posting** ("The LORD spoke to me today…"), and through
  the news outlets. Reverent; never a chat avatar.
- **Jesus:** ✅ **Jesus has a profile.** He came to Earth as fully God and fully man and
  experienced real human things, so his profile reflects that. **Guardrail:** his posts
  are faithful, modernized renderings of what the Gospels actually record him saying,
  doing, and experiencing (weariness, shared meals, friendship, grief at Lazarus' tomb)
  — **never** invented sayings or theology. Maximum reverence and scriptural fidelity.
- **Holy Spirit / angels / Satan:** angels appear as messengers inside others' posts;
  the serpent/Satan handled obliquely through events, never a relatable account.

### 3.2 Canon & chronology
**Protestant 66-book canon** + **Ussher-style / Masoretic (Anno Mundi)** timeline as the
single source of truth. Deuterocanon = possible later expansion.

### 3.3 Base translation
Anchor on a **public-domain** base — recommended: **World English Bible (WEB)**, which is
modern and readable (avoids KJV's archaic phrasing) and free of licensing limits. Since
we modernize the text anyway, this is purely our private source reference.

### 3.4 Target audience & rating
**Teen / Family (12+).** Mature events (war, David & Bathsheba, etc.) are **referenced
tastefully, never depicted** (§6.5).

---

## 4. The Experience (user-facing features)

### 4.1 The Feed
True **infinite-scroll** feed (Facebook-style) of posts from characters the user
follows, plus news reports, ads, and friend suggestions. It never hard-stops — but new
*story* content is gated by your personal story-clock (§5.1), so it can't be binged (§4.9).

**Order: reverse-chronological (newest at top)**, like Facebook. The forward story-order is
delivered by *time* — each new beat arrives **at the top** as it "happens" (the trickle, §4.6/
§5.1) — not by scroll position. You read "what just happened" at the top, exactly as you'd
follow any unfolding story on social media.

**Onboarding (cold open):** a new user does **not** land with a pre-loaded backlog. Instead the
opening posts **lay out one at a time** on a fixed dramatic cadence (post 1 at ~2s, then +15s,
+15s, +10s, +10s) — you *watch* Creation begin from nothing, post by post. **Once the backlog
is laid out, the normal density-weighted clock resumes** from that point and carries the rest of
the story forward at its real pace. Newest-at-top throughout; the world also *feels* underway via
context (the News Outlets have history, characters are mid-life). Implemented (web app): the
intro is real-time and persists; the clock is anchored at the handoff so it continues seamlessly.

### 4.2 Reactions
No commenting or posting by users. Reactions only:
**Like 👍 · Heart ❤️ · Pray 🙏 · Amen 🕊️ · Sad 😢** (Sad powers the grief mechanic).

### 4.3 Profiles
Facebook-style profile: pic, cover photo, bio/about, work, hometown/current city,
relationship status, family, and **friends list**. Users can browse a character's friends
and friend-request *those* characters.

**Profile-pic strategy** (to make thousands of portraits tractable, see §7.4):
- **Main/Supporting** → unique AI-generated portraits (hundreds, manageable).
- **NPCs** → drawn from a reusable **library of archetype portraits** keyed by
  era × gender × role (dozens of templates, reused widely).
- **Lazy generation** → a character's portrait is only generated when they're about to
  become active in the timeline, spreading the workload across the whole year.

### 4.4 Friends / "Following"
"Adding a friend" = tuning into that character's feed. The social graph drives what the
user sees. Characters can also **send the user friend requests**.

### 4.5 People You May Know
Characters surface as suggestions when they're **introduced chronologically** (driven by
`First_Mention_Ref`), so the cast grows as the story does.

### 4.6 Comment threads (with trickle-in) ⭐
Tapping a post opens its comments. Critically — **comments are not all present the moment
a post appears.** They **trickle in over time**, just like real Facebook: a character
might comment hours, days, or a week after the post. Two release types:
- **Scheduled** — authored with a delay offset from the post (e.g. +6h, +2d, +1wk).
- **Reactive** — seeded/surfaced *after a user engages* with a post (e.g. you like a
  post today, and tomorrow a character has replied to it). Makes posts feel alive and
  rewards revisiting.

**Trickle-in vs. a racing timeline — two clocks ⭐.** A fast era (§5.2) can blow through
decades in real-world days, which would otherwise orphan a "days later" comment (a dead
character replying to ancient news). Resolved by separating *when a comment is written*
from *when you see it*:
- **Story-clock (locks canon):** a comment is pinned to a story-moment where the commenter
  is **alive** (`Active_From/To_AM`) and the post is still contextually recent. No
  long-dead necro-comments; comments never reach across eras (just like real Facebook,
  nobody comments on a 10-year-old post).
- **User-clock (creates the trickle):** *when you personally see* the reply rides the
  per-user cursor (§5.3) on a real-world delay — that's the "someone replied to yesterday's
  post" delight. The delay **auto-scales to era tempo**: leisurely across real days in slow
  dense eras (the Gospels); compressed in fast sweeps so the thread resolves before the
  story moves on.
- **Reactive comments sidestep the clock** entirely (your engagement triggers an
  in-world-consistent reply for you), and **sticky spine threads** (§5.3/§5.5) wait for you
  rather than evaporating when the era sprints.

Net: canon is locked at authoring time (story-clock); the trickle is a per-user delivery
rhythm (user-clock). Reuses existing machinery — active-windows, the §5.3 cursor, reactive
comments, sticky spine.

**Live reveal — comments that perform in real time ⭐.** In fast eras especially, render
reactive comments as if they're happening *now*: you react to a post and, a beat later, a
**"… is typing"** indicator appears, the comment animates in, and a reply to *it* can follow
(**"… is typing"** again) — so a little exchange performs itself while you watch. This flips
the fast-timeline latency problem into a feeling of *liveness*: the world responds to your
presence. It's pure **client-side choreography** over pre-authored, in-world-consistent
comments — no realtime backend or live humans, just staged timing. The **voice fields drive
the performance**: a `Chatty`, high-`Emoji_Level` youth types a fast punchy reply; a `Terse`
elder pauses long and says little; a `Rare` poster may start typing… then stop (thought
better of it). Guardrail: tie it to real narrative payoff (it rewards *attention* to a moment
you chose to engage with) — never an empty tap-for-dopamine loop (anti-doomscroll, §4.9).

### 4.7 News Outlets (Pages)
3–4 recurring outlets report on major events ("THE SHINAR HERALD: Tower Project Halted
as Workers Can No Longer Understand Each Other"). Characters comment on these with
opinions and friction (drama welcome). **Outlets are auto-followed and cannot be removed**
— they are the narrator that guarantees the spine of the story reaches every user (§5.5).

### 4.8 Fake Ads
Period-true, lightly comedic ad slots ("Ur Chariotworks — 0% down," "Now hiring
bricklayers — Babel Tower Co."). Native-feeling but clearly not real.

### 4.9 Anti-doomscroll, the right way ⭐ (the differentiator)
We keep the infinite scroll (Facebook-true) but make it inherently un-bingeable:
- **Your personal story-clock rations new content** (§5.1). You can't read tomorrow's story
  today. The scroll fills with what's been released so far + ambient/older content + ads + news,
  exactly how Facebook manufactures its "infinite" feel — but the *new* story arrives only as
  your clock advances.
- **A real "You're All Caught Up" marker** (Facebook and Instagram both literally have
  this) gently signals when you've seen everything new — without a hard wall. Below it,
  older/ambient content keeps scrolling for those who want to linger.
- **The algorithm serves the story, not time-on-app** — engagement tunes *which
  characters* you see more of, to deepen threads you care about.
- **The story ends.** Reaching Revelation is a real, celebrated completion; then you may
  replay from Genesis as a fresh cut (§5.4).

### 4.10b The daily rhythm — time of day ⭐
Posts carry a **time-of-day** and the feed lives on a day/night cycle, synced to the *user's
real clock*:
- **Diurnal mood tracks your hour.** Open the app in your morning → the world is in its
  morning (fresh-start posts, "off to the field ☀️"); your evening → it's winding down
  ("bread and bed 🌙"). A quiet **parallel-life** feeling: you and Scripture's people keep
  the same hours.
- **The world sleeps ~midnight–5am.** New posts pause; a gentle card ("🌙 The world is
  resting. Come back at first light"). This is the anti-doomscroll North Star delivered by
  the clock itself — at 3am there's nothing new, the kindest nudge to put the phone down.
- **Period-true timestamps** (Principle 2): *"at the third hour"* (≈9am), *"the sixth hour"*
  (noon), *"the ninth hour"* (3pm), *"as the lamps were lit,"* *"the first watch of the
  night,"* *"at cockcrow,"* *"before daybreak"* — immersive *and* quietly educational. Not
  "9:14 AM."
- **Night events pierce the quiet** — and hit harder because the feed is normally asleep:
  Passover at midnight, Gethsemane, the Resurrection at dawn. The nightly hush is also a
  **tension instrument.**
- **Two decoupled clocks (the one new structural element):** *story-progression* (where in
  the Bible you are — the Beat map, §5.2) is separate from *time-of-day* (a recurring daily
  mood synced to your real hour). They're independent, but only the era label + the diurnal
  timestamp are user-facing, so the user never has to track it — it just *feels* like morning
  when it's morning.
- **Reuses what we have:** a `time_of_day` field on Post (§7.2) + the existing release-window
  scheduler (§6.1), and the voice system handles the "just woke up" / "turning in" flavor.

### 4.10 Extra Facebook mechanics worth stealing
- **Life Events** on profiles ("Married Rebekah," "Moved to Egypt," "Became Pharaoh's
  right hand") — biblical milestones map perfectly.
- **Memories / "On This Day"** — resurfaces past biblical moments.
- **Events / RSVPs** — Passover, festivals, weddings as events characters attend.
- **Verified badges** — "Verified Prophet" / "Verified King" as a status cue.
- **Death & grief** — when a character dies, family/friends post obituary-style
  ("Abel is gone… 💔"), others leave condolences, and the deceased's profile becomes a
  memorial wall ("gone too soon," "we miss you").

---

## 5. The World Model

### 5.1 Per-user world-clock — everyone starts at Genesis ⭐ (revised)
Each user runs their **own** ~180-day journey, beginning at **"Let there be light."** There
is no single global day; every user has a **personal story-clock** that starts when they begin
(install, or a chosen/cohort start date) and advances in **real time** through the Beat map
(§5.2). So everyone experiences the *complete* chronological arc, properly paced, with every
ember payoff intact — no one ever drops into the middle having missed Creation, Abraham, and
the Exodus.

- **One authored world, personal playheads.** The cast (`characters.csv`), pacing
  (`beats.csv`), social graph (`relationships.csv`), and content are **identical for everyone**
  — a single authored world. Only each user's *position* in it differs, like everyone watching
  the same series but each at their own episode.
- **Real-time, un-bingeable.** Content unlocks on your personal calendar as your clock advances;
  you can't read ahead of where your season has reached (preserves the anti-doomscroll,
  can't-binge property of §4.9 and the live daily trickle).
- **Users follow characters, not each other.** Your "friends" are biblical figures and NPCs you
  tune into — there is **no in-app feed of other users' activity.** Two real people are
  invisible to each other inside the app, so a friend who's further along **cannot spoil your
  feed.** (Real-world "wait till you get to David and Bathsheba!" chatter is just the watercooler
  effect — see §5.6.)

**Why this beats a shared global clock:** it makes *every* user start at the beginning
(onboarding), get the *whole* properly-paced arc, and receive the *full* ember payoff
(Gen 3:15 → Bethlehem) — all of which a shared clock denies to everyone who joins mid-stream.
The synchronized "appointment-viewing" energy of a global clock is recovered via **cohort
starts** (§5.4) instead — a far better trade.

### 5.2 Density-weighted pacing engine (chosen model)
The Bible's ~4,000 years are not spread evenly across content, so we do not map them
linearly. Real-time is allocated by **story density**:
- The story is divided into **Beats** (curated narrative units), each with a **weight**.
- Real-time days are distributed across Beats by weight. Genealogies pass in a day; the
  Exodus and the Gospels get weeks.
- Each user's personal **"story day" counter** (§5.1) drives their content release; a separate
  **biblical era/year label** shows up top for flavor ("~2000 yrs before Christ · The
  Patriarchs"). The Beat weights/day-allocations are a *shared template* every user runs through
  on their own clock.

**Realized in `beats.csv` (Stage 2).** The whole Bible is segmented into **168 Beats**,
each with a `Weight` (1 = genealogy/list, 10 = the Crucifixion/Resurrection peak). Real-world
days are allocated proportional to weight over a **~180-day window** (the season length;
dropped from 365→180, tunable via `TARGET_DAYS` in `build_beats.py` — tweak it or any weight
and recompute). Result: the density inversion the model demands — genealogies (Table of
Nations, etc.) get **~0.2 days** each, while **the Gospels get ~41 days (23% of the season)**
and **Passion Week alone spans ~11 real days**, the Crucifixion and Resurrection at max
weight ~2.1 days each. Per-era
allocation: Patriarchs 16% · Monarchy 13% · Divided Kingdom 9% · Gospels 23% · Early Church
8%; the fast millennia (Post-Flood, Babel) get <1% each. Each Beat row also carries its
`Scripture_Ref`, `Biblical_Time` label, `Start/End_Day`, and spine `Notes`.

### 5.3 Personal pace & catch-up ⭐
Even on a personal clock, casual users (logging in twice a week) must still follow the story:
- **Your own clock gates the ceiling** — you can't see beyond where your personal season has
  advanced.
- Each user has a **read-cursor** through their released backlog; we track what they've **seen**.
- **Important content is "sticky."** Unseen Main/Supporting/canonical (Spine) posts wait for you
  and resurface above brand-new ambient chatter when you return.
- **Ambient/NPC filler is ephemeral** — miss it and it scrolls away (like real Facebook old
  posts). You're never punished for missing it; you never lose the plot.

Net effect: a daily user and a twice-a-week user both follow the whole narrative on their own
clock; only the disposable background differs.

### 5.4 Replay & cohort starts
Reaching Revelation **completes** the season — a real, celebrated finish. Then:
- **Replay.** Begin again from Genesis; because the algorithm fades who you ignored and surfaces
  who you engaged (§5.6), a second run is a genuinely different *cut* — you finally follow the
  people you missed. The finish is a *reason to return*, not a reset. (No binge mode — it's lived
  on a real-time clock: personal, but not skippable.)
- **Cohort & friend-sync starts (recovering the watercooler).** Default is start-whenever, but
  friends can **begin together**, and periodic **launch waves / cohorts** (like a new game server
  or a book-club season) put many users in lockstep — recovering the synchronized
  "appointment-viewing" energy a global clock would have forced, *without* denying anyone the
  full arc.

### 5.5 The Narrative Guarantee — spine vs. texture ⭐
The feed is gated by the friend graph (you see who you follow). That risks a real problem:
a user who skips a friend suggestion could miss a major story beat. We solve it by
splitting all content into two classes and **guaranteeing only the spine**:

- **Spine** — the load-bearing beats (Abel's death, the flood, the sea parting, the
  golden calf…). The *plot*. **Must reach every user, regardless of who they follow.**
- **Texture** — daily life, side chatter, minor drama. Personal and **fine to miss.**

Reframe: missing texture is **not a bug — it's personalization.** Two users who friended
different characters get different *cuts* of the same era (great for replayability). We
only ever guarantee the spine. Four mechanisms deliver it, all Facebook-authentic:

1. **News Outlets are the safety net** (§4.7). Auto-followed, un-removable; every Spine
   beat becomes a report, so the plot lands even if you friended no one involved. This is
   the primary guarantee — the narrator that can't be unfollowed away.
2. **Main-character headline posts bypass the gate** — a `Tier: Main` Spine post can
   surface to everyone on the current arc, styled like a "suggested" post.
3. **Friend-of-friend surfacing** — friending anyone in a cluster pulls in adjacent
   drama ("Jacob commented on Esau's post"). Follow one brother, get the whole feud.
4. **The app actively pulls you into the live arc** — start friended with the era's Mains
   (a "starter pack"); characters send *you* friend requests as their arc heats up; PYMK
   is tuned to the currently-active main characters.

**The connection model (made explicit — Facebook-authentic):**
- **Characters are people → you "Add Friend"** (warm, in-world; matches the original vision and
  the "friend graph"). Character↔character relationships are also "friends."
- **News Outlets are Pages → you "Follow"**, and these are **auto-followed and un-removable**
  (§4.7) — the safety net that guarantees the spine reaches everyone even if you friend no one.
- **No silent auto-friending of characters.** Onboarding instead shows **People You May Know**
  (the era's cast + a few ordinary folks); friending is a *guided one-tap user action*, never
  forced. The outlets-as-safety-net is what makes optional friending safe (the plot can't be
  missed). Personal friend choices are exactly what make feeds diverge (§5.6 replayability).
- Characters can later send *you* a friend request as their arc heats up (§5.5 #4). Implemented
  in the prototype (PYMK card + Add Friend / Follow split).

**Same principle as §5.3, second axis:** §5.3 guarantees the spine across *time* (rare
logins); §5.5 guarantees it across the *friend graph* (few follows).

### 5.6 Emergent payoff — personal cuts, replayability & word-of-mouth ⭐
The §5.5 split (guaranteed spine, personal texture) isn't only a safety net — it's the
source of two strategic wins:

- **Replayability.** The algorithm surfaces who you engage with and fades who you ignore,
  so each playthrough is a different *cut* of the same Bible. Replaying a future season
  (§5.4) with different follow choices is a genuinely fresh experience — you finally follow
  the people you missed. The seasonal restart becomes a *reason to return*, not a reset.
- **A word-of-mouth growth loop.** Real-life friends end up with *different sub-stories*,
  so they compare notes: "You're not following Absalom?? Follow him, NOW." That chatter
  drives re-engagement and new installs — the product markets itself.

**Why it works without anxiety:** the shared **spine is the common vocabulary** that makes
the recommendation possible (everyone knows *who Absalom is* via the news outlets), while
the personal **texture is the reward** for following (his daily charisma, the slow
seduction of Israel — the "director's cut"). So a friend's nudge feels like *"you're
getting the CliffsNotes — unlock the full story,"* not *"you're hopelessly behind."*
Productive FOMO, never punishing.

**Fuel it deliberately (spoiler-safe):** since friends are usually at *different* points in
their own timelines (§5.1), the buzz is streaming-style — "are you at the part where…?",
"wait till you get to David and Bathsheba" — and that anticipation *is* the engagement. The
only user-to-user cue the app ever surfaces is **who a friend follows** ("3 friends follow
Absalom 👀") — *never* their position or reactions — so it nudges without spoiling. Plus a
shareable **"my season so far"** snapshot to screenshot and send, and **cohort starts** (§5.4)
for friends who want to ride it in sync.

### 5.7 Mortality & generational handoff ⭐

**Presence is a window: born-and-of-age → death.** A character only *exists in the app* (shows
in People You May Know, is friendable, posts, has a reachable profile) once they're **born AND
old enough to "have a phone" (~13)** relative to the user's story-clock, and stops at death.
So the cast **populates as the story advances** — at Creation only Adam exists; Eve appears in
the Garden; Cain, Abel and their siblings appear once they've come of age by the Cain & Abel
era. Computed from `Birth_AM + ~13yr` (and `Active_From/To_AM`) against the per-user clock; a
not-yet character's profile reads "Not in the story yet." (Implemented.) The *death* end of the
window is the churn this section turns into a feature:

In fast eras the calendar races (2 Kings ≈ 300 years), so a user's follows die off and
refill constantly. We turn that churn from a problem into a feature — and most of the
machinery already exists (`Active_From/To_AM`, `Family_Links`, `Faction`, memorial pages):

- **Death is a baton pass, not a vanish.** When a follow dies, pair the memorial (§4.11)
  with a **successor suggestion** drawn from `Family_Links`/role: "Elijah has been taken up
  — Elisha picked up his mantle. Follow Elisha?" Grief *and* a forward path, along story
  lines the user already cares about (prophet→prophet, father→son, king→heir).
- **Follow a House, not just a person.** Users can follow a **dynasty/faction** (House of
  David, the Prophets, a news outlet) as a continuity thread — they auto-flow to the
  current living torchbearer, so the bond survives any individual's death. News outlets are
  the immortal anchor.
- **Tiered mortality.** Main deaths are full Spine memorials (Moses, David, Elijah).
  Background NPC churn during genealogy/king-list sweeps is **aggregated by the news
  outlets** ("three kings rose and fell in Samaria this season"), not fifty individual
  funerals — so death keeps its weight where it counts and never goes numb.
- **Presence = active window, not lifespan.** Characters appear during
  `Active_From_AM`→`Active_To_AM`, not their full biblical lifespan; nobody simulates a
  900-year-old posting daily.
- **Net-stable list.** Births, PYMK, friend requests, and heirs backfill as fast as deaths
  remove — the list churns but never empties.
- **Legacy persists.** A dead follow keeps their memorial wall, returns via "On This Day,"
  and lives on through descendants you can follow — so the follow still pays off.

**The reframe:** the passing of generations *is* a core biblical theme ("a generation goes,
and a generation comes, but the earth remains" — Ecc 1:4). Handled this way the churn isn't
depressing — it lets the user *feel* the sweep of history and God's faithfulness across
mortal lifetimes.

---

## 6. Content System

### 6.1 Beats & episodes
Content is authored per **Beat**. Each Beat produces: character posts, **trickle-in reply
threads** (§4.6), news reports, ad slots, life events, and any deaths/births — all stamped
with release windows (which story-days, and what delay offsets for comments). Every post is
also tagged **Spine** or **Texture** (`Narrative_Weight`) so the system knows what must
reach everyone (§5.5); each Spine beat is mirrored by a news report. Posts are generated
from a catalog of reusable **post formats** (dilemma/advice-seeking, daily-life, memorial,
news, ad, etc.) — see `POST_FORMATS.md` — mixed per Beat so the feed feels alive. Each post
is also assigned a **`time_of_day`** and written with matching flavor ("up before the sun…",
"time to turn in…") so the feed reads with a natural daily rhythm (§4.10b).

### 6.2 Generation → review → schedule pipeline
1. **Generate** posts/threads per character per Beat (AI-assisted, voice-aware) — Claude
   produces the content.
2. **Review** — you approve for accuracy & tone (protects the mission).
3. **Schedule** — approved content lands in the DB with release timestamps; the backend
   pushes it live and optionally fires push notifications.

Because content lives in the database (not baked into the app), the story can be edited
all year without shipping an app update.

### 6.3 Voice & tone system
Each character's posts are shaped by profile fields: `Voice_Tone`, `Emoji_Level` (0–3) and
`Verbosity` (Terse→Chatty) — *age-driven* (young = emoji-heavy/casual; elders = sparse/
formal) — plus `Faction` (worldview & who they spar with) and `Posting_Frequency` (their
social habit).

### 6.4 Canonicity & creative-liberty rules
Every post is tagged `Canonicity`:
- **Canonical** — directly from a verse.
- **Inferred** — a reasonable fill-in (daily life, a meal, a feeling) that *leads toward*
  canonical events and never contradicts them.
- **Fictional** — invented NPCs/flavor woven into the world.

Rule: liberties add texture but **large events are never embellished**, and threads must
**converge on the true biblical outcome**.

### 6.5 Editorial / sensitivity policy
Mature events are **referenced tastefully, never depicted**, consistent with the 12+
rating. Scripture is never softened in meaning — only in explicitness.

### 6.6 NPC primacy & the ordinary-witness lens ⭐ (the app's heart)
Per Principle 6, the fictional NPCs carry the experience. Concretely:

- **Population.** NPCs are the **majority** of the world and should *outnumber* the canonical
  cast over the full build (target ≈ 2× canonical, hand-authored "personality" NPCs plus a
  larger procedurally-generated *ambient* crowd). Density per era is deliberately high.
- **Feed share.** On any world-day, NPC posts vastly outnumber canonical posts. Canonical
  figures post mainly at **Spine** beats; NPCs fill the everyday texture and **populate every
  comment thread** (they're the reliable reactors/witnesses to the big events).
- **Three NPC tiers:**
  - **Lead NPCs** — recurring, with their own **arcs** (Supporting tier, unique portraits,
    post often). The faces users bond with.
  - **Regulars** — recurring background faces (NPC tier, archetype portraits).
  - **Ambient** — light/procedural accounts for crowd density.
- **NPC arcs ("parallel lives").** Lead NPCs run ongoing storylines — a family living *through*
  the Exodus, a romance, a rivalry, a comic grumbler — that unfold *alongside* scripture. The
  biblical events **ripple into** these ordinary lives. This is a primary reason to return that
  is independent of already knowing the Bible's plot — wholesome serial drama (on-brand for
  the anti-doomscroll goal, §4.9).
- **Always `Canonicity: Fictional`**, `First_Mention_Ref = "(fictional)"`, anchored to a real
  era/faction/place, period-true, and never altering or contradicting the canonical record.
- **Reinforces §5.6:** a feed dominated by self-chosen NPCs makes every playthrough a
  different show in the same Bible.

---

## 7. Data Model

### 7.1 Characters (expanded CSV schema)
Current columns:
`Character_ID, Tier, Era, Voice_Tone, Display_Name, Alias_Nickname, Bio_About,
Work_Title, Employer_Faction, Current_City, Hometown, Relationship_Status, Spouse_ID,
Family_Links, Birth_AM, Death_AM, Profile_Pic_Ref, Cover_Photo_Ref`

Proposed additions:

| Column | Purpose |
|---|---|
| `First_Mention_Ref` | Chronological intro → "People You May Know" timing |
| `Active_From_AM` / `Active_To_AM` | When they actually post |
| `Posting_Frequency` | Daily / Every2-3d / Rare |
| `Emoji_Level` (0–3) | Voice tuning (age-driven) |
| `Verbosity` | Terse / Medium / Chatty |
| `Faction` | Line of Seth, Line of Cain, etc. — algorithm + drama |
| `Canonicity` | Canonical / Inferred / Fictional |
| `Gender` | Profile + voice |
| `Portrait_Tier` | Unique vs Archetype (drives §4.3 pic strategy) |
| `Status` (derived) | Alive / Dead (computed from clock vs `Death_AM`) |

### 7.2 Core entities (database)
- **Character** — the cast (from CSV).
- **Post** — author, body, `Beat_Id`, release window, `Canonicity`, `Narrative_Weight`
  (**Spine** / **Texture** — drives the §5.5 guarantee; every Spine post → a news report),
  `time_of_day` (dawn/morning/midday/afternoon/evening/night — drives the §4.10b daily rhythm
  & period-true timestamp; `night` posts are rare and used for night-set Spine events), media ref.
- **Comment** — post, author, body, parent (threads), **release_delay** + **reactive**
  flag (§4.6).
- **Reaction** — by user, on post/comment, type.
- **Friendship** — user↔character (follow) and character↔character (graph). The
  character↔character graph is realized in **`relationships.csv`** (Stage 2, via
  `build_social_graph.py`): **~20,900 edges**, avg ~30 connections/character, era-bounded
  (no anachronistic ties). Edge types: `family`, `spouse`, `faction-tie` (same era+faction
  cluster), `follows` (directional, up-tier — everyone follows their era's canonical Main
  headliners + a few Supporting; the whole Early Church follows the risen Christ), and
  `acquaintance` (cross-faction). Produces the right hub structure — **Jesus #1 (~246
  followers)**, era-Mains (Abraham, David, Elijah, Paul…) as major hubs, NPCs/ambient as
  followers. This drives feed population, "People You May Know," and the §5.5 friend-of-friend
  surfacing. Re-runnable (tunable density via the sampling sizes).
- **NewsOutlet / NewsReport**, **Ad**, **Event / LifeEvent**.
- **User** — account, auth, push opt-in, engagement profile.
- **UserSeen** — per-user read-cursor / seen tracking (powers §5.3 catch-up).
- **Engagement** — per-user signals feeding the (story-serving) algorithm.
- **WorldClock** — single row: current story-day, current Beat, era label.

### 7.3 The algorithm (intentionally simple)
Weight a character's posts up when the user views/likes/hearts them or their friends.
Goal: deepen the threads the user cares about — not maximize time-on-app.

### 7.4 Portrait asset pipeline
See §4.3. Unique portraits for Main/Supporting; archetype library for NPCs; lazy
generation timed to when a character becomes active.

---

## 8. Tech Architecture

**Recommended stack:**
- **Client:** Expo (React Native) — one codebase, iOS + Android, fast iteration.
- **Backend:** Supabase (Postgres) — database, auth, per-user story-clocks (each user's
  start date + progress), realtime, scheduled content release (edge functions / cron), and
  **push notifications**.
- **Content pipeline:** offline generation + review tooling that writes approved content
  into Postgres with release timestamps.

**Dev environment (Windows-friendly):**
- Free to start. Install **Node.js** + **VS Code** + **Expo** (all free).
- Test instantly on a **real iPhone or Android** via the **Expo Go** app (scan a QR code)
  — works on Windows.
- **Android emulator** runs on Windows via **Android Studio** (free).
- The **iOS Simulator** requires a **Mac** (Xcode). On Windows, test iOS on a physical
  iPhone via Expo Go, and use **EAS Build** (Expo's cloud build) to produce iOS App Store
  builds **without owning a Mac**.
- Later costs: Apple Developer Program **$99/yr**, Google Play **$25 one-time**; Supabase
  has a free tier.

---

## 9. Roadmap

**Phase 0 — Spec & data (now):** this doc; finalize schema; grow the character roster.

**Phase 1 — Content foundation:** define Beats + weights for Genesis 1–11; build the
generation→review→schedule pipeline; author the first Beats.

**Phase 2 — MVP app:** infinite feed, profiles, friends/PYMK, reactions, trickle-in
comment threads, the story-clock header, personal catch-up. One authored world, per-user
playhead (start each user at Genesis).

**Phase 3 — Depth:** news outlets, ads, life events, memories, death/memorial pages,
push notifications.

**Phase 4 — Polish:** seasons/restart, events/RSVPs, deuterocanon expansion (optional).

---

## 10. Resolved Decisions Log
1. **Jesus** — ✅ has a profile, handled with maximum scriptural fidelity (§3.1).
2. **Canon/chronology** — ✅ Protestant 66 + Ussher/AM.
3. **Base translation** — ✅ public-domain; recommended **World English Bible**.
4. **Rating** — ✅ Teen/Family 12+.
5. **App name** — open; candidates under discussion (BibleFeed, Manna, Selah, Scroll,
   Chronicle…).
6. **Monetization** — ✅ free, with an optional "buy me a coffee" donation.
7. **No "See Scripture" feature** — cut for immersion.
8. **Per-user timelines (revised)** — every user starts at Genesis on their *own* ~180-day
   real-time clock (not one shared global day); replay allowed, no binge. The synchronized
   "watercooler" is recovered via optional **cohort / friend-sync starts**. Users follow
   *characters*, not each other — there is no in-app user-to-user feed, hence no in-app
   spoilers. (Reworks §5.1–5.6; supersedes the earlier shared-global-clock decision.)
