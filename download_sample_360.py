#!/usr/bin/env python3
"""
Download sample 360° content for testing the head-tracked panorama viewer

This script downloads free 360° images and videos for testing purposes.
All content is from freely available sources with permissive licenses.
"""

import urllib.request
import os
import sys

# Sample directory
SAMPLE_DIR = os.path.join(os.path.dirname(__file__), "samples")

# Free 360° content sources
SAMPLES = {
    # 360° Images (Equirectangular)
    "street_360.jpg": {
        "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/6/6c/Panorama_of_the_courtyard_of_the_Great_Mosque_of_Kairouan.jpg/2560px-Panorama_of_the_courtyard_of_the_Great_Mosque_of_Kairouan.jpg",
        "description": "360° panorama of historic courtyard (Wikimedia Commons)",
        "size": "~2 MB"
    },
    "nature_360.jpg": {
        "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e7/Spherical_Panorama.jpg/2560px-Spherical_Panorama.jpg", 
        "description": "360° nature panorama (Wikimedia Commons)",
        "size": "~1.5 MB"
    }
}

def download_file(url: str, filepath: str, description: str) -> bool:
    """Download a file with progress indicator"""
    print(f"\n📥 Downloading: {description}")
    print(f"   URL: {url[:60]}...")
    
    try:
        # Create request with user agent
        request = urllib.request.Request(
            url,
            headers={'User-Agent': 'Mozilla/5.0 (Raspberry Pi; Linux) Python/3'}
        )
        
        with urllib.request.urlopen(request, timeout=30) as response:
            total_size = response.headers.get('Content-Length')
            
            if total_size:
                total_size = int(total_size)
                print(f"   Size: {total_size / 1024 / 1024:.1f} MB")
            
            # Download with progress
            downloaded = 0
            block_size = 8192
            
            with open(filepath, 'wb') as f:
                while True:
                    buffer = response.read(block_size)
                    if not buffer:
                        break
                    
                    downloaded += len(buffer)
                    f.write(buffer)
                    
                    if total_size:
                        percent = (downloaded / total_size) * 100
                        bar = '█' * int(percent / 5) + '░' * (20 - int(percent / 5))
                        print(f"\r   [{bar}] {percent:.0f}%", end='', flush=True)
            
            print(f"\n   ✓ Saved to: {filepath}")
            return True
            
    except Exception as e:
        print(f"\n   ❌ Failed: {e}")
        return False


def main():
    print("=" * 60)
    print("  360° SAMPLE CONTENT DOWNLOADER")
    print("=" * 60)
    
    # Create samples directory
    os.makedirs(SAMPLE_DIR, exist_ok=True)
    print(f"\n📁 Sample directory: {SAMPLE_DIR}")
    
    # Download samples
    success_count = 0
    
    for filename, info in SAMPLES.items():
        filepath = os.path.join(SAMPLE_DIR, filename)
        
        if os.path.exists(filepath):
            print(f"\n⏭ Skipping {filename} (already exists)")
            success_count += 1
            continue
        
        if download_file(info['url'], filepath, info['description']):
            success_count += 1
    
    # Summary
    print("\n" + "=" * 60)
    print(f"  Downloaded {success_count}/{len(SAMPLES)} samples")
    print("=" * 60)
    
    if success_count > 0:
        print("\n🎮 To view with head tracking:")
        print(f"   python panorama_viewer.py {SAMPLE_DIR}/street_360.jpg")
        print(f"\n🖱 To view with mouse control:")
        print(f"   python panorama_viewer.py --sim {SAMPLE_DIR}/street_360.jpg")
    
    # Additional resources
    print("\n" + "─" * 60)
    print("📚 FREE 360° CONTENT SOURCES:")
    print("─" * 60)
    print("""
    🖼️  360° IMAGES:
    • Wikimedia Commons 360° category
      https://commons.wikimedia.org/wiki/Category:360°_panoramas
    
    • Flickr (search "equirectangular")
      https://www.flickr.com/search/?text=equirectangular
    
    • Polyhaven (free HDRIs)
      https://polyhaven.com/hdris
    
    🎬 360° VIDEOS:
    • YouTube 360° Videos
      https://www.youtube.com/360
      (Use yt-dlp to download: yt-dlp -f best URL)
    
    • Pexels 360° Videos
      https://www.pexels.com/search/videos/360/
    
    • Sample 360° Videos (Direct Download):
      - NASA 360° ISS Tour: 
        https://svs.gsfc.nasa.gov/13181
      
    📝 NOTES:
    • Use equirectangular projection (2:1 aspect ratio)
    • Higher resolution = better quality when zoomed
    • 4K (4096x2048) recommended for good experience
    """)
    
    # Create a simple test pattern if nothing downloaded
    if success_count == 0:
        print("\n⚠ No samples downloaded. Running demo mode instead:")
        print("   python panorama_viewer.py")


if __name__ == "__main__":
    main()

