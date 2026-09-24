#!/usr/bin/env python3
"""
build_centre_pages.py — generate the /centres/ pages for
driving-test-simulator.co.uk from real app data.

Source data: tools/centre_data.json, a one-time dump of kPilotCentres and
routesForCentre() from the app's lib/features/routes/route_model.dart
(dts-main is READ-ONLY — this file is a throwaway `flutter test` dump, not a
live link. Re-run the dump and refresh centre_data.json if the app's centre
or route list changes).

Produces:
    centres/<centre-id>.html   one page per centre
    centres/index.html         index grouped by area
    sitemap.xml                updated in place with the 22 new URLs

Re-running this script is safe and idempotent — it only touches the
centres/ directory and the <url> block it owns in sitemap.xml.

    python tools/build_centre_pages.py
"""

from __future__ import annotations

import html
import json
import math
import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DATA = REPO / "tools" / "centre_data.json"
OUT_DIR = REPO / "centres"
SITEMAP = REPO / "sitemap.xml"
BASE_URL = "https://driving-test-simulator.co.uk"
PLAY_URL = "https://play.google.com/store/apps/details?id=uk.co.drivingtestsimulator.passtrack"
LASTMOD = "2026-09-24"

BANNED_PHRASES = [
    "verified",
    "checked and dated",
    "real test routes",
    "dvsa standard",
    "official",
    "passtrack",
    "guarantee",
    "pass first time",
]


def haversine_miles(lat1, lng1, lat2, lng2):
    r_miles = 3958.8
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2
    return r_miles * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


HEAD_TEMPLATE = """<!DOCTYPE html>
<html lang="en-GB" class="no-js">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">

<!-- Consent Mode v2 defaults. Runs before anything else on the page. -->
<script>
window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments);}}
gtag('consent','default',{{ad_storage:'denied',ad_user_data:'denied',ad_personalization:'denied',analytics_storage:'denied',functionality_storage:'denied',security_storage:'granted'}});
document.documentElement.classList.remove('no-js');
</script>

<title>{title}</title>
<meta name="description" content="{description}">
<link rel="canonical" href="{canonical}">

<meta property="og:type" content="website">
<meta property="og:site_name" content="Driving Test Simulator">
<meta property="og:locale" content="en_GB">
<meta property="og:url" content="{canonical}">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{description}">
<meta property="og:image" content="{base}/assets/img/og-image.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="Your driving test, rehearsed. Free mock driving tests on Android.">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:image" content="{base}/assets/img/og-image.png">
<meta name="twitter:image:alt" content="Your driving test, rehearsed. Free mock driving tests on Android.">

<link rel="icon" href="/favicon.ico" sizes="any">
<link rel="icon" type="image/png" sizes="32x32" href="/favicon-32.png">
<link rel="icon" type="image/png" sizes="16x16" href="/favicon-16.png">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<meta name="theme-color" content="#1D70B8">

<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:wght@700;800&amp;family=Manrope:wght@500;700&amp;display=swap">
<link rel="stylesheet" href="/assets/site.css">
</head>
<body>
<a class="skip" href="#main">Skip to content</a>

<header class="site-header">
  <div class="wrap">
    <a class="brand-lockup" href="/">
      <span class="mark">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" aria-hidden="true"><circle cx="12" cy="12" r="9"/><line x1="12" y1="9.8" x2="12" y2="3"/><line x1="10.1" y1="13.1" x2="4.21" y2="16.5"/><line x1="13.9" y1="13.1" x2="19.79" y2="16.5"/><circle cx="12" cy="12" r="2.2" fill="currentColor" stroke="none"/></svg>
      </span>
      Driving Test<br>Simulator
    </a>

    <nav class="site-nav" aria-label="Main">
      <ul>
        <li><a href="/#learners">Learners</a></li>
        <li><a href="/#instructors">Instructors</a></li>
        <li><a href="/#how">How it works</a></li>
        <li><a href="/#faq">FAQ</a></li>
        <li><a href="/centres/">Test centres</a></li>
      </ul>
    </nav>

    <div class="header-cta">
      <a class="btn-play" data-cta="nav" href="{play}" target="_blank" rel="noopener">
        <img src="/assets/img/google-play-badge.png" width="646" height="250" alt="Get it on Google Play">
      </a>
      <a class="btn header-cta-text" data-cta="nav" href="{play}" target="_blank" rel="noopener">Get the app</a>
    </div>
  </div>
</header>

<main id="main">
<div class="wrap">
<article class="prose">

{body}

</article>
</div>
</main>

<footer class="footer">
  <div class="wrap">
    <div class="footer-grid">
      <div>
        <span class="brand-lockup">
          <span class="mark">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" aria-hidden="true"><circle cx="12" cy="12" r="9"/><line x1="12" y1="9.8" x2="12" y2="3"/><line x1="10.1" y1="13.1" x2="4.21" y2="16.5"/><line x1="13.9" y1="13.1" x2="19.79" y2="16.5"/><circle cx="12" cy="12" r="2.2" fill="currentColor" stroke="none"/></svg>
          </span>
          Driving Test<br>Simulator
        </span>
        <p class="foot-blurb">A training aid for learner drivers and instructors. Practice results are not official driving test results, and we are not affiliated with or endorsed by the DVSA.</p>
      </div>

      <div>
        <h2>Legal</h2>
        <ul>
          <li><a href="/privacy.html">Privacy policy</a></li>
          <li><a href="/terms.html">Terms of Service</a></li>
          <li><a href="/delete-account.html">Delete your account</a></li>
          <li><a href="/support.html">Support</a></li>
          <li><button type="button" class="linklike" data-consent-settings>Cookie settings</button></li>
        </ul>
      </div>

      <div>
        <h2>Contact</h2>
        <ul>
          <li><a href="mailto:info@rds-hub-ltd.co.uk">info@rds-hub-ltd.co.uk</a></li>
          <li><a href="{play}" data-cta="footer" target="_blank" rel="noopener">Get it on Google Play</a></li>
        </ul>
      </div>
    </div>

    <div class="footer-legal">
      <p>© RDS HUB LTD · Company no. 16285288 · 6 Exeter Place, Walsall, WS2 9UQ, England &amp; Wales</p>
      <p>Google Play and the Google Play logo are trademarks of Google LLC.</p>
    </div>
  </div>
</footer>

<aside id="consent" aria-label="Cookie choices" aria-live="polite" hidden>
  <h2>Cookies, only if you say so.</h2>
  <p>We'd like to use Google Analytics and Google Ads cookies to see how people find this site and whether our adverts work. Nothing runs until you choose.</p>
  <div class="consent-actions">
    <button type="button" class="btn" id="consent-accept">Accept</button>
    <button type="button" class="btn btn--ghost" id="consent-reject">Reject</button>
    <a class="consent-more" href="/privacy.html#cookies">How we use cookies</a>
  </div>
</aside>

<script src="/assets/site.js" defer></script>
</body>
</html>
"""

