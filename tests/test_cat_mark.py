# ABOUTME: Unit, integration, and end-to-end checks for the Catilda cat mark (feature #33).
# ABOUTME: Covers logo lockups, favicon, living hero cat, mobile nav fix, how-it-works, meta tags.

from __future__ import annotations

import http.server
import socketserver
import struct
import threading
import unittest
import urllib.request
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.html"
BRAND = ROOT / "brand.html"


def _png_pixels(path: Path) -> tuple[int, int, list[tuple[int, int, int, int]]]:
    """Minimal PNG reader for the icon rasters: 8-bit RGB/RGBA, no interlace."""
    data = path.read_bytes()
    width, height, depth, ctype = struct.unpack(">IIBB", data[16:26])
    if depth != 8 or ctype not in (2, 6):
        raise AssertionError(f"{path.name}: expected 8-bit RGB/RGBA, got depth={depth} type={ctype}")
    n = 4 if ctype == 6 else 3
    idat = b""
    off = 8
    while off < len(data):
        length, tag = struct.unpack(">I4s", data[off : off + 8])
        if tag == b"IDAT":
            idat += data[off + 8 : off + 8 + length]
        off += 12 + length
    raw = zlib.decompress(idat)
    stride = width * n
    pixels: list[tuple[int, int, int, int]] = []
    prev = bytearray(stride)
    pos = 0
    for _ in range(height):
        filt = raw[pos]
        pos += 1
        line = bytearray(raw[pos : pos + stride])
        pos += stride
        for i in range(stride):
            left = line[i - n] if i >= n else 0
            up = prev[i]
            up_left = prev[i - n] if i >= n else 0
            if filt == 1:
                line[i] = (line[i] + left) & 255
            elif filt == 2:
                line[i] = (line[i] + up) & 255
            elif filt == 3:
                line[i] = (line[i] + (left + up) // 2) & 255
            elif filt == 4:
                p = left + up - up_left
                pa, pb, pc = abs(p - left), abs(p - up), abs(p - up_left)
                pred = left if pa <= pb and pa <= pc else (up if pb <= pc else up_left)
                line[i] = (line[i] + pred) & 255
        prev = line
        for x in range(width):
            px = line[x * n : x * n + n]
            pixels.append((px[0], px[1], px[2], px[3] if n == 4 else 255))
    return width, height, pixels


def _near(px: tuple[int, int, int, int], rgb: tuple[int, int, int], tol: int = 14) -> bool:
    return all(abs(px[i] - rgb[i]) <= tol for i in range(3))


class CatMarkUnitTests(unittest.TestCase):
    """The mark itself: favicon, symbol, lockups."""

    def setUp(self) -> None:
        self.html = INDEX.read_text(encoding="utf-8")

    def test_favicon_is_the_cat_not_the_monogram(self) -> None:
        icon_start = self.html.index('rel="icon" type="image/svg+xml"')
        icon = self.html[icon_start : self.html.index(">", icon_start)]
        # Marmalade tile with an ink face: an ink tile vanishes into dark
        # browser chrome and reads as an inverted image.
        self.assertIn("rx='28' fill='%23E8913F'", icon)
        self.assertIn("stroke='%23171A23'", icon)
        # Exactly one marmalade use (the tile) and five ink groups (outline,
        # eyes, nose, whiskers): a half-swapped URI fails these counts.
        self.assertEqual(icon.count("%23E8913F"), 1)
        self.assertEqual(icon.count("%23171A23"), 5)
        self.assertIn("circle", icon)  # the head
        self.assertNotIn("Verdana", icon)  # the old "c" text monogram is gone
        self.assertNotIn("%3Ctext", icon)

    def test_favicon_raster_fallbacks_for_safari(self) -> None:
        # Safari ignores SVG rel=icon; a PNG fallback and apple-touch-icon must exist.
        self.assertIn('rel="icon" type="image/png" sizes="32x32" href="favicon-32.png"', self.html)
        self.assertIn('rel="apple-touch-icon" href="apple-touch-icon.png"', self.html)
        self.assertTrue((ROOT / "favicon-32.png").is_file())
        self.assertTrue((ROOT / "apple-touch-icon.png").is_file())

    MARMALADE = (232, 145, 63)
    INK = (23, 26, 35)

    def test_favicon_png_is_marmalade_tile_with_ink_face(self) -> None:
        # Safari only sees the PNGs, so their pixels are pinned too: the tile
        # must be marmalade (dominant), the face ink, the corners transparent.
        width, height, pixels = _png_pixels(ROOT / "favicon-32.png")
        self.assertEqual((width, height), (32, 32))
        opaque = [p for p in pixels if p[3] > 200]
        marmalade = sum(1 for p in opaque if _near(p, self.MARMALADE))
        ink = sum(1 for p in opaque if _near(p, self.INK))
        self.assertGreater(marmalade, ink)
        self.assertGreater(ink, 0)
        self.assertLess(pixels[0][3], 30)  # rounded corner stays transparent

    def test_apple_touch_icon_is_full_bleed_marmalade(self) -> None:
        width, height, pixels = _png_pixels(ROOT / "apple-touch-icon.png")
        self.assertEqual((width, height), (180, 180))
        self.assertTrue(_near(pixels[0], self.MARMALADE))  # corners full-bleed
        self.assertTrue(_near(pixels[-1], self.MARMALADE))
        self.assertGreater(sum(1 for p in pixels if _near(p, self.INK)), 0)

    def test_marmalade_token_defined(self) -> None:
        self.assertIn("--orange:", self.html)
        self.assertIn("#E8913F", self.html)

    def test_cat_symbol_and_lockups(self) -> None:
        self.assertIn('symbol id="cat"', self.html)
        # Header, final CTA panel, and footer all reference the mark.
        self.assertGreaterEqual(self.html.count('href="#cat"'), 3)
        # Header lockup and footer brand row are each individually pinned.
        self.assertIn('class="lockup"', self.html)
        self.assertIn('<div class="fbrand"><svg class="cat"', self.html)
        # The old footer "c" tile is gone.
        self.assertNotIn('>c</span>', self.html)

    def test_decorative_cat_instances_are_aria_hidden(self) -> None:
        # The final CTA and footer cats are decorative; screen readers skip them.
        self.assertGreaterEqual(self.html.count('<svg class="cat" aria-hidden="true"'), 2)

    def test_social_meta_tags(self) -> None:
        self.assertIn('property="og:title"', self.html)
        self.assertIn('property="og:description"', self.html)
        self.assertIn('name="twitter:card"', self.html)


class LivingCatUnitTests(unittest.TestCase):
    """The hero cat is alive: blink, ear twitch, gaze that tracks and wanders."""

    def setUp(self) -> None:
        self.html = INDEX.read_text(encoding="utf-8")

    def test_hero_cat_structure(self) -> None:
        self.assertIn('class="herocat"', self.html)
        self.assertIn('class="cat-head"', self.html)
        self.assertIn('class="cat-face"', self.html)
        self.assertIn('class="cat-whiskers"', self.html)
        self.assertIn('class="eye"', self.html)
        self.assertIn('class="ear-r"', self.html)

    def test_idle_animations_with_reduced_motion_guard(self) -> None:
        self.assertIn("@keyframes catblink", self.html)
        self.assertIn("@keyframes eartwitch", self.html)
        # CSS guard: the animation:none rule must sit inside the media query.
        self.assertIn(
            "@media (prefers-reduced-motion:reduce){.herocat .eye,.herocat .ear-r{animation:none}}",
            self.html,
        )
        # JS guard: the gaze engine gates on the media query AND reacts to changes.
        self.assertIn("matchMedia('(prefers-reduced-motion: reduce)')", self.html)
        self.assertIn(".addEventListener('change'", self.html)

    def test_gaze_tracks_wanders_and_glances(self) -> None:
        self.assertIn("pointermove", self.html)
        self.assertIn("requestAnimationFrame", self.html)
        for hook in ("wander", "GLANCES"):
            self.assertIn(hook, self.html)
        # Scroll makes her glance at the page moving.
        self.assertIn('addEventListener("scroll"', self.html.replace("'", '"'))

    def test_gaze_engine_stops_when_pointless(self) -> None:
        # Off-screen hero, hidden tab, or reduced motion: the loop must stop.
        self.assertIn("IntersectionObserver", self.html)
        self.assertIn("visibilitychange", self.html)
        self.assertIn("cancelAnimationFrame", self.html)

    def test_hero_load_sequence_targets_real_markup(self) -> None:
        # The staged reveal must target .hero-inner (present), not .hero-content (absent).
        self.assertIn(".hero-inner > *{animation:riseIn", self.html)
        self.assertNotIn(".hero-content", self.html)

    def test_hero_cat_tilt_lives_below_the_entry_animation(self) -> None:
        # riseIn animates .herocat's transform, so a base transform there would
        # snap in when the animation ends; the tilt belongs to .cat-head.
        self.assertIn(".herocat .cat-head{transform:rotate(-6deg)", self.html)
        self.assertNotIn(".herocat{width:104px;height:104px;transform", self.html)


class PageStructureUnitTests(unittest.TestCase):
    """Supporting changes shipped with the mark."""

    def setUp(self) -> None:
        self.html = INDEX.read_text(encoding="utf-8")

    def test_mobile_nav_actually_opens(self) -> None:
        # Both halves of the fix: the collapse rule and the open rule.
        self.assertIn(".nav{display:none;position:absolute", self.html)
        self.assertIn(".nav.open{display:flex}", self.html)

    def test_mobile_nav_keyboard_and_aria(self) -> None:
        self.assertIn('aria-expanded="false"', self.html)
        self.assertIn('aria-controls="nav"', self.html)
        # Escape closes the menu; opening moves focus into it.
        self.assertIn("Escape", self.html)
        self.assertIn(".focus()", self.html)

    def test_how_it_works_strip(self) -> None:
        self.assertIn('id="how"', self.html)
        self.assertIn('href="#how"', self.html)
        for step in ("Book a call", "We plan it together", "She starts working"):
            self.assertIn(step, self.html)


class BrandBookIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.brand = BRAND.read_text(encoding="utf-8")

    def test_brand_book_documents_the_cat(self) -> None:
        self.assertIn("#E8913F", self.brand)
        self.assertIn("marmalade", self.brand.lower())
        self.assertIn('symbol id="cat"', self.brand)
        # The favicon rule now belongs to the cat face, not the "c" monogram —
        # and the old monogram tiles must stay removed.
        self.assertIn("cat face", self.brand.lower())
        self.assertNotIn('<div class="mono-mark">c</div>', self.brand)

    def test_brand_book_palette_counts_are_consistent(self) -> None:
        # The Marmalade swatch made it ten; no passage may still say nine.
        self.assertNotIn("nine-swatch", self.brand)
        self.assertNotIn("Nine colours", self.brand)
        self.assertEqual(self.brand.count('<div class="swatch">'), 10)
        # Section 08's recipe table assigns Marmalade its job.
        self.assertIn("<tr><td>The cat</td>", self.brand)


class _QuietHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return


class CatMarkE2ETests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.httpd = socketserver.TCPServer(("127.0.0.1", 0), _QuietHandler)
        cls.port = cls.httpd.server_address[1]
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.httpd.shutdown()
        cls.httpd.server_close()

    def _get(self, path: str) -> tuple[int, str]:
        with urllib.request.urlopen(f"http://127.0.0.1:{self.port}{path}") as resp:
            return resp.status, resp.read().decode("utf-8", errors="replace")

    def test_live_page_serves_the_living_cat(self) -> None:
        status, body = self._get("/")
        self.assertEqual(status, 200)
        self.assertIn("herocat", body)
        self.assertIn('symbol id="cat"', body)

    def test_live_brand_page_serves_the_cat(self) -> None:
        status, body = self._get("/brand.html")
        self.assertEqual(status, 200)
        self.assertIn("E8913F", body)


if __name__ == "__main__":
    unittest.main()
