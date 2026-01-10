"""
SELF-PURPOSE ENGINE WITH TEMPORAL INVERSION
============================================
The system defines its own purpose.
No external fitness function. No human-defined goals.

Mechanism:
1. Generate random "solutions" (expressions)
2. Temporal Inversion: Infer what "problem" this solution solves
3. Evaluate "interestingness" of the discovered problem
4. Evolve the interestingness criteria based on growth

Result: Emergent purpose that no human defined.
"""

import random
import hashlib
from dataclasses import dataclass, field
from typing import List, Dict, Any, Tuple, Optional, Set
from collections import defaultdict


# ==============================================================================
# DATA STRUCTURES
# ==============================================================================

@dataclass
class DiscoveredProblem:
    """A problem discovered through temporal inversion."""
    io_pairs: List[Tuple[int, int]]  # (input, output) pairs
    solution_expr: Any  # The expression that solves this
    interestingness: float  # How interesting this problem is
    discovery_cycle: int  # When it was discovered
    hash: str = ""  # Unique identifier
    
    def __post_init__(self):
        if not self.hash:
            sig = str(self.io_pairs[:5])
            self.hash = hashlib.md5(sig.encode()).hexdigest()[:12]


@dataclass
class InterestingnessCriteria:
    """Evolving criteria for what makes a problem interesting."""
    compression_weight: float = 1.0  # Prefer compressible patterns
    novelty_weight: float = 1.0  # Prefer unseen patterns
    difficulty_weight: float = 1.0  # Prefer barely-solvable problems
    self_reference_weight: float = 0.5  # Prefer problems about system behavior
    
    def mutate(self, rate: float = 0.1):
        """Small random mutation of criteria weights."""
        self.compression_weight = max(0.1, self.compression_weight + random.gauss(0, rate))
        self.novelty_weight = max(0.1, self.novelty_weight + random.gauss(0, rate))
        self.difficulty_weight = max(0.1, self.difficulty_weight + random.gauss(0, rate))
        self.self_reference_weight = max(0.1, self.self_reference_weight + random.gauss(0, rate))
        
        # Normalize
        total = self.compression_weight + self.novelty_weight + self.difficulty_weight + self.self_reference_weight
        self.compression_weight /= total
        self.novelty_weight /= total
        self.difficulty_weight /= total
        self.self_reference_weight /= total


# ==============================================================================
# SIMPLE EXPRESSION GENERATOR (No external deps)
# ==============================================================================

class SimpleExprGen:
    """Generate random mathematical expressions."""
    
    OPS = ['add', 'mul', 'sub', 'div', 'mod']
    
    def __init__(self):
        self.rng = random.Random()
    
    def generate(self, depth: int = 3) -> str:
        """Generate a random expression string."""
        if depth <= 0 or self.rng.random() < 0.3:
            # Terminal: n or constant
            if self.rng.random() < 0.7:
                return 'n'
            else:
                return str(self.rng.randint(0, 5))
        
        op = self.rng.choice(self.OPS)
        left = self.generate(depth - 1)
        right = self.generate(depth - 1)
        return f"{op}({left}, {right})"
    
    def evaluate(self, expr: str, n: int) -> Optional[int]:
        """Evaluate expression for given n."""
        try:
            # Build safe context
            context = {
                'add': lambda a, b: a + b,
                'mul': lambda a, b: a * b,
                'sub': lambda a, b: a - b,
                'div': lambda a, b: a // b if b != 0 else 0,
                'mod': lambda a, b: a % b if b != 0 else 0,
                'n': n
            }
            result = eval(expr, {"__builtins__": {}}, context)
            # Bounds check
            if isinstance(result, int) and -1000000 < result < 1000000:
                return result
            return None
        except:
            return None


# ==============================================================================
# SELF-PURPOSE ENGINE
# ==============================================================================

