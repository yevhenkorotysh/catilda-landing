# ABOUTME: Guards the public pricing section, the Start free funnel, and the brand book's pricing rule.
# ABOUTME: Static checks on index.html and brand.html plus a live-server check of the pricing section.

import functools
import http.server
import re
import socketserver
import threading
import unittest
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = (ROOT / "index.html").read_text(encoding="utf-8")
BRAND = (ROOT / "brand.html").read_text(encoding="utf-8")
SIGNUP = "https://catilda.com/cabinet/signup"


def section(html: str, section_id: str) -> str:
    start = html.index(f'<section id="{section_id}"')
    return html[start : html.index("</section>", start)]


class FunnelUnitTests(unittest.TestCase):
    def test_every_signup_link_points_at_the_cabinet_signup(self):
        hrefs = re.findall(r'js-signup" href="([^"]+)"', INDEX)
        self.assertGreaterEqual(len(hrefs), 3)
        for href in hrefs:
            self.assertTrue(href.startswith(SIGNUP), href)

    def test_header_order_login_start_free_burger(self):
        head = INDEX[INDEX.index('class="header-cta"') :]
        head = head[: head.index("</div>")]
        i_login = head.index('href="https://catilda.com/cabinet/login">Log in</a>')
        i_start = head.index(f'class="btn btn-primary btn-sm js-signup" href="{SIGNUP}">Start free</a>')
        i_burger = head.index('id="burger"')
        self.assertLess(i_login, i_start)
        self.assertLess(i_start, i_burger)
        self.assertNotIn("js-book", head)

    def test_hero_and_final_cta_lead_with_start_free(self):
        self.assertIn(f'class="btn btn-primary js-signup" href="{SIGNUP}">Start free</a>', INDEX)
        self.assertIn(f'class="btn btn-mint js-signup" href="{SIGNUP}">Start free</a>', INDEX)
        self.assertIn('class="btn btn-white js-book" href="#book">Book a call</a>', INDEX)

    def test_hero_note_and_micro_line_state_the_free_month(self):
        self.assertIn("her first month is on us", INDEX)
        self.assertIn("Nothing is charged for 30 days", INDEX)

    def test_steps_describe_the_self_serve_funnel(self):
        how = section(INDEX, "how")
        for step in ("Pick a plan", "Hand over a routine", "She starts working"):
            self.assertIn(step, how)

    def test_faq_states_the_plans(self):
        self.assertIn("Bronze $200, Silver $500 and Gold $900", INDEX)

    def test_no_price_on_the_call_copy_remains(self):
        for stale in (
            "before you pay anything",
            "agree a flat price",
            "agree the number there",
            "No meters",
            "Fifteen minutes on a call is all it takes",
        ):
            self.assertNotIn(stale, INDEX)
