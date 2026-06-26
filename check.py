"""Fast, offline sanity check — no API key and no running server required.

Verifies the two tools behave (including that the calculator safely rejects
non-arithmetic input). Run: ``python check.py`` (after ``uv sync``).
"""

from agent.tools import calculator, web_search


def main() -> None:
    assert calculator("6 * 7") == "42", calculator("6 * 7")
    assert calculator("2 ** 10 + 1") == "1025", calculator("2 ** 10 + 1")
    assert calculator("(3 + 4) * 2") == "14", calculator("(3 + 4) * 2")
    assert "division by zero" in calculator("1 / 0")
    # Safety: names / calls / imports are rejected, not evaluated.
    assert calculator("__import__('os').system('echo hi')").startswith("Error"), \
        "calculator must reject non-arithmetic input"
    assert "10 ** 100" not in calculator("10 ** 100000"), "exponent must be bounded"

    assert "LangGraph" in web_search("what is langgraph?")
    assert "No results" in web_search("something unrelated")

    print("PASS: tools work — calculator is AST-safe, web_search returns corpus hits.")


if __name__ == "__main__":
    main()
