#!/usr/bin/env python3
"""
make-assets.py — regenerate every derived image asset for driving-test-simulator.co.uk

Sources are READ-ONLY and live outside this repo (OneDrive). Nothing here ever
writes back to them. Re-running this script is safe and idempotent.

    pip install pillow
    python tools/make-assets.py

Produces:
    assets/img/shots/<name>-480.webp   (480w)
    assets/img/shots/<name>-960.webp   (960w)
    assets/img/shots/<name>-480.png    (480w, fallback for the <picture>)
    assets/img/og-image.png            1200x630 social card
    assets/img/logo-wheel.svg          nav/footer mark
    assets/img/google-play-badge.png   official badge, downloaded unaltered
    favicon.ico / favicon-16.png / favicon-32.png
    apple-touch-icon.png / icon-192.png / icon-512.png   (repo root)
"""

from __future__ import annotations

import io
import os
import sys
import urllib.request
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont, ImageFilter
except ImportError:  # pragma: no cover
    sys.exit("Pillow is required:  pip install pillow")

# --------------------------------------------------------------------------
# Paths
# --------------------------------------------------------------------------

REPO = Path(__file__).resolve().parent.parent
SRC = Path(
    r"C:\Users\s\OneDrive\Claude\Driving Test Simulator\store-assets"
)
SHOT_SRC = SRC / "screenshots-2026-08-19"
SCRATCH = Path(
    r"C:\Users\s\AppData\Local\Temp\claude\C--Users-s"
    r"\df91062b-db50-478d-8162-9c415aea8751\scratchpad"
)

IMG_OUT = REPO / "assets" / "img"
SHOT_OUT = IMG_OUT / "shots"

# name on the site  ->  source filename
SHOTS = {
    "practice-nav": "shot-8-practice-nav.png",
    "satnav": "shot-1-satnav-mid-drive.png",
    "fault-marking": "shot-2-fault-marking.png",
    "result": "shot-3-result-debrief.png",
    "route-detail": "shot-5-route-detail-goodmayes-8.png",
    "routes": "shot-4-routes-browser.png",
    "coaching": "shot-6-coaching-page.png",
}

ICON = SRC / "icon-512.png"

# Brand tokens (kept in sync with assets/site.css)
NAVY = (11, 46, 79)
BRAND = (29, 112, 184)
SUN = (255, 201, 64)
PAPER = (255, 255, 255)

WIDTHS = (960, 480)
BUDGET = {960: 140 * 1024, 480: 50 * 1024}

PLAY_BADGE_URL = (
    "https://play.google.com/intl/en_gb/badges/static/images/badges/"
    "en_badge_web_generic.png"
)
FONT_URLS = {
    "bricolage.ttf": "https://github.com/google/fonts/raw/main/ofl/"
    "bricolagegrotesque/BricolageGrotesque%5Bopsz%2Cwdth%2Cwght%5D.ttf",
    "manrope.ttf": "https://github.com/google/fonts/raw/main/ofl/manrope/"
    "Manrope%5Bwght%5D.ttf",
}
FALLBACK_FONT = Path(r"C:\Windows\Fonts\segoeuib.ttf")

notes: list[str] = []


def log(msg: str) -> None:
    print(msg, flush=True)


def kb(path: Path) -> str:
    return f"{path.stat().st_size / 1024:.1f} KB"


