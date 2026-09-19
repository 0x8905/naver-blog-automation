"""역할: 취향 팩 로드. 에이전트 표면은 repo의 taste/ 뿐이다.
고칠 때: taste.json 새 키는 Taste 필드와 from_dict()에만 추가. 기본값은 안전하게.
"""

from __future__ import annotations

import json
import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from nblog.config import PKG_DIR

PACKAGED_DIR = PKG_DIR / "packaged"


def taste_root(cwd: Path | None = None) -> Path:
    return (cwd or Path.cwd()) / "taste"


@dataclass
class Taste:
    name: str
    root: Path
    persona: str
    tone: str
    language: str
    min_chars: int
    title_max: int
    require_faq: bool
    require_compare: bool
    require_disclosure: bool
    min_faq: int
    min_compare: int
    disclosure: str
    cta: str
    tags_extra: list[str]
    ban_list: list[str]
    prompt_extra: str
    llm_provider: str
    llm_model: str
    llm_endpoint: str
    publish_mode: str
    max_per_run: int
    min_hours: float
    prompts: dict[str, str]
    selectors_rel: str
    raw: dict[str, Any] = field(default_factory=dict)

    def file(self, rel: str) -> Path:
        path = self.root / rel
        if not path.is_file():
            raise FileNotFoundError(f"취향 파일 없음: {path}")
        return path

    def read_prompt(self, kind: str) -> str:
        rel = self.prompts.get(kind) or f"prompts/{kind}.txt"
        return self.file(rel).read_text(encoding="utf-8")


def _clamp_publish(max_per_run: int) -> int:
    try:
        n = int(max_per_run)
    except (TypeError, ValueError):
        n = 1
    return 1 if n < 1 else min(n, 1)


def from_dict(payload: dict[str, Any], root: Path) -> Taste:
    voice = payload.get("voice") or {}
    length = payload.get("length") or {}
    gates = payload.get("gates") or {}
    llm = payload.get("llm") or {}
    publish = payload.get("publish") or {}
    prompts = payload.get("prompts") or {}
    return Taste(
        name=str(payload.get("name") or root.name),
        root=root,
        persona=str(voice.get("persona") or ""),
        tone=str(voice.get("tone") or ""),
        language=str(voice.get("language") or "ko"),
        min_chars=int(length.get("min_chars") or 1400),
        title_max=int(length.get("title_max") or 80),
        require_faq=bool(gates.get("require_faq", True)),
        require_compare=bool(gates.get("require_compare", True)),
        require_disclosure=bool(gates.get("require_disclosure", False)),
        min_faq=int(gates.get("min_faq") or 3),
        min_compare=int(gates.get("min_compare") or 3),
        disclosure=str(payload.get("disclosure") or ""),
        cta=str(payload.get("cta") or ""),
        tags_extra=[str(x) for x in (payload.get("tags_extra") or [])],
        ban_list=[str(x) for x in (voice.get("ban_list") or []) if str(x).strip()],
        prompt_extra=str(payload.get("prompt_extra") or ""),
        llm_provider=str(llm.get("provider") or ""),
        llm_model=str(llm.get("model") or ""),
        llm_endpoint=str(llm.get("endpoint") or ""),
        publish_mode=str(publish.get("mode") or "draft"),
        max_per_run=_clamp_publish(publish.get("max_per_run") or 1),
        min_hours=float(publish.get("min_hours") or 6),
        prompts={
            "system": str(prompts.get("system") or "prompts/system.txt"),
            "draft": str(prompts.get("draft") or "prompts/draft.txt"),
        },
        selectors_rel=str(payload.get("selectors") or "selectors.json"),
        raw=payload,
    )


def list_pack_names(cwd: Path | None = None) -> list[str]:
    names: set[str] = set()
    for folder in (taste_root(cwd), PACKAGED_DIR):
        if not folder.is_dir():
            continue
        for path in folder.iterdir():
            if path.is_dir() and (path / "taste.json").is_file() and not path.name.startswith("_"):
                names.add(path.name)
    return sorted(names)


def pack_dir(name: str, cwd: Path | None = None) -> Path:
    safe = Path(name).name
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,40}", safe):
        raise ValueError(f"팩 이름 불가: {name}")
    for folder in (taste_root(cwd) / safe, PACKAGED_DIR / safe):
        if (folder / "taste.json").is_file():
            return folder
    known = ", ".join(list_pack_names(cwd)) or "(없음)"
    raise FileNotFoundError(f"취향 팩 없음: {safe} (있는 것: {known})")


def active_name(cwd: Path | None = None) -> str:
    pointer = taste_root(cwd) / "active.json"
    if pointer.is_file():
        data = json.loads(pointer.read_text(encoding="utf-8"))
        name = str(data.get("name") or "").strip()
        if name:
            return name
    return "default"


def set_active(name: str, cwd: Path | None = None) -> None:
    pack_dir(name, cwd)
    root = taste_root(cwd)
    root.mkdir(parents=True, exist_ok=True)
    (root / "active.json").write_text(
        json.dumps({"name": name}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def load_taste(name: str | None = None, cwd: Path | None = None) -> Taste:
    chosen = (name or "").strip() or active_name(cwd)
    root = pack_dir(chosen, cwd)
    payload = json.loads((root / "taste.json").read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("taste.json 최상위는 객체여야 합니다.")
    return from_dict(payload, root)


def new_pack(name: str, source: str = "default", cwd: Path | None = None) -> Path:
    safe = Path(name).name
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,40}", safe):
        raise ValueError(f"팩 이름 불가: {name}")
    dest = taste_root(cwd) / safe
    if dest.exists():
        raise FileExistsError(f"이미 있음: {dest}")
    src = pack_dir(source, cwd)
    shutil.copytree(src, dest, ignore=shutil.ignore_patterns("__pycache__"))
    payload = json.loads((dest / "taste.json").read_text(encoding="utf-8"))
    payload["name"] = safe
    payload["author"] = ""
    (dest / "taste.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    notes = dest / "NOTES.md"
    extra = f"\n\nCopied from `{source}` as `{safe}`.\n"
    if notes.is_file():
        notes.write_text(notes.read_text(encoding="utf-8") + extra, encoding="utf-8")
    else:
        notes.write_text(extra, encoding="utf-8")
    return dest
