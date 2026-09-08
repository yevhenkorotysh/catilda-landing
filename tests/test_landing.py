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
BRAND = ROOT / "brand.html"


class TagCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.title = ""
        self.h1 = ""
        self._capture: str | None = None
        self.book_call_links = 0
        self.section_ids: set[str] = set()
        self.hidden_section_ids: set[str] = set()
        self.has_brand_link = False
        self.nav_hrefs: list[str] = []
        self._in_nav = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = dict(attrs)
        if tag == "title":
            self._capture = "title"
        elif tag == "h1":
            self._capture = "h1"
        elif tag == "nav":
            self._in_nav += 1
        elif tag == "section":
            section_id = attrs_dict.get("id")
            if section_id:
                self.section_ids.add(section_id)
                if "hidden" in attrs_dict or attrs_dict.get("hidden") is not None:
                    self.hidden_section_ids.add(section_id)
        elif tag == "main" and attrs_dict.get("id") == "top":
            self.section_ids.add("top")
        elif tag == "a":
            href = (attrs_dict.get("href") or "").lower()
            classes = attrs_dict.get("class") or ""
            if href.startswith("#book") or "js-book" in classes:
                self.book_call_links += 1
            if href.endswith("brand.html") or href == "brand.html":
                self.has_brand_link = True
            if self._in_nav:
                self.nav_hrefs.append(href)

    def handle_data(self, data: str) -> None:
        if self._capture == "title":
            self.title += data
        elif self._capture == "h1":
            self.h1 += data

    def handle_endtag(self, tag: str) -> None:
        if tag in {"title", "h1"}:
            self._capture = None
        elif tag == "nav" and self._in_nav:
            self._in_nav -= 1


