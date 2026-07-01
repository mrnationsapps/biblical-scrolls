#!/usr/bin/env python3
"""
Biblical Scrolls, local working backend + web UI (zero dependencies, zero accounts).
Loads characters.csv + relationships.csv into SQLite + structured posts, and serves
a Facebook-style SPA (feed + real profile pages) at http://localhost:8000
Run:  python app/serve.py
"""
import csv, json, sqlite3, http.server, socketserver, sys
from urllib.parse import urlparse, parse_qs
from pathlib import Path
import re
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass

ROOT = Path(__file__).resolve().parent.parent
PORT = 8000

db = sqlite3.connect(":memory:", check_same_thread=False); db.row_factory = sqlite3.Row
cur = db.cursor()
cur.execute("""CREATE TABLE characters(Character_ID TEXT PRIMARY KEY, Display_Name TEXT, Tier TEXT,
    Canonicity TEXT, Gender TEXT, Era TEXT, Faction TEXT, Voice_Tone TEXT, Bio_About TEXT,
    Work_Title TEXT, Personality TEXT, Current_City TEXT, Hometown TEXT)""")
with open(ROOT/"characters.csv", encoding="utf-8") as f:
    for r in csv.DictReader(f):
        cur.execute("INSERT OR IGNORE INTO characters VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (r["Character_ID"], r["Display_Name"], r["Tier"], r["Canonicity"], r["Gender"], r["Era"],
             r["Faction"], r["Voice_Tone"], r["Bio_About"], r["Work_Title"], r.get("Personality",""),
             r.get("Current_City",""), r.get("Hometown","")))
cur.execute("CREATE TABLE rels(source TEXT, target TEXT, type TEXT, mutual TEXT)")
with open(ROOT/"relationships.csv", encoding="utf-8") as f:
    cur.executemany("INSERT INTO rels VALUES (?,?,?,?)",
        [(r["Source_ID"], r["Target_ID"], r["Type"], r["Mutual"]) for r in csv.DictReader(f)])
cur.execute("CREATE INDEX i_src ON rels(source)"); cur.execute("CREATE INDEX i_tgt ON rels(target)")
db.commit()
# auto-load every content file: posts_beats_*.json (curated feed) + posts_ambient_*.json (friend-gated texture)
OUTLETS = {}; POSTS = []
for _fp in sorted((ROOT / "content").glob("posts_*.json")):
    with open(_fp, encoding="utf-8") as f:
        _data = json.load(f)
    OUTLETS.update(_data.get("outlets", {}))
    _is_amb = "ambient" in _fp.name
    for _p in _data.get("posts", []):
        if _is_amb: _p["ambient"] = True
        POSTS.append(_p)
# People You Should Know = everyone who actually appears in the story (anyone who posts). The client filters to
# the currently-alive, not-yet-friended ones and surfaces the most recently-active first.
PYMK_IDS = []; PYMK_LASTBEAT = {}; _pseen = set()
for _p in POSTS:
    _a = _p["author"]
    if _a in OUTLETS or _a == "SILENCE": continue
    PYMK_LASTBEAT[_a] = max(PYMK_LASTBEAT.get(_a, 0), _p.get("beat", 0))
    if _a not in _pseen: _pseen.add(_a); PYMK_IDS.append(_a)

# --- per-user clock: density-weighted release schedule from the Beat map (beats.csv) ---
BEATS = {}; BEAT_META = {}
_BOOK = {"Gen ": "Genesis ", "Ex ": "Exodus ", "Exo ": "Exodus ", "Lev ": "Leviticus ", "Num ": "Numbers ", "Deut ": "Deuteronomy "}
def _readable_ref(s):
    s = (s or "").strip()
    for k, v in _BOOK.items():
        if s.startswith(k): return v + s[len(k):]
    return s
