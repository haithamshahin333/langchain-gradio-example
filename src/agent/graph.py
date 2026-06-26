"""The demo agent — a basic tool-calling agent, and the deployable unit.

``create_agent`` returns a compiled graph; we assign it to the module-level
``agent``, which ``langgraph.json`` registers as ``./src/agent/graph.py:agent``.

The LangGraph Agent Server injects persistence (a checkpointer/store) at deploy
time, so we deliberately do NOT pass one here — threads/memory are the server's
job, which is exactly what the Gradio client relies on.
"""

import os

from langchain.agents import create_agent
from langchain.chat_models import init_chat_model

# Absolute import (not ``from .tools``): the server loads this module by file
# path, so relative imports have no parent package. With the package installed
# (``pip install -e .`` / ``uv sync``), ``agent`` is importable as a top-level
# package because of the ``src`` layout configured in pyproject.toml.
from agent.tools import calculator, web_search

# Model id as ``provider:model``; override with the MODEL env var.
MODEL = os.environ.get("MODEL", "openai:gpt-5-mini")


def build_model():
    """Build the chat model.

    ``OPENAI_BASE_URL`` is read ONLY from the environment (deploy-time config),
    never from request input — endpoint selection must not be user-controllable
    (avoids SSRF / pointing the model client at an arbitrary host).
    """
    base_url = os.environ.get("OPENAI_BASE_URL")
    if base_url:
        return init_chat_model(MODEL, base_url=base_url)
    return init_chat_model(MODEL)


SYSTEM_PROMPT = (
    "You are a helpful research assistant. Use the calculator tool for any "
    "arithmetic, and the web_search tool to look up facts about LangGraph, the "
    "Agent Server, LangSmith, or Gradio. Keep answers concise."
)

# Module-level compiled graph — this is what langgraph.json points at.
agent = create_agent(
    model=build_model(),
    tools=[calculator, web_search],
    system_prompt=SYSTEM_PROMPT,
)