class SelfPurposeEngine:
    """
    The system that defines its own purpose through temporal inversion.
    
    Core idea:
    - Don't ask "what solves this problem?"
    - Ask "what problem does this solution solve?"
    - Then ask "is that problem interesting?"
    - Evolve what "interesting" means based on growth.
    """
    
    def __init__(self):
        self.expr_gen = SimpleExprGen()
        self.criteria = InterestingnessCriteria()
        
        self.discovered_problems: List[DiscoveredProblem] = []
        self.problem_hashes: Set[str] = set()  # For novelty check
        self.purpose_history: List[str] = []  # Record of discovered purposes
        
        self.cycle = 0
        self.growth_before_criteria_change = 0
        self.last_criteria_snapshot = None
        
        # Stats
        self.total_generated = 0
        self.total_interesting = 0
    
    # -------------------------------------------------------------------------
    # TEMPORAL INVERSION: Solution → Problem
    # -------------------------------------------------------------------------
    
    def invert(self, expr: str, input_range: int = 10) -> Optional[DiscoveredProblem]:
        """
        Temporal Inversion: Given a solution, discover the problem it solves.
        """
        io_pairs = []
        for n in range(input_range):
            output = self.expr_gen.evaluate(expr, n)
            if output is None:
                return None  # Invalid expression
            io_pairs.append((n, output))
        
        return DiscoveredProblem(
            io_pairs=io_pairs,
            solution_expr=expr,
            interestingness=0.0,  # Will be computed
            discovery_cycle=self.cycle
        )
    
    # -------------------------------------------------------------------------
    # INTERESTINGNESS EVALUATION
    # -------------------------------------------------------------------------
    
    def evaluate_interestingness(self, problem: DiscoveredProblem) -> float:
        """
        Evaluate how interesting a discovered problem is.
        This is where "purpose" emerges - what the system values.
        """
        scores = {}
        
        # 1. Compression: Does the I/O pattern have structure?
        outputs = [p[1] for p in problem.io_pairs]
        scores['compression'] = self._compression_score(outputs)
        
        # 2. Novelty: Have we seen this pattern before?
        scores['novelty'] = 1.0 if problem.hash not in self.problem_hashes else 0.0
        
        # 3. Difficulty: Is this barely solvable? (proxy: expression complexity)
        scores['difficulty'] = self._difficulty_score(problem.solution_expr)
        
        # 4. Self-reference: Does this relate to system behavior?
        scores['self_reference'] = self._self_reference_score(problem)
        
        # Weighted sum
        total = (
            self.criteria.compression_weight * scores['compression'] +
            self.criteria.novelty_weight * scores['novelty'] +
            self.criteria.difficulty_weight * scores['difficulty'] +
            self.criteria.self_reference_weight * scores['self_reference']
        )
        
        problem.interestingness = total
        return total
    
    def _compression_score(self, outputs: List[int]) -> float:
        """Higher if outputs have clear pattern (low entropy)."""
        if len(outputs) < 2:
            return 0.0
        
        # Check for constant
        if len(set(outputs)) == 1:
            return 0.3  # Boring but structured
        
        # Check for arithmetic progression
        diffs = [outputs[i+1] - outputs[i] for i in range(len(outputs)-1)]
        if len(set(diffs)) == 1:
            return 0.9  # Linear - very structured
        
        # Check for geometric-ish
        if outputs[0] != 0:
            ratios = [outputs[i+1] / outputs[i] if outputs[i] != 0 else 0 for i in range(len(outputs)-1)]
            if len(set(ratios)) <= 2:
                return 0.8
        
        # General entropy estimate
        unique_ratio = len(set(outputs)) / len(outputs)
        return 1.0 - unique_ratio  # Less unique = more structured
    
    def _difficulty_score(self, expr: str) -> float:
        """Higher for moderately complex expressions."""
        # Count depth/operations
        ops = sum(1 for op in ['add', 'mul', 'sub', 'div', 'mod'] if op in expr)
        
        # Sweet spot: 3-5 operations
        if 3 <= ops <= 5:
            return 1.0
        elif 1 <= ops <= 7:
            return 0.7
        else:
            return 0.3
    
    def _self_reference_score(self, problem: DiscoveredProblem) -> float:
        """Higher if problem relates to system's own behavior."""
        outputs = [p[1] for p in problem.io_pairs]
        
        # Check if outputs match cycle count, problem count, etc.
        if self.cycle in outputs:
            return 0.8
        if len(self.discovered_problems) in outputs:
            return 0.6
        
        return 0.0
    
    # -------------------------------------------------------------------------
    # CRITERIA EVOLUTION (Meta-learning)
    # -------------------------------------------------------------------------
    
    def evolve_criteria(self):
        """
        Evolve what "interesting" means based on what leads to growth.
        Growth = discovery of new problems, increase in capability.
        """
        current_growth = len(self.discovered_problems)
        
        if self.last_criteria_snapshot is None:
            self.last_criteria_snapshot = InterestingnessCriteria(
                compression_weight=self.criteria.compression_weight,
                novelty_weight=self.criteria.novelty_weight,
                difficulty_weight=self.criteria.difficulty_weight,
                self_reference_weight=self.criteria.self_reference_weight
            )
            self.growth_before_criteria_change = current_growth
            return
        
        # Compare growth
        growth_delta = current_growth - self.growth_before_criteria_change
        
        if growth_delta > 5:
            # Good criteria - keep and mutate slightly
            self.criteria.mutate(rate=0.05)
            print(f"[SelfPurpose] Criteria working well (growth={growth_delta}). Small mutation.")
        else:
            # Bad criteria - mutate more aggressively
            self.criteria.mutate(rate=0.2)
            print(f"[SelfPurpose] Criteria not working (growth={growth_delta}). Large mutation.")
        
        # Reset tracking
        self.last_criteria_snapshot = InterestingnessCriteria(
            compression_weight=self.criteria.compression_weight,
            novelty_weight=self.criteria.novelty_weight,
            difficulty_weight=self.criteria.difficulty_weight,
            self_reference_weight=self.criteria.self_reference_weight
        )
        self.growth_before_criteria_change = current_growth
    
    # -------------------------------------------------------------------------
    # MAIN LOOP
    # -------------------------------------------------------------------------
    
    def run_cycle(self) -> Optional[DiscoveredProblem]:
        """
        One cycle of self-purpose discovery.
        Returns an interesting problem if found, None otherwise.
        """
        self.cycle += 1
        self.total_generated += 1
        
        # 1. Generate random solution
        expr = self.expr_gen.generate(depth=random.randint(2, 4))
        
        # 2. Temporal Inversion: What problem does this solve?
        problem = self.invert(expr)
        if problem is None:
            return None
        
        # 3. Evaluate interestingness
        score = self.evaluate_interestingness(problem)
        
        # 4. Accept if interesting enough (threshold adapts)
        threshold = 0.5 * (1.0 + self.total_interesting / max(1, self.total_generated))
        threshold = min(0.8, threshold)  # Cap
        
        if score >= threshold and problem.hash not in self.problem_hashes:
            self.discovered_problems.append(problem)
            self.problem_hashes.add(problem.hash)
            self.total_interesting += 1
            
            # Log emergent purpose
            purpose_desc = self._describe_problem(problem)
            self.purpose_history.append(purpose_desc)
            print(f"[SelfPurpose] EMERGENT PURPOSE: {purpose_desc} (score={score:.3f})")
            
            return problem
        
        # 5. Evolve criteria every 50 cycles
        if self.cycle % 50 == 0:
            self.evolve_criteria()
        
        return None
    
    def _describe_problem(self, problem: DiscoveredProblem) -> str:
        """Generate human-readable description of discovered problem."""
        outputs = [p[1] for p in problem.io_pairs[:5]]
        
        # Check patterns
        diffs = [outputs[i+1] - outputs[i] for i in range(len(outputs)-1)]
        
        if len(set(outputs)) == 1:
            return f"constant_{outputs[0]}"
        elif len(set(diffs)) == 1:
            return f"linear_d{diffs[0]}"
        elif outputs == [0, 1, 4, 9, 16]:
            return "squares"
        elif all(o == i**2 + i for i, o in enumerate(outputs)):
            return "quadratic_n2+n"
        else:
            return f"pattern_{outputs[0]}_{outputs[-1]}"
    
    def get_stats(self) -> Dict[str, Any]:
        """Return engine statistics."""
        return {
            "cycle": self.cycle,
            "total_generated": self.total_generated,
            "total_interesting": self.total_interesting,
            "discovery_rate": self.total_interesting / max(1, self.total_generated),
            "criteria": {
                "compression": round(self.criteria.compression_weight, 3),
                "novelty": round(self.criteria.novelty_weight, 3),
                "difficulty": round(self.criteria.difficulty_weight, 3),
                "self_reference": round(self.criteria.self_reference_weight, 3)
            },
            "purposes_discovered": len(self.purpose_history),
            "recent_purposes": self.purpose_history[-5:] if self.purpose_history else []
        }
    
    def get_dominant_purpose(self) -> str:
        """Identify what the system seems to value most."""
        if not self.discovered_problems:
            return "UNDEFINED"
        
        # Analyze what types of problems were discovered
        patterns = defaultdict(int)
        for p in self.discovered_problems[-20:]:  # Recent 20
            desc = self._describe_problem(p)
            pattern_type = desc.split('_')[0]
            patterns[pattern_type] += 1
        
        if patterns:
            dominant = max(patterns, key=patterns.get)
            return f"EMERGENT_PURPOSE: seeking_{dominant}_patterns"
        return "EXPLORING"


# ==============================================================================
# STANDALONE TEST
# ==============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("SELF-PURPOSE ENGINE TEST")
    print("The system will define its own purpose...")
    print("=" * 60)
    
    engine = SelfPurposeEngine()
    
    for cycle in range(100):
        result = engine.run_cycle()
        
        if cycle % 20 == 0:
            stats = engine.get_stats()
            print(f"\n[Cycle {cycle}] Discoveries: {stats['total_interesting']}, Rate: {stats['discovery_rate']:.2%}")
            print(f"  Criteria: {stats['criteria']}")
            print(f"  Dominant Purpose: {engine.get_dominant_purpose()}")
    
    print("\n" + "=" * 60)
    print("FINAL REPORT")
    print("=" * 60)
    print(f"Total Cycles: {engine.cycle}")
    print(f"Purposes Discovered: {len(engine.purpose_history)}")
    print(f"Recent Purposes: {engine.purpose_history[-10:]}")
    print(f"Dominant Purpose: {engine.get_dominant_purpose()}")
    print("=" * 60)