FOOTER_LINE = (
    "Practice results are not official driving test results. "
    "Not affiliated with, or endorsed by, the DVSA."
)


def render_page(centre, all_centres, routes_by_id):
    name = centre["name"]
    cid = centre["id"]
    n_routes = len(routes_by_id[cid])
    route_names = [r["name"] for r in routes_by_id[cid]]

    title = f"{name} driving test centre – practice routes | Driving Test Simulator"
    description = (
        f"Practise for your driving test at {name}: {n_routes} provisional "
        f"practice loop{'s' if n_routes != 1 else ''} around the test centre, "
        "sat-nav guidance and DL25-style marking. Free on Android."
    )
    canonical = f"{BASE_URL}/centres/{cid}.html"

    # nearest 3 centres by great-circle distance
    others = []
    for c in all_centres:
        if c["id"] == cid:
            continue
        d = haversine_miles(centre["lat"], centre["lng"], c["lat"], c["lng"])
        others.append((d, c))
    others.sort(key=lambda t: t[0])
    nearest = others[:3]

    if route_names:
        route_list_html = "<ul>\n" + "\n".join(
            f"        <li>{html.escape(rn)}</li>" for rn in route_names
        ) + "\n      </ul>"
    else:
        route_list_html = "<p>No practice loops are published for this centre yet — check back soon.</p>"

    nearest_html = "<ul>\n" + "\n".join(
        f'        <li><a href="/centres/{c["id"]}.html">{html.escape(c["name"])}</a> — {d:.1f} miles</li>'
        for d, c in nearest
    ) + "\n      </ul>"

    body = f"""<h1>{html.escape(name)} driving test centre — practice routes</h1>
<p>Getting ready for your practical test at {html.escape(name)}? Driving Test Simulator has {n_routes} provisional practice loop{'s' if n_routes != 1 else ''} built around this test centre, so you can rehearse the kind of roads, junctions and roundabouts you're likely to meet on the day.</p>

<h2>Practice loops at {html.escape(name)}</h2>
<p>{n_routes} provisional practice loop{'s' if n_routes != 1 else ''} around {html.escape(name)} test centre, built from map data — not the examiner's own routes, and not yet driven and checked on the road:</p>
      {route_list_html}

<h2>How to practise</h2>
<ol>
  <li>Open the Driving Test Simulator app and pick {html.escape(name)} from the list of test centres.</li>
  <li>Choose a practice loop, or start a DL25-style mock test.</li>
  <li>Drive only with a supervising driver in the car who can override the app's directions at any point — these are provisional loops, not routes that have been driven and checked.</li>
</ol>

<h2>Nearest other centres</h2>
      {nearest_html}

<p><a class="btn-play" data-cta="centre" href="{PLAY_URL}" target="_blank" rel="noopener">
  <img src="/assets/img/google-play-badge.png" width="646" height="250" alt="Get it on Google Play">
</a></p>

<p><em>{FOOTER_LINE}</em></p>"""

    return HEAD_TEMPLATE.format(
        title=html.escape(title),
        description=html.escape(description),
        canonical=canonical,
        base=BASE_URL,
        play=PLAY_URL,
        body=body,
    )


