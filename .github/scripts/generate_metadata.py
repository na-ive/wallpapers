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
METADATA_VERSION = 3 # Increment this to force re-processing

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
    """Samples the image and returns a unique list of human-readable color groups with a frequency threshold."""
    img = img.convert('RGB')
    # Use 8x8 grid for better statistical accuracy (64 samples)
    grid_size = 8
    small_img = img.resize((grid_size, grid_size), resample=Image.Resampling.BILINEAR)
    
    color_counts = {}
    for x in range(grid_size):
        for y in range(grid_size):
            r, g, b = small_img.getpixel((x, y))
            r_norm, g_norm, b_norm = r/255.0, g/255.0, b/255.0
            h, s, v = colorsys.rgb_to_hsv(r_norm, g_norm, b_norm)
            h_deg = h * 360
            
            # SMART THRESHOLDS
            # Colors with very low saturation (s < 0.25) look gray/white
            # Colors with very low value (v < 0.20) look black
            if s < 0.25 or v < 0.20: continue
            
            group = None
            # Precision-calibrated Hue ranges for human perception
            if h_deg < 10 or h_deg >= 345: group = "Red"
            elif h_deg < 45: group = "Orange"
            elif h_deg < 70: group = "Yellow"
            elif h_deg < 160: group = "Green"
            elif h_deg < 250: group = "Blue"   # Ends at 250 to catch Indigo in Purple
            elif h_deg < 345: group = "Purple" # Starts at 250, covers Indigo/Pink, ends at 345
            
            if group:
                color_counts[group] = color_counts.get(group, 0) + 1
    
    # Significant threshold (12/64 = ~19% of image area)
    significant_groups = [g for g, count in color_counts.items() if count >= 12]
    
    # Fallback: If nothing is significant enough, take the top 1 only if it's clear enough
    if not significant_groups and color_counts:
        top_color = max(color_counts, key=color_counts.get)
        # Fallback must have at least 6 pixels (~9% area)
        if color_counts[top_color] >= 6:
            significant_groups = [top_color]
        
    return sorted(significant_groups)

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
        
        # Check if we can reuse metadata AND if version matches
        if filename in old_metadata and os.path.exists(thumb_path) and \
           old_metadata[filename].get("version") == METADATA_VERSION:
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
            "wallhaven_id": get_wallhaven_id(filename),
            "version": METADATA_VERSION
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
