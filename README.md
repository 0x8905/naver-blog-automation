# naver-blog-automation

Draft, review, and optionally save a post to **your own** Naver blog.

There is no official write API (it ended in 2020). This tool researches with the public search APIs, writes a draft with whatever LLM you configure, then optionally pastes into a browser session you logged in yourself.

Not affiliated with Naver. Not a spam farm.

**Agents:** read `AGENTS.md` first. Change `taste/` only.

## Design goal

This repo is public on purpose. Whichever coding agent opens it (Claude Code, Codex, Cursor, Gemini CLI, or a human) should be able to fit it to **its own user** without forking the engine.

- `nblog/` is a frozen core: pipeline order, safety clamps, no vendor lock-in, standard library only (Playwright is an optional extra).
- `taste/<name>/` is the customization surface: voice, length, gates, prompts, editor selectors, LLM provider/model.
- Nothing about the original author is baked in. Blog id and keys are empty and every user fills their own. The personas in the shipped packs and the provider fallbacks in `nblog/llm.py` (`openai`, `gpt-4o-mini`, `claude-sonnet-4-5`) are generic placeholders. Override them in your pack.
- Not everything is in taste yet. Still fixed in the core: the Korean section headings and table layout in `render.py`, the gate's mandatory H2 / keyword / duplicate-title checks and scoring, the blocked-script list in `gate.py` (`voice.language` is read but has no effect), temperature, token budget and timeouts in `llm.py`, research sample sizes and wording in `research.py`. An agent that needs one of these should record the gap in `NOTES.md` as `AGENTS.md` says.
- `AGENTS.md` is the contract an incoming agent reads first. `CONTRACT.md` says what the core may and may not change. `nblog where` prints the same map in the terminal.

## Install

