"""Two offline tools for the demo agent — no network, no external API.

- ``calculator`` evaluates arithmetic via a hardened ``ast`` allow-list. It does
  NOT use ``eval``/``exec``: only numeric constants and a fixed set of operators
  are permitted, and the exponent is bounded to avoid huge-int blowups.
- ``web_search`` returns canned text from a tiny in-memory corpus (a mock so the
  demo runs with no network and no search API key).
"""

import ast
import operator

# Allowed binary / unary operators mapped to their safe implementations.
_BIN_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
_UNARY_OPS = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}

_MAX_POW_EXP = 100  # bound the exponent so `10 ** 10**9` can't DoS the process


def _eval_node(node: ast.AST) -> float:
    """Recursively evaluate an allow-listed arithmetic AST node."""
    if isinstance(node, ast.Constant):  # numbers only — no strings/names/bytes
        if isinstance(node.value, bool) or not isinstance(node.value, (int, float)):
            raise ValueError("only numeric constants are allowed")
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _BIN_OPS:
        left = _eval_node(node.left)
        right = _eval_node(node.right)
        if isinstance(node.op, ast.Pow) and abs(right) > _MAX_POW_EXP:
            raise ValueError(f"exponent too large (max {_MAX_POW_EXP})")
        return _BIN_OPS[type(node.op)](left, right)
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY_OPS:
        return _UNARY_OPS[type(node.op)](_eval_node(node.operand))
    raise ValueError(f"unsupported expression element: {type(node).__name__}")


def calculator(expression: str) -> str:
    """Evaluate a basic arithmetic expression and return the result as a string.

    Supports ``+ - * / // % **`` and parentheses over numbers only — e.g.
    ``"6 * 7"`` or ``"2 ** 10 + 1"``. Safe by construction: the expression is
    parsed with ``ast`` and evaluated against an allow-list, so names, calls,
    attribute access, and ``eval``/``exec`` are all rejected.
    """
    try:
        tree = ast.parse(expression, mode="eval")
        result = _eval_node(tree.body)
    except ZeroDivisionError:
        return "Error: division by zero"
    except (ValueError, SyntaxError, TypeError) as exc:
        return f"Error: {exc}"
    # Render integers without a trailing ".0".
    if isinstance(result, float) and result.is_integer():
        result = int(result)
    return str(result)


_CORPUS = {
    "langgraph": (
        "LangGraph is a framework for building stateful, multi-step agent "
        "applications as graphs."
    ),
    "agent server": (
        "The LangGraph Agent Server exposes a deployed graph as a REST API with "
        "persistence, streaming, and an OpenAPI spec."
    ),
    "langsmith": (
        "LangSmith is LangChain's platform for tracing, evaluating, and deploying "
        "LLM applications."
    ),
    "gradio": (
        "Gradio is a Python library for quickly building web UIs for ML models "
        "and apps."
    ),
}


def web_search(query: str) -> str:
    """Look a topic up in a small offline corpus (a mock 'web search', no network)."""
    q = query.lower()
    hits = [text for key, text in _CORPUS.items() if key in q]
    if hits:
        return " ".join(hits)
    return (
        "No results found in the local corpus. "
        "Try: langgraph, agent server, langsmith, gradio."
    )
