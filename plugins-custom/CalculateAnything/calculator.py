# -*- coding: utf-8 -*-
"""Natural-language math engine for the Calculate Anything plugin.

Responsibilities (and nothing about Flow Launcher):
  1. Normalize a loose, natural-language expression into a strict arithmetic one
     ("2 plus 2", "15% of 80", "2^10", "5!", "sqrt(9)" ...).
  2. Evaluate it *safely* using the ``ast`` module with a strict node/function
     whitelist -- never ``eval`` on user input.
  3. Format the numeric result for display.

Public API: ``evaluate(expression, angle="radians", thousands=False)`` returns a
``CalcResult(value, formatted)`` or raises ``CalcError``.
"""

import ast
import math
import operator
import re
from collections import namedtuple

CalcResult = namedtuple("CalcResult", ["value", "formatted"])


class CalcError(Exception):
    """Raised when an expression cannot be understood or evaluated."""


# --- Constants and functions exposed to expressions -------------------------

_CONSTANTS = {
    "pi": math.pi,
    "e": math.e,
    "tau": math.tau,
    "inf": math.inf,
}

# Functions that do not depend on the angle unit.
_BASE_FUNCTIONS = {
    "sqrt": math.sqrt,
    "cbrt": lambda x: math.copysign(abs(x) ** (1 / 3), x),
    "abs": abs,
    "round": round,
    "floor": math.floor,
    "ceil": math.ceil,
    "trunc": math.trunc,
    "exp": math.exp,
    "ln": math.log,
    "log": math.log10,          # calculator convention: log = base 10
    "log2": math.log2,
    "log10": math.log10,
    "gcd": math.gcd,
    "min": min,
    "max": max,
    "sum": lambda *a: sum(a),
    "pow": pow,
    "hypot": math.hypot,
    "fact": math.factorial,
    "factorial": math.factorial,
    "degrees": math.degrees,
    "radians": math.radians,
    "sign": lambda x: (x > 0) - (x < 0),
}

# Binary / unary operators we permit.
_BIN_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.BitOr: operator.or_,
    ast.BitAnd: operator.and_,
    ast.BitXor: operator.xor,
    ast.LShift: operator.lshift,
    ast.RShift: operator.rshift,
}
_UNARY_OPS = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
    ast.Invert: operator.invert,
}

# Guards against trivially abusive expressions (memory/CPU blow-ups).
_MAX_POW_EXP = 1000
_MAX_FACTORIAL = 10000


def _angle_functions(angle):
    """Trig functions honouring the configured angle unit (degrees/radians)."""
    if angle == "degrees":
        return {
            "sin": lambda x: math.sin(math.radians(x)),
            "cos": lambda x: math.cos(math.radians(x)),
            "tan": lambda x: math.tan(math.radians(x)),
            "asin": lambda x: math.degrees(math.asin(x)),
            "acos": lambda x: math.degrees(math.acos(x)),
            "atan": lambda x: math.degrees(math.atan(x)),
        }
    return {
        "sin": math.sin, "cos": math.cos, "tan": math.tan,
        "asin": math.asin, "acos": math.acos, "atan": math.atan,
    }


# --- Normalization (natural language -> arithmetic) -------------------------

# Word/symbol operator aliases applied with word boundaries, case-insensitive.
_WORD_REPLACEMENTS = [
    (r"\bmultiplied\s+by\b", "*"),
    (r"\bmultiply\s+by\b", "*"),
    (r"\bdivided\s+by\b", "/"),
    (r"\bdivide\s+by\b", "/"),
    (r"\bto\s+the\s+power\s+of\b", "**"),
    (r"\bpower\s+of\b", "**"),
    (r"\bplus\b", "+"),
    (r"\bminus\b", "-"),
    (r"\btimes\b", "*"),
    (r"\bsquared\b", "**2"),
    (r"\bcubed\b", "**3"),
]


