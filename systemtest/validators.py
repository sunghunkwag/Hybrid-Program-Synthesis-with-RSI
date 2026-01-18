"""Validation helpers for Systemtest generated code."""
from __future__ import annotations

import ast
from dataclasses import dataclass
from typing import Iterable, Optional, Set, Tuple

FORBIDDEN_NAMES = {"open", "eval", "exec", "compile", "__import__", "globals", "locals"}


def _safe_builtins() -> Set[str]:
    try:
        from Systemtest import SAFE_BUILTINS

        return set(SAFE_BUILTINS)
    except Exception:
        return set()


@dataclass(frozen=True)
class ValidationPolicy:
    allowed_nodes: Tuple[type, ...]


class BaseValidator(ast.NodeVisitor):
    def __init__(self, policy: ValidationPolicy):
        self.policy = policy
        self.ok = True
        self.err: Optional[str] = None

    def visit(self, node):
        if not isinstance(node, self.policy.allowed_nodes):
            self.ok, self.err = False, f"Forbidden: {type(node).__name__}"
            return
        if isinstance(node, ast.Name):
            if node.id.startswith("__") or node.id in FORBIDDEN_NAMES:
                self.ok, self.err = False, f"Forbidden name: {node.id}"
                return
        if isinstance(node, ast.Attribute):
            if node.attr.startswith("__"):
                self.ok, self.err = False, f"Forbidden attribute: {node.attr}"
                return
        if isinstance(node, ast.Call):
            if not isinstance(node.func, (ast.Name, ast.Attribute)):
                self.ok, self.err = False, "Forbidden call form (non-Name/Attribute callee)"
                return
        if isinstance(node, ast.Subscript):
            safe_builtins = _safe_builtins()
            if isinstance(node.value, ast.Name) and node.value.id in safe_builtins:
                self.ok, self.err = False, "Forbidden subscript on builtin"
                return
        super().generic_visit(node)


def _make_allowed(*nodes: Iterable[type]) -> Tuple[type, ...]:
    allowed = []
    for node_group in nodes:
        allowed.extend(node_group)
    if hasattr(ast, "Index"):
        allowed.append(ast.Index)
    return tuple(allowed)


CODE_ALLOWED = _make_allowed(
    [
        ast.Module,
        ast.FunctionDef,
        ast.arguments,
        ast.arg,
        ast.Return,
        ast.Assign,
        ast.AnnAssign,
        ast.AugAssign,
        ast.Name,
        ast.Constant,
        ast.Expr,
        ast.If,
        ast.While,
        ast.For,
        ast.Break,
        ast.Continue,
        ast.BinOp,
        ast.UnaryOp,
        ast.Compare,
        ast.Call,
        ast.List,
        ast.Tuple,
        ast.Dict,
        ast.Set,
        ast.ListComp,
        ast.SetComp,
        ast.DictComp,
        ast.GeneratorExp,
        ast.Attribute,
        ast.Subscript,
        ast.Slice,
        ast.Load,
        ast.Store,
        ast.IfExp,
        ast.operator,
        ast.boolop,
        ast.unaryop,
        ast.cmpop,
    ]
)

PROGRAM_ALLOWED = _make_allowed(
    [
        ast.Module,
        ast.FunctionDef,
        ast.arguments,
        ast.arg,
        ast.Return,
        ast.Assign,
        ast.Name,
        ast.Constant,
        ast.Expr,
        ast.If,
        ast.BinOp,
        ast.UnaryOp,
        ast.Compare,
        ast.Call,
        ast.List,
        ast.Tuple,
        ast.Dict,
        ast.Set,
        ast.ListComp,
        ast.SetComp,
        ast.DictComp,
        ast.GeneratorExp,
        ast.Attribute,
        ast.Subscript,
        ast.Slice,
        ast.Load,
        ast.Store,
        ast.IfExp,
        ast.operator,
        ast.boolop,
        ast.unaryop,
        ast.cmpop,
    ]
)

ALGO_ALLOWED = _make_allowed(
    [
        ast.Module,
        ast.FunctionDef,
        ast.arguments,
        ast.arg,
        ast.Return,
        ast.Assign,
        ast.Name,
        ast.Constant,
        ast.Expr,
        ast.If,
        ast.For,
        ast.While,
        ast.BinOp,
        ast.UnaryOp,
        ast.Compare,
        ast.BoolOp,
        ast.IfExp,
        ast.Call,
        ast.List,
        ast.Tuple,
        ast.Dict,
        ast.Set,
        ast.ListComp,
        ast.SetComp,
        ast.DictComp,
        ast.GeneratorExp,
        ast.Attribute,
        ast.Subscript,
        ast.Load,
        ast.Store,
        ast.operator,
        ast.boolop,
        ast.unaryop,
        ast.cmpop,
    ]
)


class CodeValidator(BaseValidator):
    def __init__(self):
        super().__init__(ValidationPolicy(CODE_ALLOWED))


class ProgramValidator(BaseValidator):
    def __init__(self):
        super().__init__(ValidationPolicy(PROGRAM_ALLOWED))


class AlgoProgramValidator(BaseValidator):
    def __init__(self):
        super().__init__(ValidationPolicy(ALGO_ALLOWED))


def validate_code(code: str) -> Tuple[bool, str]:
    try:
        tree = ast.parse(code)
        v = CodeValidator()
        v.visit(tree)
        return v.ok, v.err or ""
    except Exception as exc:
        return False, str(exc)


def validate_program(code: str) -> Tuple[bool, str]:
    try:
        tree = ast.parse(code)
        v = ProgramValidator()
        v.visit(tree)
        return v.ok, v.err or ""
    except Exception as exc:
        return False, str(exc)


def validate_algo_program(code: str) -> Tuple[bool, str]:
    try:
        tree = ast.parse(code)
        v = AlgoProgramValidator()
        v.visit(tree)
        if not v.ok:
            return False, v.err or ""
        from Systemtest import algo_program_limits_ok
        if not algo_program_limits_ok(code):
            return False, "algo_program_limits"
        return True, ""
    except Exception as exc:
        return False, str(exc)
