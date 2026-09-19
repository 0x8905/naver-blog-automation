import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from nblog import llm, publisher
from nblog.config import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
LLM_ENV = ("NBLOG_PROVIDER", "NBLOG_MODEL", "OPENAI_BASE_URL")


class EnvExampleTest(unittest.TestCase):
    def setUp(self):
        # patch.dict는 종료 시 os.environ을 원래대로 되돌린다.
        patcher = mock.patch.dict(os.environ)
        patcher.start()
        self.addCleanup(patcher.stop)
        for key in LLM_ENV:
            os.environ.pop(key, None)

    def test_example_does_not_override_taste_llm(self):
        self.assertTrue((ROOT / ".env.example").is_file())
        load_dotenv(ROOT / ".env.example")
        for key in LLM_ENV:
            self.assertIsNone(os.environ.get(key), key)

    def test_taste_llm_used_when_env_unset(self):
        seen = {}

        def fake(prompt, system, model="", endpoint=""):
            seen.update(model=model, endpoint=endpoint)
            return "{}"

        with mock.patch.dict(llm.PROVIDERS, {"anthropic": fake}):
            llm.complete("p", provider="anthropic", model="m1", endpoint="e1")
        self.assertEqual(seen, {"model": "m1", "endpoint": "e1"})


class _Loc:
    def __init__(self):
        self.first = self

    def count(self):
        return 1

    def click(self):
        pass


class _Keys:
    def __init__(self):
        self.pressed: list[str] = []
        self.typed: list[str] = []

    def press(self, combo):
        self.pressed.append(combo)

    def type(self, text, delay=0):
        self.typed.append(text)


class _Page:
    def __init__(self):
        self.keyboard = _Keys()

    def locator(self, _selector):
        return _Loc()


class TitleShortcutTest(unittest.TestCase):
    def test_select_all_works_off_macos(self):
        page = _Page()
        publisher._fill_title(page, "제목", ["x"])
        self.assertEqual(page.keyboard.pressed, ["ControlOrMeta+A"])
        self.assertEqual(page.keyboard.typed, ["제목"])


class BrowserChannelTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        patcher = mock.patch.dict(os.environ)
        patcher.start()
        self.addCleanup(patcher.stop)
        os.environ["NBLOG_CHROME_PROFILE"] = str(Path(self.tmp.name) / "profile")
        os.environ.pop("NBLOG_BROWSER_CHANNEL", None)

    def test_default_uses_bundled_chromium(self):
        kwargs = publisher._launch_kwargs()
        self.assertNotIn("channel", kwargs)
        self.assertFalse(kwargs["headless"])

    def test_channel_from_env(self):
        os.environ["NBLOG_BROWSER_CHANNEL"] = "chrome"
        self.assertEqual(publisher._launch_kwargs()["channel"], "chrome")


if __name__ == "__main__":
    unittest.main()
