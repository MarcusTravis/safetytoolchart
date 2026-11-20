#!/usr/bin/env python3
"""Generates every static HTML page, data.js, sitemap, robots, _headers, README, CHANGELOG.

Env overrides (for testing): WP_DATA_DIR (where the *.json live), WP_OUT_DIR (where output goes).
"""
import json, html as H, os, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BUILD = ROOT / "_build"
DATA_DIR = Path(os.environ.get("WP_DATA_DIR") or BUILD)
OUT = Path(os.environ.get("WP_OUT_DIR") or ROOT)
CANON = "https://safetytoolchart.pages.dev"
SITE = "Safety Tool Chart"
CHECKED, CHECKED_ISO = "Nov 16, 2026", "2026-11-16"
SITE_UPDATED, SITE_UPDATED_ISO = "Nov 20, 2026", "2026-11-20"  # last site/template change (sitemap lastmod)
INDEXNOW_KEY = "2ae0335037244607bc920ea25b3b348d"
OWNER = "Marcus Travis"
ASSET_V = "20261120a"
OG_ALT = "Safety Tool Chart: an overhead anchor, a lanyard and a harness D-ring drawn in teal line art"
# Cloudflare Web Analytics: paste the site token here. While it is "REPLACE_ME" the beacon is left out entirely.
CF_TOKEN = "22edf9db96334f9380517b93ca527ff9"
CF = ("" if CF_TOKEN in ("", "REPLACE_ME") else
      "<!-- Cloudflare Web Analytics --><script type='module' src='https://static.cloudflareinsights.com/beacon.min.js' "
      "data-cf-beacon='{\"token\": \"" + CF_TOKEN + "\"}'></script><!-- End Cloudflare Web Analytics -->")
PRICE_RULE = ("Price = lowest in-stock price for a new unit of that exact part number seen on a public US retailer or manufacturer-store listing "
              "(seller named and linked), checked on the date shown. No affiliate links. If no live price was found, a $ band is shown as an editorial estimate.")
BANDS = "$ under $100 · $$ $100–$250 · $$$ $250–$600 · $$$$ $600–$1,500 · $$$$$ over $1,500"
SAFETY = ("Reference only — not training and not a substitute for the manufacturer’s instructions, a competent person, or OSHA/ANSI requirements. "
          "Inspect gear before each use, remove from service any equipment that has arrested a fall, and verify specs with the manufacturer.")
KOFI = "https://ko-fi.com/marcustravis"
FONTS = ("https://fonts.googleapis.com/css2?family=Archivo:wght@600;700;800&family=IBM+Plex+Mono:wght@400;500"
         "&family=IBM+Plex+Sans:wght@400;500;600;700&display=swap")
FIELDS = ["id", "brand", "series", "model", "name", "type", "standards", "ansi_class", "cap_min_lb", "cap_max_lb", "length_ft",
          "weight_lb", "attachment", "gate_lbf", "material", "sizes", "features", "price_usd", "price_source", "price_url",
          "price_checked", "price_scale", "product_url", "spec_url", "notes"]
NUMERIC = ["cap_min_lb", "cap_max_lb", "length_ft", "weight_lb", "gate_lbf", "price_usd"]

HERO_SVG = (BUILD / "hero.svg").read_text()
SECTIONS = json.loads((BUILD / "sections.json").read_text())

NAV = [("index.html", "Home")] + [(s["file"], s["nav"]) for s in SECTIONS] + [
    ("basics.html", "Basics"), ("compare.html", "Compare"), ("updates.html", "Updates"), ("index.html#about", "About")]

COL_LABELS = {"brand": "Brand", "model": "Model / name", "type": "Type", "standards": "Standards", "cls": "Class",
              "capacity": "Capacity lb", "length": "Length ft", "weight": "Weight lb", "attachment": "Attachment",
              "gate": "Gate lbf", "material": "Material", "sizes": "Sizes", "features": "Features", "price": "Price", "links": "Links"}
NUM_COLS = {"capacity", "length", "weight", "gate"}


def e(s):
    return H.escape("" if s is None else str(s), quote=True)


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", str(s).lower()).strip("-")


def write(name, text):
    p = OUT / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def js(obj):
    return json.dumps(obj, ensure_ascii=False).replace("</", "<\\/")


def short(sec):
    return sec["title"].split(" (")[0]


# ---------------------------------------------------------------- data
def icon_for(brand):
    s = slug(brand)
    for ext in ("svg", "png"):
        if (ROOT / "icons" / f"{s}.{ext}").exists():
            return f"icons/{s}.{ext}"
    return None


def as_num(v):
    """Numbers stay numbers; numeric strings ("3,600") are coerced; anything else becomes None (check.py flags it)."""
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return v
    if isinstance(v, str):
        try:
            return float(v.replace(",", "").strip())
        except ValueError:
            return None
    return None


def load_section(sec):
    path = DATA_DIR / sec["json"]
    raw = []
    if not path.exists():
        print(f"warn: {path.name} missing — rendering empty", file=sys.stderr)
    else:
        try:
            txt = path.read_text(encoding="utf-8").strip()
            raw = json.loads(txt) if txt else []
            if not isinstance(raw, list):
                raise ValueError("top level is not a list")
        except Exception as ex:  # partial writes by other processes etc.
            print(f"warn: {path.name} failed to parse ({ex}) — treating as empty", file=sys.stderr)
            raw = []
    items, used = [], set()
    for i, d in enumerate(raw):
        if not isinstance(d, dict):
            continue
        it = {k: d.get(k) for k in FIELDS}
        if not it["brand"] and not it["model"]:
            continue
        base = slug(it["id"]) if it["id"] else slug(f"{it['brand']}-{it['model']}") or f"item-{i}"
        iid, n = base, 2
        while iid in used or iid in ALL_IDS:
            iid, n = f"{base}-{n}", n + 1
        used.add(iid); ALL_IDS.add(iid)
        it["id"] = iid
        it["rid"] = "p-" + iid
        st = it["standards"]
        it["standards"] = [str(x) for x in (st if isinstance(st, list) else [st] if st else []) if x]
        for k in NUMERIC:
            it[k] = as_num(it[k])
        it["_icon"] = icon_for(it["brand"] or "")
        items.append(it)
    return items


ALL_IDS = set()
HAS_FULL = False


# ---------------------------------------------------------------- shared chrome
def head(title, description, path, jsonld=None):
    url = CANON + (path if path != "/" else "/")
    typ = "website" if path == "/" else "article"
    ld = f'\n<script type="application/ld+json">{js(jsonld)}</script>' if jsonld else ""
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>{e(title)}</title>
<meta name="description" content="{e(description)}">
<link rel="canonical" href="{e(url)}">
<meta property="og:type" content="{typ}">
<meta property="og:site_name" content="{SITE}">
<meta property="og:locale" content="en_US">
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(description)}">
<meta property="og:url" content="{e(url)}">
<meta property="og:image" content="{CANON}/og-image.png">
<meta property="og:image:type" content="image/png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="{e(OG_ALT)}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{e(title)}">
<meta name="twitter:description" content="{e(description)}">
<meta name="twitter:image" content="{CANON}/og-image.png">
<meta name="twitter:image:alt" content="{e(OG_ALT)}">
<meta name="theme-color" content="#050d16">
<link rel="icon" href="favicon.ico" sizes="any">
<link rel="icon" href="favicon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="apple-touch-icon.png">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="{FONTS}">
<link rel="stylesheet" href="theme.css?v={ASSET_V}">{ld}
</head>
"""


LOGO_SVG = ('<svg width="28" height="28" viewBox="0 0 32 32" aria-hidden="true"><rect x="1" y="1" width="30" height="30" rx="6" fill="none" stroke="#3fc1c9" stroke-width="1.5"/>'
            '<path d="M6 7.5 H26" stroke="#9be7ea" stroke-width="2" stroke-linecap="round"/>'
            '<path d="M16 7.5 V15" stroke="#3fc1c9" stroke-width="1.6"/>'
            '<path d="M16 15 c-2.2 1.4 2.2 2.6 0 4" fill="none" stroke="#3fc1c9" stroke-width="1.5"/>'
            '<path d="M12 19.5 h8 a0 0 0 0 1 0 0 c0 3.8 -1.8 6 -4 6 s-4 -2.2 -4 -6 z" fill="none" stroke="#9be7ea" stroke-width="1.7" stroke-linejoin="round"/></svg>')


def nav(current):
    items = []
    for href, label in NAV:
        cur = ' aria-current="page"' if href == current else ""
        extra = ' <span class="cmp-n" hidden>0</span>' if href == "compare.html" else ""
        items.append(f'<li><a href="{href}"{cur}>{e(label)}{extra}</a></li>')
    return f"""<a class="skip" href="#main">Skip to content</a>
