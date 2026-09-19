# Core freeze

`nblog/` is the engine. `taste/` is the skin.

## Frozen

- Pipeline order: research → draft → gate → store → (optional) own-blog save
- No passwords in git
- No official Naver write API (it ended in 2020)
- Offline tests must pass without network
- `publish.max_per_run` is clamped to 1 in core even if taste asks for more
- Public post requires an explicit CLI flag; taste cannot turn that on by itself

## Allowed core changes

- Bug fix with a failing test first
- New LLM adapter in `nblog/llm.py` `PROVIDERS` (still no keys in repo)
- New **optional** `taste.json` key that defaults safely when missing

## Forbidden core changes

- Reordering or skipping gate
- Hard-coding a vendor, a person, a company, or a blog id
- Moving taste fields into Python literals
- Weakening core safety (rate limit, draft-default, no password store)

## Taste schema (`taste/<name>/taste.json`)

Required keys: `schema`, `name`, `voice`, `length`, `gates`, `prompts`, `publish`.

See `nblog/packaged/default/taste.json` for the full example. Unknown keys are ignored.