Python 3.10+

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
# optional, own-blog save
pip install -e ".[publish]"
python -m playwright install chromium
cp .env.example .env
```

## Taste

Incoming agents (and humans) do not fork the engine. They copy a pack:

```bash
nblog taste show
nblog taste new mypack --from default
nblog taste use mypack
```

Edit `taste/mypack/taste.json` (voice, length, gates, llm provider/model — **no API keys**).

## Draft

```bash
nblog doctor
nblog draft --from-json tests/fixtures/article.json
nblog draft "USB-C 케이블" --taste review
nblog list
nblog approve <id>
```

Output: `data/posts/`, `data/out/*.md`, `data/out/*.html`.

## LLM

Set in `.env` (keys) and/or `taste.json` (provider/model/endpoint). If both are set, the environment wins: `NBLOG_PROVIDER`, `NBLOG_MODEL` and `OPENAI_BASE_URL` override the pack's `llm` block. Leave them out of `.env` if you want the pack to decide. `endpoint` applies to `openai` / `openai_compat` only. The `anthropic` adapter always calls `api.anthropic.com`.

| provider | env |
| --- | --- |
| `openai` | `OPENAI_API_KEY` |
| `openai_compat` | `OPENAI_BASE_URL` (any `/v1/chat/completions` server) |
| `anthropic` | `ANTHROPIC_API_KEY` |

## Naver search (optional)

Search / DataLab only. Not a posting API.

```
NAVER_CLIENT_ID=
NAVER_CLIENT_SECRET=
```

## Own-blog save (optional)

Do not put a password in `.env`. Run `nblog login` and sign in yourself. This tool never asks for or reads your password. Whether the browser profile remembers it is up to what you click in the browser.

```
NAVER_BLOG_ID=
nblog login
nblog publish <id>           # Naver draft
nblog publish <id> --public  # explicit public post, 6h gap by default
```

`publish` uses the selectors and interval of the pack the post was drafted with. `--taste <name>` overrides that. An approved post stays approved after a draft save, so `--public` on the same id works, but it types a **new** post rather than resuming the draft already saved in Naver.

Core clamps one post per run. Taste cannot raise that.

The browser is Playwright's bundled Chromium by default. To use an installed browser set `NBLOG_BROWSER_CHANNEL=chrome` (or `msedge`). A profile created with one browser may not carry its login over to another, so run `nblog login` again after switching.

## Automation status

Read this before you promise anyone "fully automatic".

### How posting works

Naver has no write API. `nblog publish` opens a real browser with Playwright, goes to `blog.naver.com/<id>/postwrite`, finds the title and body fields with the CSS selectors in `taste/<name>/selectors.json`, types the text, and clicks save. The login session lives in the browser profile (`.chrome-profile/`, or `NBLOG_CHROME_PROFILE`). You create it yourself in `nblog login`.

### What is automatic today

- Research (if Naver search keys are set), drafting, the machine gate, Markdown/HTML rendering, the local queue.
- Typing an approved post into the editor and clicking **save as Naver draft**, or **publish** when you pass `--public`.

### What is manual today, on purpose

- `nblog login`: once per browser profile, and again whenever Naver expires the session or asks for 2FA or a captcha.
- `nblog approve <id>`: the human check between a draft and the browser.
- `--public`: without it the post stays a draft inside Naver and you press the final button yourself.
- Choosing keywords. There is no topic queue.
- Scheduling. Nothing in this repo runs on a timer.

### Known limits

- The body is inserted as plain text, so `##`, tables and `**bold**` arrive as literal Markdown characters. `data/out/<id>.html` is there for manual paste when you want formatting.
- Images are not uploaded. `image_prompts` are text suggestions only.
- The browser is headed (`headless=False`). It needs a logged-in desktop session (or `xvfb` on Linux), not a bare server.
- Tests are offline. The editor path (`nblog publish`) is **not** covered by them and was not exercised against the live Naver editor in the release review. Selectors are best-effort and Naver changes the editor without notice. If the editor is rendered inside an iframe on your account, page-level selectors will not match. Run `nblog publish <id>` in draft mode and look at `screenshots/` before you trust it.

### Known issues

Found in the release reviews and **not fixed yet**. They matter most if you automate.

- A draft save is reported after a fixed wait, without checking that Naver stored it.
- `publish --public` counts as done only when the confirm button was clicked (if the pack lists one under `publish_confirm`; an empty list skips that step) and the browser left the editor URL within 15 seconds. That is a heuristic. It has not been checked against the live editor, so it may reject a real success or, less likely, accept a failure.
- Login detection only recognises a top-level redirect to `nid.naver.com`.
- The cooldown between public posts can be set to any value, including 0.

Fixed in 0.2.2: success reported when the confirm button was missing, the cooldown blocking draft saves, `publish` ignoring the pack a post was drafted with, `require_disclosure` passing on empty text, same-second post id collisions.

### Going fully automatic

The core will not do this for you, but it does not stop you. Put the chain in your own scheduler (cron, launchd, systemd timer) on a machine with a desktop session. The recipe is POSIX shell. On Windows use WSL or translate it.

```bash
#!/bin/sh
set -e
cd /path/to/naver-blog-automation
. .venv/bin/activate
out=$(nblog draft "$1")                            # exits 2 when the gate rejects, chain stops
id=$(printf '%s\n' "$out" | awk 'NR==1 {print $2}')  # first line is "<status>  <id>"
[ -n "$id" ]
nblog approve "$id"                                # you are now the one skipping the human check
nblog publish "$id"                                # add --public to go live
```

What you take on when you do that:

- `approve` without reading means the gate is your only reviewer. It checks length, structure, banned words and AI self-reference. It does not check facts.
- One post per run is clamped in the core. The gap between public posts defaults to 6 hours, but it is a setting (`publish.min_hours` in the pack, `NBLOG_MIN_PUBLISH_HOURS` in the environment), not an enforced floor. `CONTRACT.md` forbids weakening it in the core. Keeping it sane in your config is on you.
- When Naver redirects to its login page, `publish` exits 1 with `로그인 세션 없음`. When the title, body, save or publish selector stops matching it exits 1 and tries to leave a screenshot. Both are best-effort, see Known issues. Have your scheduler notify you on a non-zero exit instead of retrying, and check the blog itself now and then.
- Feeding keywords is your job. A text file and a line counter is enough.
- Automated posting can get an account restricted under Naver's terms. That risk belongs to the account owner, not to this tool. The defaults are conservative for that reason.

Agents: build this loop **outside** `nblog/` (a script in your own directory or in `taste/<name>/`). Do not add a scheduler, a retry loop, or an auto-approve path to the core.

한국어 요약: 네이버에는 글쓰기 API가 없어서 Playwright로 실제 브라우저를 조작합니다. 현재는 초안 작성과 검수, 에디터 입력까지 자동이고, 로그인·승인(`approve`)·공개 발행(`--public`)·키워드 선정·스케줄링은 의도적으로 수동입니다. 완전 자동으로 운용하려면 위 셸 스크립트를 본인의 스케줄러에 등록하면 되지만, 본문이 서식 없는 텍스트로 입력되는 점, 이미지가 업로드되지 않는 점, 세션이 만료되면 다시 로그인해야 하는 점, 실제 에디터에서는 아직 검증되지 않았다는 점을 먼저 확인하시기 바랍니다.

## Tests

```bash
python -m unittest discover -s tests -v
```

## How this was built

Built with several AI models in separate roles, directed by a human.

| role | model |
| --- | --- |
| Design advice | Kimi K3, GLM-5.3 Flash, DeepSeek 4.1 Flash |
| Implementation | Grok 4.6 (xhigh) |
| Final review before publishing | Claude Fable 5.1 |
| Independent second review (0.2.1, 0.2.2) | GPT Astra (`gpt-6-astra`, via Codex CLI) |

The final review read every file in the tree, checked that no private infrastructure, personal identifiers or credentials were included, and ran the offline test suite. The second review was run read-only on the 0.2.1 changes and the whole tree. It confirmed the privacy check, corrected several overstatements in this README, and found core defects. Six of them were fixed in 0.2.2, each with a failing test first. It then reviewed that fix commit and caught four gaps (whitespace-only disclosure, posts approved before the release, non-atomic id reservation, two tests that passed without their guard), which were closed before the release, and what remains is listed under "Known issues". Neither review exercised the live Naver editor. They are reviews, not a warranty.

## License

MIT.