try:
    with open(ROOT/"beats.csv", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            try:
                n = int(r["Beat_ID"].split("_")[1])
                BEATS[n] = (float(r["Start_Day"]), float(r["End_Day"]))
                BEAT_META[n] = {"title": (r.get("Title") or "").strip(), "ref": _readable_ref(r.get("Scripture_Ref"))}
            except Exception: pass
except Exception: pass
# ORGANIC release schedule: posts within a beat arrive in a tight "burst" (organic, jittered gaps); a quiet
# "lull" falls between beats (the world's natural ebb). The clock rate turns these units into ~30s in-burst
# gaps. NOTE: liveliness also scales with how many people you follow — sparse early eras are quieter by nature.
def _jit(s):
    h = 2166136261                                    # FNV-1a: strong avalanche so P002 vs P003 differ a lot
    for ch in s: h = ((h ^ ord(ch)) * 16777619) & 0xffffffff
    return (h % 100003) / 100003.0
LULL = 1.5          # quiet stretch between beats, in clock-units (the diegetic "rest")
_t = 0.0; _prev = None
for _p in sorted(POSTS, key=lambda p: (p.get("beat", 0), 1 if p.get("ambient") else 0)):   # spine before ambient texture, then story order
    _b = _p.get("beat", 0)
    if _prev is not None:
        _t += LULL if _b != _prev else (0.25 + 0.5 * _jit(_p["id"]))   # ~0.25-0.75 units in-burst, varied
    _p["release_day"] = round(_t, 4); _prev = _b
BEAT_START = {}
for _p in POSTS:
    _b = _p.get("beat", 0)
    if _b not in BEAT_START or _p["release_day"] < BEAT_START[_b]: BEAT_START[_b] = _p["release_day"]
MAXBEAT = max((p.get("beat", 0) for p in POSTS), default=1)
# Character availability is DAY-PRECISE: a person "exists in the app" from the moment they first show up
# in the story = the release_day of their first authored post. So Adam isn't friendable until his Day-Six
# post, not the whole Creation beat. (Production: Birth_AM + ~13yr vs the clock.)
POST_AVAIL = {}
AUTHORED = set()
for _p in POSTS:
    _a = _p["author"]
    if _a in OUTLETS or _a == "SILENCE": continue
    _rd = _p.get("release_day")
    if _rd is None: continue
    AUTHORED.add(_a)
    if _rd < POST_AVAIL.get(_a, 1e9): POST_AVAIL[_a] = _rd
# Fallback for people who only ever COMMENT or are @mentioned (never author a post): they still exist in the
# app from the earliest post they appear on, so their profile is reachable instead of "Not in the story yet."
# Authored posts take precedence (this never pulls an author's existence earlier than their own first post,
# so e.g. Eve stays gated to her creation, not to an earlier comment).
for _p in POSTS:
    _rd = _p.get("release_day")
    if _rd is None: continue
    _appear = [_c["author"] for _c in _p.get("comments", [])]
    _appear += re.findall(r"@(CHAR_\d+)", (_p.get("body") or "") + " " + " ".join((_c.get("body") or "") for _c in _p.get("comments", [])))
    for _ca in _appear:
        if _ca in OUTLETS or _ca == "SILENCE" or _ca in AUTHORED: continue
        if _rd < POST_AVAIL.get(_ca, 1e9): POST_AVAIL[_ca] = _rd
# a character's death = the release_day of the memorial post tagged to them (back end of the existence window)
DEATH_DAY = {}
for _p in POSTS:
    if _p.get("kind") == "memorial":
        for _cid in _p.get("tags", []):
            DEATH_DAY[_cid] = _p.get("release_day", 1e9)
# the Flood ends the pre-flood world: everyone not aboard the ark (and not Enoch, who was taken) dies that day
_FLOOD_DAY = next((p.get("release_day") for p in POSTS if p.get("flood_day")), None)
if _FLOOD_DAY is not None:
    _ARK = {"CHAR_009","CHAR_010","CHAR_011","CHAR_012","CHAR_013","CHAR_029","CHAR_030","CHAR_031"}
    for _r in cur.execute("SELECT Character_ID FROM characters WHERE Era='Pre-Flood'").fetchall():
        _cid = _r["Character_ID"]
        if _cid in _ARK or _cid == "CHAR_007" or _cid in DEATH_DAY: continue
        DEATH_DAY[_cid] = _FLOOD_DAY
# Comments are time-gated too (two-clock model): a comment appears only once its post exists AND its
# author exists (their first post) AND any earlier comment in the thread has appeared.
for _p in POSTS:
    _t = _p.get("release_day", 0.0)
    for _i, _c in enumerate(_p.get("comments", [])):
        _gap = 0.15 + 0.3 * _jit(_p["id"] + "c" + str(_i))   # organic ~9-27s between comments at 'live' (was a fixed ~5s)
        _t = round(max(_t, POST_AVAIL.get(_c["author"], 0.0)) + _gap, 4)
        _c["release_day"] = _t
# Reactions are gated too: a post's reaction counts/labels appear only once the post exists AND every
# NAMED reactor in its react_note exists. So Adam can't be shown liking a post before he's created.
NAME2DAY = {}
for _cid, _day in POST_AVAIL.items():
    _row = cur.execute("SELECT Display_Name FROM characters WHERE Character_ID=?", (_cid,)).fetchone()
    if _row and _row["Display_Name"]: NAME2DAY[_row["Display_Name"]] = _day
for _p in POSTS:
    _mx = _p.get("release_day", 0.0); _note = _p.get("react_note", "") or ""
    for _nm, _d in NAME2DAY.items():
        if _nm in _note: _mx = max(_mx, _d)
    _p["react_day"] = round(_mx + 0.05, 4)

def author_info(aid):
    if aid in OUTLETS:
        o = OUTLETS[aid]
        return {"id": aid, "name": o["name"], "icon": o["icon"], "type": "outlet",
                "tagline": o.get("tagline",""), "badge": "News Outlet"}
    if aid == "SILENCE": return {"id": aid, "name": "", "icon": "⬛", "type": "silence"}
    row = cur.execute("SELECT * FROM characters WHERE Character_ID=?", (aid,)).fetchone()
    if row:
        badge = {"Main":"Verified ✓"}.get(row["Tier"], "")
        return {"id": aid, "name": row["Display_Name"], "icon": "", "type": "character",
                "tier": row["Tier"], "canon": row["Canonicity"], "era": row["Era"],
                "faction": row["Faction"], "personality": row["Personality"],
                "city": row["Current_City"], "hometown": row["Hometown"],
                "available_from_day": POST_AVAIL.get(aid), "died_day": DEATH_DAY.get(aid),
                "bio": row["Bio_About"], "work": row["Work_Title"], "badge": badge}
    return {"id": aid, "name": aid, "icon": "", "type": "character", "badge": ""}

def resolve_post(p):
    q = dict(p); q["author_info"] = author_info(p["author"])
    if p.get("kind") == "memorial": q["author_info"]["badge"] = "In Memoriam 🕊️"
    q["comments"] = [dict(c, author_info=author_info(c["author"])) for c in p.get("comments", [])]
    # resolve @CHAR_xxx mentions in the body + comments to display names (the client renders them as clickable tags)
    _t = (p.get("body") or "") + " " + " ".join((c.get("body") or "") for c in p.get("comments", []))
    _m = {}
    for _id in set(re.findall(r"@(CHAR_\d+)", _t)):
        _row = cur.execute("SELECT Display_Name FROM characters WHERE Character_ID=?", (_id,)).fetchone()
        _m[_id] = _row["Display_Name"] if _row else _id
    q["ment"] = _m
    return q

def assemble_feed():
    # return ALL posts (ordered by beat); the client shows spine always + ambient ONLY from friends
    return [resolve_post(p) for p in sorted(POSTS, key=lambda p: (p.get("beat", 0), 1 if p.get("ambient") else 0))]

PRIO = {"spouse":0,"family":1,"faction-tie":2,"acquaintance":3,"follows":4}
def profile_data(aid, day=1e9):
    a = author_info(aid)
    out = {"char": a, "friends": [], "friends_count": 0, "followers": 0, "posts": []}
    if a["type"] == "character":
        rows = cur.execute("SELECT (CASE WHEN source=? THEN target ELSE source END) AS other, type "
                           "FROM rels WHERE source=? OR target=?", (aid, aid, aid)).fetchall()
        seen = set(); fr = []
        for r in sorted(rows, key=lambda r: PRIO.get(r["type"], 9)):
            o = r["other"]
            if o == aid or o in seen: continue
            seen.add(o)
            av = POST_AVAIL.get(o)        # only friends who EXIST by the user's current story-day
            if av is not None and av <= day:
                fa = author_info(o)
                if fa["type"] == "character": fr.append(fa)
        out["friends"] = fr[:12]; out["friends_count"] = len(fr)
        out["followers"] = cur.execute("SELECT COUNT(*) FROM rels WHERE target=? AND type='follows'", (aid,)).fetchone()[0]
    # a timeline = the person's OWN posts + posts they're tagged in (FB-style), AND only what's HAPPENED by now
    tl = [p for p in POSTS if (p["author"] == aid or aid in p.get("tags", [])) and p.get("release_day", 0) <= day]
    out["posts"] = [resolve_post(p) for p in sorted(tl, key=lambda p: p.get("release_day", 0), reverse=True)]  # newest first
    return out

def stats():
    g = lambda s: cur.execute(s).fetchone()[0]
    return {"total": g("SELECT COUNT(*) FROM characters"),
            "canonical": g("SELECT COUNT(*) FROM characters WHERE Canonicity='Canonical'"),
            "inferred": g("SELECT COUNT(*) FROM characters WHERE Canonicity='Inferred'"),
            "fictional": g("SELECT COUNT(*) FROM characters WHERE Canonicity='Fictional'")}

PAGE = r"""<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Biblical Scrolls</title><style>
:root{--bg:#f0f2f5;--card:#fff;--ink:#1c1e21;--mut:#65676b;--blue:#1877f2;--line:#ced0d4;--bub:#f0f2f5;}
body.night{--bg:#0b1020;--card:#141a2e;--ink:#e7e9ee;--mut:#9aa3b2;--line:#2b3550;--bub:#1d2540;}
*{box-sizing:border-box;font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif}
body{margin:0;background:var(--bg);color:var(--ink);transition:.4s}
.top{position:sticky;top:0;z-index:9;background:var(--card);border-bottom:1px solid var(--line);
  padding:10px 16px;display:flex;align-items:center;gap:12px;box-shadow:0 1px 4px rgba(0,0,0,.06)}
.logo{font-size:20px;font-weight:800;color:var(--blue);cursor:pointer}
.hdr{flex:1;display:flex;align-items:center;gap:10px}.htext{min-width:0}.hdr .era{font-weight:700;font-size:14px}.hdr .sub{font-size:12px;color:var(--mut)}
.chip{font-size:12px;background:var(--bg);border:1px solid var(--line);border-radius:20px;padding:5px 11px;white-space:nowrap}
.tog{font-size:12px;color:var(--mut);cursor:pointer;user-select:none;border:1px solid var(--line);border-radius:20px;padding:5px 10px}
.tog.on{color:var(--blue);border-color:var(--blue)}
.tog.danger{color:#e41e3f;border-color:#e8a0ad}
.alive{font-size:12px;font-weight:600;color:#2fae5f;cursor:pointer;user-select:none;white-space:nowrap}
.alive .dot{display:inline-block;animation:pulse 2s infinite}
.alive.paused{color:var(--mut)}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.2}}
.wrap{max-width:600px;margin:16px auto;padding:0 10px}
.night-banner{background:linear-gradient(90deg,#1a2140,#0b1020);color:#cbd5ff;border:1px solid #2b355c;border-radius:12px;padding:14px 16px;text-align:center;margin-bottom:14px;font-size:14px}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;margin-bottom:14px;box-shadow:0 1px 2px rgba(0,0,0,.06)}
.card.news{border-top:3px solid #b07d2b}
.card.fresh{box-shadow:0 0 0 2px var(--blue),0 1px 3px rgba(0,0,0,.08)}
.newpill{background:var(--blue);color:#fff;font-size:10px;font-weight:700;border-radius:8px;padding:1px 6px;margin-left:6px}
.card.memorial{border-top:3px solid #8a7fb0;background-image:linear-gradient(rgba(138,127,176,.07),rgba(138,127,176,.07))}
.card.silence{background:transparent;border:1px dashed var(--mut);box-shadow:none}
.hd{display:flex;align-items:center;gap:10px;padding:12px 14px 6px}
.av{width:40px;height:40px;border-radius:50%;display:flex;align-items:center;justify-content:center;color:#fff;font-weight:700;font-size:17px;flex:none;cursor:pointer}
.av.sq{border-radius:10px}
.nm{font-weight:700;font-size:15px;line-height:1.15;cursor:pointer}
.meta{font-size:12px;color:var(--mut)}
.badge{font-size:11px;color:var(--blue);font-weight:600;margin-left:6px}
.badge.mem{color:#9a8ec0}.badge.news{color:#b07d2b}
.body{padding:4px 14px 12px;font-size:15px;line-height:1.5;white-space:pre-wrap}
.silence .body{text-align:center;font-style:italic;color:var(--mut);padding:18px 24px}
.engine{display:none;padding:0 14px 10px}body.engview .engine{display:block}
.enote{background:#fff8e6;border:1px solid #f0e0a8;color:#7a5a00;border-radius:8px;padding:6px 10px;font-size:12px;margin-bottom:6px}
body.night .enote{background:#2a2410;border-color:#5a4a18;color:#e8d9a0}
.tag{display:inline-block;font-size:10.5px;border:1px solid var(--line);border-radius:6px;padding:1px 6px;margin:0 4px 4px 0;color:var(--mut)}
.tag.spine{color:#9c27b0;border-color:#d6a8df}.tag.canon{color:#2e7d32;border-color:#a5d6a7}.tag.inf{color:#1565c0;border-color:#90caf9}
.rsum{display:flex;align-items:center;justify-content:space-between;padding:6px 14px;font-size:13px;color:var(--mut);border-bottom:1px solid var(--line)}
.remoji b{color:var(--ink)}.rwho{margin-left:8px}.ccount{cursor:pointer}
.abar{display:flex;position:relative;padding:3px 6px}
.abtn{flex:1;text-align:center;padding:8px;border-radius:7px;cursor:pointer;color:var(--mut);font-weight:600;font-size:14px;user-select:none}
.abtn:hover{background:var(--bub)}.abtn.on{color:var(--blue)}
.picker{position:absolute;bottom:46px;left:8px;background:var(--card);border:1px solid var(--line);border-radius:30px;padding:6px 10px;display:none;gap:6px;box-shadow:0 3px 12px rgba(0,0,0,.18)}
.picker.show{display:flex}
.pk{font-size:26px;cursor:pointer;transition:transform .12s}.pk:hover{transform:scale(1.35) translateY(-3px)}
.cwrap{padding:6px 14px 12px}
.vmore{font-size:13px;color:var(--mut);font-weight:600;cursor:pointer;margin:4px 0 8px}
.cmt{display:flex;gap:8px;margin-top:8px}.cmt .av{width:32px;height:32px;font-size:13px}.cmain{max-width:88%}
.cbb{background:var(--bub);border-radius:16px;padding:7px 12px;font-size:14px;line-height:1.4;display:inline-block}
.cmt.bad .cbb{background:#fdeaea;color:#7a2020}body.night .cmt.bad .cbb{background:#3a1414;color:#f3b0b0}
.cn{font-weight:700;font-size:13px;cursor:pointer}
.mention{color:var(--blue);font-weight:600;cursor:pointer}.mention:hover{text-decoration:underline}
.csub{font-size:11px;color:var(--mut);padding:3px 12px 0;display:flex;gap:10px}.csub span{cursor:pointer}.csub span.on{color:var(--blue);font-weight:700}
.clikebadge{display:inline-block;background:var(--card);border:1px solid var(--line);border-radius:12px;font-size:11px;padding:0 6px;margin-left:8px;vertical-align:middle;box-shadow:0 1px 2px rgba(0,0,0,.12)}
.foot{text-align:center;color:var(--mut);font-size:12px;margin:18px 0 40px}
/* profile page */
.backlink{display:inline-block;color:var(--blue);font-weight:600;cursor:pointer;margin:0 4px 10px;font-size:14px}
.pcard{background:var(--card);border:1px solid var(--line);border-radius:12px;overflow:hidden;margin-bottom:14px}
.pcov{height:130px}
.ptop{display:flex;align-items:flex-end;padding:0 16px;margin-top:-44px}
.ptop .av{width:92px;height:92px;font-size:38px;border:4px solid var(--card);cursor:default}
.pname{font-size:22px;font-weight:800;padding:10px 16px 0}
.pmeta2{padding:2px 16px;color:var(--mut);font-size:13px}
.ppers{padding:8px 16px;font-size:13px;color:var(--mut)}.ppers b{color:var(--ink)}
.pbio2{padding:6px 16px 12px;font-size:14px;line-height:1.5}
.pstats{display:flex;gap:20px;padding:10px 16px;border-top:1px solid var(--line);font-size:13px;color:var(--mut)}.pstats b{font-size:15px;color:var(--ink)}
.pfollow{padding:0 16px 16px}
.fbtn{background:var(--blue);color:#fff;border:none;border-radius:7px;padding:9px 16px;font-weight:700;cursor:pointer;font-size:14px}
.fbtn.on{background:var(--bub);color:var(--ink)}
.fbtn.pending{background:var(--bub);color:var(--mut);cursor:default}
.toast{position:fixed;bottom:20px;left:50%;transform:translateX(-50%);background:#222;color:#fff;padding:10px 18px;border-radius:8px;font-size:13px;opacity:0;transition:.3s;z-index:40;pointer-events:none}
.toast.show{opacity:1}
.section-h{font-weight:800;font-size:17px;margin:6px 4px 8px}
.friends{display:grid;grid-template-columns:repeat(3,1fr);gap:6px;background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px;margin-bottom:14px}
.fr{display:flex;flex-direction:column;align-items:center;gap:6px;cursor:pointer;text-align:center;padding:6px;border-radius:8px}
.fr:hover{background:var(--bub)}.fr .av{width:56px;height:56px;font-size:22px}.frn{font-size:12px;font-weight:600;line-height:1.2}
.empty{color:var(--mut);text-align:center;padding:24px;font-style:italic}
.pymk{background:var(--card);border:1px solid var(--line);border-radius:12px;margin-bottom:14px;padding:12px 14px}
.pymk-h{font-weight:800;font-size:15px;margin-bottom:10px}
.pymk-row{display:flex;gap:10px;overflow-x:auto;padding-bottom:4px}
.pymk-c{flex:0 0 124px;border:1px solid var(--line);border-radius:10px;padding:12px 8px;text-align:center;display:flex;flex-direction:column;align-items:center;gap:6px}
.pymk-c .av{width:62px;height:62px;font-size:24px;cursor:pointer}
.pymk-n{font-weight:700;font-size:13px;cursor:pointer;line-height:1.2}
.pymk-w{font-size:11px;color:var(--mut);min-height:14px;line-height:1.2}
.addbtn{background:var(--blue);color:#fff;border:none;border-radius:6px;padding:7px 10px;font-weight:700;cursor:pointer;font-size:13px;width:100%}
.bell{position:relative;cursor:pointer;font-size:17px;padding:5px 9px;border:1px solid var(--line);border-radius:20px;background:var(--bg);user-select:none}
.ncount{position:absolute;top:-5px;right:-5px;background:#e41e3f;color:#fff;border-radius:10px;font-size:10px;font-weight:700;padding:0 5px;min-width:17px;text-align:center;display:none}
.ncount.show{display:block}
.npanel{position:fixed;top:54px;right:10px;width:340px;max-width:92vw;background:var(--card);border:1px solid var(--line);border-radius:12px;box-shadow:0 8px 28px rgba(0,0,0,.22);z-index:30;display:none;max-height:74vh;overflow-y:auto}
.npanel.show{display:block}
.npanel-h{font-weight:800;font-size:17px;padding:13px 14px 8px}
.notif{display:flex;gap:10px;padding:10px 14px;cursor:pointer;align-items:flex-start}
.notif:hover{background:var(--bub)}.notif.unread{background:rgba(24,119,242,.07)}
.notif .av{width:44px;height:44px;font-size:18px}
.notif-t{font-size:13.5px;line-height:1.35}.notif-time{font-size:11px;color:var(--mut);margin-top:2px}
.notif-act{margin-top:7px;display:flex;gap:6px}
.notif-act button{border:none;border-radius:6px;padding:6px 14px;font-weight:700;font-size:12px;cursor:pointer}
.acc{background:var(--blue);color:#fff}.dec{background:var(--bub);color:var(--ink)}
.npanel-empty{padding:22px;text-align:center;color:var(--mut);font-size:13px}
.tocbtn{display:none} body.engview .tocbtn{display:block}
.toc{position:fixed;top:54px;right:10px;width:340px;max-width:92vw;background:var(--card);border:1px solid var(--line);border-radius:12px;box-shadow:0 8px 28px rgba(0,0,0,.22);z-index:31;display:none;max-height:74vh;overflow-y:auto}
.toc.show{display:block}
.toc-h{font-weight:800;padding:12px 14px;border-bottom:1px solid var(--line);font-size:15px}
.toc-h small{font-weight:500;color:var(--mut);font-size:11px}
.toc-i{padding:9px 14px;cursor:pointer;border-bottom:1px solid var(--line);display:flex;justify-content:space-between;gap:8px;align-items:baseline}
.toc-i:last-child{border-bottom:none}
.toc-i:hover{background:var(--bub)}
.toc-i.cur{background:rgba(24,119,242,.09)}
.toc-n{font-size:13.5px;font-weight:700}.toc-r{font-size:11.5px;color:var(--mut)}
.toc-ct{font-size:11px;color:var(--mut);white-space:nowrap}
</style></head><body>
<div class="top"><div class="logo" onclick="goFeed()">📜 Biblical Scrolls</div>
  <div class="hdr"><div class="htext"><div class="era" id="era">…</div><div class="sub" id="sub"></div></div>
    <div class="alive" id="alive" onclick="togglePause()" title="the world is alive — tap to pause"><span class="dot">●</span> live</div></div>
  <div class="chip" id="clock">…</div>
  <div class="bell" id="bell" onclick="toggleNotifs()">🔔<span class="ncount" id="ncount"></span></div>
  <div class="tog" id="speedtog" onclick="cycleSpeed()" title="story-clock speed (testing)">⏱ fast</div>
  <div class="tog" id="tog" onclick="toggleEng()">engine view</div>
  <div class="tog tocbtn" id="tocbtn" onclick="toggleTOC()" title="debug: jump the story-clock to a section">☰ contents</div>
  <div class="tog danger" id="reset" onclick="resetAll()" title="testing only: wipe everything and start over">↺ reset</div></div>
<div class="npanel" id="npanel"></div>
<div class="toc" id="tocpanel"></div>
<div class="wrap" id="wrap"></div>
<script>
const E={heart:'❤️',pray:'🙏',amen:'🕊️',sad:'😢',like:'👍'};
const LBL={heart:'Loved',pray:'Prayed',amen:'Amen',sad:'Sad',like:'Liked'};
let DATA=null, PROFILE=null, VIEW='feed', EXP={}, CCOLL={}, ENG=false, LOOKUP={};
let USERR=JSON.parse(localStorage.getItem('bf_react')||'{}');
let CLIKES=JSON.parse(localStorage.getItem('bf_clike')||'{}');
let FOLLOWS=JSON.parse(localStorage.getItem('bf_follow')||'{}');
let NOTIFS=JSON.parse(localStorage.getItem('bf_notifs')||'[]');   // start EMPTY; notifications arrive as the story unfolds
function saveNotifs(){localStorage.setItem('bf_notifs',JSON.stringify(NOTIFS));}
let NGEN=new Set(JSON.parse(localStorage.getItem('bf_ngen')||'[]'));   // keys of already-generated notifications (no dupes)
function markGen(k){NGEN.add(k);localStorage.setItem('bf_ngen',JSON.stringify([...NGEN]));}
function unreadCount(){return NOTIFS.filter(n=>!n.read).length;}
function updateBell(){const c=unreadCount();const e=document.getElementById('ncount');e.textContent=c;e.classList.toggle('show',c>0);}
function addNotif(n){NOTIFS.unshift(Object.assign({id:'n'+Date.now(),read:false,when:'just now'},n));saveNotifs();updateBell();if(document.getElementById('npanel').classList.contains('show'))renderNotifs();}
// News Outlets are Pages you FOLLOW (instant, auto-followed safety net); characters are FRIENDS you REQUEST (they accept after a delay).
const DEFAULT_FOLLOWS=new Set(['OUTLET_cosmic_herald','OUTLET_vine_fig','OUTLET_watchman','OUTLET_daily_dust']);
// Characters who send YOU a friend request as they enter the story (spread across eras; extend as content grows).
const REACHERS=['CHAR_1378','CHAR_006','CHAR_919','CHAR_925'];   // Asha (b3), Enosh (b4), Lirat of Shinar (b9), Tomer the Brickmaker (b10)
let CONN=JSON.parse(localStorage.getItem('bf_conn')||'{}');  // characters -> {status:'pending'|'accepted', at, name}
function saveConn(){localStorage.setItem('bf_conn',JSON.stringify(CONN));}
function isOutlet(id){return id.indexOf('OUTLET_')===0;}
function outletFollowed(id){return Object.prototype.hasOwnProperty.call(FOLLOWS,id)?FOLLOWS[id]:DEFAULT_FOLLOWS.has(id);}
function charStatus(id){return (CONN[id]&&CONN[id].status)||'none';}
function isFriend(id){return charStatus(id)==='accepted';}
function isConnected(a){return a.type==='outlet'?outletFollowed(a.id):isFriend(a.id);}
function pymkShow(a){return a.type==='outlet'?!outletFollowed(a.id):(charStatus(a.id)==='none' && isAvailable(a));}
function relLabel(a){const st=a.type==='outlet'?(outletFollowed(a.id)?'following':'none'):charStatus(a.id);
  return st==='following'?'✓ Following':st==='accepted'?'✓ Friends':st==='pending'?'Requested':(a.type==='outlet'?'+ Follow':'+ Add Friend');}
// Acceptance is delayed for realism, but measured in STORY time (~1 story-unit) so it scales with speed AND pauses
// when you look away. A fixed wall-clock delay let the story race past the very posts you friended someone to see
// (friend Eve, then miss Abel's whole death at 'faster' before she ever accepts, then it dumps in WAY late).
function acceptDelayUnits(){return 0.6+Math.random()*0.8;}
function maybeAskPush(){if('Notification' in window && Notification.permission==='default'){try{Notification.requestPermission();}catch(e){}}}
function pushNotify(body){if('Notification' in window && Notification.permission==='granted'){try{new Notification('Biblical Scrolls',{body:body});}catch(e){}}}
function acceptFriend(id){if(charStatus(id)!=='pending')return;const nm=(CONN[id]&&CONN[id].name)||(LOOKUP[id]&&LOOKUP[id].name)||'They';
  CONN[id]={status:'accepted',at:Date.now(),name:nm};saveConn();
  addNotif({type:'accepted',actorId:id,text:`<b>${nm}</b> accepted your friend request.`});
  pushNotify(nm+' accepted your friend request');render();}
function checkPendingAccepts(){const sd=storyDay();for(const id in CONN){const c=CONN[id];if(c&&c.status==='pending'&&sd>=(c.acceptDay||0))acceptFriend(id);}}
function resumePending(){checkPendingAccepts();}
function toast(msg){let t=document.getElementById('toast');if(!t){t=document.createElement('div');t.id='toast';t.className='toast';document.body.appendChild(t);}t.textContent=msg;t.classList.add('show');clearTimeout(t._h);t._h=setTimeout(()=>t.classList.remove('show'),2400);}
// ---- PER-USER CLOCK (density-weighted Beat map) + COLD-OPEN onboarding. Real app, web-first; speed adjustable for testing. ----
const SPEEDS={live:60000, fast:12000, faster:2500};   // ms per clock-unit: live = ~30s in-burst gaps; fast/faster for testing
const SPEED_LABEL={live:'live', fast:'fast', faster:'faster'};
let SPEED=localStorage.getItem('bf_speed')||'live'; if(!SPEEDS[SPEED])SPEED='live';   // guard stale 'real'/'fast' values
function msPerDay(){return SPEEDS[SPEED]||60000;}
// COLD OPEN: a fresh start lays out the opening posts one at a time (every 5s of ACTIVE time), then the clock resumes.
const INTRO_GAPS=[5000,5000,5000,5000,5000];
const INTRO_CUM=(function(){let a=[],s=0;for(const g of INTRO_GAPS){s+=g;a.push(s);}return a;})();
const BACKLOG=INTRO_GAPS.length;
let SPINE_SORTED=[], FIRST_DAY=0, RENDERED_N=-1;
let LASTSEEN=(localStorage.getItem('bf_seen')===null?null:+localStorage.getItem('bf_seen'));
// ---- ACTIVE-TIME CLOCK: the story advances ONLY while the page is visible AND not paused. Look away (tab away /
// close / minimise / lock the screen) and it pauses itself; come back even days later and it resumes EXACTLY where
// you left off. No wall-clock, no night-rest needed -- the world is simply asleep whenever you aren't looking. ----
let ACC=+(localStorage.getItem('bf_active')||0);            // accumulated ACTIVE milliseconds
let MANUAL_PAUSE=localStorage.getItem('bf_paused')==='1';
let RUNNING=false, SINCE=0;
function activeMs(){return ACC + (RUNNING ? Date.now()-SINCE : 0);}
function clockOn(){return RUNNING && !MANUAL_PAUSE;}
function _start(){if(RUNNING||MANUAL_PAUSE||document.hidden)return;SINCE=Date.now();RUNNING=true;}
function _stop(){if(!RUNNING)return;ACC+=Date.now()-SINCE;RUNNING=false;localStorage.setItem('bf_active',''+ACC);}
function introCount(){return Math.min(BACKLOG,SPINE_SORTED.length);}
function introEndMs(){return INTRO_CUM[(introCount()-1)]||0;}
function handoffDay(){const i=introCount();return i?SPINE_SORTED[i-1].release_day:0;}
function introDone(){return activeMs()>=introEndMs();}
function storyDayAt(am){
  if(am<introEndMs()){let k=0;for(const c of INTRO_CUM)if(am>=c)k++;k=Math.min(k,introCount());return k>0?SPINE_SORTED[k-1].release_day:(FIRST_DAY-0.0001);}  // laying out the backlog
  return handoffDay()+(am-introEndMs())/msPerDay();}                                                  // normal clock resumes
function storyDay(){return storyDayAt(activeMs());}
function currentBeat(){let cb=1;const sd=storyDay();for(const b of (DATA.beats||[]))if(b.start<=sd)cb=b.beat;return cb;}
function setSpeed(s){_stop();   // re-anchor so changing test-speed doesn't rewind: hold current storyDay, advance at the new rate
  if(activeMs()>introEndMs()){const D=storyDay();ACC=introEndMs()+(D-handoffDay())*SPEEDS[s];localStorage.setItem('bf_active',''+ACC);}
  SPEED=s;localStorage.setItem('bf_speed',s);if(!document.hidden)_start();updateAlive();render();}
function cycleSpeed(){const o=['live','fast','faster'];setSpeed(o[(o.indexOf(SPEED)+1)%3]);}
function togglePause(){MANUAL_PAUSE=!MANUAL_PAUSE;localStorage.setItem('bf_paused',MANUAL_PAUSE?'1':'');if(MANUAL_PAUSE)_stop();else _start();updateAlive();render();}
function updateAlive(){const e=document.getElementById('alive');if(!e)return;const live=clockOn();e.classList.toggle('paused',!live);e.innerHTML=live?'<span class="dot">●</span> live':'⏸ paused';e.title=live?'the world is alive — tap to pause':'paused — tap to resume';}
function isAvailable(a){const sd=storyDay();return !!a && a.available_from_day!=null && a.available_from_day<=sd && (a.died_day==null || sd<a.died_day);}
function isDead(a){return !!a && a.type!=='outlet' && a.died_day!=null && storyDay()>=a.died_day;}
// UNIVERSAL = always shown (News Outlets carry the plot; silence cards = the world). Everyone ELSE is friend-gated:
// you only see a character's OWN posts if you've friended them. (But their comments still show on your friends' posts.)
function isUniversal(p){const t=p.author_info&&p.author_info.type;return t==='outlet'||t==='silence';}
// you see someone's posts the moment you ADD them (pending OR accepted), before they accept -- FB-style. The
// acceptance still lands a beat later as a nice push; it just isn't a gate on seeing their story.
function isFollowing(id){const s=charStatus(id);return s==='accepted'||s==='pending';}
function showInFeed(p){return isUniversal(p)||isFollowing(p.author);}
function releasedItemCount(){const sd=storyDay();let n=0;
  for(const p of DATA.posts){if(p.release_day<=sd&&showInFeed(p)){n++;
    if((p.react_day===undefined)||p.react_day<=sd)n++;
    for(const c of (p.comments||[]))if(c.release_day===undefined||c.release_day<=sd)n++;}}return n;}
function feedVisible(){const sd=storyDay();
  const vis=DATA.posts.filter(p=>p.release_day<=sd && showInFeed(p)).sort((a,b)=>a.release_day-b.release_day);
  RENDERED_N=releasedItemCount();return vis;}
function connectedTo(id){return isOutlet(id)?outletFollowed(id):isFollowing(id);}
// generate notifications FROM the story as it unfolds: high-signal posts from people/pages you're connected to,
// and a character reaching out once they exist. All de-duped via NGEN; nothing appears before its time.
function syncNotifs(){if(!DATA)return;const sd=storyDay();let added=false;
  for(const p of DATA.posts){
    if(!p.highlight||p.release_day>sd)continue;
    const k='p:'+p.id;if(NGEN.has(k))continue;
    if(!connectedTo(p.author))continue;
    const nm=(LOOKUP[p.author]||{}).name||p.author;const snip=(p.body||'').slice(0,72).trim();
    NOTIFS.unshift({id:'g'+Date.now()+Math.floor(Math.random()*999),read:false,when:'just now',type:'page',actorId:p.author,text:`<b>${nm}</b> posted: "${snip}…"`});
    markGen(k);added=true;}
  // Pivotal/relatable figures reach out to YOU across the eras (FB-style incoming request). Each fires once,
  // gated by their own existence + alive-ness, and only if you haven't already added them. Spread across the
  // timeline so a fresh request keeps arriving as the story grows (the flood beats stay quiet, fittingly).
  // Extend this list as new content lands. Must be characters present in the curated feed (so LOOKUP has them).
  for(const reach of REACHERS){
    if(NGEN.has('req:'+reach))continue;
    const a=LOOKUP[reach];
    if(!a||!isAvailable(a)||charStatus(reach)!=='none')continue;
    const nm=a.name||'Someone';
    NOTIFS.unshift({id:'req'+Date.now()+Math.floor(Math.random()*999),read:false,when:'just now',type:'request',actorId:reach,pending:true,text:`<b>${nm}</b> sent you a friend request.`});
    markGen('req:'+reach);added=true;}
  if(added){saveNotifs();updateBell();if(document.getElementById('npanel').classList.contains('show'))renderNotifs();}}
function hue(s){let h=0;for(let c of (s||'?'))h=(h*31+c.charCodeAt(0))%360;return h;}
function avatar(a){
  if(!a)return '';
  if(a.type==='outlet')return `<div class="av sq" style="background:hsl(${hue(a.name)},45%,42%)" onclick="profile('${a.id}')">${a.icon}</div>`;
  if(a.type==='silence')return `<div class="av sq" style="background:#333">⬛</div>`;
  const i=(a.name||'?').trim()[0]||'?';
  return `<div class="av" style="background:hsl(${hue(a.name||a.id)},50%,45%)" onclick="profile('${a.id}')">${i}</div>`;
}
function tags(p){let t='';
  if(p.weight)t+=`<span class="tag ${p.weight==='Spine'?'spine':''}">${p.weight}</span>`;
  if(p.canon)t+=`<span class="tag ${p.canon==='Canonical'?'canon':(p.canon==='Inferred'?'inf':'')}">${p.canon}</span>`;
  t+=`<span class="tag">Beat ${p.beat}</span>`;if(p.format)t+=`<span class="tag">${p.format}</span>`;return t;}
// reactions RAMP UP over time after a post lands (fast at first, then taper) instead of appearing all at once
const REACT_K=1.0;   // ramp time-constant in story-units: ~63% of the likes by 1 unit, ~95% by 3
function reactRamp(p){const rd=p.react_day;if(rd===undefined)return 1;const age=storyDay()-rd;return age<=0?0:(1-Math.exp(-age/REACT_K));}
function counts(p){const ramp=reactRamp(p);const R={};const base=p.reactions||{};
  for(const k in base){const v=Math.round((base[k]||0)*ramp);if(v>0)R[k]=v;}
  const u=USERR[p.id];if(u)R[u]=(R[u]||0)+1;return R;}
function rampActive(){const sd=storyDay();for(const p of DATA.posts){if(!showInFeed(p)||p.react_day===undefined)continue;const age=sd-p.react_day;if(age>0&&age<4*REACT_K)return true;}return false;}
function footer(p){
  const R=counts(p),u=USERR[p.id];const total=Object.values(R).reduce((a,b)=>a+(b||0),0);
  const present=Object.keys(E).filter(k=>R[k]>0).map(k=>E[k]).join('');
  const _sd=storyDay();const nC=(p.comments||[]).filter(c=>c.release_day===undefined||c.release_day<=_sd).length;
  const _auth=Object.values(p.reactions||{}).reduce((a,b)=>a+(b||0),0);
  const _named=_auth>0 && (total-(u?1:0))>=_auth*0.6;   // show the named reactors only once most of the likes have come in
  let sum='';
  if(total>0||nC>0){let who=total>0?(u?(total>1?`You and ${total-1} others`:`You`):(_named?(p.react_note||''):'')):'';
    sum=`<div class="rsum"><span class="remoji">${present} ${total>0?`<b>${total}</b>`:''} <span class="rwho">${who}</span></span>
      ${nC?`<span class="ccount" onclick="toggleC('${p.id}')">${nC} comment${nC>1?'s':''}</span>`:'<span></span>'}</div>`;}
  const likeTxt=u?`${E[u]} ${LBL[u]}`:`👍 Like`;
  return sum+`<div class="abar"><div class="picker" id="pk-${p.id}">${Object.keys(E).map(k=>`<span class="pk" onclick="react('${p.id}','${k}')">${E[k]}</span>`).join('')}</div>
    <div class="abtn ${u?'on':''}" onclick="togglePk('${p.id}')">${likeTxt}</div></div>`;
}
// @CHAR_xxx in a body becomes a clickable name-tag that jumps to that profile (FB-style mentions)
function linkMentions(t,ment){return (t||'').replace(/@(CHAR_\d+)/g,function(_,id){const nm=(ment&&ment[id])||(LOOKUP[id]&&LOOKUP[id].name)||id;return '<span class="mention" onclick="event.stopPropagation();profile(\''+id+'\')">'+nm+'</span>';});}
function commentFB(c,cid,ment){const liked=CLIKES[cid];const b=liked?`<span class="clikebadge">👍 1</span>`:'';
  return `<div class="cmt ${c.aged_badly?'bad':''}">${avatar(c.author_info)}<div class="cmain">
    <div class="cbb"><div class="cn" onclick="profile('${c.author}')">${c.author_info.name}</div>${linkMentions(c.body,ment)}${b}</div>
    <div class="csub"><span class="${liked?'on':''}" onclick="clike('${cid}')">Like</span><span>${c.time||''}</span></div></div></div>`;}
function commentsBlock(p){const sd=storyDay();
  let items=(p.comments||[]).map((c,i)=>[c,p.id+'-c'+i]).filter(x=>x[0].release_day===undefined||x[0].release_day<=sd);
  if(!items.length)return '';
  if(CCOLL[p.id])return '';   // collapsed via the "N comments" toggle
  let more='';if(items.length>2&&!EXP[p.id]){more=`<div class="vmore" onclick="expandC('${p.id}')">View ${items.length-2} more comments</div>`;items=items.slice(-2);}
  return `<div class="cwrap">${more}${items.map(x=>commentFB(x[0],x[1],p.ment)).join('')}</div>`;}
function renderCard(p,isNew){const a=p.author_info;
  if(p.kind==='silence')return `<div class="card silence" id="card-${p.id}"><div class="body">${p.body}</div><div class="engine"><div class="enote">⚙ ${p.note||'§6.5 referenced, not depicted'}</div></div></div>`;
  const badge=a.badge?`<span class="badge ${p.kind==='memorial'?'mem':(a.type==='outlet'?'news':'')}">${a.badge}</span>`:'';
  let eng='';if(p.highlight)eng+=`<div class="enote">⭐ ${p.highlight}</div>`;if(p.ember)eng+=`<div class="enote">🌱 ember: ${p.ember}</div>`;if(p.note)eng+=`<div class="enote">⚙ ${p.note}</div>`;eng+=tags(p);
  return `<div class="card ${p.kind} ${isNew?'fresh':''}" id="card-${p.id}"><div class="hd">${avatar(a)}<div>
    <div class="nm" onclick="profile('${p.author}')">${p.kind==='memorial'?'In loving memory':a.name}${badge}</div>
    <div class="meta">${p.memorial_for?p.memorial_for+' · ':''}${a.type==='outlet'?a.tagline+' · ':''}${p.time||''}${isNew?'<span class="newpill">New</span>':''}</div></div></div>
    <div class="body">${linkMentions(p.body,p.ment)}</div><div class="engine">${eng}</div>${footer(p)}${commentsBlock(p)}</div>`;}
function pymkCard(){
  if(!DATA.pymk)return '';
  const _tr=t=>t==='Main'?0:t==='Supporting'?1:2;   // surface current era first, then main characters above NPCs
  const list=DATA.pymk.filter(a=>pymkShow(a)).sort((a,b)=>((b.last_beat||0)-(a.last_beat||0))||(_tr(a.tier)-_tr(b.tier))).slice(0,8);
  if(!list.length)return '';
  return `<div class="pymk"><div class="pymk-h">People You Should Know</div><div class="pymk-row">
    ${list.map(a=>`<div class="pymk-c">${avatar(a)}<div class="pymk-n" onclick="profile('${a.id}')">${a.name}</div>
      <div class="pymk-w">${a.work||a.faction||''}</div>
      <button class="addbtn" onclick="friend('${a.id}')">+ Add Friend</button></div>`).join('')}</div></div>`;
}
function renderFeed(){const w=document.getElementById('wrap');
  const _cb=currentBeat();const _bm=(DATA.beats||[]).find(x=>x.beat===_cb)||{};   // "where in the Bible am I" — updates as the story moves
  document.getElementById('era').textContent=_bm.title||DATA.era_header||'Genesis';
  document.getElementById('sub').textContent=_bm.ref||'';
  const h=new Date().getHours();const tod=h<5?'night':h<11?'morning':h<14?'midday':h<18?'afternoon':h<21?'evening':'night';
  const cl=document.getElementById('clock');cl.style.display='';
  cl.textContent={night:'🌙 night, the watches',morning:'🌅 morning, the third hour',midday:'🌞 midday, the sixth hour',afternoon:'☁️ afternoon, the ninth hour',evening:'🌆 evening, the cool of the day'}[tod];
  let html='';
  html+=pymkCard();
  const vis=feedVisible();let maxday=0;vis.forEach(p=>{if(p.release_day>maxday)maxday=p.release_day;});
  if(LASTSEEN===null)LASTSEEN=maxday;                       // first ever load: arrival backlog isn't flagged "new"
  html+=vis.slice().reverse().map(p=>renderCard(p,p.release_day>LASTSEEN)).join('');   // newest at TOP
  if(!vis.length)html+=`<div class="card"><div class="empty">🌑 In the beginning…</div></div>`;
  LASTSEEN=Math.max(LASTSEEN,maxday);localStorage.setItem('bf_seen',''+LASTSEEN);
  html+=`<div class="foot">A single authored world of <b>${DATA.stats.total.toLocaleString()}</b> souls
    (${DATA.stats.canonical} canonical, ${DATA.stats.inferred} inferred, ${DATA.stats.fictional} fictional)<br>
    Biblical Scrolls · your personal clock · the season runs ~180 days</div>`;
  w.innerHTML=html;}
function renderProfile(){const w=document.getElementById('wrap');const P=PROFILE,a=P.char;
  const conn=isConnected(a),pend=(a.type!=='outlet'&&charStatus(a.id)==='pending');
  document.getElementById('era').textContent=a.name;document.getElementById('sub').textContent=a.type==='outlet'?'Page':'Profile';
  document.getElementById('clock').style.display='none';
  const cov=`linear-gradient(120deg,hsl(${hue(a.name)},45%,46%),hsl(${(hue(a.name)+45)%360},45%,34%))`;
  const place=a.city||a.hometown||'';
  const sub=a.type==='outlet'?a.tagline:[a.work,place,a.faction].filter(Boolean).join(' · ');
  const friends=(P.friends_count||0)+(isFriend(a.id)?1:0);
  let html=`<span class="backlink" onclick="goFeed()">← Back to feed</span>`;
  html+=`<div class="pcard"><div class="pcov" style="background:${cov}"></div>
    <div class="ptop">${avatar(a)}</div><div class="pname">${a.name} ${a.badge?`<span class="badge">${a.badge}</span>`:''}</div>
    <div class="pmeta2">${sub}</div>`;
  if(a.type==='character')html+=`<div class="engine"><div class="enote">⚙ behind the scenes · ${[a.tier,a.era,a.canon].filter(Boolean).join(' · ')}${a.personality?' · Personality: '+a.personality:''}</div></div>`;
  if(a.bio||a.tagline)html+=`<div class="pbio2">${a.bio||a.tagline}</div>`;
  if(a.type==='character')html+=`<div class="pstats"><span><b>${friends}</b> friends</span></div>`;
  const dead=isDead(a), avail=(a.type==='outlet')||isAvailable(a);
  const btn = dead ? `<button class="fbtn pending" style="width:100%" disabled>🕊️ In memory</button>`
            : avail ? `<button class="fbtn ${conn?'on':''} ${pend?'pending':''}" style="width:100%" onclick="friend('${a.id}')">${relLabel(a)}</button>`
            : `<button class="fbtn pending" style="width:100%" disabled>Not in the story yet</button>`;
  html+=`<div class="pfollow">${btn}</div></div>`;
  if(P.friends&&P.friends.length){html+=`<div class="section-h">Friends · ${P.friends_count}</div><div class="friends">`;
    for(const f of P.friends)html+=`<div class="fr" onclick="profile('${f.id}')">${avatar(f)}<div class="frn">${f.name}</div></div>`;html+=`</div>`;}
  html+=`<div class="section-h">Timeline</div>`;
  html+=(P.posts&&P.posts.length)?P.posts.map(renderCard).join(''):`<div class="card"><div class="empty">No posts yet this season. Their story is still ahead.</div></div>`;
  w.innerHTML=html;}
function render(){const h=new Date().getHours();
  // scroll anchoring: pin the exact post you're reading so posts/comments arriving above it don't shift your place.
  // (measure a stable reference card's viewport offset before re-render, restore it after — robust to any height change.)
  let anchorId=null, anchorTop=0;
  if(VIEW==='feed'&&window.scrollY>50){
    for(const c of document.querySelectorAll('#wrap .card')){if(!c.id)continue;const r=c.getBoundingClientRect();if(r.bottom>70){anchorId=c.id;anchorTop=r.top;break;}}}
  document.body.classList.toggle('night',h<5||h>=21);document.body.classList.toggle('engview',ENG);
  const st=document.getElementById('speedtog');if(st)st.textContent='⏱ '+(SPEED_LABEL[SPEED]||SPEED);
  updateAlive();
  syncNotifs();
  if(VIEW==='profile'&&PROFILE)renderProfile();else renderFeed();
  if(anchorId){const el=document.getElementById(anchorId);if(el){const diff=el.getBoundingClientRect().top-anchorTop;if(diff)window.scrollBy(0,diff);}}}
function profile(id){if(!id||id==='SILENCE')return;
  fetch('/api/profile?id='+encodeURIComponent(id)+'&day='+storyDay()).then(r=>r.json()).then(d=>{PROFILE=d;LOOKUP[d.char.id]=d.char;for(const f of (d.friends||[]))LOOKUP[f.id]=f;VIEW='profile';window.scrollTo(0,0);render();});}
function goFeed(){VIEW='feed';PROFILE=null;document.getElementById('clock').style.display='';window.scrollTo(0,0);render();}
function togglePk(id){const e=document.getElementById('pk-'+id);document.querySelectorAll('.picker').forEach(x=>{if(x!==e)x.classList.remove('show')});e.classList.toggle('show');}
function react(id,k){USERR[id]=(USERR[id]===k?undefined:k);if(!USERR[id])delete USERR[id];localStorage.setItem('bf_react',JSON.stringify(USERR));render();}
function clike(id){CLIKES[id]=!CLIKES[id];if(!CLIKES[id])delete CLIKES[id];localStorage.setItem('bf_clike',JSON.stringify(CLIKES));render();}
function friend(id){
  if(isOutlet(id)){FOLLOWS[id]=!outletFollowed(id);localStorage.setItem('bf_follow',JSON.stringify(FOLLOWS));render();return;}
  const a=LOOKUP[id]||{};const st=charStatus(id);
  if(st==='none'&&!isAvailable(a)){toast((a.name||'They')+' is not part of the story yet.');return;}
  if(st==='none'){CONN[id]={status:'pending',acceptDay:storyDay()+acceptDelayUnits(),at:Date.now(),name:a.name||''};saveConn();maybeAskPush();toast('Friend request sent'+(a.name?' to '+a.name:''));render();}
  else{delete CONN[id];saveConn();render();}
}
function expandC(id){EXP[id]=true;render();}
function toggleC(id){CCOLL[id]=!CCOLL[id];render();}   // "N comments" expands/contracts the thread
function toggleEng(){ENG=!ENG;document.getElementById('tog').classList.toggle('on',ENG);if(!ENG)document.getElementById('tocpanel').classList.remove('show');render();}
// ---- DEBUG TABLE OF CONTENTS: list the beats that have content and jump the story-clock to any of them ----
function toggleTOC(){const p=document.getElementById('tocpanel');const open=p.classList.toggle('show');if(open)renderTOC();}
function renderTOC(){const p=document.getElementById('tocpanel');const cb=currentBeat();
  const counts={};for(const q of DATA.posts)counts[q.beat]=(counts[q.beat]||0)+1;   // only beats that actually have posts
  const beats=(DATA.beats||[]).filter(b=>counts[b.beat]).sort((a,b)=>a.start-b.start);
  let h=`<div class="toc-h">Contents <small>debug · jump the clock</small></div>`;
  if(!beats.length)h+=`<div class="toc-i"><span class="toc-r">No content loaded.</span></div>`;
  for(const b of beats){h+=`<div class="toc-i ${b.beat===cb?'cur':''}" onclick="jumpToBeat(${b.beat})">
    <div><div class="toc-n">Beat ${b.beat} · ${b.title||''}</div><div class="toc-r">${b.ref||''}</div></div>
    <span class="toc-ct">${counts[b.beat]} post${counts[b.beat]>1?'s':''}</span></div>`;}
  p.innerHTML=h;}
function jumpToBeat(bn){const ps=DATA.posts.filter(p=>p.beat===bn);
  // land at the END of the beat so the whole section is revealed (feed is cumulative, newest at top)
  let D=ps.length?Math.max.apply(null,ps.map(p=>p.release_day))+0.02:((DATA.beats||[]).find(b=>b.beat===bn)||{}).start||0;
  const am=D<=handoffDay()?introEndMs():introEndMs()+(D-handoffDay())*msPerDay();
  ACC=am;if(RUNNING)SINCE=Date.now();localStorage.setItem('bf_active',''+ACC);      // re-anchor the active-time clock
  LASTSEEN=D;localStorage.setItem('bf_seen',''+LASTSEEN);                            // don't flag the revealed backlog as "New"
  document.getElementById('tocpanel').classList.remove('show');
  VIEW='feed';PROFILE=null;window.scrollTo(0,0);renderTOC();render();}
function resetAll(){if(!confirm('Reset the whole experience? This clears your friends, reactions, notifications, and story-clock, and starts you over at the very beginning of Creation. (Testing only.)'))return;
  RUNNING=false;ACC=0;   // freeze the clock FIRST so the unload handler (_stop) doesn't re-save bf_active after we wipe it
  Object.keys(localStorage).filter(k=>k.indexOf('bf_')===0).forEach(k=>localStorage.removeItem(k));location.reload();}
function toggleNotifs(){const p=document.getElementById('npanel');const open=p.classList.toggle('show');
  if(open){renderNotifs();NOTIFS.forEach(n=>n.read=true);saveNotifs();setTimeout(updateBell,400);}}
function renderNotifs(){const p=document.getElementById('npanel');let h=`<div class="npanel-h">Notifications</div>`;
  if(!NOTIFS.length)h+=`<div class="npanel-empty">Nothing yet. Add some friends to start your story.</div>`;
  for(const n of NOTIFS){const a=LOOKUP[n.actorId]||{id:n.actorId,name:'',type:'character'};
    let act='';
    if(n.type==='request'&&n.pending)act=`<div class="notif-act"><button class="acc" onclick="event.stopPropagation();acceptReq('${n.id}','${n.actorId}')">Confirm</button><button class="dec" onclick="event.stopPropagation();declineReq('${n.id}')">Delete</button></div>`;
    h+=`<div class="notif ${n.read?'':'unread'}" onclick="profile('${n.actorId}');toggleNotifs()">${avatar(a)}<div><div class="notif-t">${n.text}</div><div class="notif-time">${n.when||''}</div>${act}</div></div>`;}
  p.innerHTML=h;}
function acceptReq(nid,aid){const a=LOOKUP[aid]||{name:'they'};CONN[aid]={status:'accepted',at:Date.now(),name:a.name};saveConn();
  const n=NOTIFS.find(x=>x.id===nid);if(n){n.pending=false;n.read=true;n.text=`You and <b>${a.name}</b> are now friends.`;}
  saveNotifs();render();renderNotifs();updateBell();}
function declineReq(nid){NOTIFS=NOTIFS.filter(x=>x.id!==nid);saveNotifs();renderNotifs();updateBell();}
fetch('/api/feed').then(r=>r.json()).then(d=>{DATA=d;
  for(const p of d.posts){LOOKUP[p.author]=p.author_info;for(const c of (p.comments||[]))LOOKUP[c.author]=c.author_info;}
  for(const a of (d.pymk||[]))LOOKUP[a.id]=a;
  SPINE_SORTED=d.posts.filter(isUniversal).slice().sort((a,b)=>a.release_day-b.release_day);   // cold-open backbone = always-shown posts
  FIRST_DAY=SPINE_SORTED.length?SPINE_SORTED[0].release_day:0;
  if(!document.hidden)_start();          // start the active-time clock if the page is visible
  resumePending();updateBell();render();
  // auto-pause when you look away, auto-resume when you return (Page Visibility API)
  document.addEventListener('visibilitychange',()=>{if(document.hidden){_stop();}else{if(!MANUAL_PAUSE)_start();render();}updateAlive();});
  window.addEventListener('pagehide',_stop); window.addEventListener('beforeunload',_stop);
  // dismiss the notifications panel when you click anywhere outside it (but not on the bell, which toggles it)
  document.addEventListener('click',e=>{const np=document.getElementById('npanel');
    if(np.classList.contains('show')&&!e.target.closest('#npanel')&&!e.target.closest('#bell'))np.classList.remove('show');
    const tp=document.getElementById('tocpanel');
    if(tp.classList.contains('show')&&!e.target.closest('#tocpanel')&&!e.target.closest('#tocbtn'))tp.classList.remove('show');});
  setInterval(()=>{if(document.hidden)return;syncNotifs();checkPendingAccepts();   // friends accept on STORY time, not wall-clock
    if(VIEW!=='feed'||document.querySelector('.picker.show'))return;
    if(releasedItemCount()!==RENDERED_N||rampActive())render();},1500);});   // re-render while reactions are still ramping up
</script></body></html>"""

class H(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def _send(self, body, ctype="application/json"):
        b = body.encode("utf-8") if isinstance(body, str) else body
        self.send_response(200); self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/" or path.startswith("/index"): self._send(PAGE, "text/html; charset=utf-8")
        elif path == "/api/feed":
            self._send(json.dumps({"era_header": "The First Family · East of Eden",
                                   "posts": assemble_feed(), "stats": stats(),
                                   "pymk": [dict(author_info(i), last_beat=PYMK_LASTBEAT.get(i, 0)) for i in PYMK_IDS],
                                   "beats": [{"beat": b, "start": s,
                                              "title": BEAT_META.get(b, {}).get("title", ""),
                                              "ref": BEAT_META.get(b, {}).get("ref", "")}
                                             for b, s in sorted(BEAT_START.items())]}))
        elif path == "/api/profile":
            q = parse_qs(urlparse(self.path).query); pid = q.get("id", [""])[0]
            try: day = float(q.get("day", ["1e9"])[0])
            except Exception: day = 1e9
            self._send(json.dumps(profile_data(pid, day)))
        else: self.send_response(404); self.end_headers()

if __name__ == "__main__":
    s = socketserver.ThreadingTCPServer(("127.0.0.1", PORT), H); s.allow_reuse_address = True
    print(f"\n  Biblical Scrolls is running.")
    print(f"      Open  ->  http://localhost:{PORT}\n")
    print(f"      {stats()['total']} characters + {cur.execute('SELECT COUNT(*) FROM rels').fetchone()[0]} relationships in SQLite, {len(POSTS)} posts.")
    print(f"      Click any name to visit their PROFILE PAGE (friends + timeline). Ctrl+C to stop.\n")
    try: s.serve_forever()
    except KeyboardInterrupt: print("  stopped.")
