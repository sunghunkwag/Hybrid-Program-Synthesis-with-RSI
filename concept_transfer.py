"""
CONCEPT TRANSFER ENGINE
Human-Level Concept Generalization WITHOUT Transformers

4 Core Modules:
1. ExecutionHasher - I/O signature hashing for semantic similarity
2. MultiLevelAntiUnifier - Meta-pattern extraction (2-3 levels)
3. GraphIsomorphismMatcher - AST structure comparison
4. TypeClusterer - Type-based concept grouping
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Tuple, Optional, Set
from collections import defaultdict
import hashlib


# ==============================================================================
# MODULE 1: ExecutionHasher
# ==============================================================================

class ExecutionHasher:
    """
    Semantic similarity via I/O fingerprinting.
    Two expressions with the same output on test inputs are considered equivalent.
    """
    
    def __init__(self, test_range: int = 11, interpreter=None):
        self.test_range = test_range
        self.interpreter = interpreter
        self.hash_index: Dict[str, List[Tuple[str, Any]]] = defaultdict(list)  # hash -> [(name, expr)]
    
    def compute_hash(self, expr, run_func=None) -> Optional[str]:
        """
        Compute I/O signature hash for an expression.
        Returns None if execution fails.
        """
        if run_func is None and self.interpreter is None:
            return None
        
        runner = run_func if run_func else self.interpreter.run
        
        outputs = []
        for n in range(self.test_range):
            try:
                result = runner(expr, {'n': n})
                if result is None:
                    outputs.append('ERR')
                else:
                    outputs.append(str(result))
            except:
                outputs.append('ERR')
        
        signature = ','.join(outputs)
        return hashlib.md5(signature.encode()).hexdigest()[:16]
    
    def register(self, name: str, expr: Any, run_func=None):
        """Register a concept with its execution hash."""
        h = self.compute_hash(expr, run_func)
        if h:
            self.hash_index[h].append((name, expr))
    
    def find_similar(self, target_outputs: List[Any]) -> List[Tuple[str, Any]]:
        """Find concepts with matching output signature."""
        signature = ','.join(str(o) if o is not None else 'ERR' for o in target_outputs)
        h = hashlib.md5(signature.encode()).hexdigest()[:16]
        return self.hash_index.get(h, [])
    
    def find_by_partial_match(self, task_ios: List[Dict[str, Any]], threshold: float = 0.8) -> List[Tuple[str, Any, float]]:
        """
        Find concepts with partial output match.
        Uses ACTUAL input values from I/O pairs, not assumed indices.
        """
        # Updated to handle ProgramGenome objects explicitly
        candidate_match = []
        
        # Pre-compute fingerprints for all library concepts
        lib_fingerprints = {}
        
        # We iterate over the hash index to get all registered concepts
        # self.hash_index maps hash -> [(name, expr)]
        for h, concepts in self.hash_index.items():
            for name, concept_expr in concepts:
                # Handle ProgramGenome: Convert to string representation for hashing/comparison
                if hasattr(concept_expr, 'instructions'):
                    # Convert [Instruction(op='ADD', ...)] -> "ADD(0,0,0);HALT(0,0,0)"
                    s_expr = ";".join([f"{i.op}({i.a},{i.b},{i.c})" for i in concept_expr.instructions])
                else:
                    s_expr = str(concept_expr)
                    
                # Get behavior on Transfer Task inputs
                outputs = []
                is_valid = True
                for io in task_ios:
                    try:
                        # Use adapter to run genome
                        val = self.interpreter.run(concept_expr, {'n': io['input']})
                        outputs.append(val)
                    except Exception:
                        is_valid = False
                        break
                
                if is_valid:
                    lib_fingerprints[name] = tuple(outputs)

        # Compare against target outputs
        target_outputs = tuple(io['output'] for io in task_ios)
        
        for name, outputs in lib_fingerprints.items():
            if outputs == target_outputs:
                # PERFECT MATCH FOUND
                # Retrieve expr again (inefficient but safe given structure)
                # Ideally we store it in lib_fingerprints but keeping change minimal
                # We need to find the expr for 'name'
                expr = None
                for _, concepts in self.hash_index.items():
                    for n, e in concepts:
                        if n == name:
                            expr = e
                            break
                    if expr: break
                
                if expr:
                    candidate_match.append((name, expr, 1.0, "behavioral_match"))

        return sorted(candidate_match, key=lambda x: -x[2])


# ==============================================================================
# MODULE 2: MultiLevelAntiUnifier
# ==============================================================================

@dataclass
class Pattern:
    """Represents an abstracted pattern with holes."""
    template: Any  # AST with Hole nodes
    holes: int     # Number of abstracted positions
    level: int     # Abstraction level (1=basic, 2=meta, 3=meta-meta)
    instances: List[Any] = field(default_factory=list)  # Concrete instances

@dataclass
class Hole:
    """Placeholder for abstracted sub-expressions."""
    index: int
    
    def __repr__(self):
        return f"?{self.index}"


class MultiLevelAntiUnifier:
    """
    Extract meta-patterns through hierarchical anti-unification.
    Level 1: Pattern from concrete expressions
    Level 2: Meta-pattern from Level 1 patterns
    Level 3: Meta-meta-pattern from Level 2 patterns
    """
    
    def __init__(self, max_level: int = 3):
        self.max_level = max_level
        self.patterns: Dict[int, List[Pattern]] = defaultdict(list)  # level -> patterns
        self.hole_counter = 0
    
    def _new_hole(self) -> Hole:
        self.hole_counter += 1
        return Hole(self.hole_counter)
    
    def anti_unify(self, e1: Any, e2: Any) -> Tuple[Any, int]:
        """
        Anti-unify two expressions into a common pattern.
        Returns (pattern, hole_count).
        """
        holes = [0]  # Mutable counter
        
        def walk(a, b):
            # Same atomic value
            if a == b:
                return a
            
            # Both are tuples/lists of same length (AST nodes)
            if isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)):
                if len(a) == len(b) and len(a) > 0:
                    # Same constructor (first element)
                    if a[0] == b[0]:
                        return tuple([a[0]] + [walk(a[i], b[i]) for i in range(1, len(a))])
            
            # Both have same type with 'func' attribute (BSApp-like)
            if hasattr(a, 'func') and hasattr(b, 'func'):
                if a.func == b.func and hasattr(a, 'args') and hasattr(b, 'args'):
                    if len(a.args) == len(b.args):
                        new_args = tuple(walk(a.args[i], b.args[i]) for i in range(len(a.args)))
                        # Return new BSApp-like structure
                        return type(a)(func=a.func, args=new_args)
            
            # Different - create hole
            holes[0] += 1
            return self._new_hole()
        
        result = walk(e1, e2)
        return result, holes[0]
    
    def unify_level(self, exprs: List[Any], level: int = 1) -> List[Pattern]:
        """
        Anti-unify a list of expressions pairwise, creating Level N patterns.
        """
        if len(exprs) < 2:
            return []
        
        patterns = []
        seen_templates = set()
        
        for i in range(len(exprs)):
            for j in range(i + 1, len(exprs)):
                template, holes = self.anti_unify(exprs[i], exprs[j])
                
                # Only keep patterns with meaningful abstraction (1-3 holes)
                if 1 <= holes <= 3:
                    template_str = str(template)
                    if template_str not in seen_templates:
                        seen_templates.add(template_str)
                        p = Pattern(
                            template=template,
                            holes=holes,
                            level=level,
                            instances=[exprs[i], exprs[j]]
                        )
                        patterns.append(p)
                        self.patterns[level].append(p)
        
        return patterns
    
    def discover_meta_patterns(self, concepts: List[Any]) -> Dict[int, List[Pattern]]:
        """
        Run multi-level anti-unification.
        Level 1: Patterns from raw expressions
        Level 2: Meta-patterns from Level 1 patterns
        """
        # Level 1
        level1 = self.unify_level(concepts, level=1)
        
        # Level 2: Anti-unify the templates from Level 1
        if len(level1) >= 2 and self.max_level >= 2:
            level1_templates = [p.template for p in level1]
            level2 = self.unify_level(level1_templates, level=2)
        else:
            level2 = []
        
        # Level 3: Meta-meta patterns
        if len(level2) >= 2 and self.max_level >= 3:
            level2_templates = [p.template for p in level2]
            level3 = self.unify_level(level2_templates, level=3)
        else:
            level3 = []
        
        return {1: level1, 2: level2, 3: level3}


# ==============================================================================
# MODULE 3: GraphIsomorphismMatcher
# ==============================================================================

@dataclass
class ASTNode:
    """Graph node representing an AST node."""
    id: int
    label: str
    children: List[int] = field(default_factory=list)


class GraphIsomorphismMatcher:
    """
    Structural analogy via AST graph comparison.
    Uses Weisfeiler-Lehman graph hashing for fast isomorphism detection.
    """
    
    def __init__(self):
        self.graph_index: Dict[str, List[Tuple[str, Any]]] = defaultdict(list)  # hash -> [(name, expr)]
        self.node_counter = 0
    
    def _next_id(self) -> int:
        self.node_counter += 1
        return self.node_counter
    
    def ast_to_graph(self, expr) -> Tuple[List[ASTNode], int]:
        """
        Convert an expression to a graph representation.
        Returns (nodes, root_id).
        """
        nodes = []
        
        def build(e) -> int:
            node_id = self._next_id()
            
            # Atomic values
            if isinstance(e, (int, float)):
                nodes.append(ASTNode(node_id, f"VAL", []))
                return node_id
            
            if isinstance(e, str):
                nodes.append(ASTNode(node_id, f"VAR", []))
                return node_id
            
            # BSApp-like with func and args
            if hasattr(e, 'func') and hasattr(e, 'args'):
                child_ids = [build(arg) for arg in e.args]
                nodes.append(ASTNode(node_id, e.func, child_ids))
                return node_id
            
            # BSVar-like with name
            if hasattr(e, 'name'):
                nodes.append(ASTNode(node_id, "VAR", []))
                return node_id
            
            # BSVal-like with val
            if hasattr(e, 'val'):
                nodes.append(ASTNode(node_id, "VAL", []))
                return node_id
            
            # Fallback
            nodes.append(ASTNode(node_id, "UNKNOWN", []))
            return node_id
        
        root = build(expr)
        return nodes, root
    
    def weisfeiler_lehman_hash(self, nodes: List[ASTNode], root_id: int, iterations: int = 3) -> str:
        """
        Compute Weisfeiler-Lehman graph hash.
        Captures structural isomorphism.
        """
        # Build adjacency
        id_to_node = {n.id: n for n in nodes}
        
        # Initialize labels
        labels = {n.id: n.label for n in nodes}
        
        for _ in range(iterations):
            new_labels = {}
            for n in nodes:
                # Aggregate neighbor labels
                child_labels = sorted(labels.get(c, "?") for c in n.children)
                combined = f"{labels[n.id]}:{'|'.join(child_labels)}"
                new_labels[n.id] = hashlib.md5(combined.encode()).hexdigest()[:8]
            labels = new_labels
        
        # Root-centric hash
        return labels.get(root_id, "?")
    
    def compute_structure_hash(self, expr) -> str:
        """Compute the structural hash of an expression."""
        nodes, root = self.ast_to_graph(expr)
        return self.weisfeiler_lehman_hash(nodes, root)
    
    def register(self, name: str, expr: Any):
        """Register a concept with its structural hash."""
        h = self.compute_structure_hash(expr)
        self.graph_index[h].append((name, expr))
    
    def find_isomorphic(self, query_expr: Any) -> List[Tuple[str, Any]]:
        """Find concepts with isomorphic structure."""
        h = self.compute_structure_hash(query_expr)
        return self.graph_index.get(h, [])
    
    def find_similar_structure(self, query_expr: Any, depth_tolerance: int = 1) -> List[Tuple[str, Any]]:
        """
        Find concepts with similar (not necessarily identical) structure.
        Uses prefix matching on hash for approximate similarity.
        """
        h = self.compute_structure_hash(query_expr)
        prefix = h[:4]  # First 4 chars for approximate match
        
        results = []
        for stored_hash, concepts in self.graph_index.items():
            if stored_hash.startswith(prefix):
                results.extend(concepts)
        return results


# ==============================================================================
# MODULE 4: TypeClusterer
# ==============================================================================

@dataclass(frozen=True)
class TypeSignature:
    """Represents a function type signature."""
    input_types: Tuple[str, ...]
    output_type: str
    
    def __repr__(self):
        inputs = ', '.join(self.input_types) if self.input_types else '()'
        return f"({inputs}) -> {self.output_type}"


class TypeClusterer:
    """
    Group concepts by type signature.
    Enables: "swap similar-typed functions" strategy.
    """
    
    def __init__(self):
        self.clusters: Dict[TypeSignature, List[Tuple[str, Any]]] = defaultdict(list)
        self.concept_types: Dict[str, TypeSignature] = {}
    
    def infer_type(self, expr, interpreter=None) -> TypeSignature:
        """
        Infer type signature by execution probing.
        Simple heuristic: run on integers, check output type.
        """
        # Default: assume Int -> Int for simple numeric functions
        input_types = ("Int",)
        output_type = "Int"
        
        if interpreter:
            try:
                # Probe with integer input
                result = interpreter.run(expr, {'n': 5})
                if isinstance(result, int):
                    output_type = "Int"
                elif isinstance(result, float):
                    output_type = "Float"
                elif isinstance(result, bool):
                    output_type = "Bool"
                elif isinstance(result, list):
                    output_type = "List"
                else:
                    output_type = "Any"
            except:
                output_type = "Any"
        
        return TypeSignature(input_types, output_type)
    
    def register(self, name: str, expr: Any, interpreter=None):
        """Register a concept with its inferred type."""
        sig = self.infer_type(expr, interpreter)
        self.clusters[sig].append((name, expr))
        self.concept_types[name] = sig
    
    def get_cluster(self, sig: TypeSignature) -> List[Tuple[str, Any]]:
        """Get all concepts with the given type signature."""
        return self.clusters.get(sig, [])
    
    def find_swappable(self, name: str) -> List[Tuple[str, Any]]:
        """Find concepts that could be swapped for the given one (same type)."""
        if name not in self.concept_types:
            return []
        sig = self.concept_types[name]
        return [(n, e) for n, e in self.clusters[sig] if n != name]
    
    def get_all_clusters(self) -> Dict[TypeSignature, List[Tuple[str, Any]]]:
        """Return all type clusters."""
        return dict(self.clusters)


# ==============================================================================
# INTEGRATION: ConceptTransferEngine
# ==============================================================================

class ConceptTransferEngine:
    """
    Orchestrates all 4 modules for human-level concept transfer.
    No Transformers used.
    """
    
    def __init__(self, interpreter=None):
        self.hasher = ExecutionHasher(interpreter=interpreter)
        self.anti_unifier = MultiLevelAntiUnifier(max_level=3)
        self.graph_matcher = GraphIsomorphismMatcher()
        self.type_clusterer = TypeClusterer()
        self.interpreter = interpreter
        
        self.concept_library: Dict[str, Any] = {}  # name -> expr
        self.transfer_log: List[Dict] = []
    
    def register_concept(self, name: str, expr: Any):
        """Register a discovered concept with all 4 indices."""
        self.concept_library[name] = expr
        
        # Index in all modules
        run_func = lambda e, env: self.interpreter.run(e, env) if self.interpreter else None
        self.hasher.register(name, expr, run_func)
        self.graph_matcher.register(name, expr)
        self.type_clusterer.register(name, expr, self.interpreter)
        
        print(f"[ConceptTransfer] Registered: {name}")
    
    def discover_meta_patterns(self) -> Dict[int, List[Pattern]]:
        """Run multi-level anti-unification on all registered concepts."""
        exprs = list(self.concept_library.values())
        if len(exprs) < 2:
            return {1: [], 2: [], 3: []}
        
        patterns = self.anti_unifier.discover_meta_patterns(exprs)
        
        for level, pats in patterns.items():
            if pats:
                print(f"[ConceptTransfer] Discovered {len(pats)} Level-{level} patterns")
        
        return patterns
    
    def transfer(self, problem_ios: List[Dict[str, Any]]) -> List[Tuple[str, Any, float, str]]:
        """
        Attempt to transfer existing concepts to a new problem.
        Returns: [(name, expr, score, method)]
        """
        candidates = []
        
        # Extract target outputs
        target_outputs = [io.get('output') for io in problem_ios]
        
        # Method 1: Execution hash matching
        exact_matches = self.hasher.find_similar(target_outputs)
        for name, expr in exact_matches:
            candidates.append((name, expr, 1.0, "exact_hash"))
        
        # Pass full I/O pairs for proper input value matching
        partial_matches = self.hasher.find_by_partial_match(problem_ios, threshold=0.7)
        for name, expr, score in partial_matches:
            if (name, expr, 1.0, "exact_hash") not in candidates:
                candidates.append((name, expr, score, "partial_hash"))
        
        # Method 2: Type-based transfer
        # Find concepts of compatible type and try them
        for sig, concepts in self.type_clusterer.get_all_clusters().items():
            if sig.output_type == "Int":  # Assuming numeric tasks
                for name, expr in concepts[:5]:  # Top 5 per cluster
                    if not any(c[0] == name for c in candidates):
                        candidates.append((name, expr, 0.5, "type_compatible"))
        
        # Rank and log
        candidates.sort(key=lambda x: -x[2])
        
        self.transfer_log.append({
            'target_outputs': target_outputs[:5],
            'candidates': len(candidates),
            'top_method': candidates[0][3] if candidates else None
        })
        
        return candidates[:10]  # Return top 10
    
    def get_analogies(self, query_expr: Any) -> List[Tuple[str, Any]]:
        """Find structurally analogous concepts."""
        return self.graph_matcher.find_isomorphic(query_expr)
    
    def get_swappable(self, concept_name: str) -> List[Tuple[str, Any]]:
        """Find concepts that could substitute for the given one."""
        return self.type_clusterer.find_swappable(concept_name)
    
    def get_stats(self) -> Dict[str, Any]:
        """Return engine statistics."""
        return {
            "total_concepts": len(self.concept_library),
            "execution_hashes": len(self.hasher.hash_index),
            "structure_hashes": len(self.graph_matcher.graph_index),
            "type_clusters": len(self.type_clusterer.clusters),
            "level1_patterns": len(self.anti_unifier.patterns.get(1, [])),
            "level2_patterns": len(self.anti_unifier.patterns.get(2, [])),
            "level3_patterns": len(self.anti_unifier.patterns.get(3, [])),
            "transfers_attempted": len(self.transfer_log)
        }


# ==============================================================================
# CONVENIENCE: Standalone test
# ==============================================================================

if __name__ == "__main__":
    print("=== ConceptTransferEngine Test ===")
    
    # Simple mock expressions
    class MockExpr:
        def __init__(self, func, args):
            self.func = func
            self.args = tuple(args)
        def __repr__(self):
            return f"{self.func}({', '.join(str(a) for a in self.args)})"
    
    class MockVar:
        def __init__(self, name):
            self.name = name
        def __repr__(self):
            return self.name
    
    # Simple interpreter
    class MockInterp:
        def run(self, expr, env):
            if isinstance(expr, MockVar):
                return env.get(expr.name, 0)
            if hasattr(expr, 'func'):
                args = [self.run(a, env) for a in expr.args]
                if expr.func == 'add':
                    return args[0] + args[1]
                if expr.func == 'mul':
                    return args[0] * args[1]
            return 0
    
    interp = MockInterp()
    engine = ConceptTransferEngine(interpreter=interp)
    
    # Register some concepts
    n = MockVar('n')
    double = MockExpr('add', [n, n])
    triple = MockExpr('add', [n, MockExpr('mul', [n, MockVar('2')])])
    
    engine.register_concept("double", double)
    engine.register_concept("triple", triple)
    
    # Discover patterns
    patterns = engine.discover_meta_patterns()
    
    # Transfer test
    ios = [{'input': 0, 'output': 0}, {'input': 1, 'output': 2}, {'input': 2, 'output': 4}]
    candidates = engine.transfer(ios)
    
    print(f"\nStats: {engine.get_stats()}")
    print(f"Transfer candidates: {candidates}")
    print("\n=== Test Complete ===")
