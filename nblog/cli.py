"""역할: 명령줄 입출력. 취향 명령은 taste.py, draft 순서는 pipeline.py.
고칠 때: 새 명령 = subparser + cmd_*. 취향 값은 여기 하드코딩하지 말 것.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from nblog import __version__
from nblog.config import load_env_files, masked
from nblog.guide import format_guide
from nblog.pipeline import run_draft
from nblog.store import list_posts, load_post, update_status
from nblog.taste import (
    active_name,
    list_pack_names,
    load_taste,
    new_pack,
    pack_dir,
    set_active,
)


def main(argv: list[str] | None = None) -> int:
    load_env_files()
    parser = _parser()
    args = parser.parse_args(argv)
    if not hasattr(args, "func"):
        parser.print_help()
        return 2
    try:
        return args.func(args)
    except (FileNotFoundError, FileExistsError, ValueError, RuntimeError) as exc:
        print(f"오류: {exc}", file=sys.stderr)
        return 1


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="nblog",
        description="블로그 초안 생성 · 검수 · 본인 계정 임시저장",
    )
    p.add_argument("--version", action="version", version=f"nblog {__version__}")
    sub = p.add_subparsers(dest="cmd")

    w = sub.add_parser("where", help="취향을 어디에 쓰는지")
    w.set_defaults(func=cmd_where)

    t = sub.add_parser("taste", help="취향 팩")
    tsub = t.add_subparsers(dest="taste_cmd")
    t_show = tsub.add_parser("show", help="현재 팩")
    t_show.set_defaults(func=cmd_taste_show)
    t_ls = tsub.add_parser("list", help="팩 목록")
    t_ls.set_defaults(func=cmd_taste_list)
    t_use = tsub.add_parser("use", help="활성 팩 변경")
    t_use.add_argument("name")
    t_use.set_defaults(func=cmd_taste_use)
    t_new = tsub.add_parser("new", help="팩 복사 생성")
    t_new.add_argument("name")
    t_new.add_argument("--from", dest="source", default="default")
    t_new.set_defaults(func=cmd_taste_new)
    t.set_defaults(func=cmd_taste_show)

    d = sub.add_parser("draft", help="키워드로 초안 생성")
    d.add_argument("keyword", nargs="?", default="", help="주제 키워드")
    d.add_argument("--taste", default="", help="팩 이름. 없으면 active")
    d.add_argument("--from-json", dest="from_json", help="LLM 대신 로컬 JSON")
    d.add_argument("--skip-research", action="store_true")
    d.add_argument("--force", action="store_true")
    d.set_defaults(func=cmd_draft)

    ls = sub.add_parser("list", help="큐 목록")
    ls.set_defaults(func=cmd_list)

    sh = sub.add_parser("show", help="글 상세")
    sh.add_argument("id")
    sh.set_defaults(func=cmd_show)

    ap = sub.add_parser("approve", help="검수 통과 표시")
    ap.add_argument("id")
    ap.add_argument("--force", action="store_true")
    ap.set_defaults(func=cmd_approve)

    lg = sub.add_parser("login", help="브라우저에서 직접 로그인")
    lg.set_defaults(func=cmd_login)

    pub = sub.add_parser("publish", help="본인 블로그 임시저장 또는 발행")
    pub.add_argument("id")
    pub.add_argument("--public", action="store_true")
    pub.add_argument("--force", action="store_true")
    pub.set_defaults(func=cmd_publish)

    doc = sub.add_parser("doctor", help="설정 점검")
    doc.set_defaults(func=cmd_doctor)
    return p


def cmd_where(_args: argparse.Namespace) -> int:
    print(format_guide())
    return 0


def cmd_taste_show(_args: argparse.Namespace) -> int:
    taste = load_taste()
    print(f"active  {active_name()}")
    print(f"path    {taste.root}")
    print(f"persona {taste.persona}")
    print(f"tone    {taste.tone}")
    print(f"min     {taste.min_chars}자")
    print(f"llm     provider={taste.llm_provider or '(env)'} model={taste.llm_model or '(env)'}")
    print(f"publish mode={taste.publish_mode} max_per_run={taste.max_per_run}")
    print("계약    AGENTS.md")
    return 0


def cmd_taste_list(_args: argparse.Namespace) -> int:
    active = active_name()
    for name in list_pack_names():
        mark = "*" if name == active else " "
        print(f"{mark} {name}  {pack_dir(name)}")
    return 0


def cmd_taste_use(args: argparse.Namespace) -> int:
    set_active(args.name)
    print(f"active {args.name}")
    return 0


def cmd_taste_new(args: argparse.Namespace) -> int:
    dest = new_pack(args.name, source=args.source)
    print(dest)
    return 0


def cmd_draft(args: argparse.Namespace) -> int:
    code, post = run_draft(
        keyword=args.keyword,
        taste_name=args.taste or None,
        from_json=args.from_json,
        skip_research=args.skip_research,
        force=args.force,
    )
    gate = post.get("gate") or {}
    if code != 0:
        print(f"게이트 실패 ({post['id']}) score={gate.get('score')}")
        for reason in gate.get("reasons") or []:
            print(f"  - {reason}")
        print(f"파일: {post['md_path']}")
        print("통과시키려면 --force 후 nblog approve <id>")
        return code
    print(f"{post['status']}  {post['id']}")
    print(f"제목  {post['title']}")
    print(f"점수  {gate.get('score')} / {gate.get('chars')}자")
    print(f"MD    {post['md_path']}")
    print(f"HTML  {post['html_path']}")
    return 0


def cmd_list(_args: argparse.Namespace) -> int:
    posts = list_posts()
    if not posts:
        print("큐가 비었습니다.")
        return 0
    print(f"{'상태':<12} {'점수':<5} {'ID':<42} 제목")
    for post in posts:
        score = (post.get("gate") or {}).get("score", "-")
        print(f"{post.get('status','?'):<10} {str(score):<5} {post.get('id',''):<36} {post.get('title','')}")
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    post = load_post(args.id)
    gate = post.get("gate") or {}
    print(f"id       {post['id']}")
    print(f"status   {post['status']}")
    print(f"keyword  {post.get('keyword')}")
    print(f"title    {post.get('title')}")
    print(f"gate     ok={gate.get('ok')} score={gate.get('score')} {gate.get('reasons')}")
    print(f"md       {post.get('md_path')}")
    print(f"html     {post.get('html_path')}")
    if post.get("published_url"):
        print(f"url      {post['published_url']}")
    md = post.get("md_path")
    if md and Path(md).is_file():
        print("---")
        print(Path(md).read_text(encoding="utf-8")[:2000])
    return 0


def cmd_approve(args: argparse.Namespace) -> int:
    post = load_post(args.id)
    gate = post.get("gate") or {}
    if not gate.get("ok") and not args.force:
        print("게이트 미통과. --force로 강제 승인할 수 있습니다.", file=sys.stderr)
        return 2
    update_status(args.id, "approved")
    print(f"approved  {args.id}")
    return 0


def cmd_login(_args: argparse.Namespace) -> int:
    from nblog.publisher import login

    login()
    return 0


def cmd_publish(args: argparse.Namespace) -> int:
    from nblog.publisher import PublishError, publish
    from nblog.render import assemble_markdown

    post = load_post(args.id)
    if post.get("status") not in {"approved", "published"} and not args.force:
        print("먼저 nblog approve 로 검수 표시를 하세요.", file=sys.stderr)
        return 2
    markdown = assemble_markdown(post["article"])
    body = "\n".join(markdown.splitlines()[1:]).strip()
    taste = load_taste()
    try:
        result = publish(post["title"], body, public=args.public, taste=taste)
    except PublishError as exc:
        print(f"오류: {exc}", file=sys.stderr)
        return 1
    status = "published" if args.public else "naver_draft"
    update_status(args.id, status, published_url=result.get("url") or "")
    print(f"{status}  {args.id}")
    if result.get("url"):
        print(result["url"])
    print(f"screenshot {result.get('screenshot')}")
    return 0


def cmd_doctor(_args: argparse.Namespace) -> int:
    from nblog import naver_api
    from nblog.llm import PROVIDERS
    from nblog.publisher import profile_dir

    taste = load_taste()
    print(f"nblog {__version__}")
    print(f"cwd            {Path.cwd()}")
    print(f"taste active   {active_name()} @ {taste.root}")
    print(f"taste packs    {', '.join(list_pack_names())}")
    print(f"llm providers  {', '.join(sorted(PROVIDERS))}")
    print(f"provider env   {os.environ.get('NBLOG_PROVIDER') or '(없음)'}")
    print(f"model env      {os.environ.get('NBLOG_MODEL') or '(없음)'}")
    print(f"OPENAI_API_KEY {masked(os.environ.get('OPENAI_API_KEY'))}")
    print(f"OPENAI_BASE    {os.environ.get('OPENAI_BASE_URL') or '(기본)'}")
    print(f"ANTHROPIC      {masked(os.environ.get('ANTHROPIC_API_KEY'))}")
    print(f"NAVER_CLIENT   {masked(os.environ.get('NAVER_CLIENT_ID'))}")
    print(f"NAVER search   {'설정됨' if naver_api.configured() else '없음(리서치 생략)'}")
    print(f"NAVER_BLOG_ID  {os.environ.get('NAVER_BLOG_ID') or '(없음)'}")
    print(f"chrome profile {profile_dir()}")
    try:
        from playwright.sync_api import sync_playwright  # noqa: F401

        print("playwright     설치됨")
    except ImportError:
        print("playwright     없음 (pip install 'naver-blog-automation[publish]')")
    print("계약           AGENTS.md")
    return 0
