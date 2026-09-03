# ABOUTME: Guards the DigitalOcean App Platform spec for catilda-prod.
# ABOUTME: Landing at /, cabinet at /cabinet, API at /api on catilda.com.

from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / ".do" / "app.yaml"


class AppSpecTests(unittest.TestCase):
    def setUp(self) -> None:
        self.spec = SPEC.read_text(encoding="utf-8")

    def test_spec_exists(self) -> None:
        self.assertTrue(SPEC.is_file())

    def test_app_is_catilda_prod_on_catilda_dot_com(self) -> None:
        self.assertRegex(self.spec, r"(?m)^name: catilda-prod$")
        self.assertIn("domain: catilda.com", self.spec)
        self.assertIn("domain: www.catilda.com", self.spec)

    def test_ingress_order_api_then_cabinet_then_landing(self) -> None:
        prefixes = re.findall(r"prefix: (/\S*)", self.spec)
        self.assertGreaterEqual(len(prefixes), 3, self.spec)
        self.assertEqual(prefixes[0], "/api")
        self.assertIn("/cabinet", prefixes)
        self.assertEqual(prefixes[-1], "/")
        self.assertLess(prefixes.index("/api"), prefixes.index("/cabinet"))
        self.assertLess(prefixes.index("/cabinet"), prefixes.index("/"))

    def test_api_preserves_path_prefix(self) -> None:
        self.assertRegex(
            self.spec,
            r"name: api\n(?:.*\n)*?\s+preserve_path_prefix: true",
        )

    def test_cabinet_does_not_preserve_path_prefix(self) -> None:
        cabinet = self._component_block("cabinet")
        self.assertNotIn("preserve_path_prefix: true", cabinet)

    def test_cabinet_build_uses_vite_base_cabinet(self) -> None:
        cabinet = self._component_block("cabinet")
        self.assertIn("VITE_BASE", cabinet)
        self.assertIn("/cabinet/", cabinet)

    def test_components_point_at_the_three_repos(self) -> None:
        self.assertIn("yevhenkorotysh/catilda-landing", self.spec)
        self.assertIn("yevhenkorotysh/de-frontend", self.spec)
        self.assertIn("yevhenkorotysh/de-backend", self.spec)

    def test_cors_origins_are_host_only(self) -> None:
        # ${cabinet.PUBLIC_URL} is https://catilda.com/cabinet — corsheaders E014.
        self.assertNotIn("${cabinet.PUBLIC_URL}", self.spec)
        self.assertNotIn("${web.PUBLIC_URL}", self.spec)
        self.assertIn(
            "https://catilda.com,https://www.catilda.com",
            self.spec,
        )

    def _component_block(self, name: str) -> str:
        """Slice from `- name: <name>` (or `name: <name>` under a list item) to the next sibling."""
        match = re.search(rf"(?m)^- name: {name}\n", self.spec)
        if match:
            start = match.start()
        else:
            match = re.search(rf"(?m)^  name: {name}\n", self.spec)
            self.assertIsNotNone(match, f"component {name} missing")
            start = match.start()
        rest = self.spec[start:]
        next_item = re.search(r"\n- name: ", rest[1:])
        return rest if next_item is None else rest[: next_item.start() + 1]


if __name__ == "__main__":
    unittest.main()
