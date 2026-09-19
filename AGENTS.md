# Agent contract

Read this file first. Do not scan `nblog/` to “improve” the pipeline.

This repo is a frozen core plus a taste pack. Incoming agents customize **taste**, not the engine.

이 파일을 먼저 읽는다. 파이프라인을 다시 짜지 않는다.

## You may edit

- `taste/<name>/taste.json`
- `taste/<name>/prompts/`
- `taste/<name>/selectors.json`
- `taste/<name>/NOTES.md`
- `taste/active.json`

```bash
nblog taste show
nblog taste new mypack --from default
nblog taste use mypack
```

## You must not edit (for taste)

- `nblog/` — frozen core
- `.env` — secrets stay local, never commit
- another agent’s `taste/<name>/` without reading its `NOTES.md`

## Five rules

1. Taste lives in one pack directory. Do not scatter settings into `nblog/`.
2. Secrets (API keys, passwords) never go in `taste.json` or git.
3. LLM calls go through `nblog.llm`. Do not add a vendor SDK to the core to match your stack; set `llm.provider` in taste (and keys in `.env`).
4. Publish stays opt-in. Default is local files + Naver draft. Do not change the core to auto-public or raise `max_per_run` above 1.
5. Before you finish: `python -m unittest discover -s tests -v` (offline) and one line in that pack’s `NOTES.md`.

## If your user asks for “fully automatic”

Read `README.md` → “Automation status” first and tell them what is manual today and why. The loop (scheduler, keyword feed, notify-on-failure) is a script **outside** `nblog/`. Do not add a scheduler, a retry loop, or an auto-approve path to the core.

## First five minutes

1. `nblog taste show`
2. Copy `taste/default` → `taste/<your-pack>` or `nblog taste new <your-pack>`
3. Edit `voice`, `length`, `gates`, `prompts`, `llm` (no keys)
4. `nblog taste use <your-pack>`
5. `nblog draft --from-json tests/fixtures/article.json`

Need a new capability the schema cannot express? Add a key to `taste.json` only if the core already reads it. If it does not, stop and document the gap in `NOTES.md`. Do not rewrite `nblog/pipeline.py`.

Core freeze details: `CONTRACT.md`.
