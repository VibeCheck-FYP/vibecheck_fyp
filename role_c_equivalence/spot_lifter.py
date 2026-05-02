import json
import sys
import os
import spot
import buddy


def build_spot_automaton_from_file(json_filepath):
    if not os.path.exists(json_filepath):
        print(f"Error: WIR file {json_filepath} not found!")
        sys.exit(1)


    print(f"--> Loading WIR Contract from: {json_filepath}")
    with open(json_filepath, 'r') as f:
        wir_data = json.load(f)


    nodes = wir_data.get("nodes", [])
    edges = wir_data.get("edges", [])


    print(f"--> Ingested {len(nodes)} states and {len(edges)} transitions.")
   
    # Initialize the BuDDy Dictionary (The Math Layer)
    bdict = spot.make_bdd_dict()
   
    # Create the empty Formal Graph (M_code)
    m_code = spot.make_twa_graph(bdict)
   
    # Create a mapping dictionary to keep track of state IDs
    state_map = {}
   
    print("\n--> Building Finite State Machine in SPOT...")
   
    for node in nodes:
        state_id = m_code.new_state()
        state_map[node] = state_id
        if node == nodes[0]:
            m_code.set_init_state(state_id)
            print(f"    [+] Initial State Set: {node} (ID: {state_id})")
        else:
            print(f"    [+] State Created: {node} (ID: {state_id})")


    for edge in edges:
        src_id = state_map[edge['src']]
        dst_id = state_map[edge['dst']]
        condition_str = edge['condition']
       
        # --- THE CORRECT C++ BINDING FIX ---
        if condition_str.lower() == "true":
            cond_bdd = buddy.bddtrue  
        else:
            # 1. Create a SPOT Atomic Proposition formula
            ap_formula = spot.formula.ap(f'"{condition_str}"')
           
            # 2. Register it in the BDD dict, which returns an integer ID
            var_id = bdict.register_proposition(ap_formula, m_code)
           
            # 3. Tell BuDDy to create a True/False decision node from that ID
            cond_bdd = buddy.bdd_ithvar(var_id)
           
        m_code.new_edge(src_id, dst_id, cond_bdd)
        print(f"    [-] Edge Connected: {edge['src']} --> {edge['dst']} [Guard: {condition_str}]")
       
    print("\nSUCCESS: M_code Automaton successfully generated in memory!")
    print(f"Automaton Stats: {m_code.num_states()} States, {m_code.num_edges()} Edges")
   
# --- C++ CLEANUP ---
    # Flush the terminal output so it prints perfectly, then instantly terminate
    # the process to let the Operating System cleanly reclaim the C++ memory.
    sys.stdout.flush()
    os._exit(0)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python spot_lifter.py <path_to_wir_json_file.json>")
        sys.exit(1)
       
    build_spot_automaton_from_file(sys.argv[1])

