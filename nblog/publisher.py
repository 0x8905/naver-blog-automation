"""역할: 본인 네이버 블로그 Playwright 발행. 비밀번호를 저장하지 않는다.
고칠 때: 버튼이 안 눌리면 selectors.json만 고친다. 로직 변경은 publish() .
"""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from nblog.config import data_dir
from nblog.taste import Taste, load_taste


class PublishError(RuntimeError):
    pass


def load_selectors(taste: Taste | None = None) -> dict[str, Any]:
    pack = taste or load_taste()
    return json.loads(pack.file(pack.selectors_rel).read_text(encoding="utf-8"))


def _as_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(x) for x in value if str(x).strip()]
    if value:
        return [str(value)]
    return []


def profile_dir() -> Path:
    raw = os.environ.get("NBLOG_CHROME_PROFILE") or ".chrome-profile"
    path = Path(raw).expanduser()
    if not path.is_absolute():
        path = Path.cwd() / path
    path.mkdir(parents=True, exist_ok=True)
    return path


def browser_channel() -> str:
    """빈 값이면 Playwright 번들 Chromium. chrome·msedge는 설치된 브라우저."""
    return (os.environ.get("NBLOG_BROWSER_CHANNEL") or "").strip()


def _launch_kwargs() -> dict[str, Any]:
    kwargs: dict[str, Any] = {"user_data_dir": str(profile_dir()), "headless": False}
    channel = browser_channel()
    if channel:
        kwargs["channel"] = channel
    return kwargs


def screenshot_dir() -> Path:
    path = Path.cwd() / "screenshots"
    path.mkdir(parents=True, exist_ok=True)
    return path


def min_hours(pack_hours: float | None = None) -> float:
    """환경변수 > 취향 팩 > 6시간. 프로세스 환경은 건드리지 않는다."""
    raw = os.environ.get("NBLOG_MIN_PUBLISH_HOURS")
    if raw:
        try:
            return float(raw)
        except ValueError:
            pass
    return float(pack_hours) if pack_hours else 6.0


def _state_path() -> Path:
    path = data_dir()
    path.mkdir(parents=True, exist_ok=True)
    return path / "publish_state.json"


def last_publish_at() -> datetime | None:
    path = _state_path()
    if not path.is_file():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8")).get("last_publish_at")
        if not raw:
            return None
        return datetime.fromisoformat(raw)
    except (OSError, ValueError):
        return None


