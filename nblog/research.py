"""역할: 키워드 경쟁·트렌드 요약. API 키가 없으면 빈 리서치로 초안만 진행.
고칠 때: 네이버 API URL은 naver_api.py, 프롬프트에 넣는 문장은 research_prompt_block().
"""

from __future__ import annotations

import re
from typing import Any

from nblog import naver_api


def _strip_tags(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text or "").strip()


def research(keyword: str) -> dict[str, Any]:
    result: dict[str, Any] = {
        "keyword": keyword,
        "total": None,
        "trend_last": None,
        "competitors": [],
        "notes": [],
    }
    if not naver_api.configured():
        result["notes"].append("네이버 API 키 없음 — 리서치 생략, 초안만 작성")
        return result

    try:
        blog = naver_api.search_blog(keyword, display=8, sort="sim")
    except naver_api.NaverAPIError as exc:
        result["notes"].append(f"블로그 검색 실패: {exc}")
        return result

    result["total"] = blog.get("total")
    items = []
    for item in blog.get("items") or []:
        items.append(
            {
                "title": _strip_tags(str(item.get("title") or "")),
                "link": item.get("link") or "",
                "description": _strip_tags(str(item.get("description") or "")),
                "blogger": item.get("bloggername") or "",
                "postdate": item.get("postdate") or "",
            }
        )
    result["competitors"] = items

    try:
        trend = naver_api.search_trend(keyword)
        series = ((trend.get("results") or [{}])[0].get("data") or [])
        if series:
            result["trend_last"] = series[-1]
            result["trend_points"] = series[-6:]
    except naver_api.NaverAPIError as exc:
        result["notes"].append(f"데이터랩 생략: {exc}")

    total = result["total"]
    if isinstance(total, int):
        if total > 500_000:
            result["notes"].append("검색 결과 많음 — 각도를 좁힌 제목이 유리")
        elif total < 5_000:
            result["notes"].append("검색 결과 적음 — 수요가 작을 수 있음")
    return result


def research_prompt_block(data: dict[str, Any]) -> str:
    lines = [f"키워드: {data.get('keyword')}", f"검색 결과 수: {data.get('total')}"]
    if data.get("trend_last"):
        lines.append(f"최근 트렌드 상대값: {data['trend_last']}")
    for note in data.get("notes") or []:
        lines.append(f"- {note}")
    lines.append("상위 글:")
    for item in (data.get("competitors") or [])[:6]:
        lines.append(f"- {item.get('title')} ({item.get('blogger')})")
        desc = item.get("description") or ""
        if desc:
            lines.append(f"  {desc[:160]}")
    return "\n".join(lines)
