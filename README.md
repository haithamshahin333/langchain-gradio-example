# langgraph-agentserver

A minimal, end-to-end example with two parts:

1. **How to start a LangGraph app from scratch** with the LangGraph CLI.
2. **A basic Gradio chat UI** that consumes that agent through the **Agent
   Server** via the **LangGraph SDK client**.

The agent is a small tool-calling agent (`create_agent`) with two offline tools
(a safe calculator + a mock web-search), so the whole thing runs locally with
just `langgraph dev` — no LangSmith Platform entitlement required.

```
langgraph-agentserver/
├── langgraph.json        # the deploy contract: points the server at your graph
├── pyproject.toml        # dependencies (src layout, package = "agent")
├── .env.example          # copy to .env, fill in OPENAI_API_KEY + LANGSMITH_API_KEY
├── .gitignore            # keeps .env and other secrets out of git
├── app.py                # the Gradio client (consumes the agent over the SDK)
├── check.py              # fast offline sanity check (no key, no server)
└── src/agent/
    ├── graph.py          # create_agent(...) -> module-level `agent`
    └── tools.py          # calculator + web_search
```

---

## Part 1 — Start from scratch with the LangGraph CLI

You don't have to hand-write any of this. The LangGraph CLI scaffolds a working
app from a template; **this repo is essentially that template, filled in.**

### 1. Scaffold a new app

```bash
# Creates a project from the official Python template.
# Omit --template for an interactive menu of templates.
langgraph new path/to/your/app --template new-langgraph-project-python
cd path/to/your/app
```

(JavaScript: `npm create langgraph`.)

### 2. What it generates

A ready-to-run project in the **`src/agent/`** layout this repo uses:

```
your-app/
├── langgraph.json        # graphs + dependencies + env  (the only required file)
├── pyproject.toml        # your package + deps
├── .env                  # secrets (gitignored)
└── src/agent/
    └── graph.py          # exposes a compiled graph as a module-level variable
```

The contract that makes it deployable is **`langgraph.json`** — point it at your
graph and you get a full Agent Server (REST API + persistence + streaming +
OpenAPI docs + LangGraph Studio) with **zero server code**:

```json
{
  "dependencies": ["."],
  "graphs": { "agent": "./src/agent/graph.py:agent" },
  "env": ".env"
}
```

- `graphs` — the only required key. Maps a graph id (`"agent"`) to
  `path:variable`. Your `graph.py` must expose that variable (here, a compiled
  graph named `agent`).
- `dependencies: ["."]` — installs your local package.
- `env: ".env"` — loads local secrets. Keep secrets in the **gitignored** `.env`,
  never in this JSON.

### 3. Install and run

```bash
uv sync                  # or: pip install -e .
cp .env.example .env     # then set OPENAI_API_KEY
langgraph dev            # serves http://127.0.0.1:2024 + Studio link
```

`langgraph dev` is the local Agent Server: hot reload, local state, no Docker.
Open `http://127.0.0.1:2024/docs` to see the REST API you just got for free.

> **Deploy later.** The same `langgraph.json` is what a real deployment uses —
> `langgraph build` / `langgraph deploy` turn it into a container/managed
> deployment. Nothing in your code changes; you only point clients at the new URL.

---

## Part 2 — Run this demo (Gradio client over the Agent Server)

This repo already contains a filled-in agent. Two terminals:

### Terminal A — start the Agent Server

```bash
uv sync                  # install deps (first time only)
cp .env.example .env     # set OPENAI_API_KEY (and OPENAI_BASE_URL if you use a gateway)
langgraph dev            # agent now served at http://127.0.0.1:2024
```

### Terminal B — start the Gradio UI

```bash
uv run python app.py     # opens a chat UI (default http://127.0.0.1:7860)
```

Ask it things like *"What is 6 \* 7?"* (uses the calculator tool) or *"What is
the Agent Server?"* (uses the web_search tool). Multi-turn memory works because
each browser session maps to its own LangGraph **thread**.

### How `app.py` consumes the agent

It's a thin **client** — the graph runs in the server, not in Gradio:

```python
from langgraph_sdk import get_sync_client
client = get_sync_client(url="http://127.0.0.1:2024")   # or your deployment URL

for part in client.runs.stream(
    thread_id, "agent",                                  # "agent" = graph id from langgraph.json
    input={"messages": [{"role": "user", "content": message}]},
    stream_mode="messages",                              # stream tokens
):
    ...                                                  # yield assistant text to Gradio
```

Key design points (see `app.py` for the details):

- **One thread per Gradio session** (keyed on `gr.Request.session_hash`). The
  server's checkpointer holds the conversation, so each turn sends only the new
  message — not Gradio's full `history`.
- **Streaming** via `stream_mode="messages"`; the handler yields the accumulated
  assistant text and Gradio streams the diff to the browser.
- **Point at production** by changing `LANGGRAPH_URL` — the client code is
  identical against `langgraph dev` and a real deployment.

---

## Tracing (LangSmith)

