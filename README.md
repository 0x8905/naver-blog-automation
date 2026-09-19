# naver-blog-automation

Draft, review, and optionally save a post to **your own** Naver blog.

There is no official write API (it ended in 2020). This tool researches with the public search APIs, writes a draft with whatever LLM you configure, then optionally pastes into a browser session you logged in yourself.

Not affiliated with Naver. Not a spam farm.

**Agents:** read `AGENTS.md` first. Change `taste/` only.

## Design goal

This repo is public on purpose. Whichever coding agent opens it (Claude Code, Codex, Cursor, Gemini CLI, or a human) should be able to fit it to **its own user** without forking the engine.

- `nblog/` is a frozen core: pipeline order, safety clamps, no vendor lock-in, standard library only (Playwright is an optional extra).
- `taste/<name>/` is the only customization surface: voice, length, gates, prompts, editor selectors, LLM provider/model.
- Nothing about the original author is baked in. No blog id, no persona, no model, no endpoint, no keys. Defaults are empty and every user fills their own.
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

Set in `.env` (keys) and/or `taste.json` (provider/model/endpoint). If both are set, the environment wins: `NBLOG_PROVIDER`, `NBLOG_MODEL` and `OPENAI_BASE_URL` override the pack's `llm` block. Leave them out of `.env` if you want the pack to decide.

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

Do not put a password in `.env`. Run `nblog login` and sign in yourself.

```
NAVER_BLOG_ID=
nblog login
nblog publish <id>           # Naver draft
nblog publish <id> --public  # explicit public post, 6h gap
```

Core clamps one post per run. Taste cannot raise that.

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

The final review read every file in the tree, checked that no private infrastructure, personal identifiers or credentials were included, and ran the offline test suite. It is a review, not a warranty. Naver's editor changes without notice, so expect to update `selectors.json`.

## License

MIT.
