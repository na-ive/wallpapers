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
        pass
    return datetime.datetime.fromtimestamp(os.stat(filename).st_mtime).isoformat()

def get_dominant_color(img):
    try:
        # Resize to 1x1 to get average color
        img = img.convert('RGB')
        img = img.resize((1, 1), resample=Image.Resampling.BILINEAR)
        color = img.getpixel((0, 0))
        return '#{:02x}{:02x}{:02x}'.format(*color)
    except:
        return '#47464f' # Fallback to surface variant color

def generate_metadata():
    if not os.path.exists(THUMB_DIR):
        os.makedirs(THUMB_DIR)

    # Clean up old thumbnails if original is gone
    existing_files = [f for f in os.listdir('.') if os.path.isfile(f)]
    image_files = [f for f in existing_files if os.path.splitext(f)[1].lower() in IMAGE_EXTENSIONS]
    
    wallpapers = []
    
    for filename in image_files:
        mtime = get_git_mtime(filename)
        
        thumb_name = f"thumb_{os.path.splitext(filename)[0]}.webp"
        thumb_path = os.path.join(THUMB_DIR, thumb_name)
        
        dominant_color = '#47464f'
        try:
            with Image.open(filename) as img:
                dominant_color = get_dominant_color(img)
                if not os.path.exists(thumb_path):
                    thumb_img = img.copy()
                    thumb_img.thumbnail(THUMB_SIZE)
                    thumb_img.save(thumb_path, 'WEBP', optimize=True, quality=85)
        except Exception as e:
            print(f"Error processing {filename}: {e}")
            thumb_path = filename
        
        wallpaper = {
            "filename": filename,
            "thumbnail": thumb_path,
            "mtime": mtime,
            "color": dominant_color,
            "wallhaven_id": get_wallhaven_id(filename)
        }
        wallpapers.append(wallpaper)
            
    wallpapers.sort(key=lambda x: x['mtime'], reverse=True)
    
    with open('wallpapers.json', 'w') as f:
        json.dump(wallpapers, f, indent=2)

if __name__ == "__main__":
    generate_metadata()
