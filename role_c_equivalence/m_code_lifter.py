import json
import os

class MCodeAutomaton:
    """
    Represents the Code-Derived Automaton (M_code) as a Labeled Transition System (LTS).
    """
    def __init__(self, uid):
        self.uid = uid
        self.states = set()
        self.transitions = []
        self.initial_state = "S0"

    def add_transition(self, source, target, guard, label):
        """
        Adds a formal transition between states, preserving the symbolic guard.
        """
        self.transitions.append({
            "from": source,
            "to": target,
            "guard": guard,
            "label": label
        })
        self.states.update([source, target])

    def display_structure(self):
        """
        Prints the formal mathematical structure.
        Ensures traceability from the IR to the M_code object.
        """
        print(f"\n--- Formal Structure for UID {self.uid} ---")
        print(f"States: {', '.join(sorted(self.states))}")
        print("Transitions:")
        for t in self.transitions:
            print(f"  {t['from']} --({t['label']})--> {t['to']} [Guard: {t['guard']}]")

def lift_ir_to_mcode(json_path):
    """
    Deterministically lifts a Validated IR (WIR) from JSON into an MCodeAutomaton object.
    Follows a 1-to-1 mapping to ensure repeatability and structural fidelity.
    """
    with open(json_path, 'r') as f:
        ir_data = json.load(f)
    
    automaton = MCodeAutomaton(ir_data['uid'])
    
    # Map nodes for label lookups to ensure edges have correct action labels
    node_labels = {node['id']: node['label'] for node in ir_data['nodes']}
    
    for edge in ir_data['edges']:
        # Lifting the edge to a formal transition within the FSM domain
        automaton.add_transition(
            source=edge['from'],
            target=edge['to'],
            guard=edge['guard'],
            label=node_labels.get(edge['to'], "UNKNOWN")
        )
    
    return automaton