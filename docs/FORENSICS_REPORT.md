# Forensics Report

## A) Dependency + connectivity map

### Systemtest.py
- **Imports:** heavy standard library usage plus local modules `neuro_genetic_synthesizer`, `meta_heuristic`, and `watchdog_executor`. The file declares multiple internal subsystems and defines the active `__main__` entrypoint at the end of the file.
- **Runtime relevance:** core runtime entrypoint (default). It contains multiple embedded systems and several `main()` definitions; the last `main()` is the one invoked by `if __name__ == "__main__"`.
- **Role:** core runtime + experimental/legacy subsystems (embedded).

### watchdog_executor.py
- **Imports:** standard library only.
- **Runtime relevance:** core runtime safety component (process isolation executor).
- **Role:** core runtime.

### safe_interpreter.py
- **Imports:** standard library plus type hints; references `neuro_genetic_synthesizer` in conversion helpers.
- **Runtime relevance:** DSL-only evaluation engine (no exec/eval). Used by `library_manager.py` for allowed op mapping.
- **Role:** core runtime (DSL evaluation).

### library_manager.py
- **Imports:** `safe_interpreter` for DSL structures and allowed ops.
- **Runtime relevance:** primitive registry + persistence for DSL system.
- **Role:** core runtime.

### neuro_genetic_synthesizer.py
- **Imports:** standard library, NumPy if available.
- **Runtime relevance:** provides `SafeInterpreter`, `LibraryManager`, and `NeuroGeneticSynthesizer` classes used by Systemtest and verify_rsi_impact.
- **Role:** core runtime.

### meta_heuristic.py
- **Imports:** standard library only.
- **Runtime relevance:** search/weighting component used by neuro_genetic_synthesizer and verify_rsi_impact.
- **Role:** core runtime.

### verify_rsi_impact.py
- **Imports:** standard library, uses `NeuroGeneticSynthesizer` and `MetaHeuristic`.
- **Runtime relevance:** tooling/experiment harness (A/B evaluation).
- **Role:** tooling/experimental.

### analyze_reuse.py
- **Imports:** standard library; reads checkpoint files.
- **Runtime relevance:** tooling/analysis (reuse checks).
- **Role:** tooling.

### inspect_checkpoint.py
- **Status:** missing from repository at time of forensics. The Phase 0 compile command failed due to missing file.
- **Role:** expected tooling (by filename).

### requirements.txt
- **Runtime relevance:** dependency list.
- **Role:** tooling/config.

## B) Entrypoints & call graph

### __main__ blocks
- `Systemtest.py` → `main()` at end of file (final definition wins).
- `watchdog_executor.py` → internal test harness.
- `safe_interpreter.py` → internal test harness.
- `library_manager.py` → internal test harness.
- `neuro_genetic_synthesizer.py` → internal self-test.
- `verify_rsi_impact.py` → `run_experiment()`.
- `analyze_reuse.py` → executes on import (top-level code; no guard).

### Multiple `main()` definitions in Systemtest.py
- Several `main()` functions appear in the file; the last definition overrides previous ones due to Python name rebinding. The final `main()` dispatches the CLI for orchestrator-related runs and is called by `if __name__ == "__main__"`.

### Default execution path for `python Systemtest.py --help`
1. Python loads `Systemtest.py`.
2. Last `main()` definition parses CLI arguments and prints help when no valid subcommand is supplied.

### Representative runtime command path
- `python Systemtest.py` (no args)
  1. `__main__` calls `main()`.
  2. `main()` sets default command to `orchestrator-smoke`.
  3. `orchestrator_main()` runs the 30-iteration loop.

## C) Zombie code verification

### 1) RuntimeGuard / EXEC BANNED legacy paths
- `RuntimeGuard()` raises unconditionally and is invoked by `legacy_evaluate_expr`, `legacy_run`, `legacy_run_algo`, `legacy_run_engine`, `legacy_load_module`.
- Several call sites reference `legacy_run`/`legacy_evaluate_expr` via lambdas or helper paths, implying any path that reaches them will raise immediately.

### 2) Orphan HRM v2
- `run_hrm_life_v2` was removed from `Systemtest.py` in the latest commit and is now located under `legacy/` (not in the target `systemtest/legacy/` path).
- No active CLI wiring exists for the legacy function.

### 3) Validator duplication
- `CodeValidator`, `ProgramValidator`, and `AlgoProgramValidator` are defined in `Systemtest.py` with overlapping allowed-node logic.
- Only `AlgoProgramValidator` is referenced in `cmd_selftest`; the others are defined but unused.

### 4) Architecture conflation
- Systemtest.py embeds multiple subsystems (Omega Forge, Two-Stage Evolution, non-RSI AGI core, orchestrator). The default `main()` at the end of the file dispatches the orchestrator smoke test by default, while earlier `main()` functions become shadowed.

## D) Execution-safety strategy conflict
- `safe_interpreter.py` declares DSL-only execution with no exec/eval.
- `watchdog_executor.py` explicitly uses exec() in a child process (process isolation).
- `Systemtest.py` uses direct exec() in the main process for candidate evaluation and other paths.

**Resolution strategy (proposed):**
- Use WatchdogExecutor for full-program execution (Strategy B), and reserve SafeInterpreter for DSL-only evaluation. Remove raw exec in the main process for generated code.

## E) dead_code_candidates.json
- Produced separately at repo root as requested.
