"""Bounded RSI improvement loop using WatchdogExecutor."""
from __future__ import annotations

import argparse
import json
import os
import random
import shutil
import time
from dataclasses import dataclass
from pathlib import Path
from statistics import median
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

from watchdog_executor import WatchdogExecutor

META_WEIGHTS_FILE = "rsi_meta_weights.json"
REGISTRY_FILE = "rsi_primitive_registry.json"

MAX_ROUNDS = 20
TRIALS_PER_ROUND = 50
WATCHDOG_TIMEOUT_SEC = 2.0


@dataclass
class TrialResult:
    success: bool
    elapsed_s: float
    code: Optional[str]


@dataclass
class RoundSummary:
    round_idx: int
    control_success_rate: float
    treatment_success_rate: float
    control_median_time: Optional[float]
    treatment_median_time: Optional[float]


def normalize_caps(rounds: int, trials: int) -> Tuple[int, int]:
    return min(rounds, MAX_ROUNDS), min(trials, TRIALS_PER_ROUND)


def build_tasks(seed: int, trials: int) -> List[Dict[str, Any]]:
    rng = random.Random(seed)
    tasks = []
    task_types = ["identity", "double", "square"]
    for i in range(trials):
        task_type = task_types[i % len(task_types)]
        io_pairs = []
        for n in range(5):
            if task_type == "identity":
                io_pairs.append({"input": n, "output": n})
            elif task_type == "double":
                io_pairs.append({"input": n, "output": n * 2})
            else:
                io_pairs.append({"input": n, "output": n * n})
        tasks.append({"id": f"task_{seed}_{i}", "type": task_type, "io_pairs": io_pairs})
    rng.shuffle(tasks)
    return tasks


def _primitive_prelude() -> str:
    return """
from neuro_genetic_synthesizer import LibraryManager
_lib = LibraryManager()
globals().update(_lib.runtime_primitives)
"""


def run_watchdog_snippet(code: str, timeout: float) -> Dict[str, Any]:
    executor = WatchdogExecutor(timeout=timeout)
    return executor.run_safe(code, timeout=timeout)


def evaluate_code_with_watchdog(code: str, io_pairs: Iterable[Dict[str, Any]], timeout: float) -> Tuple[bool, Optional[float]]:
    start = time.time()
    for pair in io_pairs:
        value = pair["input"]
        expected = pair["output"]
        if code.strip().startswith("def "):
            snippet = f"""
{_primitive_prelude()}
{code}
result = solve({value!r})
"""
        else:
            snippet = f"""
{_primitive_prelude()}

def solve(n):
    return {code}

result = solve({value!r})
"""
        result = run_watchdog_snippet(snippet, timeout)
        if not result.get("success"):
            return False, None
        if result.get("result") != expected:
            return False, None
    return True, time.time() - start


def run_trials(
    tasks: List[Dict[str, Any]],
    synth_factory: Callable[[bool], Any],
    use_meta: bool,
    synth_timeout: float,
    watchdog_timeout: float,
) -> List[TrialResult]:
    results: List[TrialResult] = []
    synth = synth_factory(use_meta)
    for task in tasks:
        start = time.time()
        code = None
        success = False
        for candidate in synth.synthesize(task["io_pairs"], timeout=synth_timeout):
            code = candidate[0]
            ok, _ = evaluate_code_with_watchdog(code, task["io_pairs"], watchdog_timeout)
            if ok:
                success = True
                break
        elapsed = time.time() - start
        results.append(TrialResult(success=success, elapsed_s=elapsed, code=code))
    return results


def summarize_round(round_idx: int, control: List[TrialResult], treatment: List[TrialResult]) -> RoundSummary:
    control_success = [r for r in control if r.success]
    treatment_success = [r for r in treatment if r.success]
    control_times = [r.elapsed_s for r in control_success]
    treatment_times = [r.elapsed_s for r in treatment_success]
    return RoundSummary(
        round_idx=round_idx,
        control_success_rate=len(control_success) / max(1, len(control)),
        treatment_success_rate=len(treatment_success) / max(1, len(treatment)),
        control_median_time=median(control_times) if control_times else None,
        treatment_median_time=median(treatment_times) if treatment_times else None,
    )


def snapshot_artifacts(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for filename in (META_WEIGHTS_FILE, REGISTRY_FILE):
        path = Path(filename)
        if path.exists():
            shutil.copy2(path, output_dir / path.name)


def write_summary(output_dir: Path, summaries: List[RoundSummary]) -> None:
    lines = ["# RSI Watchdog Loop Summary", ""]
    for summary in summaries:
        lines.append(
            f"Round {summary.round_idx}: control={summary.control_success_rate:.2f}, "
            f"treatment={summary.treatment_success_rate:.2f}"
        )
    (output_dir / "summary.md").write_text("\n".join(lines), encoding="utf-8")


def run_loop(
    rounds: int,
    trials: int,
    seed: int,
    synth_timeout: float,
    watchdog_timeout: float,
    output_root: Path,
) -> Path:
    rounds, trials = normalize_caps(rounds, trials)
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    output_dir = output_root / timestamp
    output_dir.mkdir(parents=True, exist_ok=True)

    summaries: List[RoundSummary] = []
    metrics_path = output_dir / "metrics.jsonl"

    for round_idx in range(rounds):
        tasks = build_tasks(seed + round_idx, trials)
        snapshot_artifacts(output_dir / f"round_{round_idx}_before")

        from neuro_genetic_synthesizer import NeuroGeneticSynthesizer

        control_results = run_trials(
            tasks,
            lambda _: NeuroGeneticSynthesizer(use_meta_heuristic=False),
            use_meta=False,
            synth_timeout=synth_timeout,
            watchdog_timeout=watchdog_timeout,
        )
        treatment_results = run_trials(
            tasks,
            lambda _: NeuroGeneticSynthesizer(use_meta_heuristic=True),
            use_meta=True,
            synth_timeout=synth_timeout,
            watchdog_timeout=watchdog_timeout,
        )

        summary = summarize_round(round_idx, control_results, treatment_results)
        summaries.append(summary)

        with metrics_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(summary.__dict__) + "\n")

        snapshot_artifacts(output_dir / f"round_{round_idx}_after")

    write_summary(output_dir, summaries)
    return output_dir


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Bounded RSI watchdog loop")
    parser.add_argument("--rounds", type=int, default=3)
    parser.add_argument("--trials", type=int, default=10)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--synth-timeout", type=float, default=2.0)
    parser.add_argument("--watchdog-timeout", type=float, default=WATCHDOG_TIMEOUT_SEC)
    parser.add_argument("--output-root", type=Path, default=Path("runs"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    run_loop(
        rounds=args.rounds,
        trials=args.trials,
        seed=args.seed,
        synth_timeout=args.synth_timeout,
        watchdog_timeout=args.watchdog_timeout,
        output_root=args.output_root,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
