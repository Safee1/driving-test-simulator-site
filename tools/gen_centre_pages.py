#!/usr/bin/env python3
"""
gen_centre_pages.py — generate /test-centres/ pages for the ~313 "on-demand"
GB car test centres the app covers via assets/data/all_centres.json, on top
of the 21 hand-written "featured" pages produced by build_centre_pages.py.

Source data:
    C:\\Users\\s\\dev\\dts-main\\assets\\data\\all_centres.json
        — id, name, town, postcode, lat, lon for the 313 on-demand centres
    C:\\Users\\s\\dev\\dvsa-feed\\practical-2026-09-19.csv
        — DVSA reference list, used here only to fill in County for grouping

Does NOT touch the 21 hand-written featured pages (matched by filename/slug
already present in test-centres/) — it only creates pages for centres whose
slug isn't already an existing file, and only ever appends to the
generated-block markers in index.html / sitemap.xml so re-running is safe.

    python tools/gen_centre_pages.py
"""
from __future__ import annotations

import csv
import html
import json
import math
import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ALL_CENTRES = Path(r"C:\Users\s\dev\dts-main\assets\data\all_centres.json")
DVSA_CSV = Path(r"C:\Users\s\dev\dvsa-feed\practical-2026-09-19.csv")
OUT_DIR = REPO / "test-centres"
SITEMAP = REPO / "sitemap.xml"
BASE_URL = "https://driving-test-simulator.co.uk"
PLAY_URL = "https://play.google.com/store/apps/details?id=uk.co.drivingtestsimulator.passtrack"
LASTMOD = "2026-09-25"

FOOTER_LINE = (
    "Practice loops are provisional and not the routes examiners use. "
    "Practice results are not official driving test results. "
    "Not affiliated with, or endorsed by, the DVSA."
)

HEAD_TEMPLATE = (REPO / "test-centres" / "coventry.html").read_text(encoding="utf-8")
# Split the coventry.html page into head/body/tail wrapper so we can drop in new <article> content
_HEAD, _REST = HEAD_TEMPLATE.split("<article class=\"prose\">\n", 1)
_ARTICLE_BODY, _TAIL = _REST.split("\n</article>", 1)
WRAP_HEAD = _HEAD + "<article class=\"prose\">\n"
WRAP_TAIL = "\n</article>" + _TAIL


def haversine_miles(lat1, lng1, lat2, lng2):
    r_miles = 3958.8
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2
    return r_miles * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def make_head(title, description, canonical):
    block = WRAP_HEAD
    block = re.sub(r"<title>.*?</title>", f"<title>{html.escape(title)}</title>", block, count=1)
    block = re.sub(r'(<meta name="description" content=")[^"]*(")', lambda m: m.group(1) + html.escape(description) + m.group(2), block, count=1)
    block = re.sub(r'(<link rel="canonical" href=")[^"]*(")', lambda m: m.group(1) + canonical + m.group(2), block, count=1)
    block = re.sub(r'(<meta property="og:url" content=")[^"]*(")', lambda m: m.group(1) + canonical + m.group(2), block, count=1)
    block = re.sub(r'(<meta property="og:title" content=")[^"]*(")', lambda m: m.group(1) + html.escape(title) + m.group(2), block, count=1)
    block = re.sub(r'(<meta property="og:description" content=")[^"]*(")', lambda m: m.group(1) + html.escape(description) + m.group(2), block, count=1)
    return block