Tracing is **on by default** — every agent run (model calls, tool calls, and the
full graph trajectory) is sent to LangSmith. Set `LANGSMITH_API_KEY` in `.env`
and the `langgraph dev` server reads it and traces automatically — no code
changes, and **no LangGraph Platform entitlement required** (any valid key works
with `langgraph dev`).

- Set `LANGSMITH_PROJECT` to group traces under a named project; if unset, they
  land in your LangSmith default project. View them at <https://smith.langchain.com>.
- Turn tracing off by setting `LANGSMITH_TRACING=false` (or leaving
  `LANGSMITH_API_KEY` empty).
- For a regional / self-hosted host, set `LANGSMITH_ENDPOINT`.

> Tracing happens **server-side**, where the graph actually runs — so the
> variables belong in this app's `.env` (loaded via `langgraph.json`), not in the
> Gradio client.

---

## Sanity check (no key, no server)

```bash
uv run python check.py
# -> PASS: tools work — calculator is AST-safe, web_search returns corpus hits.
```

## Configuration

All via `.env` (see `.env.example`):

| Var | Purpose | Default |
|-----|---------|---------|
| `OPENAI_API_KEY` | model credential (required to actually run the agent) | — |
| `OPENAI_BASE_URL` | route OpenAI calls through a gateway (env-only, never user input) | OpenAI default |
| `MODEL` | `provider:model` for the agent | `openai:gpt-5-mini` |
| `LANGGRAPH_URL` | where `app.py` reaches the Agent Server | `http://127.0.0.1:2024` |
| `LANGSMITH_TRACING` | trace agent runs to LangSmith | `true` |
| `LANGSMITH_API_KEY` | LangSmith credential (required for tracing) | — |
| `LANGSMITH_PROJECT` | LangSmith project to group traces under (optional) | LangSmith `default` |
| `LANGSMITH_ENDPOINT` | LangSmith host (set only for a regional/EU host) | SaaS default |

## Notes

- **Why no checkpointer in `graph.py`?** The Agent Server injects persistence at
  deploy time — that's what makes per-session threads work from the client.
- **Local vs deploy:** `langgraph dev` needs no LangSmith Platform entitlement.
  A standalone/managed deployment does (a LangGraph-Platform-entitled
  `LANGSMITH_API_KEY` or a license key).
- **Production note:** `app.py` keeps session→thread mapping in an in-process
  dict — fine for a single-process demo, but externalize it for a multi-replica
  deployment.

## References — LangChain / LangSmith docs

**Get started & the CLI**
- [LangGraph local server quickstart](https://docs.langchain.com/oss/python/langgraph/local-server) — `langgraph new`, `langgraph dev`, test the API
- [Deployment quickstart](https://docs.langchain.com/langsmith/deployment-quickstart) — scaffold → deploy → call it
- [LangGraph CLI reference](https://docs.langchain.com/langsmith/cli) — all commands + the [`langgraph.json` config file](https://docs.langchain.com/langsmith/cli#configuration-file)
- [Local development & testing](https://docs.langchain.com/langsmith/local-dev-testing) — `langgraph dev` vs `langgraph up`

**Build the agent**
- `create_agent` — [agents guide](https://docs.langchain.com/oss/python/langchain/agents) · [API reference](https://reference.langchain.com/python/langchain/agents/factory/create_agent)
- `init_chat_model` — [models guide](https://docs.langchain.com/oss/python/langchain/models) · [API reference](https://reference.langchain.com/python/langchain/chat_models/base/init_chat_model)

**Agent Server & deployment**
- [Agent Server overview](https://docs.langchain.com/langsmith/agent-server) — architecture + deployment modes (single host / split queue / distributed)
- [LangSmith Deployment overview](https://docs.langchain.com/langsmith/deployment)
- [Deploy a LangGraph app](https://docs.langchain.com/oss/python/langgraph/deploy) — `langgraph build` / `langgraph deploy`

**Consume it from a client**
- [LangGraph Python SDK reference](https://docs.langchain.com/langsmith/langgraph-python-sdk) — `get_client` / `get_sync_client`, threads, runs, store
- [Streaming API](https://docs.langchain.com/langsmith/streaming) — `runs.stream` / `runs.join_stream` over the SDK
- [LangChain streaming modes](https://docs.langchain.com/oss/python/langchain/streaming) — `updates` (progress) · `messages` (tokens) · `custom`
- [RemoteGraph](https://docs.langchain.com/langsmith/remote-graph) — call a deployed graph as a node in another graph

**Tracing & observability (LangSmith)**
- [Enable tracing](https://docs.langchain.com/oss/python/langchain/observability) — the `LANGSMITH_TRACING` / `LANGSMITH_API_KEY` env vars this demo uses
- [LangSmith Observability](https://docs.langchain.com/langsmith/observability) — traces, dashboards, monitoring
- [Conditional / per-request tracing](https://docs.langchain.com/langsmith/conditional-tracing) — redact or route traces at runtime
