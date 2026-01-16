"""
SAFE INTERPRETER - AST-based execution with no exec()/eval()
Pillar 1 of Safe & Genuine RSI

Uses the Visitor Pattern to traverse and execute DSL expressions safely.
Only whitelisted operations are allowed.
"""

import ast
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable, Union


class SecurityError(Exception):
    """Raised when unsafe operation is attempted."""
    pass


class ExecutionError(Exception):
    """Raised when execution fails."""
    pass


@dataclass
class DSLExpr:
    """Base class for DSL expressions."""
    pass


@dataclass
class DSLVar(DSLExpr):
    """Variable reference."""
    name: str


@dataclass
class DSLVal(DSLExpr):
    """Literal value."""
    value: Any


@dataclass
class DSLApp(DSLExpr):
    """Function application."""
    func: str
    args: List[DSLExpr] = field(default_factory=list)


class SafeInterpreter:
    """
    AST-based interpreter using Visitor Pattern.
    
    SECURITY: No exec(), no eval(), no __builtins__ access.
    Only whitelisted operations are allowed.
    """
    
    # Whitelisted primitive operations
    ALLOWED_OPS: Dict[str, Callable] = {
        # Arithmetic
        'add': lambda a, b: a + b,
        'sub': lambda a, b: a - b,
        'mul': lambda a, b: a * b,
        'div': lambda a, b: a // b if b != 0 else 0,
        'mod': lambda a, b: a % b if b != 0 else 0,
        'neg': lambda a: -a,
        'abs': lambda a: abs(a),
        'min': lambda a, b: min(a, b),
        'max': lambda a, b: max(a, b),
        
        # Comparison / Conditional
        'if_gt': lambda a, b, t, f: t if a > b else f,
        'if_eq': lambda a, b, t, f: t if a == b else f,
        'if_lt': lambda a, b, t, f: t if a < b else f,
        'eq': lambda a, b: a == b,
        'gt': lambda a, b: a > b,
        'lt': lambda a, b: a < b,
        
        # Boolean
        'and_op': lambda a, b: a and b,
        'or_op': lambda a, b: a or b,
        'not_op': lambda a: not a,
        'xor_op': lambda a, b: a != b,
        
        # List/String operations
        'len': lambda x: len(x) if hasattr(x, '__len__') else 0,
        'first': lambda x: x[0] if x else None,
        'second': lambda x: x[1] if len(x) > 1 else None,
        'last': lambda x: x[-1] if x else None,
        'reverse': lambda x: x[::-1] if hasattr(x, '__getitem__') else x,
        'concat': lambda a, b: a + b if type(a) == type(b) else a,
        'slice_from': lambda x, i: x[i:] if hasattr(x, '__getitem__') else x,
        'slice_to': lambda x, i: x[:i] if hasattr(x, '__getitem__') else x,
        'index': lambda x, i: x[i] if hasattr(x, '__getitem__') and 0 <= i < len(x) else None,
        
        # Identity
        'id': lambda x: x,
    }
    
    # Maximum execution steps to prevent infinite loops
    MAX_STEPS = 10000
    
    def __init__(self):
        self._custom_primitives: Dict[str, 'DSLExpr'] = {}
        self._step_count = 0
    
    def register_primitive(self, name: str, expr: DSLExpr) -> None:
        """
        Register a custom primitive (learned function).
        
        Args:
            name: Primitive name
            expr: DSL expression tree (NOT Python code string)
        """
        if not isinstance(name, str) or not name.isidentifier():
            raise SecurityError(f"Invalid primitive name: {name}")
        if name in self.ALLOWED_OPS:
            raise SecurityError(f"Cannot override built-in: {name}")
        self._custom_primitives[name] = expr
    
    def unregister_primitive(self, name: str) -> bool:
        """Remove a custom primitive."""
        if name in self._custom_primitives:
            del self._custom_primitives[name]
            return True
        return False
    
    def run(self, expr: DSLExpr, env: Dict[str, Any]) -> Any:
        """
        Execute a DSL expression safely.
        
        Args:
            expr: DSL expression tree
            env: Variable bindings (e.g., {'n': 5})
            
        Returns:
            Execution result
            
        Raises:
            SecurityError: If unsafe operation attempted
            ExecutionError: If execution fails
        """
        self._step_count = 0
        try:
            return self._eval(expr, env)
        except (SecurityError, ExecutionError):
            raise
        except Exception as e:
            raise ExecutionError(f"Execution failed: {e}")
    
    def _eval(self, expr: DSLExpr, env: Dict[str, Any]) -> Any:
        """Recursive evaluation with step counting."""
        self._step_count += 1
        if self._step_count > self.MAX_STEPS:
            raise ExecutionError("Maximum execution steps exceeded")
        
        # Pattern match on expression type
        if isinstance(expr, DSLVal):
            return expr.value
        
        elif isinstance(expr, DSLVar):
            if expr.name not in env:
                raise ExecutionError(f"Undefined variable: {expr.name}")
            return env[expr.name]
        
        elif isinstance(expr, DSLApp):
            return self._eval_app(expr, env)
        
        else:
            raise SecurityError(f"Unknown expression type: {type(expr)}")
    
    def _eval_app(self, expr: DSLApp, env: Dict[str, Any]) -> Any:
        """Evaluate function application."""
        func_name = expr.func
        
        # Check for built-in operation
        if func_name in self.ALLOWED_OPS:
            # Evaluate arguments
            args = [self._eval(arg, env) for arg in expr.args]
            # Apply built-in
            try:
                return self.ALLOWED_OPS[func_name](*args)
            except TypeError as e:
                raise ExecutionError(f"Arity mismatch for {func_name}: {e}")
        
        # Check for custom primitive
        elif func_name in self._custom_primitives:
            primitive_expr = self._custom_primitives[func_name]
            # Evaluate arguments
            arg_values = [self._eval(arg, env) for arg in expr.args]
            # Create new environment with argument bindings
            # Assuming primitives use var_0, var_1, etc.
            new_env = env.copy()
            for i, val in enumerate(arg_values):
                new_env[f'var_{i}'] = val
            # Recursively evaluate the primitive's body
            return self._eval(primitive_expr, new_env)
        
        else:
            raise SecurityError(f"Unknown function: {func_name}")
    
    def get_all_ops(self) -> List[str]:
        """Get all available operations (built-in + custom)."""
        return list(self.ALLOWED_OPS.keys()) + list(self._custom_primitives.keys())


