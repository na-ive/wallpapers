import os
import json
import re
import datetime
from PIL import Image

IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
THUMB_SIZE = (640, 360) # 16:9 ratio
THUMB_DIR = 'thumbnails'

def get_wallhaven_id(filename):
    match = re.search(r'wallhaven-([a-z0-9]+)', filename, re.IGNORECASE)
    if match:
        return match.group(1)
    return None

def generate_metadata():
    if not os.path.exists(THUMB_DIR):
        os.makedirs(THUMB_DIR)

    wallpapers = []
    files = [f for f in os.listdir('.') if os.path.isfile(f)]
    
    for filename in files:
        ext = os.path.splitext(filename)[1].lower()
        if ext in IMAGE_EXTENSIONS:
            stats = os.stat(filename)
            mtime = datetime.datetime.fromtimestamp(stats.st_mtime).isoformat()
            
            thumb_name = f"thumb_{filename}"
            thumb_path = os.path.join(THUMB_DIR, thumb_name)
            
            # Generate thumbnail if it doesn't exist or is older than original
            try:
                if not os.path.exists(thumb_path) or os.stat(thumb_path).st_mtime < stats.st_mtime:
                    with Image.open(filename) as img:
                        img.thumbnail(THUMB_SIZE)
                        img.save(thumb_path, optimize=True, quality=85)
            except Exception as e:
                print(f"Error generating thumbnail for {filename}: {e}")
                thumb_path = filename # Fallback to original
            
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
