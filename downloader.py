import os
import time
import sys
from urllib.parse import urljoin
import requests

# --- CONFIGURATION via GITHUB ACTIONS ---
API_URL = os.getenv("API_URL")
MEDIA_BASE_URL = os.getenv("MEDIA_BASE_URL")

if not API_URL or not MEDIA_BASE_URL:
    print("[-] Error: API_URL or MEDIA_BASE_URL environment variable is missing.")
    sys.exit(1)

START_PAGE = int(os.getenv("START_PAGE", 1))
MAX_FILES = int(os.getenv("MAX_FILES", 0))

DOWNLOAD_DIR = "downloaded_media"
DELAY_SECONDS = 0.5
# ----------------------------------------

def create_download_dir(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)

def download_file(url, folder):
    try:
        filename = url.split('/')[-1]
        if not filename: return False

        file_path = os.path.join(folder, filename)
        if os.path.exists(file_path): 
            print(f"[~] Already exists: {filename}")
            return True

        # CRITICAL FIX: We must pass a Referer so the server thinks we are on the actual website
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8,video/*",
            "Referer": MEDIA_BASE_URL, 
            "Origin": MEDIA_BASE_URL
        }
        
        # Use stream=True so we can check headers before downloading the whole thing
        response = requests.get(url, headers=headers, stream=True, timeout=15)
        response.raise_for_status()

        # CRITICAL FIX: Check what the server is actually sending us
        content_type = response.headers.get('Content-Type', '').lower()
        if 'text/html' in content_type:
            print(f"[-] Blocked by Server (Hotlink protection). Received a webpage instead of media for: {filename}")
            return False

        with open(file_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk: f.write(chunk)
                
        # Get the real downloaded size to verify
        actual_size_kb = os.path.getsize(file_path) / 1024
        print(f"[+] Downloaded: {filename} ({actual_size_kb:.1f} KB)")
        return True

    except requests.RequestException as e:
        print(f"[-] Failed to download {url}: {e}")
        return False

def get_api_page(page_num):
    target_url = API_URL.replace("{page}", str(page_num))
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json",
        "Referer": MEDIA_BASE_URL
    }
    
    try:
        response = requests.get(target_url, headers=headers, timeout=15)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"[-] Failed to fetch API page {page_num}: {e}")
        return None

def main():
    print(f"[*] Starting API scraper with Anti-Bot bypass.")
    create_download_dir(DOWNLOAD_DIR)
    
    current_page = START_PAGE
    total_files = 0

    while True:
        if MAX_FILES > 0 and total_files >= MAX_FILES:
            print(f"\n[*] Hit file limit ({MAX_FILES}). Stopping.")
            break 

        print(f"\n[*] Fetching Page {current_page}...")
        data = get_api_page(current_page)
        
        if not data:
            print("[-] No data returned or API error. Stopping.")
            break
            
        medias = data.get("medias", [])
        
        if not medias:
            print("[*] No more media found in this page. Gallery complete!")
            break
            
        print(f"[*] Found {len(medias)} files on page {current_page}.")

        for item in medias:
            if MAX_FILES > 0 and total_files >= MAX_FILES:
                break 

            file_path = item.get("file_path")
            if not file_path:
                continue
                
            full_media_url = urljoin(MEDIA_BASE_URL, file_path)
            
            if download_file(full_media_url, DOWNLOAD_DIR):
                total_files += 1

        current_page += 1
        time.sleep(DELAY_SECONDS)

    print(f"\n[+] Task complete! Total actual media files secured: {total_files}")

if __name__ == "__main__":
    main()
