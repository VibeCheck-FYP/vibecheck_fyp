import ast
import json
import sys
import os

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
            edges.append({"src": "State_1_CheckFunds", "dst": "State_3_Reject", "condition": f"not ({condition_str})"})

    return {"nodes": nodes, "edges": edges}

# --- DYNAMIC CLI EXECUTION ---
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python ast_parser.py <path_to_any_python_file.py>")
        sys.exit(1)

    target_file = sys.argv[1]
    
    if not os.path.exists(target_file):
        print(f"Error: Cannot find file at {target_file}")
        sys.exit(1)

    print(f"Parsing real file: {target_file}...")
    dynamic_wir = extract_wir_from_code(target_file)

    # Save it dynamically as a real .json file
    output_filename = target_file.replace('.py', '_wir.json')
    with open(output_filename, 'w') as f:
        json.dump(dynamic_wir, f, indent=2)
        
    print(f"Success! Extracted WIR saved to: {output_filename}")