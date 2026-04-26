# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Portfolio context

This sub-project lives under `CTI/Portfolio1/` and has its own `.git`. The portfolio-level `CLAUDE.md` one directory up explains its role: a lightweight single-agent research tool used as the **Western-source** counterpart to BettaFish's heavier multi-engine stack. The narrow analysis topic (semiconductor talent-poaching TTPs, 2019–2024) lives in `../CTI_STATUS.md` — read that for current strategic state before non-trivial changes.

## Run commands

This is a uv project (`pyproject.toml` + `uv.lock` tracked). Use `uv run` so the project venv resolves automatically:

```bash
# CLI
uv run python examples/basic_usage.py        # canned single-query demo
uv run python examples/advanced_usage.py     # multi-query + state save/load

# Web UI (no .env needed — keys entered in the form)
uv run streamlit run examples/streamlit_app.py
```

Reports land in `reports/` (or `OUTPUT_DIR`); per-run state JSONs land alongside them when `SAVE_INTERMEDIATE_STATES = True`.

There are no tests, no linter, no CI.

## Configuration

Configuration is split across two files:

- **`.env`** (repo root, gitignored) — API keys only: `OPENAI_API_KEY`, `TAVILY_API_KEY`. Template: `.env.example` (tracked).
- **`config.py`** (repo root, tracked) — non-secret settings: provider/model names, `MAX_REFLECTIONS`, `OUTPUT_DIR`, etc. Loaded by dynamic-import in `_load_settings_from_py` (`src/utils/config.py`), so it must remain a valid Python module.

`load_config()` calls `python-dotenv` to populate env vars from `.env`, then reads settings from `config.py` in the **current working directory** — so commands must be run from the repo root. If `config.py` is absent, the `Config` dataclass defaults are used.

Adding a new LLM provider means subclassing `BaseLLM` (`src/llms/base.py`) and registering it in `DeepSearchAgent._initialize_llm`. The OpenAI client lives in `src/llms/openai_llm.py`.

## Pipeline architecture

The agent is a fixed sequential pipeline, not a tool-using ReAct loop. `DeepSearchAgent.research()` (`src/agent.py`) drives it:

1. `ReportStructureNode` → produces report title + N `Paragraph` stubs (title + planned content) on the `State`.
2. For each paragraph:
   - `FirstSearchNode` → LLM emits `{search_query, reasoning}` for that paragraph.
   - `tavily_search` → results appended to `paragraph.research.search_history`.
   - `FirstSummaryNode` → writes `paragraph.research.latest_summary`.
   - Reflection loop runs `MAX_REFLECTIONS` times: `ReflectionNode` proposes a follow-up query (given the current summary), search runs again, `ReflectionSummaryNode` rewrites `latest_summary`. The loop count is fixed — there is no early-stop.
3. `ReportFormattingNode` stitches all `latest_summary` fields into the final Markdown. If LLM formatting throws, it falls back to `format_report_manually` (deterministic concatenation).

The whole run is serial — no async, no parallel paragraph processing. A single `tavily_search` failure returns `[]` and the pipeline continues with an empty result set rather than aborting.

## State and the two node types

`State` (`src/state/state.py`) is the single mutable object threaded through the pipeline (`State → Paragraph → Research → Search`). It is fully JSON-serializable via `to_dict`/`from_dict` round-trips, which is what `agent.save_state` / `agent.load_state` rely on.

Nodes split into two kinds (`src/nodes/base_node.py`):

- `BaseNode.run(input_data)` — pure: returns parsed output, never touches `State`. `FirstSearchNode` and `ReflectionNode` are this kind.
- `StateMutationNode.mutate_state(input_data, state, paragraph_index)` — returns the (mutated) `State`. The summary nodes and `ReportStructureNode` are this kind.

When adding a node, pick the right base class. The agent assumes `mutate_state` returns the new state and reassigns `self.state = ...` even though mutation is in-place — preserve that contract so loaded-from-disk states behave identically to fresh ones.

## Prompts

All prompts live in `src/prompts/prompts.py`. LLM outputs are parsed as JSON in the nodes — when editing a prompt, the JSON shape (`search_query`, `reasoning`, paragraph schema, etc.) is load-bearing and must match what the corresponding node expects.

`SYSTEM_PROMPT_REPORT_STRUCTURE` ships an explicit JSON-array example because newer OpenAI models would otherwise emit a single object or NDJSON stream when the prose said「對象」instead of「數組」. The parser in `src/utils/text_processing.py` (`_extract_balanced_json` + `_parse_balanced_json_sequence`) is string-aware balanced-bracket extraction, deliberately tolerant of code fences, prose prefixes, and NDJSON streams — preserve that contract when touching either layer.

## OpenAI client notes

`src/llms/openai_llm.py` sends `max_completion_tokens` (not `max_tokens` — the latter is rejected by gpt-5.x and o-series). Other newer models also reject non-default `temperature`; if you switch to one of those, strip or pin `temperature=1` in `OpenAILLM.invoke`.

## Git commits

Commit messages follow Conventional Commits: `<type>: <短描述>`. The description stays in zh-TW (per portfolio convention); only the prefix is fixed English.

| Prefix | When to use |
|--------|-------------|
| `feat:` | 新功能 |
| `fix:` | Bug 修正 |
| `refactor:` | 重構既有函數（行為不變） |
| `docs:` | 文件更新 |
| `test:` | 測試相關 |