<nav class="topnav" aria-label="Primary">
  <div class="inner">
    <a class="brand" href="index.html">
      {LOGO_SVG}
      {SITE}
    </a>
    <button type="button" class="nav-toggle" aria-expanded="false" aria-controls="primary-nav" aria-label="Open menu">☰ Menu</button>
    <ul class="nav-links" id="primary-nav">{''.join(items)}</ul>
  </div>
</nav>
"""


FOOTER_P = (f'<p class="kofi">Free and ad-free. If this site helped you, <a href="{KOFI}" target="_blank" rel="noopener">buy me a coffee →</a></p>\n'
            f'<p class="foot-safety">{e(SAFETY)}</p>')


def footer():
    return f"""<footer class="site-footer">
{FOOTER_P}
</footer>
<script>
(function () {{
  function syncNavH() {{
    var nav = document.querySelector(".topnav");
    if (!nav) return;
    document.documentElement.style.setProperty("--nav-h", Math.ceil(nav.getBoundingClientRect().height) + "px");
  }}
  syncNavH();
  window.addEventListener("resize", syncNavH);
  if (window.ResizeObserver && document.querySelector(".topnav")) {{
    new ResizeObserver(syncNavH).observe(document.querySelector(".topnav"));
  }}
}})();
</script>
"""


def hero(eyebrow, title, lede, compact=True, checked=True):
    chk = (f'<p class="checked">Data last checked: <time datetime="{CHECKED_ISO}">{CHECKED}</time> · '
           f'<a href="updates.html">What changed</a></p>') if checked else ""
    return f"""<header class="hero{' compact' if compact else ''}">
  <div class="hero-art">{HERO_SVG}</div>
  <div class="hero-copy">
    <span class="eyebrow">{e(eyebrow)}</span>
    <h1>{e(title)}</h1>
    <p class="lede">{lede}</p>
    {chk}
  </div>
</header>
"""


def safety(big=False):
    if big:
        return ('<aside class="safety safety-big" role="note"><strong>Safety first — read this.</strong> '
                f'{e(SAFETY)} Fall protection only works as a complete, compatible system chosen for the job, with a rescue plan in place. '
                'See <a href="basics.html">Basics &amp; standards</a> for a plain-language overview.</aside>\n')
    return f'<aside class="safety" role="note"><strong>Safety note.</strong> {e(SAFETY)}</aside>\n'


def page(name, title, desc, path, current, body, scripts="", jsonld=None, page_id="", pre=""):
    pid = f' data-page="{page_id}"' if page_id else ""
    html = head(title, desc, path, jsonld) + f"<body{pid}>\n" + '<div class="page-bg"></div>\n' + nav(current)
    html += body + footer()
    html += (f'{pre}<script src="compare.js?v={ASSET_V}" defer></script>\n<script src="nav.js?v={ASSET_V}" defer></script>\n'
             f'{scripts}\n{CF}\n</body>\n</html>\n')
    write(name, html)


# ---------------------------------------------------------------- shared helpers (breadcrumbs, rich text, JSON-LD)
def crumbs(label):
    return ('<nav class="crumbs" aria-label="Breadcrumb"><ol><li><a href="index.html">Home</a></li>'
            f'<li><span aria-current="page">{e(label)}</span></li></ol></nav>\n')


def rich(text):
    """[[O502|label]] -> external source link; [[page.html#x|label]] -> internal link. Everything else is escaped."""
    out, pos = [], 0
    for m in re.finditer(r"\[\[([^|\]]+)\|([^\]]+)\]\]", text):
        out.append(e(text[pos:m.start()]))
        key, label = m.group(1), m.group(2)
        out.append(src(globals()[key], e(label)) if key in OSHA_KEYS else f'<a href="{e(key)}">{e(label)}</a>')
        pos = m.end()
    out.append(e(text[pos:]))
    return "".join(out)


def plain(htmltext):
    return H.unescape(re.sub(r"<[^>]+>", "", htmltext)).strip()


# Related charts (symmetric); Basics is always linked too.
RELATED = {"harnesses": ["lanyards", "srls", "connectors"], "lanyards": ["harnesses", "srls", "anchors"],
           "srls": ["harnesses", "lanyards", "lifelines", "rescue"], "anchors": ["lanyards", "connectors", "lifelines"],
           "connectors": ["harnesses", "anchors"], "lifelines": ["anchors", "srls"], "rescue": ["srls"]}
PERSON = {"@type": "Person", "name": OWNER}


def breadcrumb_ld(label, path):
    return {"@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": "Home", "item": CANON + "/"},
        {"@type": "ListItem", "position": 2, "name": label, "item": CANON + path}]}


def brands_of(items):
    return sorted({it["brand"] for it in items if it["brand"]}, key=str.lower)


