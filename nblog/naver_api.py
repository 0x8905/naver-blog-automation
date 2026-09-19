"""역할: 네이버 공식 검색·데이터랩 API. 글쓰기 API는 2020년에 종료됨.
고칠 때: 엔드포인트·헤더만 여기. 호출 조합은 research.py.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, timedelta
from typing import Any


class NaverAPIError(RuntimeError):
    pass


def _client() -> tuple[str, str]:
    cid = os.environ.get("NAVER_CLIENT_ID") or ""
    secret = os.environ.get("NAVER_CLIENT_SECRET") or ""
    return cid, secret


def configured() -> bool:
    cid, secret = _client()
    return bool(cid and secret)


def _get(url: str) -> dict[str, Any]:
    cid, secret = _client()
    if not cid or not secret:
        raise NaverAPIError("NAVER_CLIENT_ID / NAVER_CLIENT_SECRET이 없습니다.")
    req = urllib.request.Request(
        url,
        headers={
            "X-Naver-Client-Id": cid,
            "X-Naver-Client-Secret": secret,
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:400]
        raise NaverAPIError(f"HTTP {exc.code}: {detail}") from exc


def search_blog(query: str, display: int = 10, sort: str = "sim") -> dict[str, Any]:
    qs = urllib.parse.urlencode(
        {
            "query": query,
            "display": max(1, min(display, 100)),
            "start": 1,
            "sort": sort,
        }
    )
    return _get(f"https://openapi.naver.com/v1/search/blog.json?{qs}")


def search_trend(keyword: str, days: int = 90) -> dict[str, Any]:
    cid, secret = _client()
    if not cid or not secret:
        raise NaverAPIError("NAVER_CLIENT_ID / NAVER_CLIENT_SECRET이 없습니다.")
    end = date.today()
    start = end - timedelta(days=days)
    payload = {
        "startDate": start.isoformat(),
        "endDate": end.isoformat(),
        "timeUnit": "week",
        "keywordGroups": [{"groupName": keyword[:80], "keywords": [keyword]}],
    }
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        "https://openapi.naver.com/v1/datalab/search",
        data=body,
        headers={
            "Content-Type": "application/json",
            "X-Naver-Client-Id": cid,
            "X-Naver-Client-Secret": secret,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:400]
        raise NaverAPIError(f"데이터랩 HTTP {exc.code}: {detail}") from exc
