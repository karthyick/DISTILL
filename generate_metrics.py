import os
import json
import glob
from pathlib import Path
from distill import compress, count_tokens

def get_size(obj):
    return len(json.dumps(obj, separators=(',', ':')))

def format_size(size):
    for unit in ['B', 'KB', 'MB']:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} GB"

print(f"{'File':<25} | {'Orig Size':<10} | {'Comp Size':<10} | {'Reduction':<10} | {'Tokens (Orig/Comp)':<20}")
print("-" * 85)

files = glob.glob("tests/fixtures/*.json")
for file_path in files:
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        original_size = get_size(data)
        original_tokens = count_tokens(json.dumps(data))
        
        result = compress(data)
        compressed_size = len(result["compressed"])
        compressed_tokens = result["meta"]["compressed_tokens"]
        reduction = result["meta"]["reduction_percent"]
        
        filename = os.path.basename(file_path)
        print(f"{filename:<25} | {format_size(original_size):<10} | {format_size(compressed_size):<10} | {reduction:>9.1f}% | {original_tokens}/{compressed_tokens}")
        
    except Exception as e:
        print(f"{os.path.basename(file_path):<25} | Error: {e}")
