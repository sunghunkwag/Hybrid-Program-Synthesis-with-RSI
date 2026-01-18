# Refactor Plan

## Commit sequence

1) **Commit 1: add trace hooks**
   - Add TRACE_EXEC env-controlled logging in Systemtest entrypoints.
   - Add missing `inspect_checkpoint.py` as a tooling script (minimal, read-only).
   - Risk: low.
   - Tests: `python -m py_compile ...` (full list).

2) **Commit 2: de-duplicate WatchdogExecutor**
   - Ensure Systemtest imports WatchdogExecutor from watchdog_executor.py.
   - Confirm all call sites use the shared executor.
   - Risk: low.
   - Tests: `python -m py_compile ...`.

3) **Commit 3: unify generated-code execution**
   - Route generated program execution through WatchdogExecutor only.
   - Remove raw exec in main process for generated code.
   - Risk: medium.
   - Tests: `pytest -q` + `python -m py_compile ...`.

4) **Commit 4: registry filename normalization**
   - Default registry to `rsi_primitive_registry.json` with legacy fallback load only.
   - Risk: low.
   - Tests: `pytest -q` + `python -m py_compile ...`.

5) **Commit 5: quarantine HRM v2**
   - Move legacy HRM v2 into `systemtest/legacy/hrm_life_v2.py` and document in REMOVALS.
   - Optional CLI stub to invoke legacy module when explicitly called.
   - Risk: low.
   - Tests: `python -m py_compile ...`.

6) **Commit 6: validator dedup**
   - Create `systemtest/validators.py` and update Systemtest imports.
   - Risk: medium.
   - Tests: `pytest -q`.

7) **Commit 7: bounded RSI watchdog loop**
   - Add `rsi_watchdog_loop.py` with explicit caps and artifact logging.
   - Add tests for caps, watchdog timeout enforcement, and persistence.
   - Risk: medium.
   - Tests: `pytest -q` + short loop run.

## Risk & rollback
- Rollback is `git revert` of commits in reverse order.
- High-risk points: commit 3 (execution changes) and commit 6/7 (new modules/tests).

## Test plan per commit
- Compile: `python -m py_compile ...` every commit.
- Pytest coverage once tests are added, plus a short loop run after commit 7.
