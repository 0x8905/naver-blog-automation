"""역할: LLM 초안 → article dict.
고칠 때: 문장은 taste 팩의 prompts/*.txt. 여기 코드는 파싱만.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from nblog.llm import LLMError, complete, extract_json
from nblog.research import research_prompt_block
from nblog.taste import Taste


class _Safe(dict):
    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


def system_prompt(taste: Taste) -> str:
    return taste.read_prompt("system").strip()


def build_prompt(keyword: str, taste: Taste, research: dict[str, Any]) -> str:
    template = taste.read_prompt("draft")
    return template.format_map(
        _Safe(
            persona=taste.persona,
            tone=taste.tone,
            keyword=keyword,
            profile_name=taste.name,
            research=research_prompt_block(research),
            min_chars=taste.min_chars,
            prompt_extra=taste.prompt_extra,
        )
    ).strip()


def generate_article(keyword: str, taste: Taste, research: dict[str, Any]) -> dict[str, Any]:
    prompt = build_prompt(keyword, taste, research)
    system = system_prompt(taste)
    raw = complete(
        prompt,
        system=system,
        provider=taste.llm_provider,
        model=taste.llm_model,
        endpoint=taste.llm_endpoint,
    )
    try:
        article = extract_json(raw)
    except LLMError:
        raw = complete(
            prompt + "\n\n이전 출력이 JSON이 아니었다. JSON 객체만 출력하라.",
            system=system,
            provider=taste.llm_provider,
            model=taste.llm_model,
            endpoint=taste.llm_endpoint,
        )
        article = extract_json(raw)
    return normalize_article(article, keyword, taste)


def normalize_article(article: dict[str, Any], keyword: str, taste: Taste) -> dict[str, Any]:
    title = str(article.get("title") or keyword).strip()
    tags = [str(t).strip() for t in (article.get("tags") or []) if str(t).strip()]
    for extra in taste.tags_extra:
        if extra not in tags:
            tags.append(extra)
    faq = []
    for row in article.get("faq") or []:
        if not isinstance(row, dict):
            continue
        q, a = str(row.get("q") or "").strip(), str(row.get("a") or "").strip()
        if q and a:
            faq.append({"q": q, "a": a})
    compare = []
    for row in article.get("compare") or []:
        if not isinstance(row, dict):
            continue
        situation = str(row.get("situation") or row.get("item") or "").strip()
        choice = str(row.get("choice") or row.get("best") or "").strip()
        reason = str(row.get("reason") or "").strip()
        if situation and choice:
            compare.append({"situation": situation, "choice": choice, "reason": reason})
    images = []
    for row in article.get("image_prompts") or []:
        if not isinstance(row, dict):
            continue
        images.append(
            {
                "placement": str(row.get("placement") or "").strip(),
                "prompt": str(row.get("prompt") or "").strip(),
            }
        )
    return {
        "keyword": keyword,
        "title": title,
        "ai_answer": str(article.get("ai_answer") or "").strip(),
        "tags": tags[:12],
        "body_markdown": str(article.get("body_markdown") or "").strip(),
        "faq": faq,
        "compare": compare,
        "recommended_for": [str(x).strip() for x in (article.get("recommended_for") or []) if str(x).strip()],
        "not_for": [str(x).strip() for x in (article.get("not_for") or []) if str(x).strip()],
        "image_prompts": images,
        "disclosure": taste.disclosure,
        "cta": taste.cta,
    }


def load_article_file(path: str, keyword: str, taste: Taste) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("from-json 파일은 객체여야 합니다.")
    return normalize_article(payload, keyword or str(payload.get("keyword") or ""), taste)
