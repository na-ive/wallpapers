import os
import json
import re
import datetime
import subprocess
from PIL import Image

IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
THUMB_SIZE = (640, 360)
THUMB_DIR = 'thumbnails'

def get_wallhaven_id(filename):
    match = re.search(r'wallhaven-([a-z0-9]+)', filename, re.IGNORECASE)
    if match:
        return match.group(1)
    return None

def get_git_mtime(filename):
    try:
        result = subprocess.run(
            ['git', 'log', '-1', '--format=%cI', filename],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        if result.stdout.strip():
            return result.stdout.strip()
    except Exception as e:
        print(f"Error getting git mtime for {filename}: {e}")
    return datetime.datetime.fromtimestamp(os.stat(filename).st_mtime).isoformat()

def generate_metadata():
    if not os.path.exists(THUMB_DIR):
        os.makedirs(THUMB_DIR)

    wallpapers = []
    files = [f for f in os.listdir('.') if os.path.isfile(f)]
    
    for filename in files:
        ext = os.path.splitext(filename)[1].lower()
        if ext in IMAGE_EXTENSIONS:
            mtime = get_git_mtime(filename)
            
            # Use .webp for even better performance in thumbnails
            thumb_name = f"thumb_{os.path.splitext(filename)[0]}.webp"
            thumb_path = os.path.join(THUMB_DIR, thumb_name)
            
            try:
                if not os.path.exists(thumb_path):
                    with Image.open(filename) as img:
                        img.thumbnail(THUMB_SIZE)
                        # Save as WebP for list view optimization
                        img.save(thumb_path, 'WEBP', optimize=True, quality=85)
            except Exception as e:
                print(f"Error generating thumbnail for {filename}: {e}")
                thumb_path = filename
            
            wallpaper = {
                "filename": filename,
                "thumbnail": thumb_path,
                "mtime": mtime,
                "wallhaven_id": get_wallhaven_id(filename)
            }
            wallpapers.append(wallpaper)
            
    wallpapers.sort(key=lambda x: x['mtime'], reverse=True)
    
    with open('wallpapers.json', 'w') as f:
        json.dump(wallpapers, f, indent=2)

if __name__ == "__main__":
    generate_metadata()
