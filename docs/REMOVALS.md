# Removals / Quarantines

- `run_hrm_life_v2` moved from `legacy/hrm_life_v2.py` to `systemtest/legacy/hrm_life_v2.py` to quarantine the legacy loop while keeping it reachable via an explicit `hrm-life-v2` CLI subcommand in Systemtest.
- Removed `rsi_verification_results.json` (generated experiment output) and added it to `.gitignore` to avoid committing run artifacts.
