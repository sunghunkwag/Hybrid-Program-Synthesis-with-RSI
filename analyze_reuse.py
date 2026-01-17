import pickle
import os

codes = []
for f in sorted(os.listdir('checkpoints')):
    with open(f'checkpoints/{f}', 'rb') as fp:
        codes.append(pickle.load(fp))

print('=== All synthesized codes ===')
for c in codes:
    print(f"{c['name']}: {c['code']}")

# Check for reuse
print('\n=== Reuse Analysis ===')
all_code_parts = set()
reuse_count = 0
for c in codes:
    code = c['code']
    # Check if this code uses any previously seen pattern
    for prev in all_code_parts:
        if prev in code and prev != code:
            print(f"REUSE DETECTED: '{prev}' reused in '{code}'")
            reuse_count += 1
    all_code_parts.add(code)

print(f"\nTotal reuse instances: {reuse_count}")