# ---------------------------------------------------------------- section pages
def write_section(sec, items):
    n = len(items)
    cols = sec["cols"]
    labels = dict(COL_LABELS, **sec.get("labels", {}))
    ths = ""
    for c in cols:
        num = ' class="num"' if c in NUM_COLS else ""
        inner = e(labels[c]) if c == "links" else f'<button type="button" class="th-btn" data-k="{c}">{e(labels[c])}</button>'
        ths += f"<th{num} scope=\"col\">{inner}</th>"
    payload = [{k: v for k, v in it.items()} for it in items]
    path = "/" + sec["slug"]
    itemlist = {"@type": "ItemList", "name": sec["page_title"] + " — " + SITE, "numberOfItems": n,
                "itemListElement": [{"@type": "ListItem", "position": i + 1, "name": f"{it['brand'] or ''} {it['model'] or it['series'] or ''}".strip(),
                                     "url": f"{CANON}/{sec['slug']}#{it['rid']}"} for i, it in enumerate(items)]}
    dataset = {"@type": "Dataset", "@id": CANON + path + "#dataset", "name": sec["page_title"], "description": sec["description"],
               "url": CANON + path, "inLanguage": "en", "creator": dict(PERSON), "dateModified": CHECKED_ISO, "isAccessibleForFree": True,
               "keywords": ["fall protection", short(sec).lower(), "OSHA", "ANSI Z359", "comparison chart"],
               "variableMeasured": [labels[c] for c in cols if c != "links"]}
    if HAS_FULL:
        dataset["distribution"] = [{"@type": "DataDownload", "encodingFormat": "text/plain", "contentUrl": CANON + "/llms-full.txt"}]
    ld = {"@context": "https://schema.org", "@graph": [dataset, breadcrumb_ld(short(sec), path), itemlist]}
    rel = [x for x in SECTIONS if x["slug"] in RELATED[sec["slug"]]]
    rel_links = " · ".join([f'<a href="{x["file"]}">{e(short(x))}</a>' for x in rel] +
                           ['<a href="basics.html#rescue">Rescue planning</a>' if sec["slug"] == "rescue" else '<a href="basics.html">Basics &amp; standards</a>'] +
                           ['<a href="compare.html">Compare</a>'])
    answer = (f'  <div class="answer">\n    <p>{rich(sec["answer"])}</p>\n  </div>\n'
              f'  <p class="related"><strong>Related charts:</strong> {rel_links}</p>\n')
    body = '<div class="wrap chart-wrap" id="main">\n' + crumbs(short(sec))
    body += hero(("Catalog · " + str(n) + " " + sec["card_noun"]) if n else "Catalog", sec["title"], e(sec["lede"]))
    body += safety()
    body += answer
    body += f"""  <div class="toolbar">
    <div class="fgroups" id="fgroups"></div>
    <div class="tools">
      <label class="search">Search
        <input type="search" id="search" placeholder="Brand, model, type, standard" autocomplete="off">
      </label>
      <label class="sort">Sort
        <select id="sort"></select>
      </label>
    </div>
  </div>
  <p class="count" id="count" aria-live="polite"></p>
  <p class="table-caption" id="cap"><strong>Price rule:</strong> {e(PRICE_RULE)} <strong>Editorial estimate</strong> (no live price seen): {e(BANDS)}. Blank cells show “—” (not published / not found). Every row links the page its specs came from.</p>
  <div class="table-box">
    <table class="chart" aria-describedby="cap">
      <caption class="sr-only">{e(sec['title'])}: one row per part number</caption>
      <thead><tr>{ths}</tr></thead>
      <tbody id="rows"></tbody>
    </table>
  </div>
  <div class="notes">
    <section><h2>How to read this chart</h2><ul>
      <li>Tick <strong>Compare</strong> on up to 4 rows (across any catalog), then open <a href="compare.html">Compare</a> to see them side by side.</li>
      <li>Click a column heading to sort; rows with no value for that column always sort last.</li>
      <li>Capacity is the user weight range the maker rates the product for (worker plus clothing and tools).</li>
      <li>New to classes, clearance and the OSHA numbers? Start with <a href="basics.html">Basics &amp; standards</a>.</li>
    </ul></section>
    <section><h2>Sources and limits</h2>
      <p>Facts come from official manufacturer pages, spec sheets and instruction manuals, plus public retailer listings for the exact part number. Each row links its source. Notes are written in our own words. Nothing is guessed: a missing number means it was not published or not found. Data last checked {CHECKED}. Always follow the instructions that ship with the product.</p></section>
    <section><h2>Independence</h2>
      <p>No ads, no affiliate links, no tracking parameters. Every link goes straight to the manufacturer or retailer page it names.</p></section>
  </div>
</div>
"""
    cfg = {"noun": sec["noun"], "cols": cols, "labels": labels, "filters": sec["filters"], "defaultSort": "brand"}
    scripts = (f'<script src="app.js?v={ASSET_V}" defer></script>\n<script src="scroll-hint.js?v={ASSET_V}" defer></script>\n'
               f'<script>\nconst DATA = {js(payload)};\n'
               f'document.addEventListener("DOMContentLoaded", function () {{ initCatalog(DATA, {js(cfg)}); }});\n</script>')
    page(sec["file"], f"{sec['seo_title']} · {SITE}", sec["description"], path, sec["file"], body, scripts, ld)
    print(f"wrote {sec['file']}: {n} rows")


# ---------------------------------------------------------------- home
def write_home(sections_items):
    index = []
    for sec, items in sections_items:
        for it in items:
            name = (f"{it['series']} {it['model']}" if it["series"] and it["model"] and it["series"] not in it["model"] else (it["model"] or it["series"] or ""))
            tags = [t for t in [it["type"], it["ansi_class"]] if t]
            index.append({"name": name, "maker": it["brand"] or "", "tags": tags, "extra": " ".join(str(x) for x in [it["name"], it["series"], " ".join(it["standards"])] if x), "icon": it["_icon"], "section": short(sec),
                          "href": f"{sec['file']}#{it['rid']}"})
    cards = "".join(
        f'<a class="card" href="{s["file"]}"><span class="cnt">{len(items)} {s["card_noun"]}</span><span class="nm">{e(short(s))}</span>'
        f'<span class="ds">{e(s["card"])}</span><span class="go">Open catalog →</span></a>' for s, items in sections_items)
    cards += ('<a class="card" href="basics.html"><span class="cnt">Explainer</span><span class="nm">Basics &amp; standards</span>'
              '<span class="ds">OSHA fall arrest limits, ANSI Z359 classes, fall clearance, swing falls, rescue and inspection — in plain language.</span><span class="go">Read the basics →</span></a>')
    cards += ('<a class="card" href="compare.html"><span class="cnt">Tool</span><span class="nm">Compare</span>'
              '<span class="ds">Pick up to four rows from any catalog and see every field and source side by side.</span><span class="go">Open compare →</span></a>')
    total = len(index)
    body = '<div class="wrap chart-wrap" id="main">\n'
    body += hero("Independent fall protection reference", SITE,
                 "A free, ad-free, cross-brand reference for personal fall protection gear: harnesses, lanyards, self-retracting lifelines, anchors, connectors, lifelines, and rescue equipment — specs side by side, with a link to every source.",
                 compact=False)
    body += safety(big=True)
    body += f"""  <section class="site-search" role="search" aria-labelledby="site-search-h">
    <h2 id="site-search-h">Search every product</h2>
    <label for="site-search">Harnesses, lanyards, SRLs, anchors and more — by brand, model, type or class</label>
    <input type="search" id="site-search" placeholder="Try twin leg, Class 2, beam clamp, rebar hook…" autocomplete="off" spellcheck="false" aria-describedby="site-status" aria-controls="site-results">
    <p class="sr-status" id="site-status" aria-live="polite">Searches all {total} products across every catalog.</p>
    <ul class="sr-list" id="site-results" hidden></ul>
  </section>
  <section class="grp">
    <h2>Start here</h2>
    <div class="grid">{cards}</div>
  </section>
  <div class="notes">
    <section>
      <h2>Why this exists</h2>
      <p>Falls are consistently among the leading causes of death in U.S. construction, and OSHA’s fall protection rule is regularly one of its most-cited standards. Picking gear still means opening one brand site at a time. This chart lines up the specs that matter — class, capacity, length, connectors, gate strength — with a link to the maker’s own page for each.</p>
    </section>
    <section>
      <h2>How to use it</h2>
      <p>Search above, or open a catalog. Each catalog is a dense, sortable chart with filter chips for brand, type, ANSI class, CSA listing and capacity. Tick <strong>Compare</strong> on up to four rows to line them up. New to the standards? Read <a href="basics.html">Basics &amp; standards</a> first.</p>
    </section>
  </div>
  <section class="notes" id="about" style="display:block">
    <section>
      <h2>About this site</h2>
      <p>{SITE} is free and has no ads, no affiliate links, and no tracking parameters in its links. Facts come from official manufacturer pages, spec sheets and instruction manuals, and from public retailer listings for the exact part number, last checked {CHECKED}. Every row links the page its specs came from. Notes are written in original words; marketing text, photos and tables are never copied.</p>
      <p><strong>Price rule.</strong> {e(PRICE_RULE)} If no live price was seen for that exact part number, the cell shows an editorial band, labelled “Editorial estimate”: {e(BANDS)}.</p>
      <p><strong>Logos.</strong> Official brand marks are shown only where the maker’s own site offers one (sources in <code>icons/README.md</code>); other brands appear as a plain text badge. Marks belong to their owners.</p>
      <p><strong>Not advice.</strong> {e(SAFETY)}</p>
      <p><a href="updates.html">See what changed →</a></p>
    </section>
  </section>
</div>
"""
    ld = {"@context": "https://schema.org", "@type": "WebSite", "name": SITE, "url": CANON + "/", "inLanguage": "en",
          "description": "Free, ad-free cross-brand reference for personal fall protection gear.",
          "publisher": dict(PERSON), "creator": dict(PERSON)}
    scripts = f'<script>window.SEARCH_INDEX = {js(index)};</script>\n<script src="home-search.js?v={ASSET_V}" defer></script>'
    page("index.html", f"{SITE} — fall protection gear compared",
         "Free, ad-free fall protection reference: harnesses, lanyards, SRLs, anchors, connectors, lifelines and rescue gear compared across brands, plus OSHA basics.",
         "/", "index.html", body, scripts, ld)
    print("wrote index.html")


