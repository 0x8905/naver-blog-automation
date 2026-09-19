import io
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from nblog.cli import main
from nblog.guide import ROWS, format_guide
from nblog.llm import PROVIDERS
from nblog.publisher import load_selectors
from nblog.taste import load_taste, new_pack
from nblog.writer import build_prompt, system_prompt


class GuideTest(unittest.TestCase):
    def test_where_points_at_taste_not_core(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            self.assertEqual(main(["where"]), 0)
        text = buf.getvalue()
        self.assertIn("taste/<name>/taste.json", text)
        self.assertIn("AGENTS.md", text)
        self.assertNotIn("nblog/profiles", text)
        self.assertNotIn("nblog/pipeline.py", text)

    def test_format_guide_covers_all_rows(self):
        text = format_guide()
        for want, path, _how in ROWS:
            self.assertIn(want, text)
            self.assertIn(path, text)

    def test_providers_registered(self):
        for name in ("openai", "openai_compat", "anthropic"):
            self.assertIn(name, PROVIDERS)

    def test_selectors_have_required_keys(self):
        sel = load_selectors(load_taste("default"))
        for key in ("title", "body", "save_draft", "publish", "popup"):
            self.assertTrue(sel.get(key), key)

    def test_prompt_template_has_placeholders(self):
        taste = load_taste("default")
        text = build_prompt("USB-C 케이블", taste, {"keyword": "USB-C 케이블", "notes": [], "competitors": []})
        self.assertIn("USB-C 케이블", text)
        self.assertIn(str(taste.min_chars), text)
        self.assertTrue(system_prompt(taste))


class TasteOverlayTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cwd = Path(self.tmp.name)
        self._old = os.getcwd()
        os.chdir(self.cwd)

    def tearDown(self):
        os.chdir(self._old)
        self.tmp.cleanup()

    def test_packaged_default_when_no_local_taste(self):
        taste = load_taste("default")
        self.assertEqual(taste.name, "default")
        self.assertGreaterEqual(taste.min_chars, 1)
        self.assertIn("packaged", taste.root.parts)

    def test_new_pack_and_use(self):
        dest = new_pack("mypack", source="default")
        self.assertTrue((dest / "taste.json").is_file())
        self.assertEqual(main(["taste", "use", "mypack"]), 0)
        buf = io.StringIO()
        with redirect_stdout(buf):
            main(["taste", "show"])
        self.assertIn("mypack", buf.getvalue())

    def test_max_per_run_clamped(self):
        dest = new_pack("spammy", source="default")
        path = dest / "taste.json"
        raw = path.read_text(encoding="utf-8").replace('"max_per_run": 1', '"max_per_run": 99')
        path.write_text(raw, encoding="utf-8")
        taste = load_taste("spammy")
        self.assertEqual(taste.max_per_run, 1)


if __name__ == "__main__":
    unittest.main()