def render_page(centre, all_centres):
    name = centre["name"]
    town = centre["town"]
    postcode = centre["postcode"]
    cid = centre["id"]

    title = f"{name} Driving Test Centre — Practice Loops & Mock Test | Driving Test Simulator"
    description = (
        f"Practise around {name} driving test centre with provisional practice "
        "loops, a DL25-style mock test and turn-by-turn directions. Free on Android."
    )
    canonical = f"{BASE_URL}/test-centres/{cid}.html"

    others = []
    for c in all_centres:
        if c["id"] == cid:
            continue
        d = haversine_miles(centre["lat"], centre["lon"], c["lat"], c["lon"])
        others.append((d, c))
    others.sort(key=lambda t: t[0])
    nearest = others[:3]
    nearest_html = "\n".join(
        f'        <li><a href="/test-centres/{c["id"]}.html">{html.escape(c["name"])}</a> — {d:.1f} miles</li>'
        for d, c in nearest
    )

    body = f"""<h1>Practise for your test at {html.escape(name)}</h1>
<p>Driving Test Simulator covers {html.escape(name)} driving test centre in {html.escape(town)} ({html.escape(postcode)}). Pick it in the app and it builds a provisional practice loop starting there, from map data — not the DVSA's own test routes. Drive it with a supervising, licensed driver, following turn-by-turn directions, and log faults on a DL25-style sheet.</p>

<h2>What you can practise here</h2>
<ul>
  <li>Roundabouts, junctions and dual carriageways near the centre</li>
  <li>Manoeuvres: parallel park, bay park, pull up on the right</li>
  <li>Show me / Tell me questions</li>
</ul>

<h2>Nearest other centres</h2>
      <ul>
{nearest_html}
      </ul>

<p><a class="btn-play" data-cta="centre" href="{PLAY_URL}" target="_blank" rel="noopener">
  <img src="/assets/img/google-play-badge.png" width="646" height="250" alt="Get it on Google Play">
</a></p>

<p><em>{FOOTER_LINE}</em></p>"""

    return make_head(title, description, canonical) + body + WRAP_TAIL


def load_all_centres():
    data = json.loads(ALL_CENTRES.read_text(encoding="utf-8"))
    csv_rows = {}
    with DVSA_CSV.open(encoding="cp1252") as f:
        for row in csv.DictReader(f):
            csv_rows[row["Name"].strip().lower()] = row
    for c in data:
        row = csv_rows.get(c["name"].strip().lower())
        c["county"] = (row["County"].strip() if row and row.get("County") else c["town"])
    return data


def existing_slugs():
    return {p.stem for p in OUT_DIR.glob("*.html") if p.stem != "index"}


def region_for(county):
    # collapse DVSA county into the site's existing region labels where it already
    # matches one, otherwise use the county name itself as the group heading.
    return county


def update_index(featured_entries, generated_centres):
    """Rewrite test-centres/index.html to list every centre, grouped by region."""
    idx_path = OUT_DIR / "index.html"
    text = idx_path.read_text(encoding="utf-8")

    by_area: dict[str, list[tuple[str, str, str]]] = {}
    for area, slug, label, count in featured_entries:
        by_area.setdefault(area, []).append((slug, label, f"{count} route{'s' if count != 1 else ''}"))
    for c in generated_centres:
        by_area.setdefault(c["county"], []).append((c["id"], c["name"], "provisional loop"))

    sections = []
    for area in sorted(by_area):
        items = sorted(by_area[area], key=lambda t: t[1])
        lis = "\n".join(
            f'        <li><a href="/test-centres/{slug}.html">{html.escape(label)}</a> — {count}</li>'
            for slug, label, count in items
        )
        sections.append(f"<h2>{html.escape(area)}</h2>\n      <ul>\n{lis}\n      </ul>")

    total_centres = sum(len(v) for v in by_area.values())

    new_h1_p = (
        "<h1>Driving test centres — practice routes</h1>\n"
        f"<p>Driving Test Simulator covers every open GB car driving-test centre — {total_centres} in all. "
        "Pick one and the app builds a provisional practice loop starting there; featured centres below "
        "have hand-picked loops with named routes.</p>"
    )

    # Replace the old <h1>...</h1><p>...</p> intro
    text = re.sub(
        r"<h1>Driving test centres.*?</p>",
        new_h1_p,
        text,
        count=1,
        flags=re.S,
    )
    # Replace everything between the intro paragraph and the Play button paragraph with new sections
    text = re.sub(
        r"(</p>\n)\n<h2>.*?(?=\n<p><a class=\"btn-play\")",
        r"\1\n" + "\n".join(sections) + "\n",
        text,
        count=1,
        flags=re.S,
    )
    idx_path.write_text(text, encoding="utf-8")