# ---------------------------------------------------------------- compare + data.js
def write_compare(sections_items):
    items = {}
    for sec, its in sections_items:
        for it in its:
            d = dict(it)
            d["section"] = sec["slug"]; d["sectionLabel"] = short(sec); d["sectionFile"] = sec["file"]
            items[it["id"]] = d
    secs = [{"file": s["file"], "label": short(s)} for s in SECTIONS]
    write("data.js", "/* Generated by _build/generate.py — all catalog items, used by compare.html. */\n"
          f"window.WP_SECTIONS = {js(secs)};\nwindow.WP_ITEMS = " + js(items) + ";\n")
    body = '<div class="wrap chart-wrap" id="main">\n' + crumbs("Compare")
    body += hero("Side by side", "Compare", "Up to four items from any catalog, every field and source in one view. Rows that are blank for all chosen items are hidden.", checked=False)
    body += safety()
    chart_links = " · ".join(f'<a href="{x["file"]}">{e(short(x))}</a>' for x in SECTIONS)
    body += f"""  <div class="cmp-actions"><button type="button" class="btn" id="cmp-clear" hidden>Clear all</button>
    <span class="count">Selections are saved in this browser only. Prices: {e(PRICE_RULE)}</span></div>
  <div class="cmp-wrap" id="cmp-root" aria-live="polite"><div class="cmp-empty">Loading…</div></div>
  <p class="related"><strong>Pick items from a chart:</strong> {chart_links}. New to the terms? Read <a href="basics.html">Basics &amp; standards</a>.</p>
</div>
"""
    page("compare.html", f"Compare fall protection gear · {SITE}",
         "Compare up to four fall protection products from any chart side by side: every spec, price source and official link in one table.",
         "/compare", "compare.html", body, "", {"@context": "https://schema.org", "@graph": [breadcrumb_ld("Compare", "/compare")]},
         page_id="compare", pre=f'<script src="data.js?v={ASSET_V}" defer></script>\n')
    print("wrote compare.html, data.js")


# ---------------------------------------------------------------- basics
def src(url, label):
    return f'<a href="{url}" target="_blank" rel="noopener">{label}</a>'


O502 = "https://www.osha.gov/laws-regs/regulations/standardnumber/1926/1926.502"
O501 = "https://www.osha.gov/laws-regs/regulations/standardnumber/1926/1926.501"
O140 = "https://www.osha.gov/laws-regs/regulations/standardnumber/1910/1910.140"
O28 = "https://www.osha.gov/laws-regs/regulations/standardnumber/1910/1910.28"
ASSP = "https://www.assp.org/standards/standards-topics/fall-protection-z359"
CSA = "https://www.csagroup.org/standards/"

OSHA_KEYS = {"O501", "O502", "O28", "O140", "ASSP", "CSA"}

FAQ = [
    ("What weight can a full-body harness hold?",
     f'ANSI Z359.11 harnesses are rated by the maker for a user weight range, meaning the worker plus clothing and tools ({src(ASSP, "ASSP Z359 overview")}). '
     f'OSHA’s Appendix C test criteria for 1926.502(d)(16) assume a combined weight under 310 lb, and heavier users need adjusted criteria ({src(O502, "1926.502")}). '
     'Check the harness label and the maker’s instructions. The <a href="harnesses.html">Harnesses chart</a> lists each model’s published capacity.'),
    ("What is the OSHA free-fall limit?",
     f'Under {src(O502, "1926.502(d)(16)")}, a personal fall arrest system must be rigged so the worker cannot free fall more than 6 ft or hit a lower level, with a maximum arresting force of 1,800 lb and a maximum deceleration distance of 3.5 ft. '
     f'{src(O140, "1910.140")} allows a free fall of more than 6 ft only if the manufacturer designed and tested the system for it and the 1,800 lb limit is still met.'),
    ("When is fall protection required?",
     f'In construction, at 6 feet or more above a lower level ({src(O501, "1926.501")}). In general industry, at 4 feet or more ({src(O28, "1910.28")}). '
     'Other OSHA subparts, such as scaffolds and ladders, set their own rules, so check the one that covers the work.'),
    ("Should I use a lanyard or an SRL?",
     f'An energy-absorbing lanyard has a fixed length and an absorber rated for a 6 ft or 12 ft free fall under Z359.13. An SRL pays out and retracts and typically locks within a short distance, so it often needs less clearance. '
     f'Class 1 SRLs are meant for overhead anchors; Class 2 are also tested for lower anchorages ({src(ASSP, "ASSP Z359 overview")}). '
     'Whichever you pick, use the maker’s clearance chart. Compare the <a href="lanyards.html">Lanyards</a> and <a href="srls.html">SRLs</a> charts.'),
    ("What should I do with gear after a fall?",
     f'Take it out of service immediately. Under {src(O502, "1926.502(d)(19)")}, equipment that took an impact load stays out until a competent person inspects it and decides it is undamaged and fit for reuse. '
     'Most makers say to retire it, and an activated impact indicator means remove it.'),
    ("How does ANSI Z359 differ from OSHA?",
     f'OSHA is the law. ANSI/ASSP Z359 is a family of voluntary consensus standards that most U.S. gear is designed and labelled to ({src(ASSP, "ASSP Z359 overview")}). '
     f'In Canada the equivalent product standards are CSA Z259 ({src(CSA, "CSA Group")}).'),
    ("How often should fall protection gear be inspected?",
     f'Before each use ({src(O502, "1926.502(d)(21)")}); {src(O140, "1910.140")} says before initial use during each work shift. '
     f'ANSI expects a documented inspection by a competent person at intervals set by the program and the maker, commonly at least yearly ({src(ASSP, "ASSP Z359 overview")}).'),
    ("What about rescue after a fall?",
     f'OSHA requires prompt rescue, or workers who can rescue themselves ({src(O502, "1926.502(d)(20)")}). A worker hanging in a harness is at risk of suspension intolerance, so the plan, gear and trained people must be ready before work starts. '
     'Suspension relief straps help while waiting, and rescued workers should be medically evaluated. See <a href="#rescue">Suspension and rescue planning</a> and the <a href="rescue.html">Rescue &amp; descent chart</a>.'),
    ("How strong does an anchor need to be?",
     f'An anchorage must support at least 5,000 lb per worker attached, or be designed, installed and used as part of a complete system with a safety factor of at least two, under a qualified person ({src(O502, "1926.502(d)")}). '
     'See the <a href="anchors.html">Anchors chart</a> for anchorage connectors.'),
]
FAQ_HTML = "".join(f"<h3>{e(q)}</h3>\n  <p>{a}</p>\n  " for q, a in FAQ)

