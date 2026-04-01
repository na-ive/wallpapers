import os
import json
import re
import datetime
import subprocess
import colorsys
from PIL import Image

IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
THUMB_SIZE = (640, 360)
THUMB_DIR = 'thumbnails'
METADATA_FILE = 'wallpapers.json'

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
    except Exception:
        pass
    return datetime.datetime.fromtimestamp(os.stat(filename).st_mtime).isoformat()

def get_dominant_color(img):
    try:
        # Resize to 1x1 to get average color
        img = img.convert('RGB')
        img = img.resize((1, 1), resample=Image.Resampling.BILINEAR)
        color = img.getpixel((0, 0))
        return '#{:02x}{:02x}{:02x}'.format(*color)
    except Exception:
        return '#47464f' # Fallback

def get_color_group(hex_color):
    """Categorizes a hex color into a general color group name."""
    hex_color = hex_color.lstrip('#')
    r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    
    # Normalize RGB to 0-1
    r_norm, g_norm, b_norm = r/255.0, g/255.0, b/255.0
    h, s, v = colorsys.rgb_to_hsv(r_norm, g_norm, b_norm)
    
    # Hue is 0-1, convert to 0-360 degrees
    h_deg = h * 360
    
    # 1. Check for neutral colors (Black, White, Gray)
    if v < 0.15: return "Black"
    if s < 0.15:
        if v > 0.85: return "White"
        return "Gray"
    
    # 2. Check for Brown (Dark Orange/Red)
    if v < 0.5 and (h_deg < 40 or h_deg > 330): return "Brown"
    
    # 3. Categorize by Hue
    if h_deg < 15 or h_deg >= 330: return "Red"
    if h_deg < 45: return "Orange"
    if h_deg < 70: return "Yellow"
    if h_deg < 160: return "Green"
    if h_deg < 190: return "Cyan"
    if h_deg < 260: return "Blue"
    if h_deg < 300: return "Purple"
    return "Pink"

def generate_metadata():
    if not os.path.exists(THUMB_DIR):
        os.makedirs(THUMB_DIR)

    # Load existing metadata
    old_metadata = {}
    if os.path.exists(METADATA_FILE):
        try:
            with open(METADATA_FILE, 'r') as f:
                data = json.load(f)
                old_metadata = {item['filename']: item for item in data}
        except Exception as e:
            print(f"Warning: Could not load old metadata: {e}")

    # List current image files
    current_files = [f for f in os.listdir('.') if os.path.isfile(f) and os.path.splitext(f)[1].lower() in IMAGE_EXTENSIONS]
    
    wallpapers = []
    processed_count = 0
    skipped_count = 0
    
    for filename in current_files:
        thumb_name = f"thumb_{os.path.splitext(filename)[0]}.webp"
        thumb_path = os.path.join(THUMB_DIR, thumb_name)
        
        # Check if we can reuse metadata AND if it already has color_group
        if filename in old_metadata and os.path.exists(thumb_path) and "color_group" in old_metadata[filename]:
            wallpapers.append(old_metadata[filename])
            skipped_count += 1
            continue
        
        # If not, process the file
        print(f"Processing: {filename}")
        processed_count += 1
        mtime = get_git_mtime(filename)
        
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
            "color_group": get_color_group(dominant_color),
            "wallhaven_id": get_wallhaven_id(filename)
        }
        wallpapers.append(wallpaper)
            
    wallpapers.sort(key=lambda x: x['mtime'], reverse=True)
    
    with open(METADATA_FILE, 'w') as f:
        json.dump(wallpapers, f, indent=2)
    
    # Cleanup thumbnails
    current_thumb_names = {f"thumb_{os.path.splitext(f)[0]}.webp" for f in current_files}
    for thumb in os.listdir(THUMB_DIR):
        if thumb not in current_thumb_names:
            try:
                os.remove(os.path.join(THUMB_DIR, thumb))
            except:
                pass

    print(f"Done! Processed: {processed_count}, Skipped: {skipped_count}")

if __name__ == "__main__":
    generate_metadata()
