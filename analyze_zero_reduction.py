import json
import os
from distill import compress
from distill.config import with_config

files_to_check = ["tests/fixtures/nested.json", "tests/fixtures/random.json", "tests/fixtures/simple.json"]

print(f"{'File':<25} | {'Reason':<30} | {'Orig Tokens':<12} | {'Comp Tokens (Forced)':<20}")
print("-" * 95)

for file_path in files_to_check:
    if not os.path.exists(file_path):
        continue
        
    with open(file_path, 'r') as f:
        data = json.load(f)
    
    # Run normal compression to get the reason
    result = compress(data)
    meta = result["meta"]
    reason = meta.get("reason", "N/A")
    orig_tokens = meta.get("original_tokens", 0)
    
    # Run forced compression (disable fallback) to see what the size WOULD have been
    with with_config(fallback_on_increase=False):
        forced_result = compress(data)
        forced_tokens = forced_result["meta"]["compressed_tokens"]
        
    print(f"{os.path.basename(file_path):<25} | {reason:<30} | {orig_tokens:<12} | {forced_tokens:<20}")
