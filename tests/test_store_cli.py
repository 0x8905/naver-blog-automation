import json
import os
import tempfile
import unittest
from pathlib import Path

from nblog.cli import main
from nblog.store import list_posts, load_post


class StoreCliTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.data = Path(self.tmp.name) / "data"
        self.cwd = Path(self.tmp.name) / "work"
        self.cwd.mkdir()
        os.environ["NBLOG_DATA_DIR"] = str(self.data)
        self._old = os.getcwd()
        os.chdir(self.cwd)

    def tearDown(self):
        os.chdir(self._old)
        self.tmp.cleanup()
        os.environ.pop("NBLOG_DATA_DIR", None)

    def test_draft_from_json_and_approve(self):
        fixture = Path(__file__).parent / "fixtures" / "article.json"
        code = main(["draft", "--from-json", str(fixture), "--taste", "review"])
        self.assertEqual(code, 0)
        posts = list_posts()
        self.assertEqual(len(posts), 1)
        post = posts[0]
        self.assertEqual(post["status"], "draft")
        self.assertTrue(Path(post["md_path"]).is_file())
        self.assertTrue(Path(post["html_path"]).is_file())
        html = Path(post["html_path"]).read_text(encoding="utf-8")
        self.assertIn("<h2>", html)

        self.assertEqual(main(["list"]), 0)
        self.assertEqual(main(["show", post["id"]]), 0)
        self.assertEqual(main(["approve", post["id"]]), 0)
        self.assertEqual(load_post(post["id"])["status"], "approved")

    def test_doctor(self):
        self.assertEqual(main(["doctor"]), 0)

    def test_help(self):
        with self.assertRaises(SystemExit) as ctx:
            main(["--help"])
        self.assertEqual(ctx.exception.code, 0)

    def test_reject_without_force_still_saves(self):
        payload = {
            "keyword": "테스트",
            "title": "짧은글",
            "ai_answer": "한줄",
            "tags": ["t"],
            "body_markdown": "짧다",
            "faq": [],
            "compare": [],
        }
        src = Path(self.tmp.name) / "short.json"
        src.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        code = main(["draft", "--from-json", str(src), "--taste", "review"])
        self.assertEqual(code, 2)
        posts = list_posts()
        self.assertEqual(posts[0]["status"], "rejected")


if __name__ == "__main__":
    unittest.main()
