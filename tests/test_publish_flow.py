import dataclasses
import json
import os
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest import mock

from nblog import publisher, store
from nblog.cli import main
from nblog.gate import evaluate
from nblog.render import assemble_markdown
from nblog.store import list_posts, load_post
from nblog.taste import load_taste, new_pack, set_active
from nblog.writer import normalize_article

FIXTURE = Path(__file__).parent / "fixtures" / "article.json"


class _Loc:
    def __init__(self, page, selector):
        self.page, self.selector, self.first = page, selector, self

    def count(self):
        return 1 if self.selector in self.page.present else 0

    def click(self, **_kw):
        self.page.clicked.append(self.selector)
        if self.selector == self.page.leaves_editor_on:
            self.page.url = self.page.goes_to


class _Page:
    def __init__(self, present, leaves_editor_on="", goes_to="https://blog.naver.com/me/223000000001"):
        self.present = set(present)
        self.leaves_editor_on = leaves_editor_on
        self.goes_to = goes_to
        self.url = "https://blog.naver.com/me/postwrite"
        self.clicked: list[str] = []

    def locator(self, selector):
        return _Loc(self, selector)

    def wait_for_timeout(self, _ms):
        pass


class _Isolated(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        patcher = mock.patch.dict(os.environ)
        patcher.start()
        self.addCleanup(patcher.stop)
        os.environ["NBLOG_DATA_DIR"] = str(Path(self.tmp.name) / "data")
        os.environ["NBLOG_CHROME_PROFILE"] = str(Path(self.tmp.name) / "profile")
        os.environ["NAVER_BLOG_ID"] = "me"
        os.environ.pop("NBLOG_MIN_PUBLISH_HOURS", None)
        self.cwd = Path(self.tmp.name) / "work"
        self.cwd.mkdir()
        old = os.getcwd()
        os.chdir(self.cwd)
        self.addCleanup(os.chdir, old)


class ClickPublishTest(unittest.TestCase):
    def test_missing_confirm_is_not_success(self):
        # 확인 버튼 없이 주소만 바뀌어도 성공이 아니다. URL 검사로는 못 잡는 경우.
        page = _Page(present={"pub"}, leaves_editor_on="pub")
        with self.assertRaises(publisher.PublishError):
            publisher._click_publish(page, ["pub"], ["confirm"])

    def test_still_in_editor_is_not_success(self):
        page = _Page(present={"pub", "confirm"})
        with self.assertRaises(publisher.PublishError):
            publisher._click_publish(page, ["pub"], ["confirm"])

    def test_redirected_editor_url_is_not_success(self):
        # 다른 에디터 주소로 옮겨간 것은 발행이 아니다. 대소문자 무시 검사만 잡는다.
        page = _Page(
            present={"pub", "confirm"},
            leaves_editor_on="confirm",
            goes_to="https://blog.naver.com/PostWriteForm.naver?blogId=me",
        )
        with self.assertRaises(publisher.PublishError):
            publisher._click_publish(page, ["pub"], ["confirm"])

    def test_left_editor_is_success(self):
        page = _Page(present={"pub", "confirm"}, leaves_editor_on="confirm")
        url = publisher._click_publish(page, ["pub"], ["confirm"])
        self.assertNotIn("postwrite", url)
        self.assertEqual(page.clicked, ["pub", "confirm"])


class _RecKeys:
    def __init__(self):
        self.events: list[tuple[str, str]] = []

    def insert_text(self, text):
        self.events.append(("text", text))

    def press(self, combo):
        self.events.append(("press", combo))


class _BodyPage(_Page):
    def __init__(self):
        super().__init__(present={"body"})
        self.keyboard = _RecKeys()

    def wait_for_timeout(self, ms):
        self.keyboard.events.append(("wait", ms))


def _keys_only(events):
    return [e for e in events if e[0] != "wait"]


class FillBodyTest(unittest.TestCase):
    def test_line_breaks_become_enter_presses(self):
        # insert_text 한 번에 넣으면 SmartEditor ONE 이 줄바꿈을 버린다(2026-09-19 실측).
        page = _BodyPage()
        publisher._fill_body(page, "첫 줄\n\n## 소제목\n끝", ["body"])
        self.assertEqual(
            _keys_only(page.keyboard.events),
            [
                ("text", "첫 줄"),
                ("press", "Enter"),
                ("press", "Enter"),
                ("text", "## 소제목"),
                ("press", "Enter"),
                ("text", "끝"),
            ],
        )

    def test_every_key_event_is_followed_by_a_pause(self):
        # 쉬지 않고 넣으면 긴 글 중간부터 문단이 사라진다(2026-09-19 실측, 80ms 대기로 해결).
        page = _BodyPage()
        publisher._fill_body(page, "\n".join(f"줄 {i}" for i in range(30)), ["body"])
        events = page.keyboard.events + [("end", 0)]
        for i, (kind, _v) in enumerate(events[:-1]):
            if kind in ("text", "press"):
                nxt = events[i + 1]
                self.assertEqual(nxt[0], "wait", f"event {i} {kind} not followed by wait")
                self.assertGreaterEqual(nxt[1], publisher.TYPE_PAUSE_MS)

    def test_no_text_contains_newline(self):
        page = _BodyPage()
        publisher._fill_body(page, "a\r\nb\n", ["body"])
        texts = [v for k, v in page.keyboard.events if k == "text"]
        self.assertTrue(all("\n" not in t and "\r" not in t for t in texts), texts)


class _TitleEl:
    def __init__(self, page):
        self.page, self.first = page, self

    def count(self):
        return 1

    def click(self, **_kw):
        pass

    def inner_text(self):
        return self.page.text


class _TitleKeys:
    def __init__(self, page):
        self.page = page

    def press(self, combo):
        if combo == "ControlOrMeta+A":
            self.page.selected = True

    def insert_text(self, text):
        self.page.attempts += 1
        # 처음 drops 번은 첫 글자를 잃는다(실측: 「USB-C」→「SB-C」)
        dropped = text[1:] if self.page.attempts <= self.page.drops else text
        self.page.text = dropped if self.page.selected else self.page.text + dropped
        self.page.selected = False

    def type(self, text, delay=0):
        self.insert_text(text)


class _TitlePage:
    def __init__(self, drops):
        self.drops, self.attempts, self.text, self.selected = drops, 0, "제목", False
        self.keyboard = _TitleKeys(self)

    def locator(self, _s):
        return _TitleEl(self)

    def wait_for_timeout(self, _ms):
        pass


class FillTitleTest(unittest.TestCase):
    def test_retries_when_first_char_dropped(self):
        page = _TitlePage(drops=1)
        publisher._fill_title(page, "USB-C 케이블", ["t"])
        self.assertEqual(page.text, "USB-C 케이블")

    def test_raises_when_title_never_matches(self):
        page = _TitlePage(drops=99)
        with self.assertRaises(publisher.PublishError):
            publisher._fill_title(page, "USB-C 케이블", ["t"])


class _Stop(Exception):
    pass


class RateLimitScopeTest(_Isolated):
    def _publish(self, public):
        with mock.patch.object(publisher, "_playwright", side_effect=_Stop):
            publisher.publish("t", "b", public=public, taste=load_taste("default"))

    def test_cooldown_does_not_block_draft_save(self):
        publisher.mark_published()
        with self.assertRaises(_Stop):
            self._publish(public=False)

    def test_cooldown_blocks_public(self):
        publisher.mark_published()
        with self.assertRaises(publisher.PublishError):
            self._publish(public=True)

    def test_pack_interval_does_not_leak_into_env(self):
        with self.assertRaises(_Stop):
            self._publish(public=True)
        self.assertIsNone(os.environ.get("NBLOG_MIN_PUBLISH_HOURS"))


class DisclosureGateTest(unittest.TestCase):
    def test_required_but_empty_disclosure_fails(self):
        taste = dataclasses.replace(load_taste("review"), disclosure="")
        raw = json.loads(FIXTURE.read_text(encoding="utf-8"))
        article = normalize_article(raw, raw["keyword"], taste)
        gate = evaluate(article, assemble_markdown(article), taste, set())
        self.assertFalse(gate["ok"])
        self.assertTrue(any("고지" in r for r in gate["reasons"]), gate["reasons"])

    def test_whitespace_disclosure_fails(self):
        taste = dataclasses.replace(load_taste("review"), disclosure="  \n")
        raw = json.loads(FIXTURE.read_text(encoding="utf-8"))
        article = normalize_article(raw, raw["keyword"], taste)
        gate = evaluate(article, assemble_markdown(article), taste, set())
        self.assertFalse(gate["ok"])


class PublishCommandTest(_Isolated):
    def setUp(self):
        super().setUp()
        self.calls: list[dict] = []

        def fake(title, body, *, public=False, blog_id=None, taste=None):
            self.calls.append({"public": public, "taste": taste.name})
            return {"ok": True, "url": "", "screenshot": ""}

        patcher = mock.patch.object(publisher, "publish", fake)
        patcher.start()
        self.addCleanup(patcher.stop)

    def _draft(self, taste):
        self.assertEqual(main(["draft", "--from-json", str(FIXTURE), "--taste", taste]), 0)
        return list_posts()[0]["id"]

    def test_uses_pack_the_post_was_drafted_with(self):
        new_pack("mine", source="default")
        set_active("mine")
        post_id = self._draft("review")
        main(["approve", post_id])
        self.assertEqual(main(["publish", post_id]), 0)
        self.assertEqual(self.calls[-1]["taste"], "review")

    def test_taste_flag_overrides(self):
        post_id = self._draft("review")
        main(["approve", post_id])
        self.assertEqual(main(["publish", post_id, "--taste", "default"]), 0)
        self.assertEqual(self.calls[-1]["taste"], "default")

    def test_public_after_draft_save_keeps_approval(self):
        post_id = self._draft("review")
        main(["approve", post_id])
        self.assertEqual(main(["publish", post_id]), 0)
        self.assertEqual(load_post(post_id)["status"], "naver_draft")
        self.assertEqual(main(["publish", post_id, "--public"]), 0)
        self.assertTrue(self.calls[-1]["public"])

    def test_post_approved_before_0_2_2_keeps_approval(self):
        post_id = self._draft("review")
        store.update_status(post_id, "approved")  # 예전 레코드: approved 플래그 없음
        self.assertEqual(main(["publish", post_id]), 0)
        self.assertEqual(main(["publish", post_id, "--public"]), 0)

    def test_forced_publish_does_not_grant_approval(self):
        post_id = self._draft("review")
        self.assertEqual(main(["publish", post_id, "--force"]), 0)
        self.assertEqual(main(["publish", post_id, "--public"]), 2)

    def test_unapproved_still_blocked(self):
        post_id = self._draft("review")
        self.assertEqual(main(["publish", post_id]), 2)
        self.assertEqual(self.calls, [])


class PostIdTest(_Isolated):
    def test_same_second_same_slug_gets_distinct_ids(self):
        with mock.patch("nblog.store.datetime") as clock:
            clock.now.return_value = datetime(2026, 1, 2, 3, 4, 5)
            first = store.new_id("같은 제목")
            store.save_post({"id": first, "title": "먼저 쓴 글"})
            second = store.new_id("같은 제목")
        self.assertNotEqual(first, second)
        self.assertEqual(store.load_post(first)["title"], "먼저 쓴 글")


if __name__ == "__main__":
    unittest.main()
