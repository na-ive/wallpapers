import os
import json
import re
import datetime

IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}

def get_wallhaven_id(filename):
    match = re.search(r'wallhaven-([a-z0-9]+)', filename, re.IGNORECASE)
    if match:
        return match.group(1)
    return None

def generate_metadata():
    wallpapers = []
    files = [f for f in os.listdir('.') if os.path.isfile(f)]
    
    for filename in files:
        ext = os.path.splitext(filename)[1].lower()
        if ext in IMAGE_EXTENSIONS:
            stats = os.stat(filename)
            mtime = datetime.datetime.fromtimestamp(stats.st_mtime).isoformat()
            
            wallpaper = {
                "filename": filename,
                "mtime": mtime,
                "wallhaven_id": get_wallhaven_id(filename)
            }
            wallpapers.append(wallpaper)
            
    # Sort by newest by default
    wallpapers.sort(key=lambda x: x['mtime'], reverse=True)
    
    with open('wallpapers.json', 'w') as f:
        json.dump(wallpapers, f, indent=2)

if __name__ == "__main__":
    generate_metadata()
