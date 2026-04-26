# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Portfolio context

This sub-project lives under `CTI/Portfolio1/` and has its own `.git`. The portfolio-level `CLAUDE.md` one directory up explains its role: a lightweight single-agent research tool used as the **Western-source** counterpart to BettaFish's heavier multi-engine stack. The narrow analysis topic (semiconductor talent-poaching TTPs, 2019–2024) lives in `../CTI_STATUS.md` — read that for current strategic state before non-trivial changes.

## Run commands

```bash
# CLI
python examples/basic_usage.py        # canned single-query demo
python examples/advanced_usage.py     # multi-query + state save/load + provider swap

# Web UI (no config.py needed — keys entered in the form)
streamlit run examples/streamlit_app.py
```

Reports land in `reports/` (or `OUTPUT_DIR`); per-run state JSONs land alongside them when `SAVE_INTERMEDIATE_STATES = True`.

There are no tests, no linter, no CI.

## Configuration

`config.py` at the repo root holds real API keys (DeepSeek / OpenAI / Tavily) and is gitignored. `Config.from_file` (`src/utils/config.py`) loads it by dynamic-import, so it must remain a valid Python module — not `.env` syntax. A `.env`-style file is also accepted as a fallback.

`load_config()` searches `config.py`, `config.env`, `.env` in order from the **current working directory**, so commands must be run from the repo root.

DeepSeek is wired through the `openai` SDK pointed at `https://api.deepseek.com` (`src/llms/deepseek.py`) — it is not a separate client. Adding a new provider means subclassing `BaseLLM` and registering it in `DeepSearchAgent._initialize_llm`.

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