BASICS = f"""
<div class="wrap" id="main">
{{CRUMBS}}{{HERO}}{{SAFETY}}
<article class="prose">
  <p class="callout"><strong>Plain-language summary — read the standard.</strong> This page paraphrases public rules and standards so the chart columns make sense. It is not training, it leaves out exceptions and details, and standards are revised. The text of the regulation, the current edition of the standard, and the manufacturer’s instructions always win.</p>
  <nav class="toc" aria-label="On this page"><strong>On this page</strong>
    <ol>
      <li><a href="#when">When fall protection is required</a></li>
      <li><a href="#pfas">OSHA personal fall arrest limits (construction)</a></li>
      <li><a href="#gi">General industry (1910.140) differences</a></li>
      <li><a href="#ansi">ANSI/ASSP Z359 and CSA Z259 at a glance</a></li>
      <li><a href="#clearance">Fall clearance</a></li>
      <li><a href="#swing">Swing falls and leading edges</a></li>
      <li><a href="#rescue">Suspension and rescue planning</a></li>
      <li><a href="#inspect">Inspection and retirement</a></li>
      <li><a href="#faq">Frequently asked questions</a></li>
    </ol>
  </nav>
  <p class="related"><strong>Charts that go with this page:</strong> {{CHARTS}}.</p>

  <h2 id="when">1. When fall protection is required</h2>
  <ul>
    <li><strong>Construction:</strong> under {src(O501, "29 CFR 1926.501")}, a worker on a surface with an unprotected side or edge <strong>6 feet or more</strong> above a lower level must be protected by guardrails, a safety net, or a personal fall arrest system (with specific rules and exceptions for leading edges, holes, roofs and other situations).</li>
    <li><strong>General industry:</strong> under {src(O28, "29 CFR 1910.28")}, the trigger for unprotected sides and edges is <strong>4 feet or more</strong> above a lower level, and the options include guardrails, nets, or personal fall protection (fall arrest, travel restraint, or positioning).</li>
    <li>Other OSHA subparts (scaffolds, ladders, steel erection, aerial lifts and more) set their own rules. Check the subpart that covers the work.</li>
  </ul>
  <p>Personal gear is usually the last line of defense: removing the hazard, guardrails, and travel restraint (which keeps a worker from reaching the edge at all) are generally preferred over arresting a fall after it starts.</p>

  <h2 id="pfas">2. OSHA personal fall arrest limits (construction)</h2>
  <p>Paraphrasing {src(O502, "29 CFR 1926.502(d)")}, a personal fall arrest system in construction must, among other things:</p>
  <div class="mini-box"><table class="mini">
    <thead><tr><th>Item</th><th>Key number (paraphrased)</th></tr></thead>
    <tbody>
      <tr><td>Anchorage</td><td>Supports at least <strong>5,000 lb per worker attached</strong> — or is designed, installed and used as part of a complete system with a <strong>safety factor of at least two</strong>, under the supervision of a qualified person.</td></tr>
      <tr><td>Maximum arresting force</td><td><strong>1,800 lb</strong> on the worker when used with a body harness (body belts are not allowed for fall arrest).</td></tr>
      <tr><td>Free fall</td><td>Rigged so the worker cannot free fall more than <strong>6 ft</strong>, and cannot hit any lower level.</td></tr>
      <tr><td>Deceleration distance</td><td>Stops the worker within <strong>3.5 ft</strong> of deceleration distance.</td></tr>
      <tr><td>D-rings and snap hooks</td><td>Minimum tensile strength <strong>5,000 lb</strong>, proof-tested to <strong>3,600 lb</strong> without cracking, breaking or permanent deformation. Only <strong>locking</strong> snap hooks may be used.</td></tr>
      <tr><td>Lanyards and vertical lifelines</td><td>Minimum breaking strength <strong>5,000 lb</strong>; each worker on a vertical lifeline needs their own line (narrow exception for elevator shafts).</td></tr>
      <tr><td>Horizontal lifelines</td><td>Designed, installed and used under the supervision of a qualified person, keeping a safety factor of at least two.</td></tr>
      <tr><td>Harness attachment</td><td>Center of the back near shoulder level, or above the head.</td></tr>
      <tr><td>After a fall</td><td>Equipment that took an impact load comes out of service immediately until a competent person inspects it and decides it is undamaged and fit for reuse.</td></tr>
      <tr><td>Inspection and rescue</td><td>Inspect before each use; remove defective parts. There must be a plan for <strong>prompt rescue</strong>, or workers must be able to rescue themselves.</td></tr>
    </tbody>
  </table></div>
  <p class="count">Also note: OSHA’s Appendix C test criteria for (d)(16) assume a combined worker-plus-tool weight under 310 lb; heavier users need adjusted criteria. That is one reason capacity ratings above 310 lb are called out in the chart.</p>

  <h2 id="gi">3. General industry (1910.140) differences</h2>
  <p>{src(O140, "29 CFR 1910.140")} covers personal fall protection systems outside construction. The core performance numbers match construction — 1,800 lb maximum arresting force, 3.5 ft maximum deceleration distance, 6 ft free fall with no contact with a lower level, 5,000 lb anchorages (or safety factor of two under a qualified person), 5,000 lb connector strength proof-tested to 3,600 lb. Points worth knowing:</p>
  <ul>
    <li>It states a <strong>gate strength of 3,600 lb</strong> for snap hooks and carabiners, and requires them to be the automatic-locking type.</li>
    <li>Free fall may exceed 6 ft if the manufacturer designed and tested the system for it and the 1,800 lb force limit is still met — this is how 12 ft free-fall lanyards fit in.</li>
    <li>The harness attachment may be at the front (sternal) if free fall is limited to 2 ft or less.</li>
    <li>Gear must be inspected before initial use during each work shift.</li>
  </ul>

  <h2 id="ansi">4. ANSI/ASSP Z359 and CSA Z259 at a glance</h2>
  <p>The ANSI/ASSP Z359 Fall Protection Code is a family of voluntary consensus standards that most U.S. gear is designed and labelled to; OSHA is the law, Z359 is the product and program standard most makers test against. The family is maintained by ASSP ({src(ASSP, "ASSP Z359 overview")}). Canada’s equivalent product standards are the CSA Z259 series ({src(CSA, "CSA Group standards")}), which is why some rows list both. A few parts you will see in the chart:</p>
  <ul>
    <li><strong>Z359.11 — full-body harnesses.</strong> Harnesses are labelled with classes by attachment point: <strong>A</strong> (fall arrest, dorsal D-ring — every fall arrest harness), <strong>D</strong> (suspension / controlled descent), <strong>E</strong> (confined space entry and retrieval, usually shoulder attachments), <strong>L</strong> (ladder climbing, front attachment) and <strong>P</strong> (work positioning, side D-rings at the hips). A harness can carry several letters, e.g. “A, P”.</li>
    <li><strong>Z359.13 — energy absorbers and energy-absorbing lanyards.</strong> Rated by maximum free fall: <strong>6 ft</strong> free-fall units for tie-off at or above the D-ring, and <strong>12 ft</strong> free-fall units for tie-off down to foot level. The 12 ft versions allow more stretch, so they need more clearance below.</li>
    <li><strong>Z359.14 — self-retracting devices.</strong> <strong>Class 1</strong> SRLs are meant for anchors overhead (at or above the dorsal D-ring). <strong>Class 2</strong> SRLs are also tested for anchorages lower than that, where the free fall and arrest distance are longer. Device types include <strong>SRL</strong>, <strong>SRL-R</strong> (with an integral rescue / retrieval function), <strong>SRL-P</strong> (personal, worn on the harness), and <strong>SRL-LE</strong> (leading edge: tested for the line running over a sharp edge).</li>
    <li><strong>Z359.12 — connecting components.</strong> Snap hooks, carabiners and similar connectors must be self-closing and self-locking, with gates rated to <strong>3,600 lbf</strong> — the “Gate lbf” column in the Connectors chart.</li>
    <li>Other parts cover program management, anchorages, horizontal lifelines, rescue systems, ladder systems and training. Read the current edition: this summary simplifies.</li>
  </ul>

  <h2 id="clearance">5. Fall clearance</h2>
  <p>Fall clearance is how much open space must exist below the working surface (or below the anchor) so a falling worker stops before hitting anything. Add up:</p>
  <p><span class="formula">clearance = free fall + deceleration distance + harness stretch / D-ring shift + D-ring-to-feet height + safety margin</span></p>
  <ul>
    <li><strong>Free fall:</strong> how far the D-ring drops before the system starts to slow it. With a 6 ft lanyard tied at D-ring height, that is about 6 ft; tied at foot level it can be close to 12 ft.</li>
    <li><strong>Deceleration distance:</strong> how far the energy absorber or SRL brake extends while stopping the fall (OSHA caps it at 3.5 ft; many products publish their own figure).</li>
    <li><strong>Harness stretch and D-ring shift:</strong> the harness webbing stretches and the D-ring slides up the back under load.</li>
    <li><strong>Worker height:</strong> the distance from the D-ring down to the soles of the feet.</li>
    <li><strong>Safety margin:</strong> extra room for the unknowns.</li>
  </ul>
  <div class="example">
    <p><strong>Illustrative example only (round numbers, not a design).</strong> 6 ft energy-absorbing lanyard anchored at D-ring height: 6 ft free fall + 3.5 ft deceleration (the OSHA maximum) + 1 ft harness stretch and D-ring shift + 5 ft from D-ring to feet + 2 ft margin ≈ <strong>17.5 ft below the anchor</strong>.</p>
    <p>That is why a 6 ft lanyard often does not work for low work, and why SRLs — which typically lock within a short distance — are common when clearance is tight. Always use the manufacturer’s clearance chart for the exact product and anchor position.</p>
  </div>
  <p><strong>Why Class 2 and leading-edge setups need more room:</strong> when the anchor is at foot level or below the D-ring, the worker falls further before the line is taut and the device locks, and over an edge the line also bends and rubs. Makers publish larger clearance figures for these cases — often with extra allowance for swing.</p>

  <h2 id="swing">6. Swing falls and leading edges</h2>
  <p>If the anchor is not directly overhead, a falling worker swings like a pendulum back toward the line under the anchor. The swing can slam them into a column or the structure, and the arc also <em>adds</em> to the vertical distance fallen. Keep work close to the area under the anchor, move the anchor as you move (trolleys, horizontal lifelines), and treat the maker’s swing-fall limits as part of clearance. Where the line may contact an edge (roof decks, steel, slab edges), use equipment rated for leading-edge use and follow its setback and edge-angle rules.</p>

  <h2 id="rescue">7. Suspension and rescue planning</h2>
  <p>Arresting the fall is only half the job. A worker hanging in a harness can develop suspension intolerance (often called suspension trauma), in which leg straps restrict circulation and the worker can lose consciousness. OSHA requires prompt rescue; in practice that means a written plan, gear and trained people <em>before</em> work starts, not a 911 call afterward.</p>
  <ul>
    <li>Plan how a fallen worker will be reached: ladders or lifts, an SRL with a rescue function, a pre-rigged rescue or descent kit, or professional rescue that can actually arrive in time.</li>
    <li>Suspension relief straps let a conscious worker stand in a loop and take pressure off the legs while waiting.</li>
    <li>Rescued workers should be medically evaluated.</li>
  </ul>

  <h2 id="inspect">8. Inspection and retirement</h2>
  <ul>
    <li><strong>Before each use:</strong> the user checks webbing and stitching (cuts, burns, fraying, chemical or UV damage, broken stitches), hardware (cracks, deformation, corrosion, gates that do not close and lock), labels, and any impact or fall indicators.</li>
    <li><strong>Periodic inspection:</strong> ANSI expects documented inspection by a competent person at intervals set by the program and the maker (commonly at least yearly; harsher use means more often). SRLs may also need factory service.</li>
    <li><strong>Retire immediately</strong> any gear that has arrested a fall or shows an activated impact indicator, until a competent person decides otherwise per the manufacturer — most makers say retire.</li>
    <li>Some manufacturers set a service life for textile gear; others rely on inspection. Follow the instructions for your product.</li>
    <li>Never hoist materials with personal fall protection, and never tie off to a guardrail or anything not rated as an anchorage.</li>
  </ul>
  <h2 id="faq">Frequently asked questions</h2>
  {FAQ_HTML}<h2 id="sources">Official sources</h2>
  <ul>
    <li>{src(O501, "OSHA 29 CFR 1926.501 — duty to have fall protection (construction)")}</li>
    <li>{src(O502, "OSHA 29 CFR 1926.502 — fall protection systems criteria and practices")}</li>
    <li>{src(O28, "OSHA 29 CFR 1910.28 — duty to have fall protection (general industry)")}</li>
    <li>{src(O140, "OSHA 29 CFR 1910.140 — personal fall protection systems (general industry)")}</li>
    <li>{src(ASSP, "ANSI/ASSP Z359 Fall Protection Code — ASSP overview")}</li>
    <li>{src(CSA, "CSA Group — Z259 fall protection standards (search “Z259”)")}</li>
  </ul>
  <p class="count">OSHA numbers on this page were checked against the regulation text on {CHECKED}.</p>
</article>
</div>
"""


