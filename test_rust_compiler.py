
import sys
import os
import random
try:
    # Path trick to find rs_machine if not installed in site-packages
    sys.path.append(os.getcwd())
    import rs_machine
    print(f"[TEST] rs_machine imported: {rs_machine}")
except ImportError:
    print("[TEST] rs_machine NOT found. Test will likely check fallback only.")

from neuro_genetic_synthesizer import RustCompiler, NeuroInterpreter, BSApp, BSVal, BSVar

def test_rust_jit():
    print("="*60)
    print("TEST: Rust JIT Compiler & Execution")
    print("="*60)

    # 1. Create a simple expression: add(mul(n, 2), 5)
    # n * 2 + 5
    # Input n=3 -> 11
    expr = BSApp('add', (
        BSApp('mul', (BSVar('n'), BSVal(2))),
        BSVal(5)
    ))
    
    print(f"Expression: {expr}")
    
    # 2. Compile
    compiler = RustCompiler()
    try:
        insts = compiler.compile(expr)
        print(f"[OK] Compiled to {len(insts)} instructions.")
        for i, inst in enumerate(insts):
            print(f"  {i}: {inst.op} {inst.a} {inst.b} {inst.c}")
    except Exception as e:
        print(f"[FAIL] Compilation error: {e}")
        return

    # 3. Execute on Rust VM
    try:
        vm = rs_machine.VirtualMachine(100, 64, 16)
        inputs = [3.0]
        st = vm.execute(insts, inputs)
        res = st.regs[0]
        print(f"[rust] Result(n=3): {res}")
        
        # Verify correctness
        expected = 11.0
        if abs(res - expected) < 1e-9:
            print("[PASS] Rust result matches expected.")
        else:
            print(f"[FAIL] Rust result {res} != expected {expected}")
            
    except Exception as e:
        print(f"[FAIL] Runtime error: {e}")

    # 4. Test Fallback (MOD op)
    # mod(n, 2) -> Should fail compilation
    print("\n[TEST] Fallback (MOD operator)")
    expr_mod = BSApp('mod', (BSVar('n'), BSVal(2)))
    compiler_mod = RustCompiler()
    insts_mod = compiler_mod.compile(expr_mod)
    if insts_mod is None:
        print("[PASS] Compilation correctly returned None for MOD op.")
    else:
        print(f"[FAIL] Compilation should have failed for MOD, got: {insts_mod}")

if __name__ == "__main__":
    test_rust_jit()
