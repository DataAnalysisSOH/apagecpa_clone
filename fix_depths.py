import os
import glob
from pathlib import Path

base_dir = Path("/Users/lucywang/Desktop/agape_clone/agapecpa.com")

count = 0
for filepath in glob.glob(str(base_dir / "**/*"), recursive=True):
    if not os.path.isfile(filepath):
        continue
    if not (filepath.endswith(".html") or filepath.endswith(".js")):
        continue
    
    path = Path(filepath)
    try:
        rel_path = path.relative_to(base_dir)
    except ValueError:
        continue
        
    depth = len(rel_path.parts) - 1
    if depth == 0:
        continue # ./images is already correct for depth 0
        
    prefix = "../" * depth
    escaped_prefix = "..\\/" * depth
    
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception:
        continue
        
    new_content = content
    # For regular paths
    new_content = new_content.replace('="./images', f'="{prefix}images')
    new_content = new_content.replace("='./images", f"='{prefix}images")
    new_content = new_content.replace("url(./images", f"url({prefix}images")
    new_content = new_content.replace(" ./images", f" {prefix}images")
    new_content = new_content.replace(",./images", f",{prefix}images")
    new_content = new_content.replace(':"./images', f':"{prefix}images')
    new_content = new_content.replace('content="./images', f'content="{prefix}images')
    
    # For escaped paths
    new_content = new_content.replace('".\\/images', f'"{escaped_prefix}images')
    new_content = new_content.replace("'.\\/images", f"'{escaped_prefix}images")
    new_content = new_content.replace('":".\\/images', f'":"{escaped_prefix}images')
    
    if content != new_content:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(new_content)
        count += 1

print(f"Done fixing depths for {count} files!")
