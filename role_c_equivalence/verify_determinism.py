import hashlib
import json
import os
from m_code_lifter import lift_ir_to_mcode

def get_m_code_hash(uid):
    ir_path = f"/root/vibecheck_fyp/data/processed/irs/uid_{uid}.json"
    m_code = lift_ir_to_mcode(ir_path)
    # Ensuring set objects are converted to sorted lists for stable hashing
    m_code_str = json.dumps(m_code.__dict__, sort_keys=True, default=lambda x: sorted(list(x)) if isinstance(x, set) else x)
    return hashlib.sha256(m_code_str.encode()).hexdigest()

if __name__ == "__main__":
    ir_dir = "/root/vibecheck_fyp/data/processed/irs/"
    all_passed = True

    print("--- Determinism Verification Report ---")
    for filename in sorted(os.listdir(ir_dir)):
        if filename.endswith(".json"):
            uid = filename.split('_')[1].split('.')[0]
            # Run 10 iterations per UID to verify stability
            hashes = {get_m_code_hash(uid) for _ in range(10)}
            
            if len(hashes) == 1:
                print(f"UID {uid:3}: PASSED (Hash: {list(hashes)[0][:10]}...)")
            else:
                print(f"UID {uid:3}: FAILED (Inconsistent hashes detected)")
                all_passed = False
    
    if all_passed:
        print("\nCONCLUSION: All M_code lifting is 100% deterministic and repeatable.")