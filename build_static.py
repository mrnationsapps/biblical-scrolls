#!/usr/bin/env python3
"""
Build a fully static version of BibleFeed into ./docs (for GitHub Pages).

It reuses the EXISTING, tested logic in app/serve.py:
  - /api/feed        -> docs/api/feed.json          (one authored world, same for everyone)
  - /api/profile?id= -> docs/api/profile/<id>.json  (one file per character + outlet; day=all)
  - the embedded PAGE -> docs/index.html            (two fetch() calls rewritten to static paths)
Plus PWA: manifest.json, sw.js, and generated icons.

Per-user state (friends, reactions, clock, notifications) already lives in the browser's
localStorage, so nothing here depends on a running server. Re-runnable: wipes and rebuilds docs/.
"""
import sys, os, json, shutil
sys.path.insert(0, "app")
import serve  # imports cleanly; the server only starts under serve.py's __main__

ROOT = os.path.dirname(os.path.abspath(__file__))
DOCS = os.path.join(ROOT, "docs")
BLUE = (24, 119, 242, 255)  # matches the app theme color #1877f2

# ---------------------------------------------------------------- clean output
shutil.rmtree(DOCS, ignore_errors=True)
os.makedirs(os.path.join(DOCS, "api", "profile"), exist_ok=True)

# ---------------------------------------------------------------- feed.json (identical to /api/feed)
feed = {
    "era_header": "The First Family · East of Eden",
    "posts": serve.assemble_feed(),
    "stats": serve.stats(),
    "pymk": [dict(serve.author_info(i), last_beat=serve.PYMK_LASTBEAT.get(i, 0)) for i in serve.PYMK_IDS],
    "beats": [{"beat": b, "start": s,
               "title": serve.BEAT_META.get(b, {}).get("title", ""),
               "ref": serve.BEAT_META.get(b, {}).get("ref", "")}
              for b, s in sorted(serve.BEAT_START.items())],
}
with open(os.path.join(DOCS, "api", "feed.json"), "w", encoding="utf-8") as f:
    json.dump(feed, f, ensure_ascii=False)

# ---------------------------------------------------------------- profiles (one file per character + outlet)
ids = [row[0] for row in serve.cur.execute("SELECT Character_ID FROM characters").fetchall()]
try:
    ids += [o for o in list(serve.OUTLETS)]   # outlets are clickable Pages too
except Exception:
    pass
