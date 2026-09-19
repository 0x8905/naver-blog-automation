"""역할: LLM 호출.
고칠 때: 업체 추가 = 함수 하나 복사 후 파일 맨 아래 PROVIDERS에 이름 등록.
테스트: extract_json()만 네트워크 없이 검증.
"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from collections.abc import Callable
from typing import Any


class LLMError(RuntimeError):
    pass


def extract_json(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start < 0 or end <= start:
        raise LLMError("모델 출력에서 JSON 객체를 찾지 못했습니다.")
    try:
        data = json.loads(cleaned[start : end + 1])
    except json.JSONDecodeError as exc:
        raise LLMError(f"JSON 파싱 실패: {exc}") from exc
    if not isinstance(data, dict):
        raise LLMError("JSON 최상위가 객체가 아닙니다.")
    return data


def complete(
    prompt: str,
    system: str = "",
    *,
    provider: str = "",
    model: str = "",
    endpoint: str = "",
) -> str:
    provider = (os.environ.get("NBLOG_PROVIDER") or provider or "openai").strip().lower()
    fn = PROVIDERS.get(provider)
    if fn is None:
        known = ", ".join(sorted(PROVIDERS))
        raise LLMError(f"지원하지 않는 NBLOG_PROVIDER: {provider} (가능: {known})")
    return fn(prompt, system, model=model, endpoint=endpoint)


def _headers_json(extra: dict[str, str] | None = None) -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if extra:
        headers.update(extra)
    return headers


def _post(url: str, payload: dict[str, Any], headers: dict[str, str], timeout: int) -> dict[str, Any]:
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        raise LLMError(f"HTTP {exc.code} {url}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise LLMError(f"연결 실패 {url}: {exc.reason}") from exc


def openai_compat(prompt: str, system: str, model: str = "", endpoint: str = "") -> str:
    """OpenAI Chat Completions. OPENAI_BASE_URL 바꾸면 호환 서버도 여기로."""
    api_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("LLM_API_KEY") or ""
    base = (os.environ.get("OPENAI_BASE_URL") or endpoint or "https://api.openai.com/v1").rstrip("/")
    model = os.environ.get("NBLOG_MODEL") or model or "gpt-4o-mini"
    messages: list[dict[str, str]] = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    headers = _headers_json()
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    data = _post(
        f"{base}/chat/completions",
        {"model": model, "messages": messages, "temperature": 0.6},
        headers,
        timeout=180,
    )
    choices = data.get("choices") or []
    if not choices:
        raise LLMError("OpenAI 호환 응답에 choices가 없습니다.")
    content = (choices[0].get("message") or {}).get("content") or ""
    if not str(content).strip():
        raise LLMError("모델 content가 비었습니다.")
    return str(content)


def anthropic(prompt: str, system: str, model: str = "", endpoint: str = "") -> str:
    api_key = os.environ.get("ANTHROPIC_API_KEY") or ""
    if not api_key:
        raise LLMError("ANTHROPIC_API_KEY가 없습니다.")
    model = os.environ.get("NBLOG_MODEL") or model or "claude-sonnet-4-5"
    payload: dict[str, Any] = {
        "model": model,
        "max_tokens": 4096,
        "messages": [{"role": "user", "content": prompt}],
    }
    if system:
        payload["system"] = system
    data = _post(
        "https://api.anthropic.com/v1/messages",
        payload,
        _headers_json({"x-api-key": api_key, "anthropic-version": "2023-06-01"}),
        timeout=180,
    )
    blocks = data.get("content") or []
    texts = [b.get("text") for b in blocks if isinstance(b, dict) and b.get("type") == "text"]
    content = "\n".join(t for t in texts if t)
    if not content.strip():
        raise LLMError("Anthropic 응답이 비었습니다.")
    return content


# 새 제공자: 위 함수를 복사해 고친 뒤 여기에 한 줄.
# 로컬 서버는 별도 어댑터 없이 openai_compat + OPENAI_BASE_URL 이면 된다.
PROVIDERS: dict[str, Callable[..., str]] = {
    "openai": openai_compat,
    "openai_compat": openai_compat,
    "anthropic": anthropic,
}
