import os
import re
from pathlib import Path

# Regex for YouTube iframe
IFRAME_RE = re.compile(
    r'(<iframe[^>]*src=[\'"]https?://(?:www\.)?youtube\.com/embed/([^?\'"]+)[^\'"]*[\'"][^>]*>.*?</iframe>)',
    re.IGNORECASE | re.DOTALL
)

# Regex for <head>
HEAD_RE = re.compile(r'(<head[^>]*>)', re.IGNORECASE)

def process_html_file(html_file, base_dir, videos_dir):
    try:
        content = html_file.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return False

    changes_made = False

    # 1. Add Meta Referrer if not present
    if 'name="referrer"' not in content:
        content = HEAD_RE.sub(r'\1\n\t<meta name="referrer" content="strict-origin-when-cross-origin">', content)
        changes_made = True

    # 2. Process Iframes
    def iframe_replacer(match):
        full_iframe = match.group(1)
        video_id = match.group(2)
        
        # Check if local video exists
        local_vid_path = videos_dir / f"{video_id}.mp4"
        
        if local_vid_path.exists():
            rel_path = os.path.relpath(local_vid_path, start=html_file.parent)
            
            width_match = re.search(r'width=[\'"]([0-9]+%?)[\'"]', full_iframe)
            height_match = re.search(r'height=[\'"]([0-9]+%?)[\'"]', full_iframe)
            w = width_match.group(1) if width_match else "100%"
            h = height_match.group(1) if height_match else "auto"
            
            class_match = re.search(r'class=[\'"]([^\'"]+)[\'"]', full_iframe)
            cls_attr = f' class="{class_match.group(1)}"' if class_match else ""
            
            return f'<video src="{rel_path}" controls width="{w}" height="{h}"{cls_attr} style="max-width: 100%; height: auto;"></video>'
        else:
            # Fix Error 153 by adding referrerpolicy and origin
            new_src = f'https://www.youtube.com/embed/{video_id}?origin=https://agapecpa.com'
            
            # Replace src attribute
            fixed_iframe = re.sub(r'src=[\'"][^\'"]+[\'"]', f'src="{new_src}"', full_iframe)
            
            # Add referrerpolicy if missing
            if 'referrerpolicy' not in fixed_iframe:
                fixed_iframe = fixed_iframe.replace('<iframe', '<iframe referrerpolicy="strict-origin-when-cross-origin"')
            
            return fixed_iframe

    new_content = IFRAME_RE.sub(iframe_replacer, content)
    if new_content != content:
        html_file.write_text(new_content, encoding="utf-8")
        return True
    return False

def main():
    base_dir = Path("/Users/lucywang/Desktop/agape_clone/agapecpa.com")
    videos_dir = base_dir / "videos"
    videos_dir.mkdir(exist_ok=True)
    
    html_files = list(base_dir.rglob("*.html"))
    count = 0
    for html_file in html_files:
        if not html_file.is_file():
            continue
        if process_html_file(html_file, base_dir, videos_dir):
            print(f"Updated: {html_file.relative_to(base_dir)}")
            count += 1
    
    print(f"Finished processing {count} files.")

if __name__ == '__main__':
    main()
