# SystemTest: Structural Synthesis and Discovery

## Overview

This repository contains an autonomous algorithm discovery system implementing Recursive Self-Improvement (RSI). The system uses a hybrid Neuro-Genetic architecture to synthesize programs, discover reusable concepts, and expand its own grammar dynamically.

## Core Components

* **Systemtest.py**: Main orchestrator handling the life-cycle loop, problem generation, and H-Module (Discovery) / L-Module (Execution) coordination.
* **rs_machine (Rust)**: High-performance Virtual Machine implementation using PyO3. Accelerates program evaluation by orders of magnitude compared to the Python fallback.
* **SelfPurposeEngine**: Autonomous goal definition system that detects emergent patterns in the environment to formulate internal objectives.
* **ConceptTransferEngine**: Mechanism for generalizing learned concepts to new, unseen domains (Human-Level Generalization).

## New Capabilities: High Performance & Autonomy

* **Rust Acceleration**: The core execution loop is rewriting in Rust. The system automatically detects and loads the optimized `rs_machine` binary if installed, falling back to Python transparently if not.
* **Autonomous Goal Discovery**: The system no longer relies solely on external tasks but can formulate its own "purpose" based on environmental novelty and pattern consistency.

## Usage

Run the infinite life-cycle loop:

```bash
python Systemtest.py hrm-life
```

## Requirements

* Python 3.8+
* Rust Toolchain & Cargo (for compiling `rs_machine`)
* `maturin` (for building the Python-Rust bridge)
* Standard library only for fallback mode.

