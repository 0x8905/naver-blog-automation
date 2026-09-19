"""역할: `nblog where` 표의 정본.
고칠 때: 에이전트가 만져도 되는 경로만 적는다. 코어 파일은 적지 않는다.
"""

from __future__ import annotations

ROWS: list[tuple[str, str, str]] = [
    ("지금 켜진 취향 보기", "nblog taste show", "active.json 포인터"),
    ("문체·분량·고지", "taste/<name>/taste.json", "voice / length / gates"),
    ("LLM 기본값(키 금지)", "taste/<name>/taste.json llm", "provider·model·endpoint. 키는 .env"),
    ("프롬프트", "taste/<name>/prompts/", "{중괄호} 변수 유지"),
    ("에디터 버튼", "taste/<name>/selectors.json", "셀렉터 배열 맨 앞에 추가"),
    ("왜 바꿨는지", "taste/<name>/NOTES.md", "다음 에이전트를 위해 한 줄"),
    ("새 팩", "nblog taste new <name>", "--from default|review"),
    ("팩 전환", "nblog taste use <name>", "taste/active.json 만 변경"),
]


def format_guide() -> str:
    w1 = max(len(r[0]) for r in ROWS)
    w2 = max(len(r[1]) for r in ROWS)
    lines = [
        "에이전트는 taste/ 만 고친다. 코어는 nblog/ 이고 취향 때문에 열지 않는다.",
        "계약: AGENTS.md",
        "",
        f"{'하고 싶은 일'.ljust(w1)}  {'어디'.ljust(w2)}  방법",
        f"{'-' * w1}  {'-' * w2}  ----",
    ]
    for want, path, how in ROWS:
        lines.append(f"{want.ljust(w1)}  {path.ljust(w2)}  {how}")
    return "\n".join(lines)
