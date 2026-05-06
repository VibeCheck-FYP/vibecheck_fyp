# main_role_c.py
import os
import json
from m_code_lifter import lift_ir_to_mcode

if __name__ == "__main__":
    ir_dir = "/root/vibecheck_fyp/data/processed/irs/"
    
    for filename in os.listdir(ir_dir):
        if filename.endswith(".json"):
            path = os.path.join(ir_dir, filename)
            m_code = lift_ir_to_mcode(path)
            print(f"Lifted UID {m_code.uid}: {len(m_code.states)} states generated.")

# python3 main_role_c.py - command in terminal to generate the MCodeAutomaton for each IR JSON file.

# Following code shows the state table transition in the terminal.

# if os.path.exists(ir_dir):
#         for filename in sorted(os.listdir(ir_dir)):
#             if filename.endswith(".json"):
#                 path = os.path.join(ir_dir, filename)
#                 m_code = lift_ir_to_mcode(path)
                
#                 # This call provides the formal proof of the lifting process.
#                 m_code.display_structure()
