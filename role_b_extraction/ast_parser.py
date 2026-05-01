import ast
import json

def extract_wir_from_code(filepath):
    # 1. Read the raw Python file
    with open(filepath, 'r') as file:
        file_content = file.read()
        
    # 2. Parse it into an Abstract Syntax Tree (AST)
    tree = ast.parse(file_content)
    
    # 3. Setup our WIR structures based on the Role C Contract
    nodes = ["State_0_Start"]
    edges = []
    
    # 4. Walk through the AST to find 'If' statements
    for node in ast.walk(tree):
        if isinstance(node, ast.If):
            # We found an 'If' block! Let's extract the condition.
            # ast.unparse() turns the AST math node back into a readable string
            condition_str = ast.unparse(node.test)
            
            # Add the new states discovered via this If block
            nodes.extend(["State_1_CheckFunds", "State_2_Approve", "State_3_Reject"])
            
            # Draw the edges
            edges.append({"src": "State_0_Start", "dst": "State_1_CheckFunds", "condition": "true"})
            edges.append({"src": "State_1_CheckFunds", "dst": "State_2_Approve", "condition": condition_str})
            edges.append({"src": "State_1_CheckFunds", "dst": "State_3_Reject", "condition": f"not ({condition_str})"})

    # 5. Package into the final JSON WIR Format
    wir = {
        "nodes": nodes,
        "edges": edges
    }
    return wir

# --- Execution ---
print("Extracting AST from Good Code...")
good_wir = extract_wir_from_code("good_code.py")
print(json.dumps(good_wir, indent=2))

print("\n-----------------------------------\n")

print("Extracting AST from Buggy Code...")
buggy_wir = extract_wir_from_code("buggy_code.py")
print(json.dumps(buggy_wir, indent=2))