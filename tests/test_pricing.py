# ABOUTME: Guards the public pricing section, the Start free funnel, and the brand book's pricing rule.
# ABOUTME: Static checks on index.html and brand.html plus a live-server check of the pricing section.

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


class PricingUnitTests(unittest.TestCase):
    def test_pricing_section_lists_the_three_plans(self):
        sec = section(INDEX, "pricing")
        for name, price, seats, pool in (
            ("Bronze", "$200", "1 employee", "Standard pool of work"),
            ("Silver", "$500", "Up to 3 employees", "2.5× the Bronze pool"),
            ("Gold", "$900", "Up to 5 employees", "4.5× the Bronze pool"),
        ):
            self.assertIn(f'data-plan="{name.lower()}"', sec)
            self.assertIn(f"<h3>{name}</h3>", sec)
            self.assertIn(price, sec)
            self.assertIn(seats, sec)
            self.assertIn(pool, sec)
        self.assertIn("Talk to us", sec)
        self.assertNotIn("$750", INDEX)
        self.assertNotIn("$1000", INDEX)
        self.assertNotIn("$1,000", INDEX)

    def test_plan_buttons_deep_link_to_signup_with_the_plan(self):
        for plan in ("bronze", "silver", "gold"):
            self.assertIn(f'class="btn btn-primary js-signup" href="{SIGNUP}?plan={plan}">Start free</a>', INDEX)

    def test_nav_and_footer_link_to_pricing(self):
        nav = INDEX[INDEX.index('<nav class="nav" id="nav">') :]
        nav = nav[: nav.index("</nav>")]
        self.assertIn('href="#pricing"', nav)
        footer = INDEX[INDEX.index("<footer") :]
        self.assertIn('href="#pricing"', footer)

    def test_pricing_section_has_one_heading(self):
        sec = section(INDEX, "pricing")
        self.assertEqual(sec.count("<h2>"), 1)


class _QuietHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return


class PricingE2ETests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = socketserver.TCPServer(("127.0.0.1", 0), _QuietHandler)
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def test_live_page_serves_the_plans(self):
        with urllib.request.urlopen(f"http://127.0.0.1:{self.port}/") as resp:
            self.assertEqual(resp.status, 200)
            body = resp.read().decode("utf-8")
        self.assertIn('id="pricing"', body)
        for price in ("$200", "$500", "$900"):
            self.assertIn(price, body)
        self.assertIn("Start free", body)