baked, failed = 0, 0
for pid in ids:
    if not pid or pid == "SILENCE":
        continue
    try:
        data = serve.profile_data(pid, 1e9)   # day=all; the client filters the timeline by its own clock
        with open(os.path.join(DOCS, "api", "profile", pid + ".json"), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        baked += 1
    except Exception as e:
        failed += 1

# ---------------------------------------------------------------- index.html (rewrite the two fetch() calls + PWA hooks)
html = serve.PAGE

# 1) feed endpoint -> static file
assert "fetch('/api/feed')" in html, "feed fetch string not found; serve.py changed"
html = html.replace("fetch('/api/feed')", "fetch('api/feed.json')")

# 2) profile endpoint -> static file, and filter the timeline client-side by the story clock
#    (the server used to filter by a ?day= param; we bake all posts and filter here instead)
assert "fetch('/api/profile?id='+encodeURIComponent(id)+'&day='+storyDay())" in html, "profile fetch string not found"
html = html.replace(
    "fetch('/api/profile?id='+encodeURIComponent(id)+'&day='+storyDay())",
    "fetch('api/profile/'+encodeURIComponent(id)+'.json')")
assert ".then(d=>{PROFILE=d;" in html, "profile then() string not found"
html = html.replace(
    ".then(d=>{PROFILE=d;",
    ".then(d=>{d.posts=(d.posts||[]).filter(function(p){return p.release_day===undefined||p.release_day<=storyDay();});PROFILE=d;")

# 3) PWA hooks in <head>
head_bits = (
    '<link rel="manifest" href="manifest.json">'
    '<meta name="theme-color" content="#1877f2">'
    '<meta name="apple-mobile-web-app-capable" content="yes">'
    '<meta name="mobile-web-app-capable" content="yes">'
    '<meta name="apple-mobile-web-app-title" content="Biblical Scrolls">'
    '<link rel="apple-touch-icon" href="apple-touch-icon.png">'
    '<link rel="icon" type="image/png" href="favicon-32.png">'
    "</head>"
)
html = html.replace("</head>", head_bits, 1)

# 4) service-worker registration before </body>
sw_reg = ("<script>if('serviceWorker' in navigator){window.addEventListener('load',function(){"
          "navigator.serviceWorker.register('sw.js').catch(function(){});});}</script></body>")
html = html.replace("</body>", sw_reg, 1)

with open(os.path.join(DOCS, "index.html"), "w", encoding="utf-8") as f:
    f.write(html)

# ---------------------------------------------------------------- manifest.json
manifest = {
    "name": "Biblical Scrolls",
    "short_name": "Scrolls",
    "description": "Scroll the Bible as it unfolds, chronologically, as one living feed.",
    "start_url": ".",
    "scope": ".",
    "display": "standalone",
    "orientation": "portrait",
    "background_color": "#f0f2f5",
    "theme_color": "#1877f2",
    "icons": [
        {"src": "icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any maskable"},
        {"src": "icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any maskable"},
    ],
}
with open(os.path.join(DOCS, "manifest.json"), "w", encoding="utf-8") as f:
    json.dump(manifest, f, ensure_ascii=False, indent=2)

# ---------------------------------------------------------------- service worker (network-first for html/json so
# test updates show immediately; cache-first for icons; offline fallback from cache)
sw = """const CACHE='biblical-scrolls-v2';
const SHELL=['.','index.html','manifest.json','api/feed.json','icon-192.png','icon-512.png','apple-touch-icon.png','favicon-32.png'];
self.addEventListener('install',e=>{e.waitUntil(caches.open(CACHE).then(c=>c.addAll(SHELL).catch(()=>{})).then(()=>self.skipWaiting()));});
self.addEventListener('activate',e=>{e.waitUntil(caches.keys().then(ks=>Promise.all(ks.map(k=>k!==CACHE?caches.delete(k):null))).then(()=>self.clients.claim()));});
self.addEventListener('fetch',e=>{
  if(e.request.method!=='GET')return;
  const u=new URL(e.request.url);
  const netFirst = e.request.mode==='navigate' || u.pathname.endsWith('.json') || u.pathname.endsWith('.html') || u.pathname.endsWith('/');
  if(netFirst){
    e.respondWith(fetch(e.request).then(r=>{const c=r.clone();caches.open(CACHE).then(x=>x.put(e.request,c));return r;}).catch(()=>caches.match(e.request)));
  } else {
    e.respondWith(caches.match(e.request).then(h=>h||fetch(e.request).then(r=>{const c=r.clone();caches.open(CACHE).then(x=>x.put(e.request,c));return r;})));
  }
});
"""
with open(os.path.join(DOCS, "sw.js"), "w", encoding="utf-8") as f:
    f.write(sw)

# ---------------------------------------------------------------- icons (a clean open-book glyph on brand blue)
from PIL import Image, ImageDraw

def draw_book(S, rounded):
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    if rounded:
        d.rounded_rectangle([0, 0, S - 1, S - 1], radius=int(S * 0.22), fill=BLUE)
    else:
        d.rectangle([0, 0, S, S], fill=BLUE)  # full-bleed for iOS apple-touch-icon
    cx = S / 2
    xl, xr = S * 0.20, S * 0.80
    top_spine, top_edge = S * 0.30, S * 0.365
    bot_spine, bot_edge = S * 0.70, S * 0.635
    left = [(cx, top_spine), (xl, top_edge), (xl, bot_edge), (cx, bot_spine)]
    right = [(cx, top_spine), (xr, top_edge), (xr, bot_edge), (cx, bot_spine)]
    d.polygon(left, fill=(255, 255, 255, 255))
    d.polygon(right, fill=(255, 255, 255, 255))
    # page lines
    line = (190, 205, 230, 255)
    for i in range(1, 4):
        ty = top_edge + (bot_edge - top_edge) * (i / 4.0)
        d.line([(xl + S * 0.03, ty + S * 0.012), (cx - S * 0.02, ty - S * 0.006)], fill=line, width=max(2, S // 170))
        d.line([(cx + S * 0.02, ty - S * 0.006), (xr - S * 0.03, ty + S * 0.012)], fill=line, width=max(2, S // 170))
    # center fold
    d.line([(cx, top_spine), (cx, bot_spine)], fill=(150, 170, 205, 255), width=max(2, S // 150))
    return img

master = draw_book(1024, rounded=True)
master.resize((512, 512), Image.LANCZOS).save(os.path.join(DOCS, "icon-512.png"))
master.resize((192, 192), Image.LANCZOS).save(os.path.join(DOCS, "icon-192.png"))
master.resize((32, 32), Image.LANCZOS).save(os.path.join(DOCS, "favicon-32.png"))
draw_book(1024, rounded=False).resize((180, 180), Image.LANCZOS).save(os.path.join(DOCS, "apple-touch-icon.png"))

# GitHub Pages: skip Jekyll processing
open(os.path.join(DOCS, ".nojekyll"), "w").close()

print("Static build complete -> docs/")
print(f"  feed.json       : {len(feed['posts'])} posts, {len(feed['beats'])} beats, {feed['stats']['total']} souls")
print(f"  profiles baked  : {baked} (failed {failed})")
print(f"  icons           : icon-192/512, apple-touch-icon, favicon-32")
print(f"  pwa             : manifest.json + sw.js + .nojekyll")