def write_basics():
    body = BASICS.replace("{HERO}", hero("Explainer", "Basics & standards",
                                         "OSHA fall arrest limits, ANSI/ASSP Z359 classes, fall clearance, swing falls, rescue and inspection — a plain-language summary that points you to the real documents.",
                                         checked=False)).replace("{SAFETY}", safety()).replace("{CRUMBS}", crumbs("Basics & standards"))
    body = body.replace("{CHARTS}", " · ".join(f'<a href="{x["file"]}">{e(short(x))}</a>' for x in SECTIONS) + ' · <a href="compare.html">Compare</a>')
    ld = {"@context": "https://schema.org", "@graph": [
        breadcrumb_ld("Basics & standards", "/basics"),
        {"@type": "FAQPage", "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": plain(a)}} for q, a in FAQ]}]}
    page("basics.html", f"Fall protection basics: OSHA, ANSI Z359 · {SITE}",
         "Plain-language fall protection basics: OSHA 1926.502 and 1910.140 limits, 6 ft and 4 ft trigger heights, ANSI Z359 classes, clearance, rescue and an FAQ.",
         "/basics", "basics.html", body, jsonld=ld)
    print("wrote basics.html")


# ---------------------------------------------------------------- updates / changelog
def changelog(stats):
    c = stats["counts"]
    lines = ", ".join(f"{short(s)} {c[s['slug']]}" for s in SECTIONS)
    return [{
        "month": "November 2026", "iso": SITE_UPDATED_ISO, "date": SITE_UPDATED,
        "title": "SEO and AI-search pass",
        "items": ["SEO and AI-search pass: llms.txt, structured data (Dataset, BreadcrumbList, FAQPage), FAQ on Basics, plain-English intros, robots.txt crawler rules, IndexNow."]},
        {
        "month": "November 2026", "iso": CHECKED_ISO, "date": CHECKED,
        "title": "Initial release",
        "items": [
            f"Initial release with seven catalogs: {lines} — {stats['total']} rows in all.",
            "Added Basics & standards: OSHA 1926.502 / 1910.140 fall arrest limits, trigger heights, ANSI/ASSP Z359 and CSA Z259 overview, fall clearance, swing falls, rescue planning, and inspection — in plain language with links to the official sources.",
            "Added the Compare tool: tick up to four rows from any catalog and view every field, source and link side by side.",
            f"Sourcing: specs come from official manufacturer pages, spec sheets and instruction manuals, plus public retailer listings for the exact part number, checked {CHECKED}. Every row links its source; notes are in our own words.",
            f"Prices: {stats['priced']} rows have a live retailer price with a source link and check date; {stats['estimated']} show an editorial band. {PRICE_RULE}",
            f"Editorial price bands (shown only when no live price was seen): {BANDS}.",
        ]}]


