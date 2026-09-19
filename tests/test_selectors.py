import json
import unittest
from pathlib import Path

from nblog.taste import PACKAGED_DIR

ROOT = Path(__file__).resolve().parents[1]
PACKS = [PACKAGED_DIR / "default", PACKAGED_DIR / "review", ROOT / "taste" / "default"]

# 2026-09-19 실제 SmartEditor ONE(/postwrite)에서 확인한 잘못된 매칭.
# - ".se-module.se-module-text" 첫 매칭 = 제목 모듈 → 본문이 제목란에 들어간다
# - "button:has-text('발행')" 첫 매칭 = 숨은 「예약 발행」 버튼
# - "button:has-text('글쓰기')" 는 발행 버튼이 아니다
KNOWN_BAD = {
    "body": {".se-module.se-module-text"},
    "publish": {"button:has-text('발행')", "button:has-text('글쓰기')"},
}


def _load(pack: Path) -> dict:
    return json.loads((pack / "selectors.json").read_text(encoding="utf-8"))


class SelectorPackTest(unittest.TestCase):
    def test_known_bad_selectors_absent(self):
        for pack in PACKS:
            sel = _load(pack)
            for key, bad in KNOWN_BAD.items():
                self.assertFalse(bad & set(sel[key]), f"{pack.name}:{key}")

    def test_title_and_body_target_different_sections(self):
        for pack in PACKS:
            sel = _load(pack)
            self.assertIn("documentTitle", sel["title"][0], pack.name)
            self.assertNotIn("documentTitle", sel["body"][0], pack.name)
            self.assertFalse(set(sel["title"]) & set(sel["body"]), pack.name)

    def test_resume_popup_is_cancelled_not_confirmed(self):
        # 「작성 중인 글이 있습니다. 이어서 작성하시겠습니까?」 에서 확인을 누르면
        # 예전 내용 위에 새 글이 섞인다. 취소가 먼저여야 한다.
        for pack in PACKS:
            popup = _load(pack)["popup"]
            cancel = next(i for i, s in enumerate(popup) if "cancel" in s)
            confirm = [i for i, s in enumerate(popup) if "확인" in s or "confirm" in s]
            self.assertTrue(all(cancel < i for i in confirm), pack.name)

    def test_repo_default_matches_packaged_default(self):
        self.assertEqual(_load(ROOT / "taste" / "default"), _load(PACKAGED_DIR / "default"))


if __name__ == "__main__":
    unittest.main()
