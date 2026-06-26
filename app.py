"""A basic Gradio chat UI that consumes the deployed LangGraph agent.

The agent itself runs inside the LangGraph **Agent Server** (start it with
``langgraph dev``). This file is a thin **client** over that server's REST API,
using the LangGraph SDK — it does not import or run the graph in-process.

Run order:
    1. Terminal A:  langgraph dev          # serves the agent at :2024
    2. Terminal B:  python app.py          # opens the Gradio chat UI
"""

import os

import gradio as gr
from dotenv import load_dotenv
from langgraph_sdk import get_sync_client

load_dotenv()

# Where to reach the Agent Server. This is deploy-time configuration from the
# environment, NOT user input — never let chat text choose the endpoint.
LANGGRAPH_URL = os.environ.get("LANGGRAPH_URL", "http://127.0.0.1:2024")
ASSISTANT = "agent"  # the graph id declared in langgraph.json

client = get_sync_client(url=LANGGRAPH_URL)

# One LangGraph thread per Gradio session. The Agent Server's checkpointer holds
# the conversation history, so each turn sends ONLY the new user message — we do
# not replay Gradio's `history` into the graph (that would duplicate every turn).
_threads: dict[str, str] = {}


def _stream_event(part):
    """Return ``(event_name, data)`` from an SDK stream part, tolerant of both
    the object form (``part.event`` / ``part.data``) and any dict form."""
    if isinstance(part, dict):
        return str(part.get("event") or part.get("type") or ""), part.get("data")
    return str(getattr(part, "event", "") or ""), getattr(part, "data", None)


def _text(msg) -> str:
    """Extract assistant text from a message (string content or content blocks)."""
    content = msg.get("content", "") if isinstance(msg, dict) else getattr(msg, "content", "")
    if isinstance(content, list):
        return "".join(
            block.get("text", "") for block in content if isinstance(block, dict)
        )
    return content or ""


def chat(message: str, history, request: gr.Request):
    """Gradio streaming handler: relay one user turn to the agent, yield tokens."""
    thread_id = _threads.get(request.session_hash)
    if not thread_id:
        thread_id = client.threads.create()["thread_id"]
        _threads[request.session_hash] = thread_id

    accumulated = ""
    for part in client.runs.stream(
        thread_id,
        ASSISTANT,
        input={"messages": [{"role": "user", "content": message}]},
        stream_mode="messages",  # token-level streaming
    ):
        event, data = _stream_event(part)
        # messages-mode events carry [message, metadata]; show assistant text only.
        if not (event.startswith("messages") and isinstance(data, list) and data):
            continue
        msg = data[0]
        mtype = msg.get("type") if isinstance(msg, dict) else getattr(msg, "type", None)
        if mtype != "ai":
            continue  # skip tool-result / human messages in the chat view
        text = _text(msg)
        if text:
            # messages mode carries the ACCUMULATED message text each tick;
            # yield it whole and Gradio sends only the diff to the browser.
            accumulated = text
            yield accumulated


demo = gr.ChatInterface(
    fn=chat,
    type="messages",
    title="LangGraph Agent — Gradio client",
    description=(
        "A basic Gradio UI that consumes a LangGraph agent through the Agent "
        "Server via the LangGraph SDK. Try: 'What is 6 * 7?' or 'What is the "
        "Agent Server?'"
    ),
)

if __name__ == "__main__":
    # localhost only — no share link. Set GRADIO_SERVER_PORT to change the port.
    demo.launch()
