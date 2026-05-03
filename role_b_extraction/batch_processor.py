import os
import subprocess
import sys

def run_batch(directory):
    print(f"\n[+] VibeCheck Batch Processor Initialized")
    print(f"[*] Scanning directory: {directory}")
    
    # Find all Python files in the folder
    files = [f for f in os.listdir(directory) if f.endswith('.py')]
    
    if not files:
        print("[-] No Python files found. Exiting.")
        sys.exit(1)

    print(f"[*] Found {len(files)} implementations to process.\n")

    # Loop through each file and pass it to the Day 3 Z3 pipeline
    for idx, file in enumerate(files, 1):
        filepath = os.path.join(directory, file)
        print(f"{'='*50}")
        print(f"---> Processing File {idx}/{len(files)}: {file}")
        print(f"{'='*50}")
        
        # We use subprocess to run the Day 3 script exactly as if you typed it in the terminal
        # This keeps the Z3 memory clean between runs
        subprocess.run(["python", "ast_parser.py", filepath])
        
    print(f"\n[SUCCESS] Batch processing complete! All valid WIRs generated in {directory}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python batch_processor.py <directory_path>")
        sys.exit(1)
        
    target_dir = sys.argv[1]
    
    if not os.path.exists(target_dir):
        print(f"Error: Directory '{target_dir}' does not exist.")
        sys.exit(1)
        
    run_batch(target_dir)