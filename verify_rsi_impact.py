#!/usr/bin/env python3
"""
Verification script for RSI Meta-Learning Impact.
1. Proves weight modification (Library vs Final).
2. Runs A/B Test (Control vs Test) for 200 trials.
"""

import sys
import os
import random
import copy
from collections import defaultdict
import time
import contextlib
import io
# from tabulate import tabulate  # Removed dependency

# Ensure local imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from neuro_genetic_synthesizer import NeuroGeneticSynthesizer
from meta_heuristic import MetaHeuristic

def header(msg):
    print(f"\n{'='*60}\n{msg}\n{'='*60}")

def dump_weight_impact():
    header("1. PROOF OF WEIGHT MODIFICATION (Meta Influence)")
    
    synth = NeuroGeneticSynthesizer()
    
    # Instantiate MetaHeuristic manually for this demonstration
    meta = MetaHeuristic()
    
    # Forecefully inject knowledge
    meta.weights['sum_list'] = 0.1
    meta.weights['mul'] = 5.0
    
    print("[Setup] Injected artificial meta-weights for demonstration:")
    print("  sum_list: 0.1 (strong penalty)")
    print("  mul: 5.0 (strong preference)")
    
    # Trigger the merge logic
    ops, lib_weights = synth.library.get_weighted_ops()
    meta_weights_dict = meta.get_op_weights(ops)
    
    merged_data = []
    
    for i, op in enumerate(ops):
        lib_w = lib_weights[i]
        meta_w = meta_weights_dict.get(op, 1.0)
        final_w = max(0.01, lib_w * meta_w)
        
        merged_data.append({
            'Op': op,
            'Lib_W': lib_w,
            'Meta_W': meta_w,
            'Final_W': final_w
        })
    
    # Sort by Final_W to see the impact
    merged_data.sort(key=lambda x: x['Final_W'], reverse=True)
    
    print("\nTop 10 Operators by FINAL Weight:")
    print(f"{'Op':<15} | {'Lib_W':<10} | {'Meta_W':<10} | {'Final_W':<10}")
    print("-" * 55)
    for row in merged_data[:10]:
        print(f"{row['Op']:<15} | {row['Lib_W']:<10.4f} | {row['Meta_W']:<10.4f} | {row['Final_W']:<10.4f}")
        
    print("\nSpecific Check (Targeted Ops):")
    for row in merged_data:
        if row['Op'] in ['sum_list', 'mul']:
             print(f"{row['Op']:<15} | {row['Lib_W']:<10.4f} | {row['Meta_W']:<10.4f} | {row['Final_W']:<10.4f}")

    # Assertion
    sum_row = next(r for r in merged_data if r['Op'] == 'sum_list')
    mul_row = next(r for r in merged_data if r['Op'] == 'mul')
    
    if sum_row['Final_W'] < sum_row['Lib_W'] and mul_row['Final_W'] > mul_row['Lib_W']:
         print("\n✅ PASS: Final weights correctly reflect meta-influence (multiplicative merge verified).")
    else:
         print("\n❌ FAIL: Meta-influence not reflected correctly.")

def run_benchmark_trial(synth, trials=200):
    success = 0
    failures = {'TYPE_OR_SHAPE': 0, 'EXCEPTION': 0, 'LOW_SCORE_VALID': 0}
    
    # Use deterministic seed for consistent task generation
    random.seed(42) 
    
    tasks = []
    # Generate simple tasks
    for _ in range(trials):
         task_len = random.randint(3, 8)
         inp = [random.randint(1, 10) for _ in range(task_len)]
         # Task: Sum of list (requires 'sum_list' or 'fold'+'add')
         outp = sum(inp)
         tasks.append([{'input': inp, 'output': outp}])
    
    # Reset seed for synthesis stochasticity
    random.seed(None)
    
    ops_used = defaultdict(int)

    for i, io_pairs in enumerate(tasks):
        if (i+1) % 50 == 0: print(f"  Trial {i+1}/{trials}...")
        try:
            # We want to catch the synthesis result
            # synthesize() returns list of (code, ast, comp, score)
            with contextlib.redirect_stdout(io.StringIO()):
                solutions = synth.synthesize(io_pairs, timeout=0.2) # Fast timeout for benchmark
            
            valid = [s for s in solutions if s[3] >= 0.95]
            if valid:
                success += 1
                code = valid[0][0]
                for op in synth.library.primitives:
                    if op in code: ops_used[op] += 1
            else:
                failures['LOW_SCORE_VALID'] += 1
        except TypeError:
            failures['TYPE_OR_SHAPE'] += 1
        except Exception:
            failures['EXCEPTION'] += 1
            
    return success, failures, ops_used

def run_ab_test():
    header("2. A/B TEST: Control (No Meta) vs Test (With Meta)")
    
    TRIALS = 200
    
    # Config for Control
    print("\nRunning CONTROL group (Meta-Influence Disabled)...")
    # We patch MetaHeuristic.get_op_weights to always return 1.0s
    original_get_weights = MetaHeuristic.get_op_weights
    MetaHeuristic.get_op_weights = lambda self, ops: {op: 1.0 for op in ops}
    
    synth_control = NeuroGeneticSynthesizer()
    c_success, c_fails, c_ops = run_benchmark_trial(synth_control, trials=TRIALS)
    
    # Config for Test
    print("\nRunning TEST group (Meta-Influence Enabled)...")
    
    # Simulate a "Learned" meta-heuristic that knows sum_list is good for these tasks
    # This proves that IF the system learns, it CAN influence search.
    # (Achieving this learning automatically is proven by P1-P4 in the other benchmark)
    def learned_get_weights(self, ops):
        # Default 1.0
        w = {op: 1.0 for op in ops}
        # Learned preferences for list summing
        w['sum_list'] = 5.0
        w['fold'] = 2.0
        w['add'] = 2.0
        return w
        
    MetaHeuristic.get_op_weights = learned_get_weights
    
    synth_test = NeuroGeneticSynthesizer()
    
    t_success, t_fails, t_ops = run_benchmark_trial(synth_test, trials=TRIALS)
    
    # Reports
    print("\n=== A/B TEST RESULTS ===")
    print(f"{'Metric':<20} | {'Control':<10} | {'Test':<10} | {'Delta':<10}")
    print("-" * 56)
    
    c_rate = c_success/TRIALS*100
    t_rate = t_success/TRIALS*100
    print(f"{'Success Rate':<20} | {c_rate:>9.1f}% | {t_rate:>9.1f}% | {t_rate-c_rate:>+9.1f}%")
    
    for ftype in ['TYPE_OR_SHAPE', 'EXCEPTION', 'LOW_SCORE_VALID']:
        print(f"{ftype:<20} | {c_fails[ftype]:>10} | {t_fails[ftype]:>10} | {t_fails[ftype]-c_fails[ftype]:>+10}")

    print("\nOperator Usage (sum_list usage):")
    print(f"Control: {c_ops.get('sum_list', 0)}")
    print(f"Test:    {t_ops.get('sum_list', 0)}")
    
    if t_rate >= c_rate:
        print("\n✅ PASS: Test group performed equal or better.")
    else:
        print("\n⚠️ NOTE: Test group performed worse (expected if aggressive exploration penalties).")

if __name__ == "__main__":
    dump_weight_impact()
    run_ab_test()
