# Safety Tool Chart

**Live site:** [https://safetytoolchart.pages.dev](https://safetytoolchart.pages.dev)

A free, ad-free, cross-brand reference for personal fall protection gear: full-body harnesses, lanyards, self-retracting lifelines (SRLs), anchors, connectors, horizontal lifelines and rope grabs, and rescue and descent equipment, plus a plain-language basics page (OSHA and ANSI/ASSP Z359) and a compare tool. Plain static HTML, CSS and JavaScript. Cloudflare Pages project name: `safetytoolchart`; **no build command** (the HTML is already generated), output directory = repo root.

There are no ads and no affiliate links. Links go to the manufacturer or retailer page they name.

**Safety:** Reference only — not training and not a substitute for the manufacturer’s instructions, a competent person, or OSHA/ANSI requirements. Inspect gear before each use, remove from service any equipment that has arrested a fall, and verify specs with the manufacturer.

## Local preview

From this folder: `python3 -m http.server`, then open `http://localhost:8000`.

## Regenerate pages

After editing the JSON in `_build/`:

```
python3 _build/generate.py
python3 _build/check.py
```

The site URL is set once as `CANON` in `_build/generate.py` (canonicals, sitemap, Open Graph). `ASSET_V` there cache-busts the CSS/JS. `CF_TOKEN` holds the Cloudflare Web Analytics token; while it is `REPLACE_ME` the beacon is left out. Missing, empty, or unparseable JSON files render as “No rows yet”. `check.py` validates every row and the generated HTML and exits non-zero on errors. For testing, `WP_DATA_DIR` and `WP_OUT_DIR` point the generator (and `WP_DATA_DIR` the checker) at other folders.

## Data rules

Rows live in `harnesses.json`, `lanyards.json`, `srls.json`, `anchors.json`, `connectors.json`, `lifelines.json`, `rescue.json` (all in `_build/`); section titles, columns and filters are in `_build/sections.json`. The schema, the single price rule, and the hard rules (facts only from official pages and public listings, a source link on every row, no invented numbers, no copied marketing text, no affiliate or tracking parameters) are in [`_build/SCHEMA.md`](_build/SCHEMA.md). After changing facts, update the monthly entry in `changelog()` in `generate.py` (this regenerates `CHANGELOG.md` and `updates.html`).

Brand logos: see [`icons/README.md`](icons/README.md). Brands without an official icon appear as text badges. Site art (hero, favicon, Open Graph image) is drawn by `_build/make_assets.py` and `_build/hero.svg`.
