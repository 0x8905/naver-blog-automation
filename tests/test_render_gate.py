import json
import unittest
from pathlib import Path

from nblog.gate import evaluate
from nblog.render import assemble_markdown, markdown_to_naver_html
from nblog.taste import load_taste
from nblog.writer import normalize_article

FIXTURE = Path(__file__).parent / "fixtures" / "article.json"


class RenderGateTest(unittest.TestCase):
    def setUp(self):
        self.taste = load_taste("review")
        raw = json.loads(FIXTURE.read_text(encoding="utf-8"))
        self.article = normalize_article(raw, raw["keyword"], self.taste)
        self.markdown = assemble_markdown(self.article)

    def test_assemble_has_title_faq_disclosure(self):
        self.assertIn("# USB-C 케이블", self.markdown)
        self.assertIn("자주 묻는 질문", self.markdown)
        self.assertIn(self.taste.disclosure, self.markdown)
        self.assertIn("#USB-C", self.markdown)

    def test_html_has_table_and_h2(self):
        html = markdown_to_naver_html(self.markdown)
        self.assertIn("<h2>", html)
        self.assertIn("<table", html)
        self.assertIn("<blockquote>", html)
        self.assertNotIn("<script", html)

    def test_gate_pass(self):
        gate = evaluate(self.article, self.markdown, self.taste, set())
        self.assertTrue(gate["ok"], gate["reasons"])
        self.assertGreaterEqual(gate["score"], 80)

    def test_gate_duplicate_title(self):
        gate = evaluate(self.article, self.markdown, self.taste, {self.article["title"]})
        self.assertFalse(gate["ok"])
        self.assertTrue(any("제목" in r for r in gate["reasons"]))

    def test_gate_short_body(self):
        short = dict(self.article)
        short["body_markdown"] = "짧음"
        md = assemble_markdown(short)
        gate = evaluate(short, md, self.taste, set())
        self.assertFalse(gate["ok"])

    def test_ban_list(self):
        taste = load_taste("default")
        taste.ban_list.append("금지단어XYZ")
        article = dict(self.article)
        article["body_markdown"] = (self.article["body_markdown"] or "") + "\n금지단어XYZ\n"
        md = assemble_markdown(article)
        gate = evaluate(article, md, taste, set())
        self.assertTrue(any("금칙어" in r for r in gate["reasons"]))


if __name__ == "__main__":
    unittest.main()