def write_updates(stats):
    log = changelog(stats)
    entries = "".join(
        f'<div class="log"><h2>{e(x["month"])} — {e(x["title"])}</h2><p><time datetime="{x["iso"]}">{x["date"]}</time></p><ul>' +
        "".join(f"<li>{e(i)}</li>" for i in x["items"]) + "</ul></div>" for x in log)
    body = '<div class="wrap" id="main">\n' + crumbs("Updates") + hero("Changelog", "Updates", "A short, plain-English monthly record of what changed on this site.", checked=False)
    body += f'<article class="prose">{entries}</article>\n</div>\n'
    page("updates.html", f"Updates and changelog · {SITE}", f"Changelog for {SITE}: catalogs added, row counts, how the data is sourced, the price rule, and site changes such as structured data and the FAQ.",
         "/updates", "updates.html", body, jsonld={"@context": "https://schema.org", "@graph": [breadcrumb_ld("Updates", "/updates")]})
    md = f"# Changelog\n\nAll notable changes to {SITE}, by month.\n\n"
    for x in log:
        md += f"## {x['month']} — {x['title']} ({x['date']})\n\n" + "".join(f"- {i}\n" for i in x["items"]) + "\n"
    write("CHANGELOG.md", md)
    print("wrote updates.html, CHANGELOG.md")


# ---------------------------------------------------------------- 404, meta, readme
D404 = "That page is not here. It may have moved, or the link has a typo. Try one of the Safety Tool Chart catalogs, the basics page or the compare tool instead."


def write_404():
    pages = [("/", "Home"), *[("/" + s["slug"], short(s)) for s in SECTIONS], ("/basics", "Basics & standards"), ("/compare", "Compare")]
    grid = "".join(f'<a class="card" href="{CANON}{p}"><span class="nm">{e(n)}</span><span class="go">Open →</span></a>' for p, n in pages)
    html = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>Page not found · {SITE}</title>
<meta name="description" content="{e(D404)}">
<meta name="robots" content="noindex">
<link rel="canonical" href="{CANON}/404">
<meta property="og:type" content="website">
<meta property="og:site_name" content="{SITE}">
<meta property="og:locale" content="en_US">
<meta property="og:title" content="Page not found · {SITE}">
<meta property="og:description" content="{e(D404)}">
<meta property="og:url" content="{CANON}/404">
<meta property="og:image" content="{CANON}/og-image.png">
<meta property="og:image:type" content="image/png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="{e(OG_ALT)}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="Page not found · {SITE}">
<meta name="twitter:description" content="{e(D404)}">
<meta name="twitter:image" content="{CANON}/og-image.png">
<meta name="twitter:image:alt" content="{e(OG_ALT)}">
<meta name="theme-color" content="#050d16">
<link rel="icon" href="{CANON}/favicon.ico" sizes="any">
<link rel="icon" href="{CANON}/favicon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="{CANON}/apple-touch-icon.png">
<link rel="stylesheet" href="{FONTS.replace('&', '&amp;')}">
<link rel="stylesheet" href="{CANON}/theme.css?v={ASSET_V}">
<script>
(function(){{var p=location.pathname;if(p.length>1&&p.charAt(p.length-1)==="/")location.replace(p.slice(0,-1)+location.search+location.hash);}})();
</script>
</head>
<body>
<div class="page-bg"></div>
<div class="wrap" id="main">
  <span class="eyebrow">Error 404</span>
  <h1>Page not found</h1>
  <p class="lede">That page is not here. It may have moved, or the link has a typo. Try one of these instead.</p>
  <div class="grid">{grid}</div>
