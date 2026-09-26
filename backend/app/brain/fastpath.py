"""Tiny deterministic fast-path solver for common computational requests."""
from __future__ import annotations

import ast
import operator
import re


_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.Mod: operator.mod,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


class FastPath:
    """Answer safe arithmetic locally without invoking the language model."""

    _pattern = re.compile(r"^\s*(?:calculate|compute|solve)\s+(.+?)\s*[?]?$", re.I)

    def try_answer(self, message: str) -> str | None:
        match = self._pattern.match(message)
        if not match:
            return None
        expression = match.group(1).strip().replace("×", "*").replace("÷", "/")
        if len(expression) > 200 or not re.fullmatch(r"[0-9+\-*/().%\s^]+", expression):
            return None
        try:
            value = self._eval(ast.parse(expression.replace("^", "**"), mode="eval").body)
        except (SyntaxError, ValueError, ZeroDivisionError, OverflowError):
            return None
        return f"The answer is {value:g}." if isinstance(value, float) else f"The answer is {value}."

    def _eval(self, node: ast.AST) -> int | float:
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value
        if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
            return _OPS[type(node.op)](self._eval(node.operand))
        if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
            left, right = self._eval(node.left), self._eval(node.right)
            if isinstance(node.op, ast.Pow) and abs(right) > 12:
                raise ValueError("exponent too large")
            return _OPS[type(node.op)](left, right)
        raise ValueError("unsupported expression")
