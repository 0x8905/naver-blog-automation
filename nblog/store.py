"""역할: 로컬 JSON 큐 (data/posts, data/out).
고칠 때: 글 JSON 필드가 늘면 create_post()와 이 스키마만 맞춘다.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from nblog.config import data_dir


def _now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9가-힣]+", "-", text).strip("-")
    return slug[:48] or "post"


def posts_dir() -> Path:
    path = data_dir() / "posts"
    path.mkdir(parents=True, exist_ok=True)
    return path


def out_dir() -> Path:
    path = data_dir() / "out"
    path.mkdir(parents=True, exist_ok=True)
    return path


def new_id(title: str) -> str:
    """ID를 정하고 빈 파일로 선점한다. 같은 초·같은 슬러그면 번호를 붙인다."""
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    base = f"{stamp}-{slugify(title)}"
    candidate, n = base, 1
    while True:
        try:
            # "x" 모드는 원자적 생성. 동시에 도는 다른 draft와도 겹치지 않는다.
            (posts_dir() / f"{candidate}.json").open("x").close()
            return candidate
        except FileExistsError:
            n += 1
            candidate = f"{base}-{n}"


def save_post(post: dict[str, Any]) -> Path:
    path = posts_dir() / f"{post['id']}.json"
    path.write_text(json.dumps(post, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def write_outputs(post_id: str, markdown: str, html: str) -> tuple[Path, Path]:
    md_path = out_dir() / f"{post_id}.md"
    html_path = out_dir() / f"{post_id}.html"
    md_path.write_text(markdown, encoding="utf-8")
    html_path.write_text(html, encoding="utf-8")
    return md_path, html_path


def load_post(post_id: str) -> dict[str, Any]:
    path = posts_dir() / f"{post_id}.json"
    if not path.is_file():
        raise FileNotFoundError(f"글 없음: {post_id}")
    return json.loads(path.read_text(encoding="utf-8"))


def list_posts() -> list[dict[str, Any]]:
    posts = []
    for path in sorted(posts_dir().glob("*.json"), reverse=True):
        try:
            posts.append(json.loads(path.read_text(encoding="utf-8")))
        except json.JSONDecodeError:
            continue
    return posts


def existing_titles(exclude_id: str | None = None) -> set[str]:
    titles = set()
    for post in list_posts():
        if exclude_id and post.get("id") == exclude_id:
            continue
        title = post.get("title") or (post.get("article") or {}).get("title")
        if title:
            titles.add(str(title))
    return titles


def update_status(post_id: str, status: str, **extra: Any) -> dict[str, Any]:
    post = load_post(post_id)
    post["status"] = status
    post["updated_at"] = _now()
    post.update(extra)
    save_post(post)
    return post


def create_post(
    *,
    profile_id: str,
    keyword: str,
    article: dict[str, Any],
    research: dict[str, Any],
    gate: dict[str, Any],
    markdown: str,
    html: str,
    status: str | None = None,
) -> dict[str, Any]:
    post_id = new_id(article["title"])
    md_path, html_path = write_outputs(post_id, markdown, html)
    post = {
        "id": post_id,
        "status": status or ("draft" if gate.get("ok") else "rejected"),
        "profile": profile_id,
        "keyword": keyword,
        "title": article["title"],
        "created_at": _now(),
        "updated_at": _now(),
        "article": article,
        "research": research,
        "gate": gate,
        "md_path": str(md_path),
        "html_path": str(html_path),
        "published_url": "",
    }
    save_post(post)
    return post
