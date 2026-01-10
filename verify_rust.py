import sys
import time
import os

# Force Python to ignore the local 'rs_machine' source folder
# and look for the installed package in site-packages
cwd = os.getcwd()
sys.path = [p for p in sys.path if p != cwd and p != '']

print(f"Modified sys.path to avoid collision: {sys.path[:2]}...")


print("Attempting to import rs_machine...")
try:
    import rs_machine
    print(f"[PASS] rs_machine imported successfully.")
    print(f"[INFO] Location: {getattr(rs_machine, '__file__', 'NAMESPACE (Local Folder?)')}")
    print(f"[INFO] Contents: {dir(rs_machine)}")
except ImportError as e:
    print(f"[FAIL] Could not import rs_machine: {e}")
    sys.exit(1)

try:
    print("Testing VirtualMachine instantiation...")
    # 100 max steps, 1024 memory, 256 stack
    vm = rs_machine.VirtualMachine(100, 1024, 256)
    print(f"[PASS] VirtualMachine created: {vm}")
except AttributeError as e:
    print(f"[FAIL] Runtime error: {e}")
    print("HINT: If Location is 'NAMESPACE', Python is importing the local 'rs_machine' folder instead of the installed library.")
    print("TRY: Run this script from a different directory or rename the local 'rs_machine' folder.")
    sys.exit(1)
except Exception as e:
    print(f"[FAIL] Unexpected error: {e}")
    sys.exit(1)

try:
    print("Testing minimal execution...")
    # Simple MOV 1, 2 (OpCode MOV is usually mapped, checking implementation)
    # This is just a smoke test for the method existence
    state = vm.reset([1.0, 2.0])
    print(f"[PASS] vm.reset() returned state with regs: {state.regs[:2]}")
except Exception as e:
    print(f"[FAIL] Execution error: {e}")
    sys.exit(1)

print("\nAll checks passed! The Rust module is functioning correctly.")
