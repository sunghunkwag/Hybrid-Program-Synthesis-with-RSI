
import json
import ast

def simplify(code):
    # Very basic simplifier simulation
    old_code = ""
    while code != old_code:
        old_code = code
        code = code.replace("reverse(reverse(", "")
        code = code.replace("add(n, 0)", "n")
        code = code.replace("sub(n, 0)", "n")
        code = code.replace("mul(n, 1)", "n")
        # .. add more as needed
        if code.endswith("))"):
             code = code.replace("))", ")") # Hacky fix for the replace above
    return code

with open('rsi_primitive_registry.json', 'r') as f:
    data = json.load(f)

print(f"Total Concepts: {len(data)}")
trivial_count = 0
for name, info in data.items():
    code = info['code']
    simpler = simplify(code)
    # Check if it collapses to strictly 'n' or simpler concept
    if len(simpler) < len(code):
        print(f"{name}: {code} -> {simpler}")
        trivial_count += 1

print(f"Bloated Concepts: {trivial_count}")
