import sys
import os
import json
import spot
import buddy

def build_graph(filepath, shared_bdict):
    """Builds a SPOT automaton using the shared dictionary."""
    with open(filepath, 'r') as f:
        wir = json.load(f)

    m_graph = spot.make_twa_graph(shared_bdict)
    state_map = {}
    
    for node in wir['nodes']:
        state_id = m_graph.new_state()
        state_map[node] = state_id
        if node == wir['nodes'][0]:
            m_graph.set_init_state(state_id)

    for edge in wir['edges']:
        src_id = state_map[edge['src']]
        dst_id = state_map[edge['dst']]
        cond_str = edge['condition']
        
        if cond_str.lower() == "true":
            cond_bdd = buddy.bddtrue  
        else:
            ap_formula = spot.formula.ap(f'"{cond_str}"')
            var_id = shared_bdict.register_proposition(ap_formula, m_graph)
            cond_bdd = buddy.bdd_ithvar(var_id)
            
        m_graph.new_edge(src_id, dst_id, cond_bdd)
        
    return m_graph

def run_model_check(spec_file, code_file):
    print(f"\n{'='*60}")
    print(" VIBECHECK: FINAL VERIFICATION ENGINE (PHASE 3)")
    print(f"{'='*60}")
    
    shared_dict = spot.make_bdd_dict()

    print(f"[*] Loading Business Spec (M_spec) from: {spec_file}")
    m_spec = build_graph(spec_file, shared_dict)
    
    print(f"[*] Loading AI Representative (M_code) from: {code_file}")
    m_code = build_graph(code_file, shared_dict)

    print("\n[+] Executing Formal Model Check (System x Property)...")
    
    # POC Strict Conformance Check
    is_conforming = spot.are_equivalent(m_spec, m_code)

    print(f"\n{'*'*60}")
    if is_conforming:
        print(" VERDICT: [SYSTEM PASSED]")
        print(" DETAIL:  The AI-generated code perfectly conforms to the")
        print("          BPMN business rules. It is safe for production.")
    else:
        print(" VERDICT: [SYSTEM FAILED]")
        print(" DETAIL:  The AI-generated code violates the business spec.")
        print("          Rejecting implementation.")
    print(f"{'*'*60}\n")

    print("[+] Cleaning up C++ memory spaces...")
    del m_spec
    del m_code
    del shared_dict
    sys.exit(0)

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python final_verifier.py <m_spec.json> <m_code_representative.json>")
        sys.exit(1)
        
    spec = sys.argv[1]
    code = sys.argv[2]
    
    run_model_check(spec, code)