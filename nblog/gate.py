"""역할: 발행 전 기계 검수.
고칠 때: 코어 안전(AI 누설·스크립트)은 유지. 분량/FAQ/금칙어는 taste.json.
"""

from __future__ import annotations

import re
from typing import Any

from nblog.taste import Taste

AI_LEAK = re.compile(
    r"(as an ai|language model|저는\s*ai|인공지능으로서|as a large language)",
    re.I,
)
FOREIGN = re.compile(r"[Ѐ-ӿ֐-׿؀-ۿऀ-ॿ฀-๿]")


def evaluate(article: dict[str, Any], markdown: str, taste: Taste, titles: set[str]) -> dict[str, Any]:
    reasons: list[str] = []
    body = markdown.strip()
    chars = len(re.sub(r"\s+", "", body))
    if chars < taste.min_chars:
        reasons.append(f"본문 {chars}자 < 최소 {taste.min_chars}자")
    if not re.search(r"^## ", markdown, re.M):
        reasons.append("H2 소제목 없음")
    keyword = str(article.get("keyword") or "")
    if keyword and keyword.replace(" ", "") not in body.replace(" ", ""):
        reasons.append("키워드가 본문에 없음")
    title = str(article.get("title") or "")
    if not title:
        reasons.append("제목 없음")
    if len(title) > taste.title_max:
        reasons.append(f"제목이 {taste.title_max}자를 넘김")
    if title in titles:
        reasons.append("같은 제목이 이미 큐에 있음")
    if taste.require_faq and len(article.get("faq") or []) < taste.min_faq:
        reasons.append(f"FAQ {taste.min_faq}개 미만")
    if taste.require_compare and len(article.get("compare") or []) < taste.min_compare:
        reasons.append(f"비교표 {taste.min_compare}행 미만")
    if taste.require_disclosure:
        disclosure = taste.disclosure or article.get("disclosure") or ""
        if disclosure and disclosure not in markdown:
            reasons.append("제휴 고지문구 없음")
    if AI_LEAK.search(body):
        reasons.append("AI 자기소개 문장")
    if FOREIGN.search(body):
        reasons.append("허용 외 스크립트 문자")
    lowered = body.lower()
    for word in taste.ban_list:
        if word and word.lower() in lowered:
            reasons.append(f"금칙어: {word}")
    score = max(0, 100 - 12 * len(reasons))
    if chars >= taste.min_chars + 400:
        score = min(100, score + 4)
    return {
        "ok": not reasons,
        "score": score,
        "chars": chars,
        "reasons": reasons,
    }
