# ABOUTME: Unit, integration, and end-to-end checks for the Catilda marketing landing.
# ABOUTME: Parses static HTML, serves it over HTTP, and asserts hero + CTA content.

from __future__ import annotations

import http.server
import socketserver
import threading
import unittest
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.html"
ASSETS = ROOT / "assets"


class TagCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.title = ""
        self.h1 = ""
        self._capture: str | None = None
        self.has_sand_canvas = False
        self.book_demo_links = 0
        self.external_stylesheets = 0
        self.external_scripts = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = dict(attrs)
        if tag == "title":
            self._capture = "title"
        elif tag == "h1":
            self._capture = "h1"
        elif tag == "canvas" and attrs_dict.get("id") == "sandCanvas":
            self.has_sand_canvas = True
        elif tag == "a":
            href = (attrs_dict.get("href") or "").lower()
            classes = attrs_dict.get("class") or ""
            text_hint = "btn" in classes
            if href.startswith("#book") or "calendly.com" in href:
                self.book_demo_links += 1
            elif text_hint and "book" in href:
                self.book_demo_links += 1
        elif tag == "link" and attrs_dict.get("rel") == "stylesheet":
            self.external_stylesheets += 1
        elif tag == "script" and attrs_dict.get("src"):
            self.external_scripts += 1

    def handle_data(self, data: str) -> None:
        if self._capture == "title":
            self.title += data
        elif self._capture == "h1":
            self.h1 += data

    def handle_endtag(self, tag: str) -> None:
        if tag in {"title", "h1"}:
            self._capture = None


class LandingUnitTests(unittest.TestCase):
    def test_required_files_exist(self) -> None:
        self.assertTrue(INDEX.is_file())
        self.assertTrue(ASSETS.is_dir())
        self.assertTrue((ASSETS / "logos").is_dir())

    def test_html_structure(self) -> None:
        html = INDEX.read_text(encoding="utf-8")
        parser = TagCollector()
        parser.feed(html)
        self.assertIn("Catilda", parser.title)
        self.assertIn("digital employee", parser.h1.lower())
        self.assertTrue(parser.has_sand_canvas)
        self.assertGreaterEqual(parser.book_demo_links, 1)
        self.assertNotIn("Famulatus", html)
        self.assertNotIn("Coming soon", html)
        self.assertIn("Book a free 15 minute demo", html)

    def test_inline_brand_tokens(self) -> None:
        html = INDEX.read_text(encoding="utf-8")
        self.assertIn("--void", html)
        self.assertIn("sandCanvas", html)
        self.assertIn("hello@catilda.com", html)


class LandingIntegrationTests(unittest.TestCase):
    def test_assets_referenced_and_present(self) -> None:
        html = INDEX.read_text(encoding="utf-8")
        self.assertIn("assets/", html)
        # Marketing page is self-contained (no external site CSS/JS bundles).
        self.assertNotIn('href="styles.css"', html)
        self.assertNotIn('src="script.js"', html)
        self.assertTrue((ASSETS / "ribbon-poster.jpg").is_file() or any(ASSETS.glob("ribbon*")))
        logo_count = len(list((ASSETS / "logos").iterdir()))
        self.assertGreaterEqual(logo_count, 5)


class _QuietHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return


class LandingE2ETests(unittest.TestCase):
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

    def test_live_page_renders_hero(self) -> None:
        status, body = self._get("/")
        self.assertEqual(status, 200)
        self.assertIn("Catilda", body)
        self.assertIn("Hire a digital employee", body)
        self.assertIn('id="sandCanvas"', body)
        self.assertIn("Book a free 15 minute demo", body)
        self.assertNotIn("Coming soon", body)

        asset_status, _ = self._get("/assets/ribbon-poster.jpg")
        self.assertEqual(asset_status, 200)


if __name__ == "__main__":
    unittest.main()
