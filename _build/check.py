#!/usr/bin/env python3
"""Consistency checker for Safety Tool Chart.

1. Validates every row in the section JSON files (list in _build/sections.json).
2. Scans the generated HTML in the site root for forbidden wording and required tags.

Prints WARN / ERROR lines and exits 1 if there is any ERROR.
Env: WP_DATA_DIR (JSON folder, default _build), WP_OUT_DIR (HTML folder, default repo root).
"""
import json, os, re, sys
from pathlib import Path
from urllib.parse import urlparse, parse_qsl

ROOT = Path(__file__).resolve().parent.parent
BUILD = ROOT / "_build"
DATA_DIR = Path(os.environ.get("WP_DATA_DIR") or BUILD)
OUT = Path(os.environ.get("WP_OUT_DIR") or ROOT)

NUMERIC = ["cap_min_lb", "cap_max_lb", "length_ft", "weight_lb", "gate_lbf", "price_usd"]
URL_FIELDS = ["product_url", "spec_url", "price_url"]
# Values that must agree when the same model number appears in more than one file.
SHARED = ["brand", "series", "standards", "ansi_class", "cap_min_lb", "cap_max_lb", "length_ft", "weight_lb",
          "attachment", "gate_lbf", "material", "sizes", "price_usd", "price_source", "price_url", "price_checked",
          "price_scale", "product_url", "spec_url"]
BANDS = {"$", "$$", "$$$", "$$$$", "$$$$$"}
TRACK_KEYS = re.compile(r"^(tag|ref|ref_?id|aff.*|affiliate.*|utm_.*|gclid|fbclid|msclkid|irclickid|clickid|cjevent|ranmid|ransiteid|sub_?id|mc_[ce]id)$", re.I)
TRACK_PATH = re.compile(r"(/ref=|[?&]aff|affiliate|/aff/|go\.redirectingat|click\.linksynergy|anrdoezrs|jdoqocy|tkqlhce|dpbolvw|awin1|shareasale|avantlink)", re.I)
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
FORBIDDEN = [r"affiliat(?!e links?\b)", r"side project", r"work hours", r"employer"]  # "No affiliate links" is allowed
SAFETY_MARK = "Reference only"
KOFI = "https://ko-fi.com/marcustravis"

errors, warns = [], []


def err(msg): errors.append(msg)
def warn(msg): warns.append(msg)


def is_num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def check_url(where, field, u):
    if u is None:
        return
    if not isinstance(u, str) or not u.strip():
        err(f"{where}: {field} is not a non-empty string")
        return
    p = urlparse(u)
    if p.scheme != "https" or not p.netloc:
        err(f"{where}: {field} must be an https URL: {u}")
    bad = [k for k, _ in parse_qsl(p.query, keep_blank_values=True) if TRACK_KEYS.match(k)]
    if bad:
        err(f"{where}: {field} has tracking/affiliate parameter(s) {bad}: {u}")
    if TRACK_PATH.search(u):
        err(f"{where}: {field} looks like an affiliate/tracking link: {u}")


def norm_model(m):
    return re.sub(r"[^a-z0-9]", "", str(m).lower())


