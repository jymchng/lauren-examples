# NOTE: Do NOT add `from __future__ import annotations` to this file.
# The @tool() decorator uses inspect.signature() at decoration time to build
# the JSON schema, and PEP 563 lazy evaluation breaks that introspection.
"""Utility tools available to the ChatAgent."""

import ast
import operator
import re
from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from lauren_ai import tool


@tool()
async def get_current_time(timezone: str = "UTC") -> dict:
    """Get the current time in the specified timezone.

    Args:
        timezone: IANA timezone name (e.g. 'UTC', 'America/New_York').
    """
    try:
        tz = ZoneInfo(timezone)
        now = datetime.now(tz=tz)
        return {
            "timezone": timezone,
            "datetime": now.isoformat(),
            "date": now.strftime("%Y-%m-%d"),
            "time": now.strftime("%H:%M:%S"),
            "utc_offset": str(now.utcoffset()),
        }
    except ZoneInfoNotFoundError:
        return {
            "error": f"Unknown timezone: {timezone!r}",
            "hint": "Use an IANA timezone name like 'UTC' or 'America/New_York'.",
        }


# Safe AST-based expression evaluator
_ALLOWED_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


def _eval_node(node: ast.AST) -> float:
    """Recursively evaluate a safe arithmetic AST node."""
    if isinstance(node, ast.Expression):
        return _eval_node(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return float(node.value)
    if isinstance(node, ast.BinOp):
        op_type = type(node.op)
        if op_type not in _ALLOWED_OPS:
            raise ValueError(f"Unsupported operator: {op_type.__name__}")
        left = _eval_node(node.left)
        right = _eval_node(node.right)
        return _ALLOWED_OPS[op_type](left, right)
    if isinstance(node, ast.UnaryOp):
        op_type = type(node.op)
        if op_type not in _ALLOWED_OPS:
            raise ValueError(f"Unsupported unary operator: {op_type.__name__}")
        operand = _eval_node(node.operand)
        return _ALLOWED_OPS[op_type](operand)
    raise ValueError(f"Unsupported expression node: {type(node).__name__}")


@tool()
async def calculate(expression: str) -> dict:
    """Evaluate a mathematical expression safely.

    Args:
        expression: A math expression like '2 + 2 * 3'.
    """
    # Strip whitespace and sanity-check characters
    sanitised = expression.strip()
    if re.search(r"[a-zA-Z_]", sanitised):
        return {"error": "Variables and function calls are not supported.", "expression": expression}
    try:
        tree = ast.parse(sanitised, mode="eval")
        result = _eval_node(tree)
        # Return int when result is a whole number
        display = int(result) if result == int(result) else result
        return {"expression": expression, "result": display}
    except ZeroDivisionError:
        return {"error": "Division by zero.", "expression": expression}
    except Exception as exc:  # noqa: BLE001
        return {"error": f"Could not evaluate expression: {exc}", "expression": expression}


@tool()
async def word_count(text: str) -> dict:
    """Count words, characters, and sentences in a text.

    Args:
        text: The text to analyse.
    """
    words = text.split()
    word_count_val = len(words)
    char_count = len(text)
    char_no_spaces = len(text.replace(" ", "").replace("\n", "").replace("\t", ""))
    # Simple sentence split on . ! ?
    sentences = [s.strip() for s in re.split(r"[.!?]+", text) if s.strip()]
    sentence_count = len(sentences)
    return {
        "word_count": word_count_val,
        "character_count": char_count,
        "character_count_no_spaces": char_no_spaces,
        "sentence_count": sentence_count,
    }
