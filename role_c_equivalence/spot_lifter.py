import spot
import buddy
import json

# ---------------------------------------------------------
# 1. MOCK DATA: This simulates the JSON WIR that Role B 
# (Fernando) will eventually pass to you.
# ---------------------------------------------------------
dummy_wir_json = """
{
    "nodes": ["State_0_Start", "State_1_CheckFunds", "State_2_Approve"],
    "edges": [
        {"src": "State_0_Start", "dst": "State_1_CheckFunds", "condition": "true"},
        {"src": "State_1_CheckFunds", "dst": "State_2_Approve", "condition": "balance_sufficient"}
    ]
}
"""

print("1. Parsing JSON WIR...")
wir = json.loads(dummy_wir_json)

# ---------------------------------------------------------
# 2. SPOT INITIALIZATION
# ---------------------------------------------------------
print("2. Initializing SPOT and BuDDY...")
bdict = spot.make_bdd_dict()
aut = spot.make_twa_graph(bdict)
aut.set_buchi() # Standard setting for infinite behavior modeling

# ---------------------------------------------------------
# 3. LIFTING NODES TO STATES
# ---------------------------------------------------------
print("3. Lifting nodes to mathematical states...")
spot_states = {}
for node in wir["nodes"]:
    spot_states[node] = aut.new_state()

# ---------------------------------------------------------
# 4. LIFTING EDGES AND CONDITIONS (Guards)
# ---------------------------------------------------------
print("4. Encoding transition guards using BuDDY...")
for edge in wir["edges"]:
    src_state = spot_states[edge["src"]]
    dst_state = spot_states[edge["dst"]]
    condition = edge["condition"]
    
    # If there's no specific condition, it happens automatically (True)
    if condition.lower() == "true":
        guard_bdd = buddy.bddtrue
    else:
        # Explicitly register the string with the automaton
        aut.register_ap(condition)
        # Create a boolean Atomic Proposition (AP) from the string
        ap = spot.formula.ap(condition)
        # Compress it using BuDDY
        guard_bdd = spot.formula_to_bdd(ap, bdict, aut)
        
    # Draw the connection
    aut.new_edge(src_state, dst_state, guard_bdd)

# ---------------------------------------------------------
# 5. VERDICT
# ---------------------------------------------------------
print("\n--- SUCCESS! CODE-DERIVED AUTOMATON (M_code) BUILT ---")
print(f"Total States: {aut.num_states()}")
print(f"Total Edges: {aut.num_edges()}")
print("\nHere is the raw mathematical structure (HOA format):")
print(aut.to_str('hoa'))