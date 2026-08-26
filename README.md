# driving-test-simulator.co.uk

The public marketing site for **Driving Test Simulator**, a free UK mock driving
test app for Android, made by RDS HUB LTD.

> **This repository is the single source of truth for the live website.**
> Whatever is on `main` is what is served at
> <https://driving-test-simulator.co.uk>. There is no CMS, no build step and no
> staging copy — if it disagrees with a document elsewhere, this repo is right.

---

## Deploying

GitHub Pages serves `main` directly.

```bash
git add -A
git commit -m "your message"
git push origin main
```

That is the whole deploy. Pages usually reflects the change within a minute.

### ⚠️ Never delete `CNAME`

`CNAME` contains the custom domain. GitHub Pages rewrites the repository's
Pages settings from that file on every deploy — **if it disappears from a
commit, the custom domain is unset and the site goes down at
driving-test-simulator.co.uk.** Do not remove it, rename it, or add it to
`.gitignore`. If you ever do, restore it and push again.

`.nojekyll` is also required: it stops Pages running the files through Jekyll,
which would otherwise ignore directories beginning with an underscore and can
interfere with asset paths.

---

## Layout

```
index.html              Home page
privacy.html            Privacy policy (includes the website cookies section)
terms.html              Terms of Service
delete-account.html     Account deletion instructions (Play Store requirement)
404.html                Styled not-found page, noindex
assets/site.css         All styling. Design tokens live at the top.
assets/site.js          Consent banner, consent-gated analytics, reveal motion
assets/img/             Generated images — do not hand-edit
tools/make-assets.py    Regenerates everything under assets/img/ and the favicons
robots.txt, sitemap.xml, CNAME, .nojekyll
```

---

## Regenerating images

Screenshots, the social card, the favicon set, the wheel logo and the Google
Play badge are all produced by one script. Sources live outside this repo (in
OneDrive) and are **read-only** — the script never writes back to them.

```bash
pip install pillow
python tools/make-assets.py
```

It is idempotent, so re-running it is safe. Outputs and their budgets:

| Output | Notes |
| --- | --- |
| `assets/img/shots/<name>-{480,960}.webp` | Responsive screenshots, ≤50 KB / ≤140 KB |
| `assets/img/shots/<name>-480.png` | Fallback for the `<picture>` element |
| `assets/img/og-image.png` | 1200×630 social card |
| `assets/img/logo-wheel.svg` | Standalone wheel mark |
| `assets/img/google-play-badge.png` | Downloaded from Google, **unaltered** |
| `favicon.ico`, `favicon-{16,32}.png`, `apple-touch-icon.png`, `icon-{192,512}.png` | Repo root |

If the Play badge download fails, the script writes
`assets/img/google-play-badge.MISSING.txt` explaining what to do. Google's brand
guidelines forbid recolouring, cropping or redrawing that asset.

Screenshots are used **as captured** — they are deliberately not retouched.

---

## Analytics and consent

Nothing Google-owned loads until a visitor presses **Accept**.

- Every page carries an inline Consent Mode v2 snippet in `<head>` that denies
  all storage before any other script runs.
- The choice is stored in `localStorage` under `dts-consent` (not a cookie).
- **Cookie settings** in the footer clears the record and reopens the banner.

### ⚠️ Measurement IDs are still placeholders

The three constants at the top of `assets/site.js` are placeholders:

```js
var GA4_ID    = 'G-XXXXXXXXXX';
var ADS_ID    = 'AW-XXXXXXXXXX';
var ADS_LABEL = 'XXXXXXXX';
```

While they contain `X`s, a **placeholder guard** means no Google tag is injected
even when a visitor accepts, and a single console warning explains why. Replace
all three with the real values to switch measurement on. Nothing else needs to
change.

---

## Held-back change: privacy policy sign-in section

There is an **uncommitted, deliberately withheld** edit to `privacy.html`
sitting in the git stash:

```
stash@{0}  On main: vc13-privacy-hold
```

It adds three list items covering Google/Apple sign-in and a hashed
licence/PRN lock. **That functionality is not live yet, so the text must not go
public.** Leave the stash alone. When the corresponding app release ships:

```bash
git stash pop            # resolve against the current privacy.html
```

Note that `privacy.html` has been restyled since the stash was made, so expect
to reapply those three `<li>` items by hand rather than getting a clean pop.

---

## Content rules

These are not stylistic preferences — they are compliance and store-listing
constraints:

- The public name is **Driving Test Simulator** everywhere. The old internal
  codename must not appear in site copy or metadata.
- Android only in public. No iOS, App Store, TestFlight, CarPlay or Android
  Auto references, other than the FAQ line "Android only right now".
- The app is 100% free: no ads, no subscription, no in-app purchases. No
  pricing language anywhere.
- The DVSA disclaimer must stay prominent — hero trust line, "The honest bit"
  and the footer. Never claim the app is official, endorsed, or a guarantee of
  any result.
- Routes are **desk-checked, not road-driven**, and that caveat travels with
  every mention of route coverage.
- Instructor badges get an **ADI/PDI badge check** (a person looks at it) —
  never "verified instructor profiles".

---

## Contact

info@rds-hub-ltd.co.uk · RDS HUB LTD, company no. 16285288,
6 Exeter Place, Walsall, WS2 9UQ, England &amp; Wales.