def fetch(url: str, dest: Path, timeout: int = 30) -> bool:
    """Download url -> dest. Returns True on success."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(
        url, headers={"User-Agent": "Mozilla/5.0 (make-assets.py)"}
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = r.read()
        if not data:
            raise ValueError("empty response")
        dest.write_bytes(data)
        return True
    except Exception as exc:  # noqa: BLE001
        log(f"  ! download failed {url} -> {exc}")
        return False


# --------------------------------------------------------------------------
# 1. Screenshots -> responsive WebP + PNG fallback
# --------------------------------------------------------------------------


def build_shots() -> None:
    log("\n== screenshots ==")
    SHOT_OUT.mkdir(parents=True, exist_ok=True)

    for name, filename in SHOTS.items():
        src = SHOT_SRC / filename
        if not src.exists():
            notes.append(f"MISSING SOURCE: {src}")
            log(f"  ! missing {src}")
            continue

        # Flatten onto white: the captures are RGBA and WebP/PNG both
        # behave better without a stray alpha channel.
        with Image.open(src) as raw:
            base = Image.new("RGB", raw.size, PAPER)
            rgba = raw.convert("RGBA")
            base.paste(rgba, mask=rgba.split()[3])

        for w in WIDTHS:
            h = round(w * base.height / base.width)
            resized = base.resize((w, h), Image.LANCZOS)

            # --- WebP, q82 method 6, stepping down only if over budget ---
            out = SHOT_OUT / f"{name}-{w}.webp"
            for q in (82, 78, 74, 70, 66, 62, 58):
                buf = io.BytesIO()
                resized.save(buf, "WEBP", quality=q, method=6)
                if buf.tell() <= BUDGET[w] or q == 58:
                    out.write_bytes(buf.getvalue())
                    flag = "" if buf.tell() <= BUDGET[w] else "  OVER BUDGET"
                    if flag:
                        notes.append(
                            f"{out.name} is {buf.tell()/1024:.0f} KB, over the "
                            f"{BUDGET[w]//1024} KB budget"
                        )
                    log(f"  {out.name}  {w}x{h}  q{q}  {kb(out)}{flag}")
                    break

            # --- PNG fallback at 480 only ---
            if w == 480:
                png = SHOT_OUT / f"{name}-480.png"
                # Adaptive palette keeps the fallback sane without touching
                # the WebP quality the browser will actually use.
                quant = resized.quantize(colors=256, method=Image.MAXCOVERAGE)
                quant.save(png, "PNG", optimize=True)
                log(f"  {png.name}  {w}x{h}  {kb(png)}")


# --------------------------------------------------------------------------
# 2. Open Graph card
# --------------------------------------------------------------------------


def load_font(filename: str, size: int, weight: float | None = None):
    """Variable-font aware loader with a Segoe UI Bold fallback."""
    path = SCRATCH / filename
    if path.exists():
        try:
            f = ImageFont.truetype(str(path), size)
            if weight is not None:
                try:
                    f.set_variation_by_axes([weight])
                except Exception:  # noqa: BLE001
                    try:
                        axes = f.get_variation_axes()
                        vals = [a["default"] for a in axes]
                        for i, a in enumerate(axes):
                            if a["name"] in (b"Weight", "Weight"):
                                vals[i] = weight
                        f.set_variation_by_axes(vals)
                    except Exception:  # noqa: BLE001
                        pass
            return f
        except Exception as exc:  # noqa: BLE001
            log(f"  ! {filename} unusable ({exc})")
    if FALLBACK_FONT.exists():
        return ImageFont.truetype(str(FALLBACK_FONT), size)
    return ImageFont.load_default()


def rounded(img: Image.Image, radius: int) -> Image.Image:
    mask = Image.new("L", img.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        (0, 0, img.width - 1, img.height - 1), radius=radius, fill=255
    )
    out = img.convert("RGBA")
    out.putalpha(mask)
    return out


def wrap(draw, text, font, max_w):
    words, lines, cur = text.split(), [], ""
    for word in words:
        trial = f"{cur} {word}".strip()
        if draw.textlength(trial, font=font) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def build_og() -> None:
    log("\n== og-image ==")
    SCRATCH.mkdir(parents=True, exist_ok=True)
    for fname, url in FONT_URLS.items():
        target = SCRATCH / fname
        if not target.exists():
            if fetch(url, target):
                log(f"  font ok {fname} ({kb(target)})")
            else:
                notes.append(f"font download failed: {fname} (used Segoe UI Bold)")
        else:
            log(f"  font cached {fname}")

    W, H = 1200, 630
    card = Image.new("RGB", (W, H), NAVY)

    # Diagonal navy -> brand gradient, painted per-row then sheared by a
    # horizontal component so it reads as a diagonal wash rather than a band.
    grad = Image.new("RGB", (W, H))
    gd = ImageDraw.Draw(grad)
    for y in range(H):
        for_x = y / H
        for x in range(0, W, 8):
            t = min(1.0, max(0.0, 0.15 + 0.55 * for_x + 0.45 * (x / W)))
            col = tuple(round(NAVY[i] + (BRAND[i] - NAVY[i]) * t) for i in range(3))
            gd.rectangle((x, y, x + 8, y + 1), fill=col)
    card.paste(grad, (0, 0))

    draw = ImageDraw.Draw(card)

    # Sun accent, bottom-left — a soft glow, not a disc. Blurred hard so the
    # edge never reads as a stray shape behind the type.
    blob = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(blob).ellipse((-160, 430, 340, 930), fill=SUN + (74,))
    blob = blob.filter(ImageFilter.GaussianBlur(90))
    card.paste(Image.alpha_composite(card.convert("RGBA"), blob).convert("RGB"))

    # App icon (the wheel mark), 160px, top-left
    if ICON.exists():
        with Image.open(ICON) as ic:
            icon = ic.convert("RGBA").resize((160, 160), Image.LANCZOS)
        card.paste(rounded(icon, 36), (72, 64), rounded(icon, 36))
    else:
        notes.append(f"MISSING SOURCE: {ICON}")

    # --- Right third: practice-nav phone crop ---
    phone_src = SHOT_SRC / SHOTS["practice-nav"]
    if phone_src.exists():
        with Image.open(phone_src) as raw:
            shot = raw.convert("RGB")
        pw = 322
        ph = round(pw * shot.height / shot.width)
        shot = shot.resize((pw, ph), Image.LANCZOS)
        crop_h = 470
        shot = shot.crop((0, 0, pw, crop_h))

        bezel = Image.new("RGB", (pw + 16, crop_h + 16), (16, 18, 22))
        bezel.paste(shot, (8, 8))
        bezel_r = rounded(bezel, 34)

        shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(shadow).rounded_rectangle(
            (824, 106, 824 + bezel_r.width, 106 + bezel_r.height),
            radius=34,
            fill=(4, 16, 30, 130),
        )
        shadow = shadow.filter(ImageFilter.GaussianBlur(18))
        card.paste(
            Image.alpha_composite(card.convert("RGBA"), shadow).convert("RGB")
        )
        card.paste(bezel_r, (818, 96), bezel_r)

    # --- Headline ---
    head_font = load_font("bricolage.ttf", 68, weight=800)
    sub_font = load_font("manrope.ttf", 30, weight=600)

    text_w = 700
    lines = wrap(draw, "Your driving test, rehearsed.", head_font, text_w)
    y = 272
    for line in lines:
        draw.text((72, y), line, font=head_font, fill=PAPER)
        y += 78

    draw.text(
        (72, y + 14),
        "Free mock driving tests \u00b7 Android",
        font=sub_font,
        fill=SUN,
    )

    IMG_OUT.mkdir(parents=True, exist_ok=True)
    out = IMG_OUT / "og-image.png"
    card.save(out, "PNG", optimize=True)
    log(f"  {out.name}  {W}x{H}  {kb(out)}")


# --------------------------------------------------------------------------
# 3. Favicons / touch icons
# --------------------------------------------------------------------------


def build_icons() -> None:
    log("\n== icons ==")
    if not ICON.exists():
        notes.append(f"MISSING SOURCE: {ICON}")
        log(f"  ! missing {ICON}")
        return

    with Image.open(ICON) as raw:
        icon = raw.convert("RGBA")

    for size, name in ((16, "favicon-16.png"), (32, "favicon-32.png")):
        icon.resize((size, size), Image.LANCZOS).save(REPO / name, "PNG", optimize=True)
        log(f"  {name}  {kb(REPO / name)}")

    # .ico with 16/32/48
    ico = REPO / "favicon.ico"
    icon.resize((48, 48), Image.LANCZOS).save(
        ico, "ICO", sizes=[(16, 16), (32, 32), (48, 48)]
    )
    log(f"  favicon.ico  {kb(ico)}")

    # apple-touch-icon: 180, no transparency (iOS renders alpha as black)
    at = Image.new("RGB", (180, 180), PAPER)
    scaled = icon.resize((180, 180), Image.LANCZOS)
    at.paste(scaled, mask=scaled.split()[3])
    at.save(REPO / "apple-touch-icon.png", "PNG", optimize=True)
    log(f"  apple-touch-icon.png  {kb(REPO / 'apple-touch-icon.png')}")

    for size in (192, 512):
        name = f"icon-{size}.png"
        icon.resize((size, size), Image.LANCZOS).save(
            REPO / name, "PNG", optimize=True
        )
        log(f"  {name}  {kb(REPO / name)}")

    # The old single favicon.png is replaced by the set above.
    old = REPO / "favicon.png"
    if old.exists():
        old.unlink()
        log("  removed legacy favicon.png")


# --------------------------------------------------------------------------
# 4. Wheel logo (SVG, authored not traced)
# --------------------------------------------------------------------------


def build_logo() -> None:
    log("\n== logo ==")
    import math

    cx = cy = 24.0
    r_outer, r_hub = 18.0, 4.0
    spokes = []
    for deg in (90, 210, 330):
        rad = math.radians(deg)
        x1 = cx + r_hub * math.cos(rad)
        y1 = cy - r_hub * math.sin(rad)
        x2 = cx + r_outer * math.cos(rad)
        y2 = cy - r_outer * math.sin(rad)
        spokes.append(
            f'  <line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}"/>'
        )

    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48" '
        'fill="none" role="img" aria-hidden="true" focusable="false">\n'
        '  <g stroke="#fff" stroke-width="5" stroke-linecap="round">\n'
        f'  <circle cx="24" cy="24" r="18"/>\n'
        + "\n".join(spokes)
        + "\n  </g>\n"
        '  <circle cx="24" cy="24" r="4" fill="#fff"/>\n'
        "</svg>\n"
    )
    IMG_OUT.mkdir(parents=True, exist_ok=True)
    out = IMG_OUT / "logo-wheel.svg"
    out.write_text(svg, encoding="utf-8")
    log(f"  {out.name}  {kb(out)}")


# --------------------------------------------------------------------------
# 5. Google Play badge (downloaded unaltered — trademark asset)
# --------------------------------------------------------------------------


def build_badge() -> None:
    log("\n== play badge ==")
    IMG_OUT.mkdir(parents=True, exist_ok=True)
    dest = IMG_OUT / "google-play-badge.png"
    marker = IMG_OUT / "google-play-badge.MISSING.txt"

    if fetch(PLAY_BADGE_URL, dest):
        with Image.open(dest) as im:
            log(f"  google-play-badge.png  {im.size[0]}x{im.size[1]}  {kb(dest)}")
        if marker.exists():
            marker.unlink()
    else:
        if dest.exists():
            dest.unlink()
        marker.write_text(
            "The official 'Get it on Google Play' badge could not be downloaded "
            "when tools/make-assets.py last ran.\n\n"
            f"Source: {PLAY_BADGE_URL}\n\n"
            "The site is currently rendering a temporary styled text button in "
            "place of the badge (see .btn-play in assets/site.css). Download the "
            "badge to assets/img/google-play-badge.png UNALTERED, then swap the "
            "text button for the <picture>/<img> markup before launch. Google's "
            "brand guidelines forbid recolouring, cropping or redrawing it.\n",
            encoding="utf-8",
        )
        notes.append(
            "Play badge download FAILED — google-play-badge.MISSING.txt written, "
            "site falls back to a styled text button."
        )
        log("  ! badge unavailable; placeholder marker written")


# --------------------------------------------------------------------------


def main() -> None:
    log(f"repo:    {REPO}")
    log(f"sources: {SRC}  (read-only)")
    build_shots()
    build_og()
    build_icons()
    build_logo()
    build_badge()

    log("\n== notes ==")
    if notes:
        for n in notes:
            log(f"  - {n}")
    else:
        log("  none — every asset built within budget")


if __name__ == "__main__":
    main()
