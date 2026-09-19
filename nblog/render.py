"""역할: article dict → 마크다운 → 네이버 붙여넣기 HTML.
고칠 때: 섹션 제목·표 모양은 assemble_markdown(), 태그 변환은 markdown_to_naver_html().
"""

from __future__ import annotations

import html
import re
from typing import Any


def assemble_markdown(article: dict[str, Any]) -> str:
    parts: list[str] = [f"# {article['title']}", ""]
    if article.get("ai_answer"):
        parts.extend([f"> {article['ai_answer']}", ""])
    parts.append(article.get("body_markdown") or "")
    compare = article.get("compare") or []
    if compare:
        parts.extend(["", "## 상황별 선택", "", "| 상황 | 선택 | 이유 |", "| --- | --- | --- |"])
        for row in compare:
            parts.append(
                f"| {row.get('situation','')} | {row.get('choice','')} | {row.get('reason','')} |"
            )
    faq = article.get("faq") or []
    if faq:
        parts.extend(["", "## 자주 묻는 질문", ""])
        for row in faq:
            parts.append(f"**Q. {row.get('q','')}**")
            parts.append(f"{row.get('a','')}")
            parts.append("")
    if article.get("recommended_for"):
        parts.extend(["## 이런 분께 맞습니다", ""])
        parts.extend([f"- {x}" for x in article["recommended_for"]])
        parts.append("")
    if article.get("not_for"):
        parts.extend(["## 이런 분께는 비추천", ""])
        parts.extend([f"- {x}" for x in article["not_for"]])
        parts.append("")
    if article.get("cta"):
        parts.extend([article["cta"], ""])
    if article.get("disclosure"):
        parts.extend([article["disclosure"], ""])
    tags = article.get("tags") or []
    if tags:
        parts.append(" ".join(f"#{t.replace(' ', '')}" for t in tags))
    return "\n".join(parts).strip() + "\n"


def markdown_to_naver_html(md: str) -> str:
    text = md.replace("\r\n", "\n")
    text = re.sub(r"^# .+\n+", "", text, count=1)
    lines = text.split("\n")
    out: list[str] = []
    i = 0
    in_quote = False
    while i < len(lines):
        line = lines[i]
        if line.startswith("> "):
            if not in_quote:
                out.append("<blockquote>")
                in_quote = True
            out.append(f"<p>{_inline(line[2:])}</p>")
            i += 1
            continue
        if in_quote:
            out.append("</blockquote>")
            in_quote = False
        if line.startswith("| ") and i + 1 < len(lines) and re.match(r"^\|\s*-+", lines[i + 1] or ""):
            table_lines = [line]
            i += 1
            while i < len(lines) and lines[i].startswith("|"):
                table_lines.append(lines[i])
                i += 1
            out.append(_table(table_lines))
            continue
        if line.startswith("## "):
            out.append(f"<h2>{_inline(line[3:])}</h2>")
        elif line.startswith("### "):
            out.append(f"<h3>{_inline(line[4:])}</h3>")
        elif line.startswith("- "):
            items = []
            while i < len(lines) and lines[i].startswith("- "):
                items.append(f"<li>{_inline(lines[i][2:])}</li>")
                i += 1
            out.append("<ul>" + "".join(items) + "</ul>")
            continue
        elif not line.strip():
            pass
        else:
            out.append(f"<p>{_inline(line)}</p>")
        i += 1
    if in_quote:
        out.append("</blockquote>")
    return "\n".join(out)


def _table(lines: list[str]) -> str:
    rows = []
    for idx, line in enumerate(lines):
        if idx == 1 and re.match(r"^\|\s*-+", line):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        tag = "th" if idx == 0 else "td"
        rows.append("<tr>" + "".join(f"<{tag}>{_inline(c)}</{tag}>" for c in cells) + "</tr>")
    return (
        "<table border='1' cellpadding='8' cellspacing='0' "
        "style='border-collapse:collapse;width:100%'>"
        + "".join(rows)
        + "</table>"
    )


def _inline(text: str) -> str:
    escaped = html.escape(text)
    escaped = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", escaped)
    escaped = re.sub(r"`(.+?)`", r"<code>\1</code>", escaped)
    return escaped
