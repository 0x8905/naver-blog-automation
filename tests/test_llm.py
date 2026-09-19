import unittest

from nblog.llm import LLMError, extract_json


class ExtractJsonTest(unittest.TestCase):
    def test_plain_object(self):
        data = extract_json('{"title": "안녕", "tags": ["a"]}')
        self.assertEqual(data["title"], "안녕")

    def test_fenced_block(self):
        raw = """설명문\n```json\n{"title": "제목"}\n```\n"""
        self.assertEqual(extract_json(raw)["title"], "제목")

    def test_missing_object(self):
        with self.assertRaises(LLMError):
            extract_json("제목만 있는 텍스트")


if __name__ == "__main__":
    unittest.main()
