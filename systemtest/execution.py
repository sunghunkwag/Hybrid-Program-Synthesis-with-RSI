"""Execution helpers for generated code (watchdog-isolated)."""
from __future__ import annotations

import dataclasses
import json
import textwrap
from typing import Any, Dict, List, Tuple

from watchdog_executor import WatchdogExecutor


def _serialize_task(task: Any) -> str:
    if dataclasses.is_dataclass(task):
        payload = dataclasses.asdict(task)
    elif hasattr(task, "__dict__"):
        payload = dict(task.__dict__)
    else:
        payload = {"value": task}
    return json.dumps(payload, default=str)


def _primitive_prelude() -> str:
    return textwrap.dedent(
        """
        from neuro_genetic_synthesizer import LibraryManager

        _lib = LibraryManager()
        globals().update(_lib.runtime_primitives)
        """
    )


def run_candidate_with_watchdog(code: str, task: Any, timeout: float) -> Tuple[bool, str]:
    payload = _serialize_task(task)
    wrapper = textwrap.dedent(
        f"""
        import json

        _payload = json.loads({payload!r})

        class Task:
            def __init__(self, payload: dict):
                self.__dict__.update(payload)

        task = Task(_payload)
        {_primitive_prelude()}
        {code}
        if 'solve' in locals():
            result = solve(task)
        else:
            result = None
        """
    )
    executor = WatchdogExecutor(timeout=timeout)
    result = executor.run_safe(wrapper, timeout=timeout)
    if not result.get("success"):
        return False, result.get("error", "Watchdog failure")
    if result.get("result") is None:
        return False, "No 'solve' function defined"
    return True, f"Result: {result.get('result')}, Expected: {getattr(task, 'expected', None)}"


def make_watchdog_callable(code: str, func_name: str, timeout: float = 2.0, inject_primitives: bool = True):
    def _call(*args, **kwargs):
        payload = json.dumps({"args": args, "kwargs": kwargs}, default=str)
        prelude = _primitive_prelude() if inject_primitives else ""
        wrapper = textwrap.dedent(
            f"""
            import json
            _payload = json.loads({payload!r})
            {prelude}
            {code}
            result = {func_name}(*_payload['args'], **_payload['kwargs'])
            """
        )
        executor = WatchdogExecutor(timeout=timeout)
        result = executor.run_safe(wrapper, timeout=timeout)
        if not result.get("success"):
            raise RuntimeError(result.get("error", "Watchdog execution failed"))
        return result.get("result")

    return _call


def make_watchdog_expr_callable(
    expr: str,
    params: List[str],
    timeout: float = 2.0,
    inject_primitives: bool = True,
):
    def _call(*args, **kwargs):
        payload = json.dumps({"args": args, "kwargs": kwargs}, default=str)
        assignments = "\n".join(
            f"{name} = args[{idx}]" for idx, name in enumerate(params)
        )
        prelude = _primitive_prelude() if inject_primitives else ""
        wrapper = textwrap.dedent(
            f"""
            import json
            _payload = json.loads({payload!r})
            args = _payload['args']
            kwargs = _payload['kwargs']
            {prelude}
            {assignments}
            result = ({expr})
            """
        )
        executor = WatchdogExecutor(timeout=timeout)
        result = executor.run_safe(wrapper, timeout=timeout)
        if not result.get("success"):
            raise RuntimeError(result.get("error", "Watchdog execution failed"))
        return result.get("result")

    return _call