def check_rows():
    sections = json.loads((BUILD / "sections.json").read_text(encoding="utf-8"))
    ids, models, total = {}, {}, 0
    for sec in sections:
        path = DATA_DIR / sec["json"]
        if not path.exists():
            warn(f"{sec['json']}: missing (renders empty)")
            continue
        txt = path.read_text(encoding="utf-8").strip()
        if not txt:
            warn(f"{sec['json']}: empty file")
            continue
        try:
            rows = json.loads(txt)
        except Exception as ex:
            err(f"{sec['json']}: invalid JSON ({ex})")
            continue
        if not isinstance(rows, list):
            err(f"{sec['json']}: top level must be a JSON array")
            continue
        for i, r in enumerate(rows):
            total += 1
            where = f"{sec['json']}[{i}]"
            if not isinstance(r, dict):
                err(f"{where}: row is not an object"); continue
            where = f"{sec['json']}[{i}] {r.get('id') or ''}".strip()
            for k in ("brand", "model", "type"):
                if not (isinstance(r.get(k), str) and r[k].strip()):
                    err(f"{where}: required field '{k}' missing/empty")
            if not (r.get("spec_url") or r.get("product_url")):
                err(f"{where}: needs spec_url or product_url (every row must show a source)")
            if not r.get("spec_url"):
                warn(f"{where}: no spec_url (product_url used as source)")
            rid = r.get("id")
            if not (isinstance(rid, str) and rid.strip()):
                err(f"{where}: id missing")
            elif rid in ids:
                err(f"{where}: duplicate id '{rid}' (also in {ids[rid]})")
            else:
                ids[rid] = where
                if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", rid):
                    warn(f"{where}: id is not kebab-case")
            for k in NUMERIC:
                v = r.get(k)
                if v is not None and not is_num(v):
                    err(f"{where}: {k} must be a number or null, got {v!r}")
                elif is_num(v) and v < 0:
                    err(f"{where}: {k} is negative")
            lo, hi = r.get("cap_min_lb"), r.get("cap_max_lb")
            if is_num(lo) and is_num(hi) and lo > hi:
                err(f"{where}: cap_min_lb {lo} > cap_max_lb {hi}")
            st = r.get("standards")
            if st is not None and not (isinstance(st, list) and all(isinstance(x, str) for x in st)):
                err(f"{where}: standards must be a list of strings")
            for k in URL_FIELDS:
                check_url(where, k, r.get(k))
            if r.get("price_usd") is not None:
                for k in ("price_source", "price_url", "price_checked"):
                    if not r.get(k):
                        err(f"{where}: price_usd set but {k} missing")
                pc = r.get("price_checked")
                if pc and not DATE.match(str(pc)):
                    err(f"{where}: price_checked must be YYYY-MM-DD, got {pc!r}")
                if r.get("price_scale"):
                    warn(f"{where}: price_scale should be null when price_usd is set")
            else:
                if not r.get("price_scale"):
                    err(f"{where}: price_usd is null so price_scale is required")
                elif r["price_scale"] not in BANDS:
                    err(f"{where}: price_scale must be one of $..$$$$$, got {r['price_scale']!r}")
            if r.get("model"):
                key = (str(r.get("brand") or "").lower(), norm_model(r["model"]))
                models.setdefault(key, []).append((sec["json"], where, r))
    # same model number in more than one file → shared values must match
    for key, occ in models.items():
        files = {f for f, _, _ in occ}
        if len(files) < 2:
            if len(occ) > 1:
                warn(f"model {key[1]!r} ({key[0]}) appears {len(occ)} times in {occ[0][0]}")
            continue
        base_where, base = occ[0][1], occ[0][2]
        for _, w, r in occ[1:]:
            for k in SHARED:
                if r.get(k) != base.get(k):
                    err(f"model {r['model']!r} in {w} and {base_where}: '{k}' differs ({r.get(k)!r} vs {base.get(k)!r})")
    return total


def check_html():
    pages = sorted(OUT.glob("*.html"))
    if not pages:
        err(f"no HTML found in {OUT}")
    for p in pages:
        t = p.read_text(encoding="utf-8")
        plain = re.sub(r"<script\b[^>]*>.*?</script>", " ", t, flags=re.S | re.I)  # data blobs are checked as rows
        for pat in FORBIDDEN:
            m = re.search(pat, plain, re.I)
            if m:
                ctx = plain[max(0, m.start() - 40):m.end() + 40].replace("\n", " ")
                err(f"{p.name}: forbidden wording /{pat}/ … {ctx} …")
        if not re.search(r'<link rel="canonical" href="https://', t):
            err(f"{p.name}: missing canonical link")
        if 'property="og:title"' not in t:
            err(f"{p.name}: missing og:title")
        if not re.search(r'<footer[^>]*>.*?' + re.escape(SAFETY_MARK) + r'.*?</footer>', t, re.S):
            err(f"{p.name}: footer safety line missing")
        if KOFI not in t:
            err(f"{p.name}: ko-fi link missing")
        if "REPLACE_ME" in t:
            err(f"{p.name}: contains a REPLACE_ME placeholder")
        for u in re.findall(r'href="(https?://[^"]+)"', t):
            check_url(p.name, "href", u.replace("&amp;", "&"))
    return len(pages)


def main():
    n_rows = check_rows()
    n_pages = check_html()
    for w in warns:
        print("WARN ", w)
    for x in errors:
        print("ERROR", x)
    print(f"checked {n_rows} rows and {n_pages} HTML pages: {len(errors)} error(s), {len(warns)} warning(s)")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