class SemanticHasher:
    """
    Computes semantic hash of DSL expressions.
    
    Ignores variable names to detect functionally equivalent expressions.
    E.g., add(var_0, var_1) == add(x, y) semantically.
    """
    
    @staticmethod
    def hash(expr: DSLExpr) -> str:
        """Compute canonical hash of expression."""
        return SemanticHasher._canonicalize(expr, {})
    
    @staticmethod
    def _canonicalize(expr: DSLExpr, var_map: Dict[str, int]) -> str:
        """Create canonical string representation."""
        if isinstance(expr, DSLVal):
            return f"V({expr.value})"
        
        elif isinstance(expr, DSLVar):
            # Rename variables to canonical form
            if expr.name not in var_map:
                var_map[expr.name] = len(var_map)
            return f"X{var_map[expr.name]}"
        
        elif isinstance(expr, DSLApp):
            args_str = ",".join(
                SemanticHasher._canonicalize(arg, var_map) 
                for arg in expr.args
            )
            return f"{expr.func}({args_str})"
        
        return "?"
    
    @staticmethod
    def are_equivalent(expr1: DSLExpr, expr2: DSLExpr) -> bool:
        """Check if two expressions are semantically equivalent."""
        return SemanticHasher.hash(expr1) == SemanticHasher.hash(expr2)


class UtilityScorer:
    """
    Scores primitives based on utility metrics.
    
    A primitive is kept if:
    1. Compression ratio > 1.1 (reduces code length)
    2. Used in 3+ successful solutions
    """
    
    MIN_COMPRESSION_RATIO = 1.1
    MIN_USAGE_COUNT = 3
    
    @staticmethod
    def compute_size(expr: DSLExpr) -> int:
        """Compute AST node count."""
        if isinstance(expr, (DSLVal, DSLVar)):
            return 1
        elif isinstance(expr, DSLApp):
            return 1 + sum(UtilityScorer.compute_size(arg) for arg in expr.args)
        return 1
    
    @staticmethod
    def compression_ratio(original_size: int, primitive_size: int) -> float:
        """
        Compute compression ratio.
        
        Returns: original_size / (primitive_size + 1 for call overhead)
        """
        if primitive_size <= 0:
            return 0.0
        return original_size / (primitive_size + 1)
    
    @staticmethod
    def should_keep(
        compression_ratio: float, 
        usage_count: int,
        is_unique: bool
    ) -> bool:
        """Determine if primitive meets quality threshold."""
        return (
            is_unique and
            compression_ratio >= UtilityScorer.MIN_COMPRESSION_RATIO and
            usage_count >= UtilityScorer.MIN_USAGE_COUNT
        )


# Utility: Convert between legacy BSExpr and new DSLExpr
def bs_to_dsl(bs_expr) -> DSLExpr:
    """Convert BSExpr (legacy) to DSLExpr."""
    # Import here to avoid circular dependency
    from neuro_genetic_synthesizer import BSVar, BSVal, BSApp
    
    if isinstance(bs_expr, BSVar):
        return DSLVar(bs_expr.name)
    elif isinstance(bs_expr, BSVal):
        return DSLVal(bs_expr.val)
    elif isinstance(bs_expr, BSApp):
        return DSLApp(bs_expr.func, [bs_to_dsl(arg) for arg in bs_expr.args])
    else:
        return DSLVal(bs_expr)


def dsl_to_bs(dsl_expr: DSLExpr):
    """Convert DSLExpr to BSExpr (legacy)."""
    from neuro_genetic_synthesizer import BSVar, BSVal, BSApp
    
    if isinstance(dsl_expr, DSLVar):
        return BSVar(dsl_expr.name)
    elif isinstance(dsl_expr, DSLVal):
        return BSVal(dsl_expr.value)
    elif isinstance(dsl_expr, DSLApp):
        return BSApp(dsl_expr.func, [dsl_to_bs(arg) for arg in dsl_expr.args])
    else:
        return BSVal(dsl_expr)


if __name__ == "__main__":
    # Quick test
    interp = SafeInterpreter()
    
    # Test expression: add(mul(n, 2), 1)
    expr = DSLApp('add', [
        DSLApp('mul', [DSLVar('n'), DSLVal(2)]),
        DSLVal(1)
    ])
    
    result = interp.run(expr, {'n': 5})
    print(f"add(mul(5, 2), 1) = {result}")  # Should be 11
    
    # Test semantic hashing
    expr1 = DSLApp('add', [DSLVar('x'), DSLVar('y')])
    expr2 = DSLApp('add', [DSLVar('a'), DSLVar('b')])
    print(f"Equivalent: {SemanticHasher.are_equivalent(expr1, expr2)}")  # True
