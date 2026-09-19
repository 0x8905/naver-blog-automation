"""역할: draft 한 건의 순서 (리서치 → 초안 → 게이트 → 저장).
고칠 때: 단계 추가는 여기만. 취향 값은 taste 팩에서 읽는다.
"""

from __future__ import annotations

from typing import Any

from nblog.gate import evaluate
from nblog.render import assemble_markdown, markdown_to_naver_html
from nblog.research import research
from nblog.store import create_post, existing_titles
from nblog.taste import load_taste
from nblog.writer import generate_article, load_article_file


def run_draft(
    *,
    keyword: str = "",
    taste_name: str | None = None,
    from_json: str | None = None,
    skip_research: bool = False,
    force: bool = False,
) -> tuple[int, dict[str, Any]]:
    taste = load_taste(taste_name)
    keyword = keyword.strip()

    if from_json:
        article = load_article_file(from_json, keyword, taste)
        keyword = keyword or str(article.get("keyword") or "")
        research_data: dict[str, Any] = {
            "keyword": keyword,
            "notes": ["from-json"],
            "competitors": [],
        }
    else:
        if not keyword:
            raise ValueError("키워드가 필요합니다.")
        if skip_research:
            research_data = {"keyword": keyword, "notes": ["리서치 생략"], "competitors": []}
        else:
            research_data = research(keyword)
        article = generate_article(keyword, taste, research_data)

    markdown = assemble_markdown(article)
    html = markdown_to_naver_html(markdown)
    gate = evaluate(article, markdown, taste, existing_titles())
    if force and not gate.get("ok"):
        gate = {**gate, "forced": True}
    status = "draft" if gate.get("ok") or force else "rejected"
    post = create_post(
        profile_id=taste.name,
        keyword=keyword,
        article=article,
        research=research_data,
        gate=gate,
        markdown=markdown,
        html=html,
        status=status,
    )
    code = 0 if status == "draft" else 2
    return code, post
