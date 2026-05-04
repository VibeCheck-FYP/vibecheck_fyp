import sys
import os
import json
import spot
import buddy

def build_graph(filepath, shared_bdict):
    """Builds a SPOT automaton using a SHARED math dictionary."""
    with open(filepath, 'r') as f:
        wir = json.load(f)

    m_code = spot.make_twa_graph(shared_bdict)
    state_map = {}
    
    # Create states
    for node in wir['nodes']:
        state_id = m_code.new_state()
        state_map[node] = state_id
        if node == wir['nodes'][0]:
            m_code.set_init_state(state_id)

    # Create edges linked to the shared dictionary
    for edge in wir['edges']:
        src_id = state_map[edge['src']]
        dst_id = state_map[edge['dst']]
        cond_str = edge['condition']
        
        if cond_str.lower() == "true":
            cond_bdd = buddy.bddtrue  
        else:
            ap_formula = spot.formula.ap(f'"{cond_str}"')
            var_id = shared_bdict.register_proposition(ap_formula, m_code)
            cond_bdd = buddy.bdd_ithvar(var_id)
            
        m_code.new_edge(src_id, dst_id, cond_bdd)
        
    return m_code

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python equivalence_engine.py <variant_1.json> <variant_2.json>")
        sys.exit(1)

    file_1 = sys.argv[1]
    file_2 = sys.argv[2]

    print("\n[+] Initializing Shared BuDDy Mathematical Dictionary...")
    shared_dict = spot.make_bdd_dict()

    print(f"[-] Compiling M_code_1 from: {file_1}")
    aut_1 = build_graph(file_1, shared_dict)
    
    print(f"[-] Compiling M_code_2 from: {file_2}")
    aut_2 = build_graph(file_2, shared_dict)

    print("\n[+] Executing Formal Equivalence Analysis...")
    
    # SPOT built-in language equivalence check
    is_equivalent = spot.are_equivalent(aut_1, aut_2)

    print("-" * 50)
    if is_equivalent:
        print("RESULT: [MATCH] -> The generated implementations are mathematically EQUIVALENT.")
    else:
        print("RESULT: [DISCREPANCY] -> The implementations diverge logically.")
    print("-" * 50)

    # Clean C++ memory exit
    sys.stdout.flush()
    os._exit(0)
    