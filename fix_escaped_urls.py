import os
import glob

# 3. Fix the HTML and JS files
for filepath in glob.glob("/Users/lucywang/Desktop/agape_clone/agapecpa.com/**/*.html", recursive=True):
    if not os.path.isfile(filepath):
        continue
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        continue
    
    new_content = content.replace("https:\\/\\/agapecpa.com", ".\\/images")
    new_content = new_content.replace("https://agapecpa.com", "./images")
    
    if content != new_content:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(new_content)
        print(f"Fixed {filepath}")

for filepath in glob.glob("/Users/lucywang/Desktop/agape_clone/agapecpa.com/**/*.js", recursive=True):
    if not os.path.isfile(filepath):
        continue
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        continue
    
    new_content = content.replace("https:\\/\\/agapecpa.com", ".\\/images")
    new_content = new_content.replace("https://agapecpa.com", "./images")
    
    if content != new_content:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(new_content)
        print(f"Fixed {filepath}")

print("Done fixing URLs!")
