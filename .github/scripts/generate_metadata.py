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

def get_color_groups(img):
    """Samples the image and returns a unique list of human-readable color groups."""
    # Resize to 4x4 to get a small sample of colors across the image
    img = img.convert('RGB')
    small_img = img.resize((4, 4), resample=Image.Resampling.BILINEAR)
    
    groups = set()
    for x in range(4):
        for y in range(4):
            r, g, b = small_img.getpixel((x, y))
            r_norm, g_norm, b_norm = r/255.0, g/255.0, b/255.0
            h, s, v = colorsys.rgb_to_hsv(r_norm, g_norm, b_norm)
            h_deg = h * 360
            
            # Skip neutrals (White, Black, Gray)
            if v < 0.2: continue # Too dark (Black)
            if s < 0.2: # Low saturation
                if v > 0.8: continue # Too bright (White)
                continue # Gray
            
            # Brown (Dark Orange/Red)
            if v < 0.5 and (h_deg < 40 or h_deg > 330): 
                groups.add("Brown")
                continue
                
            # Categorize by Hue
            if h_deg < 20 or h_deg >= 335: groups.add("Red")
            elif h_deg < 45: groups.add("Orange")
            elif h_deg < 70: groups.add("Yellow")
            elif h_deg < 165: groups.add("Green")
            elif h_deg < 265: groups.add("Blue") # Combined Cyan and Blue
            elif h_deg < 305: groups.add("Purple")
            elif h_deg < 335: groups.add("Pink")
            
    return sorted(list(groups))

def generate_metadata():
    if not os.path.exists(THUMB_DIR):
        os.makedirs(THUMB_DIR)

    # Load existing metadata
    old_metadata = {}
    if os.path.exists(METADATA_FILE):
        try:
            with open(METADATA_FILE, 'r') as f:
                data = json.load(f)
                # Key by filename
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
        
        # Check if we can reuse metadata AND if it has the new color_groups (plural)
        if filename in old_metadata and os.path.exists(thumb_path) and "color_groups" in old_metadata[filename]:
            wallpapers.append(old_metadata[filename])
            skipped_count += 1
            continue
        
        # If not, process the file
        print(f"Processing: {filename}")
        processed_count += 1
        mtime = get_git_mtime(filename)
        
        dominant_color = '#47464f'
        color_groups = []
        resolution = "Unknown"
        try:
            with Image.open(filename) as img:
                width, height = img.size
                resolution = f"{width}x{height}"
                dominant_color = get_dominant_color(img)
                color_groups = get_color_groups(img)
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
            "resolution": resolution,
            "color": dominant_color,
            "color_groups": color_groups,
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
