"""
CONCEPT TRANSFER VERIFICATION TEST
Proves that concepts learned from one task can be transferred to another.
"""

import sys
sys.path.insert(0, '.')

from concept_transfer import ConceptTransferEngine

from Systemtest import ProgramGenome, Instruction, VirtualMachine
from neuro_genetic_synthesizer import NeuroInterpreter

# Use the REAL components
class RealInterpreterAdapter:
    """Adapts the Systemtest.VirtualMachine to the ConceptTransfer interface."""
    def __init__(self):
        self.vm = VirtualMachine(max_steps=100)

    def run(self, genome, env):
        # Convert dictionary env to list inputs based on index convention
        # This assumes the concept expression relies on standard register/memory conventions
        # For this test, we construct inputs where n is at index 0
        inputs = [0.0] * 8
        if 'n' in env:
            inputs[0] = float(env['n'])
        
        state = self.vm.execute(genome, inputs)
        # Assume result is in register 0 (standard accumulation register)
        return state.regs[0]

# Helper to create REAL genomes
def create_genome(op_list):
    insts = [Instruction(op, a, b, c) for op, a, b, c in op_list]
    return ProgramGenome(gid="test", instructions=insts)


def test_concept_transfer():
    print("=" * 60)
    print("CONCEPT TRANSFER PROOF TEST")
    print("=" * 60)
    
    interp = RealInterpreterAdapter()
    engine = ConceptTransferEngine(interpreter=interp)
    
    # n is assumed to be in Reg[0]
    
    # =========================================
    # PHASE 1: Learn concepts from Task A
    # =========================================
    print("\n[PHASE 1] Learning Phase - Task A")
    print("-" * 40)
    
    # Concept 1: double(n) = n + n (REAL ASM CODE)
    # Reg[0] has n. ADD Reg[0], Reg[0] -> Reg[0]
    double_genome = create_genome([("ADD", 0, 0, 0), ("HALT", 0, 0, 0)])
    engine.register_concept("double", double_genome)
    print(f"  Registered: double = {double_genome.instructions}")
    
    # Concept 2: triple(n) = n + n + n
    # ADD 0, 0 -> 1 (tmp); ADD 1, 0 -> 0
    triple_genome = create_genome([("ADD", 0, 0, 1), ("ADD", 1, 0, 0), ("HALT", 0, 0, 0)])
    engine.register_concept("triple", triple_genome)
    print(f"  Registered: triple = {triple_genome.instructions}")
    
    # Concept 3: square(n) = n * n
    square_genome = create_genome([("MUL", 0, 0, 0), ("HALT", 0, 0, 0)])
    engine.register_concept("square", square_genome)
    print(f"  Registered: square = {square_genome.instructions}")
    
    print(f"\n  Library size: {engine.get_stats()['total_concepts']} concepts")
    
    # =========================================
    # PHASE 2: Meta-Pattern Discovery
    # =========================================
    print("\n[PHASE 2] Meta-Pattern Discovery")
    print("-" * 40)
    
    patterns = engine.discover_meta_patterns()
    print(f"  Level 1 patterns: {len(patterns[1])}")
    print(f"  Level 2 patterns: {len(patterns[2])}")
    print(f"  Level 3 patterns: {len(patterns[3])}")
    
    # =========================================
    # PHASE 3: Transfer to Task B (CRITICAL TEST)
    # =========================================
    print("\n[PHASE 3] Transfer Test - Task B")
    print("-" * 40)
    
    # Task B: Find function where f(n) = 2n
    # This SHOULD match "double" from Task A!
    task_b_ios = [
        {'input': 0, 'output': 0},
        {'input': 1, 'output': 2},
        {'input': 2, 'output': 4},
        {'input': 3, 'output': 6},
        {'input': 5, 'output': 10},
    ]
    
    print(f"  Task B I/O: {task_b_ios[:3]}...")
    print(f"  Attempting transfer...")
    
    candidates = engine.transfer(task_b_ios)
    
    if candidates:
        top_name, top_expr, score, method = candidates[0]
        print(f"\n  TOP CANDIDATE:")
        print(f"    Name: {top_name}")
        print(f"    Expr: {top_expr}")
        print(f"    Score: {score:.2f}")
        print(f"    Method: {method}")
        
        if score >= 0.9:
            print(f"\n  *** SUCCESS! Concept '{top_name}' transferred with {score*100:.0f}% confidence! ***")
            transfer_success = True
        else:
            print(f"\n  Partial match only (score < 0.9)")
            transfer_success = False
    else:
        print(f"\n  No transfer candidates found!")
        transfer_success = False
    
    # =========================================
    # PHASE 4: Structure Analogy Test
    # =========================================
    print("\n[PHASE 4] Structure Analogy Test")
    print("-" * 40)
    
    # Query for expressions with similar structure to double
    # Query for expressions with similar structure to double
    analogies = engine.get_analogies("double")
    print(f"  Expressions structurally similar to 'double': {len(analogies)}")
    for name, expr in analogies[:5]:
        print(f"    - {name}: {expr.instructions}")
    
    # =========================================
    # PHASE 5: Type-Based Swapping Test
    # =========================================
    print("\n[PHASE 5] Type-Based Swapping Test")
    print("-" * 40)
    
    swappable = engine.get_swappable("double")
    print(f"  Concepts swappable with 'double': {len(swappable)}")
    for name, expr in swappable:
        print(f"    - {name}: {expr.instructions}")
    
    # =========================================
    # FINAL VERDICT
    # =========================================
    print("\n" + "=" * 60)
    if transfer_success:
        print("VERDICT: CONCEPT TRANSFER VERIFIED!")
        print("  - Concept 'double' learned from Task A")
        print("  - Successfully transferred to Task B")
        print("  - NO NEW SYNTHESIS REQUIRED")
    else:
        print("VERDICT: TRANSFER INCOMPLETE")
        print("  - Concepts registered but transfer not triggered")
    print("=" * 60)
    
    return transfer_success


if __name__ == "__main__":
    success = test_concept_transfer()
    sys.exit(0 if success else 1)