def _normalize(expr):
    """Turn a loose expression into a strict Python arithmetic expression."""
    s = expr.strip()

    # Unicode operators and symbols.
    s = (s.replace("×", "*").replace("·", "*").replace("÷", "/")
          .replace("−", "-").replace("—", "-").replace("π", "pi")
          .replace("√", "sqrt"))

    for pattern, repl in _WORD_REPLACEMENTS:
        s = re.sub(pattern, repl, s, flags=re.IGNORECASE)

    # "5 x 3" -> "5 * 3" (spaces required so we never touch 0x.. hex literals).
    s = re.sub(r"(?<=[\d)\s])\s+[xX]\s+(?=[\d(])", " * ", s)

    # Caret power.
    s = s.replace("^", "**")

    # Percentages (handled before "mod" so a literal % is unambiguous here):
    #   "15% of 80"  -> "(15/100)*80"
    s = re.sub(r"([\d.]+)\s*%\s*of\b", r"(\1/100)*", s, flags=re.IGNORECASE)
    #   "80 + 15%" / "200 - 10%" -> apply percent of the left-hand side
    m = re.match(r"^(.+?)\s*([+\-])\s*([\d.]+)\s*%\s*$", s)
    if m:
        left, op, pct = m.group(1), m.group(2), m.group(3)
        s = f"({left}) {op} ({left})*({pct}/100)"
    #   bare "50%" -> "(50/100)" (but keep "10 % 3" as modulo: % followed by an operand)
    s = re.sub(r"([\d.]+)\s*%(?!\s*[\d.(a-zA-Z])", r"(\1/100)", s)

    # "mod" word -> modulo operator.
    s = re.sub(r"\bmod\b", "%", s, flags=re.IGNORECASE)

    # Factorial: "5!" -> "factorial(5)".
    s = re.sub(r"(\d+)\s*!", r"factorial(\1)", s)

    return s.strip()


# --- Safe evaluation --------------------------------------------------------

def _eval_node(node, functions):
    if isinstance(node, ast.Expression):
        return _eval_node(node.body, functions)

    if isinstance(node, ast.Constant):
        if isinstance(node.value, bool) or not isinstance(node.value, (int, float)):
            raise CalcError("Unsupported value")
        return node.value

    if isinstance(node, ast.Name):
        if node.id in _CONSTANTS:
            return _CONSTANTS[node.id]
        raise CalcError(f"Unknown name '{node.id}'")

    if isinstance(node, ast.BinOp):
        op_type = type(node.op)
        if op_type not in _BIN_OPS:
            raise CalcError("Unsupported operator")
        left = _eval_node(node.left, functions)
        right = _eval_node(node.right, functions)
        if op_type is ast.Pow and isinstance(right, (int, float)) and abs(right) > _MAX_POW_EXP:
            raise CalcError("Exponent too large")
        return _BIN_OPS[op_type](left, right)

    if isinstance(node, ast.UnaryOp):
        op_type = type(node.op)
        if op_type not in _UNARY_OPS:
            raise CalcError("Unsupported operator")
        return _UNARY_OPS[op_type](_eval_node(node.operand, functions))

    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name) or node.func.id not in functions:
            name = getattr(node.func, "id", "?")
            raise CalcError(f"Unknown function '{name}'")
        func = functions[node.func.id]
        if node.keywords:
            raise CalcError("Keyword arguments are not supported")
        args = [_eval_node(a, functions) for a in node.args]
        if func is math.factorial and args and args[0] > _MAX_FACTORIAL:
            raise CalcError("Factorial argument too large")
        return func(*args)

    raise CalcError("Unsupported expression")


def evaluate(expression, angle="radians", thousands=False):
    """Evaluate a natural-language math ``expression``.

    Raises ``CalcError`` on anything we cannot safely understand.
    """
    if not expression or not expression.strip():
        raise CalcError("Empty expression")

    normalized = _normalize(expression)
    if not normalized:
        raise CalcError("Empty expression")

    try:
        tree = ast.parse(normalized, mode="eval")
    except SyntaxError:
        raise CalcError("Invalid expression")

    functions = dict(_BASE_FUNCTIONS)
    functions.update(_angle_functions(angle))

    try:
        value = _eval_node(tree, functions)
    except CalcError:
        raise
    except ZeroDivisionError:
        raise CalcError("Division by zero")
    except (ValueError, OverflowError) as exc:
        raise CalcError(str(exc) or "Math error")
    except Exception:
        raise CalcError("Invalid expression")

    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise CalcError("Not a number")
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        raise CalcError("Result is undefined")

    return CalcResult(value, _format_number(value, thousands))


def _format_number(value, thousands=False):
    """Render a number cleanly: integers without a dot, floats trimmed."""
    # Collapse float values that are really integers (e.g. 4.0 -> 4).
    if isinstance(value, float) and value.is_integer() and abs(value) < 1e16:
        value = int(value)

    if isinstance(value, int):
        return f"{value:,}" if thousands else str(value)

    # Float: up to 10 significant digits, trailing zeros stripped by 'g'.
    spec = ",.10g" if thousands else ".10g"
    return format(value, spec)