</div>
<footer class="site-footer">
{FOOTER_P}
</footer>
{CF}
</body>
</html>
"""
    write("404.html", html)
    print("wrote 404.html")


BOTS = ["GPTBot", "OAI-SearchBot", "ChatGPT-User", "ClaudeBot", "Claude-SearchBot", "PerplexityBot", "Google-Extended", "Bingbot"]


def llms_texts(sections_items):
    """Returns (llms.txt, llms-full.txt or None). Counts come from the loaded data."""
    allitems = [it for _, i in sections_items for it in i]
    total, brands = len(allitems), brands_of(allitems)
    priced = sum(1 for it in allitems if it["price_usd"] is not None)
    L = [f"# {SITE}", "",
         "> Free, ad-free reference comparing fall protection gear across brands: harnesses, lanyards, SRLs, anchors, connectors, lifelines and rescue equipment, with a source link on every row.", "",
         f"{SITE} lines up the specs that matter (class, capacity, length, connectors, gate strength, standards, price) for {total} products from {len(brands)} brands, "
         "and links each row to the manufacturer or retailer page its facts came from. There are no ads and no affiliate links.", "",
         "## Charts", ""]
    for sec, items in sections_items:
        L.append(f"- [{short(sec)}]({CANON}/{sec['slug']}): {len(items)} rows from {len(brands_of(items))} brands. {sec['card']}")
    L += ["", "## Guides and tools", "",
          f"- [Home]({CANON}/): site search across every product and an overview of all charts",
          f"- [Basics and standards]({CANON}/basics): plain-language OSHA 1926.502 / 1910.140 limits, ANSI/ASSP Z359 and CSA Z259 overview, fall clearance, swing falls, rescue, inspection, and an FAQ",
          f"- [Compare]({CANON}/compare): put up to four products from any chart side by side",
          f"- [Updates]({CANON}/updates): changelog", "",
          "## Totals", "", f"- {total} product rows across {len(sections_items)} charts, {len(brands)} brands in all.",
          f"- {priced} rows show a live retailer price; {total - priced} show an editorial price band.", "",
          "## Sources policy", "",
          "- Facts come from official manufacturer pages, spec sheets and instruction manuals, plus public retailer listings for the exact part number.",
          "- Every row links its source. Notes are written in our own words. Nothing is guessed: a blank cell means the value was not published or not found.",
          f"- Price rule: {PRICE_RULE}", f"- Editorial bands: {BANDS}.", "",
          "## Safety", "", f"{SAFETY}", "",
          "## Data freshness", "", f"Data last checked {CHECKED_ISO}.", ""]
    if HAS_FULL:
        L += ["## Optional", "", f"- [Full product list as plain text]({CANON}/llms-full.txt): one line per row, grouped by chart", ""]
    full = None
    if HAS_FULL:
        F = [f"# {SITE} — full product list", "",
             f"> {total} rows from {len(brands)} brands, grouped by chart. Data last checked {CHECKED_ISO}. Format: brand | model | type | standards | class | capacity lb | price | source.",
             f"> {SAFETY}", ""]
        for sec, items in sections_items:
            F += [f"## {short(sec)} ({len(items)})", ""]
            for it in items:
                cap = ""
                lo, hi = it["cap_min_lb"], it["cap_max_lb"]
                if lo is not None or hi is not None:
                    fmt = lambda v: f"{v:g}"
                    cap = fmt(lo) if hi is None else fmt(hi) if lo is None else (fmt(lo) if lo == hi else f"{fmt(lo)}-{fmt(hi)}")
                price = f"${it['price_usd']:g}" if it["price_usd"] is not None else (f"{it['price_scale']} est." if it["price_scale"] else "")
                model = " ".join(x for x in [it["model"] if it["model"] and (not it["series"] or it["series"] in it["model"]) else f"{it['series'] or ''} {it['model'] or ''}"] if x).strip()
                F.append(" | ".join([it["brand"] or "", model, it["type"] or "", ", ".join(it["standards"]), it["ansi_class"] or "", cap, price, it["spec_url"] or it["product_url"] or ""]))
            F.append("")
        full = "\n".join(F)
    return "\n".join(L), full


def write_meta(sections_items):
    paths = ["/"] + ["/" + s["slug"] for s in SECTIONS] + ["/basics", "/compare", "/updates"]
    sm = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    sm += [f"  <url><loc>{CANON}{p}</loc><lastmod>{SITE_UPDATED_ISO}</lastmod></url>" for p in paths]
    sm.append("</urlset>")
    write("sitemap.xml", "\n".join(sm) + "\n")
    groups = ["User-agent: *\nAllow: /"] + [f"User-agent: {b}\nAllow: /" for b in BOTS]
    write("robots.txt", "\n\n".join(groups) + f"\n\nSitemap: {CANON}/sitemap.xml\n")
    llms, full = llms_texts(sections_items)
    write("llms.txt", llms + "\n")
    if full:
        write("llms-full.txt", full + "\n")
    write(f"{INDEXNOW_KEY}.txt", INDEXNOW_KEY)
    TXT = "  Content-Type: text/plain; charset=utf-8\n"
    write("_headers",
          f"# {CANON.removeprefix('https://')} is the canonical address; other hostnames point search engines here.\n"
          f"/*\n  Link: <{CANON}/:splat>; rel=\"canonical\"\n"
          "  X-Content-Type-Options: nosniff\n"
          "  Referrer-Policy: strict-origin-when-cross-origin\n"
          "  X-Frame-Options: SAMEORIGIN\n"
          f"\n/llms.txt\n{TXT}" + (f"\n/llms-full.txt\n{TXT}" if full else "") + f"\n/{INDEXNOW_KEY}.txt\n{TXT}")
    files = ", ".join(f"`{s['json']}`" for s in SECTIONS)
    write("README.md", f"""# {SITE}

**Live site:** [{CANON}]({CANON})

A free, ad-free, cross-brand reference for personal fall protection gear: full-body harnesses, lanyards, self-retracting lifelines (SRLs), anchors, connectors, horizontal lifelines and rope grabs, and rescue and descent equipment, plus a plain-language basics page (OSHA and ANSI/ASSP Z359) and a compare tool. Plain static HTML, CSS and JavaScript. Cloudflare Pages project name: `safetytoolchart`; **no build command** (the HTML is already generated), output directory = repo root.

There are no ads and no affiliate links. Links go to the manufacturer or retailer page they name.

**Safety:** {SAFETY}

## Local preview

From this folder: `python3 -m http.server`, then open `http://localhost:8000`.

## Regenerate pages

After editing the JSON in `_build/`:

```
python3 _build/generate.py
python3 _build/check.py
```

The site URL is set once as `CANON` in `_build/generate.py` (canonicals, sitemap, Open Graph). `ASSET_V` there cache-busts the CSS/JS. `SITE_UPDATED_ISO` is the sitemap `lastmod` (bump it when the site changes); `CHECKED_ISO` is the data-checked date. The build also writes `robots.txt` (explicit AI-crawler groups), `sitemap.xml`, `llms.txt` and `llms-full.txt` (row counts computed from the data; the full file is only written while it stays under 40 KB), the IndexNow key file (`INDEXNOW_KEY`), and JSON-LD (Dataset, BreadcrumbList, FAQPage) on each page. Chart intros are the `answer` field in `sections.json`. `CF_TOKEN` holds the Cloudflare Web Analytics token; while it is `REPLACE_ME` the beacon is left out. Missing, empty, or unparseable JSON files render as “No rows yet”. `check.py` validates every row and the generated HTML and exits non-zero on errors. For testing, `WP_DATA_DIR` and `WP_OUT_DIR` point the generator (and `WP_DATA_DIR` the checker) at other folders.

## Data rules

Rows live in {files} (all in `_build/`); section titles, columns and filters are in `_build/sections.json`. The schema, the single price rule, and the hard rules (facts only from official pages and public listings, a source link on every row, no invented numbers, no copied marketing text, no affiliate or tracking parameters) are in [`_build/SCHEMA.md`](_build/SCHEMA.md). After changing facts, update the monthly entry in `changelog()` in `generate.py` (this regenerates `CHANGELOG.md` and `updates.html`).

Brand logos: see [`icons/README.md`](icons/README.md). Brands without an official icon appear as text badges. Site art (hero, favicon, Open Graph image) is drawn by `_build/make_assets.py` and `_build/hero.svg`.
""")
    if not (ROOT / "icons" / "README.md").exists():  # hand-maintained once icons exist
        write("icons/README.md", """# Brand icons

Drop a brand's **official** mark here as `<brand-slug>.svg` or `<brand-slug>.png` (for example `msa.svg`, `3m-dbi-sala.png`; the slug is the brand name lower-cased with non-alphanumerics replaced by `-`). The generator picks it up automatically on the next run.

Rules:
- Only official brand marks from the manufacturer's own brand/press/media page. No recreated, traced, or third-party logos.
- List the source URL for every file in the table below.
- Until an icon exists for a brand, the site shows a plain text badge with the brand name.

| File | Brand | Source URL |
| --- | --- | --- |
| _(none yet — text badges are used)_ | | |
""")
    print("wrote sitemap, robots, _headers, README, icons/README.md")


def main():
    global HAS_FULL
    sections_items = [(s, load_section(s)) for s in SECTIONS]
    HAS_FULL = True
    _, full = llms_texts(sections_items)
    HAS_FULL = bool(full) and len(full.encode("utf-8")) < 40000
    print(f"llms-full.txt: {len(full.encode('utf-8')) // 1} bytes, {'written' if HAS_FULL else 'skipped (too big)'}")
    counts = {s["slug"]: len(i) for s, i in sections_items}
    allitems = [it for _, i in sections_items for it in i]
    priced = sum(1 for it in allitems if it["price_usd"] is not None)
    stats = {"counts": counts, "total": len(allitems), "priced": priced, "estimated": len(allitems) - priced}
    for s, i in sections_items:
        write_section(s, i)
    write_home(sections_items)
    write_compare(sections_items)
    write_basics()
    write_updates(stats)
    write_404()
    write_meta(sections_items)
    print("DONE", stats)


if __name__ == "__main__":
    main()
