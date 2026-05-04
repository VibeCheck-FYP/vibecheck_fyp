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
    
    for node in wir['nodes']:
        state_id = m_code.new_state()
        state_map[node] = state_id
        if node == wir['nodes'][0]:
            m_code.set_init_state(state_id)

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

def cluster_implementations(directory):
    print("\n[+] Initializing VibeCheck Clustering Engine...")
    
    # CRITICAL: We need one master dictionary for the entire batch
    shared_dict = spot.make_bdd_dict()

    files = [f for f in os.listdir(directory) if f.endswith('.json')]
    if not files:
        print("[-] No WIR JSON files found to cluster.")
        sys.exit(1)

    print(f"[*] Loaded {len(files)} certified WIRs for equivalence analysis.\n")

    # This will hold our distinct mathematical groups
    clusters = [] 

    for file in files:
        filepath = os.path.join(directory, file)
        aut = build_graph(filepath, shared_dict)
        print(f"[-] Lifted {file} into M_code memory space.")

        found_cluster = False
        
        # Check this new graph against the representatives of existing clusters
        for cluster in clusters:
            is_equivalent = spot.are_equivalent(aut, cluster['representative'])
            
            if is_equivalent:
                cluster['files'].append(file)
                found_cluster = True
                print(f"    -> [MATCH] Grouped into Cluster {cluster['id']}")
                break

        # If it doesn't match any existing cluster, it becomes a new one
        if not found_cluster:
            new_id = len(clusters) + 1
            clusters.append({
                'id': new_id,
                'representative': aut, 
                'files': [file]
            })
            print(f"    -> [NEW UNIQUE LOGIC] Created Cluster {new_id}")

    print("\n" + "=" * 60)
    print("FINAL CLUSTERING RESULTS:")
    print("=" * 60)
    for cluster in clusters:
        print(f"Cluster {cluster['id']}:")
        print(f"  -> Contains {len(cluster['files'])} implementations: {', '.join(cluster['files'])}")
        print(f"  -> Representative M_code held in memory for final verification.")
        print("-" * 40)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python clustering_engine.py <directory_with_json_wirs>")
        sys.exit(1)
        
    target_dir = sys.argv[1]
    
    if not os.path.exists(target_dir):
        print(f"Error: Directory '{target_dir}' does not exist.")
        sys.exit(1)
        
    cluster_implementations(target_dir)
    
    print("\n[+] Cleaning up C++ memory spaces...")
    # Delete the Python references so the C++ garbage collector can wipe the board
    del clusters 
    del shared_dict
    
    sys.exit(0)