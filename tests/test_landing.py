# ABOUTME: Unit, integration, and end-to-end checks for the Catilda landing page.
# ABOUTME: Parses static HTML, serves it over HTTP, and asserts hero content.

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
STYLES = ROOT / "styles.css"
SCRIPT = ROOT / "script.js"


class TagCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.title = ""
        self.h1 = ""
        self._capture: str | None = None
        self.links: list[str] = []
        self.scripts: list[str] = []
        self.has_starfield = False
        self.status_text = ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = dict(attrs)
        if tag == "title":
            self._capture = "title"
        elif tag == "h1":
            self._capture = "h1"
        elif tag == "p" and attrs_dict.get("class") == "status":
            self._capture = "status"
        elif tag == "canvas" and attrs_dict.get("id") == "starfield":
            self.has_starfield = True
        elif tag == "link" and attrs_dict.get("rel") == "stylesheet":
            href = attrs_dict.get("href")
            if href:
                self.links.append(href)
        elif tag == "script":
            src = attrs_dict.get("src")
            if src:
                self.scripts.append(src)

    def handle_data(self, data: str) -> None:
        if self._capture == "title":
            self.title += data
        elif self._capture == "h1":
            self.h1 += data
        elif self._capture == "status":
            self.status_text += data

    def handle_endtag(self, tag: str) -> None:
        if tag in {"title", "h1", "p"}:
            self._capture = None


class LandingUnitTests(unittest.TestCase):
    def test_required_files_exist(self) -> None:
        self.assertTrue(INDEX.is_file())
        self.assertTrue(STYLES.is_file())
        self.assertTrue(SCRIPT.is_file())

    def test_html_structure(self) -> None:
        parser = TagCollector()
        parser.feed(INDEX.read_text(encoding="utf-8"))
        self.assertEqual(parser.title.strip(), "Catilda")
        self.assertEqual(parser.h1.strip(), "Catilda")
        self.assertIn("Coming soon", parser.status_text)
        self.assertTrue(parser.has_starfield)
        self.assertIn("styles.css", parser.links)
        self.assertIn("script.js", parser.scripts)

    def test_css_has_space_tokens(self) -> None:
        css = STYLES.read_text(encoding="utf-8")
        self.assertIn("--void", css)
        self.assertIn("--signal", css)
        self.assertIn("porthole", css)


class LandingIntegrationTests(unittest.TestCase):
    def test_assets_served_together(self) -> None:
        html = INDEX.read_text(encoding="utf-8")
        css = STYLES.read_text(encoding="utf-8")
        js = SCRIPT.read_text(encoding="utf-8")
        self.assertIn('href="styles.css"', html)
        self.assertIn('src="script.js"', html)
        self.assertIn("starfield", js)
        self.assertIn("Instrument+Serif", html)
        self.assertIn("Instrument Serif", STYLES.read_text(encoding="utf-8"))
        self.assertGreater(len(css), 200)


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
            return resp.status, resp.read().decode("utf-8")

    def test_live_page_renders_hero(self) -> None:
        status, body = self._get("/")
        self.assertEqual(status, 200)
        self.assertIn("<h1>Catilda</h1>", body)
        self.assertIn("Coming soon", body)
        self.assertIn('id="starfield"', body)

        css_status, css_body = self._get("/styles.css")
        self.assertEqual(css_status, 200)
        self.assertIn("--signal", css_body)

        js_status, js_body = self._get("/script.js")
        self.assertEqual(js_status, 200)
        self.assertIn("requestAnimationFrame", js_body)


if __name__ == "__main__":
    unittest.main()