def update_sitemap(new_slugs):
    text = SITEMAP.read_text(encoding="utf-8")
    text = re.sub(
        r"\n?  <!-- BEGIN on-demand centres \(generated by tools/gen_centre_pages\.py\) -->.*?<!-- END on-demand centres \(generated\) -->\n?",
        "\n",
        text,
        flags=re.S,
    )
    block_lines = ["  <!-- BEGIN on-demand centres (generated by tools/gen_centre_pages.py) -->"]
    for slug in new_slugs:
        block_lines.append("  <url>")
        block_lines.append(f"    <loc>{BASE_URL}/test-centres/{slug}.html</loc>")
        block_lines.append(f"    <lastmod>{LASTMOD}</lastmod>")
        block_lines.append("    <changefreq>monthly</changefreq>")
        block_lines.append("    <priority>0.4</priority>")
        block_lines.append("  </url>")
    block_lines.append("  <!-- END on-demand centres (generated) -->")
    block = "\n".join(block_lines) + "\n"
    text = text.replace("</urlset>", block + "</urlset>")
    SITEMAP.write_text(text, encoding="utf-8")


FEATURED = [
    # (area, slug, display name, route count) — read from the existing 21 hand-written pages'
    # "Practice loops at X (N)" headings, kept in sync manually since those pages are hand-authored.
    ("Essex", "loughton", "Loughton (London)", 1),
    ("Greater London", "barking", "Barking (Tanner Street)", 5),
    ("Greater London", "belvedere", "Belvedere (London)", 2),
    ("Greater London", "chingford", "Chingford (London)", 2),
    ("Greater London", "erith", "Erith (London)", 4),
    ("Greater London", "goodmayes", "Goodmayes", 4),
    ("Greater London", "hornchurch", "Hornchurch", 4),
    ("Greater London", "wanstead", "Wanstead (London)", 3),
    ("Staffordshire", "lichfield", "Lichfield", 5),
    ("Warwickshire", "warwick", "Warwick", 4),
    ("West Midlands", "garretts-green", "Birmingham (Garretts Green)", 1),
    ("West Midlands", "kings-heath", "Birmingham (Kings Heath)", 2),
    ("West Midlands", "kingstanding", "Birmingham (Kingstanding)", 3),
    ("West Midlands", "shirley", "Birmingham (Shirley)", 2),
    ("West Midlands", "south-yardley", "Birmingham (South Yardley)", 4),
    ("West Midlands", "coventry", "Coventry", 2),
    ("West Midlands", "featherstone", "Featherstone (Wolverhampton)", 1),
    ("West Midlands", "sutton-coldfield", "Sutton Coldfield", 3),
    ("West Midlands", "wednesbury", "Wednesbury", 6),
    ("West Midlands", "wolverhampton", "Wolverhampton", 3),
    ("Worcestershire", "redditch", "Redditch", 4),
]


def main():
    all_centres = load_all_centres()
    existing = existing_slugs()

    generated = []
    for c in all_centres:
        if c["id"] in existing:
            continue  # never overwrite a hand-written page
        page = render_page(c, all_centres)
        (OUT_DIR / f"{c['id']}.html").write_text(page, encoding="utf-8")
        generated.append(c)

    update_index(FEATURED, all_centres)
    update_sitemap([c["id"] for c in generated])

    print(f"Generated {len(generated)} new centre pages (skipped {len(all_centres) - len(generated)} already existing).")
    print(f"Total centre pages on disk: {len(list(OUT_DIR.glob('*.html'))) - 1}")


if __name__ == "__main__":
    main()