def render_index(all_centres, routes_by_id):
    title = "Test centres – Driving Test Simulator"
    description = (
        "Every test centre covered by Driving Test Simulator's provisional "
        "practice loops, grouped by area, with route counts. Free on Android."
    )
    canonical = f"{BASE_URL}/centres/"

    by_area: dict[str, list] = {}
    for c in all_centres:
        by_area.setdefault(c["area"], []).append(c)

    sections = []
    for area in sorted(by_area):
        centres = sorted(by_area[area], key=lambda c: c["name"])
        items = "\n".join(
            f'        <li><a href="/centres/{c["id"]}.html">{html.escape(c["name"])}</a> '
            f'— {len(routes_by_id[c["id"]])} route{"s" if len(routes_by_id[c["id"]]) != 1 else ""}</li>'
            for c in centres
        )
        sections.append(f"<h2>{html.escape(area)}</h2>\n      <ul>\n{items}\n      </ul>")

    total_routes = sum(len(v) for v in routes_by_id.values())
    body = f"""<h1>Driving test centres — practice routes</h1>
<p>Driving Test Simulator has {total_routes} provisional practice loops across {len(all_centres)} UK driving test centres. Pick a centre below to see its loops, or open the app to start practising.</p>

{chr(10).join(sections)}

<p><a class="btn-play" data-cta="centres-index" href="{PLAY_URL}" target="_blank" rel="noopener">
  <img src="/assets/img/google-play-badge.png" width="646" height="250" alt="Get it on Google Play">
</a></p>

<p><em>{FOOTER_LINE}</em></p>"""

    return HEAD_TEMPLATE.format(
        title=html.escape(title),
        description=html.escape(description),
        canonical=canonical,
        base=BASE_URL,
        play=PLAY_URL,
        body=body,
    )


def update_sitemap(centre_ids):
    text = SITEMAP.read_text(encoding="utf-8")
    # Remove any previously generated centres block (idempotent re-run)
    text = re.sub(
        r"\n?  <!-- BEGIN centres \(generated by tools/build_centre_pages\.py\) -->.*?<!-- END centres \(generated\) -->\n?",
        "\n",
        text,
        flags=re.S,
    )

    urls = [("/centres/", "monthly", "0.6")] + [
        (f"/centres/{cid}.html", "monthly", "0.5") for cid in centre_ids
    ]
    block_lines = ["  <!-- BEGIN centres (generated by tools/build_centre_pages.py) -->"]
    for path, changefreq, priority in urls:
        block_lines.append("  <url>")
        block_lines.append(f"    <loc>{BASE_URL}{path}</loc>")
        block_lines.append(f"    <lastmod>{LASTMOD}</lastmod>")
        block_lines.append(f"    <changefreq>{changefreq}</changefreq>")
        block_lines.append(f"    <priority>{priority}</priority>")
        block_lines.append("  </url>")
    block_lines.append("  <!-- END centres (generated) -->")
    block = "\n".join(block_lines) + "\n"

    text = text.replace("</urlset>", block + "</urlset>")
    SITEMAP.write_text(text, encoding="utf-8")


def scan_banned_phrases(paths):
    hits = []
    footer_lower = FOOTER_LINE.lower()
    site_footer_blurb = (
        "practice results are not official driving test results, and we are "
        "not affiliated with or endorsed by the dvsa"
    )
    play_pkg = "uk.co.drivingtestsimulator.passtrack".lower()
    for p in paths:
        text = p.read_text(encoding="utf-8")
        lower = text.lower()
        for phrase in BANNED_PHRASES:
            idx = 0
            while True:
                idx = lower.find(phrase, idx)
                if idx == -1:
                    break
                window = lower[max(0, idx - 120): idx + 120]
                # allow "official" only inside the mandated disclaimer line
                if phrase == "official" and (footer_lower in window or site_footer_blurb in window):
                    idx += len(phrase)
                    continue
                # allow "passtrack" only inside the Play Store package id
                if phrase == "passtrack" and play_pkg in window:
                    idx += len(phrase)
                    continue
                hits.append((p, phrase, idx))
                idx += len(phrase)
    return hits


def main():
    data = json.loads(DATA.read_text(encoding="utf-8"))
    all_centres = data["centres"]
    routes_by_id = data["routes"]

    OUT_DIR.mkdir(exist_ok=True)

    for centre in all_centres:
        page = render_page(centre, all_centres, routes_by_id)
        (OUT_DIR / f"{centre['id']}.html").write_text(page, encoding="utf-8")

    index_page = render_index(all_centres, routes_by_id)
    (OUT_DIR / "index.html").write_text(index_page, encoding="utf-8")

    update_sitemap([c["id"] for c in all_centres])

    generated = list(OUT_DIR.glob("*.html"))
    hits = scan_banned_phrases(generated)
    print(f"Generated {len(generated)} files in {OUT_DIR}")
    if hits:
        print(f"BANNED PHRASE HITS: {len(hits)}")
        for p, phrase, idx in hits:
            print(f"  {p.name}: '{phrase}' at offset {idx}")
    else:
        print("Banned-phrase scan: clean.")


if __name__ == "__main__":
    main()
