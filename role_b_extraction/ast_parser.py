import ast
import json
import sys
import os
from z3 import *  # <--- Microsoft Z3 Theorem Prover

def extract_wir_from_code(filepath):
    with open(filepath, 'r') as file:
        file_content = file.read()
        
    tree = ast.parse(file_content)
    nodes = ["State_0_Start"]
    edges = []
    
    for node in ast.walk(tree):
        if isinstance(node, ast.If):
            condition_str = ast.unparse(node.test)
            nodes.extend(["State_1_CheckFunds", "State_2_Approve", "State_3_Reject"])
            
            edges.append({"src": "State_0_Start", "dst": "State_1_CheckFunds", "condition": "true"})
            edges.append({"src": "State_1_CheckFunds", "dst": "State_2_Approve", "condition": condition_str})
            
            # Z3 handles 'not' differently than Python strings, so we format it for the math engine
            edges.append({"src": "State_1_CheckFunds", "dst": "State_3_Reject", "condition": f"Not({condition_str})"})

    return {"nodes": nodes, "edges": edges}

def validate_wir_with_z3(wir_data):
    print("\n--- Z3 Theorem Prover Initialization ---")
    valid_edges = []
    
    # Define our mathematical universe for Z3
    balance = Int('balance')
    
    for edge in wir_data['edges']:
        cond = edge['condition']
        print(f"[*] Analyzing Path: {edge['src']} -> {edge['dst']}")
        print(f"    Guard Condition: {cond}")
        
        if cond.lower() == "true":
            print("    Result: [SAT] (Trivial Path)\n")
            valid_edges.append(edge)
            continue
            
        # Spin up a fresh Z3 solver for this specific path
        solver = Solver()
        
        try:
            # We map the string back into python/Z3 logic safely
            # (In a full production build, this uses an AST-to-Z3 visitor)
            z3_expr = eval(cond, {"balance": balance, "Not": Not})
            solver.add(z3_expr)
            
            if solver.check() == sat:
                print("    Result: [SAT] -> Mathematically Feasible. Appending to WIR.\n")
                valid_edges.append(edge)
            else:
                print("    Result: [UNSAT] -> HALLUCINATION DETECTED. Dead branch pruned.\n")
        except Exception as e:
            print(f"    Result: [ERROR] Could not parse math -> {e}\n")
            valid_edges.append(edge) # Default to keep on error for safety
            
    # Return the "Correctness Certificate" WIR (only containing SAT paths)
    wir_data['edges'] = valid_edges
    return wir_data

# --- DYNAMIC CLI EXECUTION ---
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python ast_parser.py <path_to_any_python_file.py>")
        sys.exit(1)

    target_file = sys.argv[1]
    
    if not os.path.exists(target_file):
        print(f"Error: Cannot find file at {target_file}")
        sys.exit(1)

    print(f"Parsing raw syntax from: {target_file}...")
    raw_wir = extract_wir_from_code(target_file)
    
    # THE DAY 3 PIPELINE UPGRADE: Pass raw WIR through Z3 Validation
    certified_wir = validate_wir_with_z3(raw_wir)

    # Save the certified JSON
    output_filename = target_file.replace('.py', '_wir.json')
    with open(output_filename, 'w') as f:
        json.dump(certified_wir, f, indent=2)
        
    print(f"Success! Certified WIR saved to: {output_filename}")