def mark_published() -> None:
    _state_path().write_text(
        json.dumps(
            {"last_publish_at": datetime.now(timezone.utc).astimezone().isoformat()},
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def check_rate_limit(pack_hours: float | None = None) -> None:
    last = last_publish_at()
    if not last:
        return
    hours = min_hours(pack_hours)
    wait_until = last + timedelta(hours=hours)
    now = datetime.now(timezone.utc).astimezone()
    if now < wait_until:
        raise PublishError(
            f"발행 간격 제한: {hours:g}시간. {wait_until.isoformat(timespec='minutes')} 이후 가능"
        )


def _playwright():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise PublishError("playwright 미설치. pip install 'naver-blog-automation[publish]'") from exc
    return sync_playwright()


def login() -> None:
    """헤드 브라우저를 열고 사용자가 직접 로그인할 때까지 기다린다."""
    blog_id = os.environ.get("NAVER_BLOG_ID") or ""
    start = f"https://blog.naver.com/{blog_id}" if blog_id else "https://nid.naver.com/nidlogin.login"
    with _playwright() as p:
        context = p.chromium.launch_persistent_context(**_launch_kwargs())
        page = context.pages[0] if context.pages else context.new_page()
        page.goto(start, wait_until="domcontentloaded")
        print("브라우저에서 네이버에 로그인한 뒤 이 터미널에서 Enter를 누르세요.")
        print("로그인할 때 「로그인 상태 유지」를 체크하세요. 안 하면 창을 닫는 순간 로그인이 풀립니다.")
        print("비밀번호는 .env에 넣지 마세요.")
        try:
            input()
        except EOFError:
            time.sleep(60)
        context.close()


def publish(
    title: str,
    body: str,
    *,
    public: bool = False,
    blog_id: str | None = None,
    taste: Taste | None = None,
) -> dict[str, Any]:
    """본문 텍스트를 에디터에 넣고 임시저장(기본) 또는 발행한다."""
    pack = taste or load_taste()
    if public:
        # 간격 제한은 공개 발행에만 건다. 임시저장은 막지 않는다.
        check_rate_limit(pack.min_hours)
    blog_id = blog_id or os.environ.get("NAVER_BLOG_ID") or ""
    if not blog_id:
        raise PublishError("NAVER_BLOG_ID가 없습니다.")
    if public and pack.publish_mode != "public":
        # 취향이 draft여도 CLI --public 은 명시 플래그로 허용. 자동 공개는 안 함.
        pass
    sel = load_selectors(pack)
    url = f"https://blog.naver.com/{blog_id}/postwrite"
    shot = screenshot_dir() / f"publish-{int(time.time())}.png"
    with _playwright() as p:
        context = p.chromium.launch_persistent_context(**_launch_kwargs())
        page = context.pages[0] if context.pages else context.new_page()
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=60_000)
            page.wait_for_timeout(2500)
            current = page.url
            if "nidlogin" in current or "nid.naver.com" in current:
                raise PublishError("로그인 세션 없음. 먼저 `nblog login`을 실행하세요.")
            _dismiss_popups(page, _as_list(sel.get("popup")))
            _fill_title(page, title, _as_list(sel.get("title")))
            _fill_body(page, body, _as_list(sel.get("body")))
            if public:
                result_url = _click_publish(
                    page,
                    _as_list(sel.get("publish")),
                    _as_list(sel.get("publish_confirm")),
                )
            else:
                _click_first(page, _as_list(sel.get("save_draft")), "임시저장 버튼을 찾지 못했습니다.")
                result_url = ""
            if public:
                mark_published()
            try:
                page.screenshot(path=str(shot), full_page=True)
            except Exception:
                # 스크린샷은 진단용. 실패해도 발행 결과를 뒤집지 않는다.
                pass
            return {
                "ok": True,
                "mode": "public" if public else "naver_draft",
                "url": result_url,
                "screenshot": str(shot),
            }
        except Exception:
            try:
                page.screenshot(path=str(shot), full_page=True)
            except Exception:
                pass
            raise
        finally:
            context.close()


def _dismiss_popups(page: Any, selectors: list[str]) -> None:
    for selector in selectors:
        loc = page.locator(selector)
        if loc.count() > 0:
            try:
                loc.first.click(timeout=1500)
                page.wait_for_timeout(400)
            except Exception:
                continue


def _fill_title(page: Any, title: str, selectors: list[str]) -> None:
    for selector in selectors:
        loc = page.locator(selector)
        if loc.count() == 0:
            continue
        el = loc.first
        el.click()
        page.keyboard.press("ControlOrMeta+A")
        page.keyboard.type(title, delay=20)
        return
    raise PublishError("제목 입력란을 찾지 못했습니다. selectors.json의 title을 고치세요.")


def _fill_body(page: Any, body: str, selectors: list[str]) -> None:
    for selector in selectors:
        loc = page.locator(selector)
        if loc.count() == 0:
            continue
        loc.first.click()
        page.wait_for_timeout(300)
        page.keyboard.insert_text(body)
        return
    raise PublishError("본문 입력란을 찾지 못했습니다. selectors.json의 body를 고치세요.")


def _click_first(page: Any, selectors: list[str], error: str) -> None:
    for selector in selectors:
        loc = page.locator(selector)
        if loc.count() > 0:
            loc.first.click()
            page.wait_for_timeout(1500)
            return
    raise PublishError(error)


def _click_publish(page: Any, publish: list[str], confirm: list[str]) -> str:
    editor_url = page.url
    _click_first(page, publish, "발행 버튼을 찾지 못했습니다. selectors.json의 publish를 고치세요.")
    page.wait_for_timeout(1000)
    if confirm:
        _click_first(
            page,
            confirm,
            "발행 확인 버튼을 찾지 못했습니다. selectors.json의 publish_confirm을 고치세요.",
        )
    # 발행되면 에디터 주소를 떠난다. 그대로면 성공으로 기록하지 않는다.
    for _ in range(15):
        current = page.url
        if current != editor_url and "postwrite" not in current.lower():
            return current
        page.wait_for_timeout(1000)
    raise PublishError("발행 후에도 에디터 화면입니다. 발행되지 않았을 수 있습니다. 스크린샷을 확인하세요.")