class LandingUnitTests(unittest.TestCase):
    def test_required_files_exist(self) -> None:
        self.assertTrue(INDEX.is_file())
        self.assertTrue(BRAND.is_file())

    def test_html_structure(self) -> None:
        html = INDEX.read_text(encoding="utf-8")
        parser = TagCollector()
        parser.feed(html)
        self.assertIn("Catilda", parser.title)
        self.assertIn("digital employee", parser.h1.lower())
        self.assertIn("Meet Catilda", parser.h1)
        self.assertGreaterEqual(parser.book_call_links, 1)
        self.assertFalse(parser.has_brand_link)
        self.assertTrue({"what", "faq", "book"}.issubset(parser.section_ids))
        self.assertIn("safe", parser.hidden_section_ids)
        self.assertNotIn("#safe", parser.nav_hrefs)
        self.assertNotIn("Famulatus", html)
        self.assertNotIn("Coming soon", html)
        self.assertIn("Book a call", html)
        self.assertNotIn(
            "Your data is never sold and never used to train anything outside your business",
            html,
        )

    def test_header_has_login_button_before_book_a_call(self) -> None:
        html = INDEX.read_text(encoding="utf-8")
        cta_start = html.index('class="header-cta"')
        cta_end = html.index("</div>", cta_start)
        header_cta = html[cta_start:cta_end]
        login_pos = header_cta.index(
            '<a class="btn btn-ghost btn-sm" href="https://catilda.com/cabinet/login">Log in</a>'
        )
        book_pos = header_cta.index('js-book" href="#book">Book a call</a>')
        burger_pos = header_cta.index('id="burger"')
        self.assertLess(login_pos, book_pos)
        self.assertLess(book_pos, burger_pos)

    def test_login_button_stays_visible_at_every_width(self) -> None:
        # Log in lives once, in the header bar, and never hides behind the
        # burger: a phone visitor sees the way into the app without opening
        # the menu. Under 620px the bar tightens so lockup, Log in, Book a
        # call and the burger share one row on a 375px phone, and under
        # 380px the cat carries the brand alone.
        html = INDEX.read_text(encoding="utf-8")
        self.assertNotIn(".header-cta .btn-ghost{display:none}", html)
        self.assertNotIn("nav-login", html)
        nav_start = html.index('<nav class="nav" id="nav">')
        nav_end = html.index("</nav>", nav_start)
        self.assertNotIn("Log in", html[nav_start:nav_end])
        query_start = html.index("@media (max-width:620px)")
        # The phone rules share specificity with the base header rules, so
        # they must come later in the sheet to win the cascade.
        self.assertGreater(query_start, html.index(".header-bar{display:flex"))
        self.assertGreater(query_start, html.index(".header-cta{display:flex"))
        query_620 = html[query_start : html.index("\n}\n", query_start)]
        for rule in (
            ".header-bar{padding:0 6px 0 12px;gap:8px}",
            ".header-cta{gap:4px}",
            ".header-cta .btn-sm{padding:0 12px}",
            ".header-cta .btn-ghost{background:transparent;border-color:transparent;padding:0 6px}",
            ".lockup .cat{width:30px;height:30px}",
            ".lockup .wordmark{font-size:1.1rem}",
        ):
            self.assertIn(rule, query_620)
        query_start = html.index("@media (max-width:380px)")
        query_380 = html[query_start : html.index("\n}\n", query_start)]
        self.assertIn(".lockup .wordmark{display:none}", query_380)

    def test_what_card_names_the_work_nobody_loves(self) -> None:
        html = INDEX.read_text(encoding="utf-8")
        what_start = html.index('<section id="what"')
        what = html[what_start : html.index("</section>", what_start)]
        self.assertIn("<h3>Loves repeated work which nobody loves</h3>", what)
        self.assertNotIn("Best at the work you already repeat", html)

    def test_faq_cost_answer_is_one_sentence(self) -> None:
        html = INDEX.read_text(encoding="utf-8")
        self.assertIn(
            '["What does she cost?",\n   "A fraction of a part-time hire."]',
            html,
        )
        self.assertNotIn("agree the number there", html)
        self.assertNotIn("No meters", html)

    def test_final_panel_is_light(self) -> None:
        # The closing panel is a light surface like the rest of the page:
        # ink text on a cloud-to-mint wash, cobalt button, marmalade cat.
        html = INDEX.read_text(encoding="utf-8")
        for dark in ("grad-dark", "btn-mint", ".panel .eyebrow", ".panel h2"):
            self.assertNotIn(dark, html)
        panel_start = html.index(".panel{")
        panel = html[panel_start : html.index("}\n", panel_start)]
        for rule in ("var(--cloud)", "border:1px solid var(--line-2)", "rgba(141,216,197,.28)"):
            self.assertIn(rule, panel)
        self.assertIn(".final .lead{color:var(--body)", html)
        self.assertIn(".final .micro{font-size:.9rem;color:var(--muted)}", html)
        book_start = html.index('<section class="final" id="book">')
        book = html[book_start : html.index("</section>", book_start)]
        self.assertIn('class="btn btn-primary js-book" href="#book">Book a call</a>', book)
        self.assertIn("--cat-line:var(--ink);--cat-fur:var(--orange)", book)

    def test_inline_brand_tokens(self) -> None:
        html = INDEX.read_text(encoding="utf-8")
        self.assertIn("--cobalt", html)
        self.assertIn("--mint", html)
        self.assertIn("--cloud", html)
        self.assertIn("CONTACT_EMAIL", html)
        self.assertIn("info@catilda.com", html)
        self.assertNotIn("korotysh@gmail.com", html)


class LandingIntegrationTests(unittest.TestCase):
    def test_self_contained_page(self) -> None:
        html = INDEX.read_text(encoding="utf-8")
        # Marketing page is self-contained (inline CSS/JS, inline logo SVGs).
        self.assertNotIn('href="styles.css"', html)
        self.assertNotIn('src="script.js"', html)
        self.assertNotIn("assets/", html)
        self.assertIn("logoTrack", html)
        self.assertIn("faqList", html)

    def test_brand_page_present(self) -> None:
        brand = BRAND.read_text(encoding="utf-8")
        self.assertIn("Catilda Brand Guidelines", brand)
        self.assertIn("--cobalt", brand)


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
        self.assertIn("Meet Catilda", body)
        self.assertIn("your digital employee", body)
        self.assertIn("Book a call", body)
        self.assertNotIn("Coming soon", body)

    def test_live_page_carries_the_review_copy(self) -> None:
        status, body = self._get("/")
        self.assertEqual(status, 200)
        self.assertIn("Loves repeated work which nobody loves", body)
        self.assertIn("A fraction of a part-time hire.", body)
        book_start = body.index('<section class="final" id="book">')
        book = body[book_start : body.index("</section>", book_start)]
        self.assertIn('class="btn btn-primary js-book"', book)

    def test_brand_page_serves(self) -> None:
        status, body = self._get("/brand.html")
        self.assertEqual(status, 200)
        self.assertIn("Brand Guidelines", body)


if __name__ == "__main__":
    unittest.main()
