import os
import time
import sys
from urllib.parse import urljoin
# We import requests from curl_cffi instead of the standard library
from curl_cffi import requests

# --- CONFIGURATION via GITHUB ACTIONS ---
API_URL = os.getenv("API_URL")
MEDIA_BASE_URL = os.getenv("MEDIA_BASE_URL")
COOKIE_STRING = os.getenv("COOKIE_STRING", "").strip()

if not API_URL or not MEDIA_BASE_URL:
    print("[-] Error: API_URL or MEDIA_BASE_URL environment variable is missing.")
    sys.exit(1)

START_PAGE = int(os.getenv("START_PAGE", 1))
MAX_FILES = int(os.getenv("MAX_FILES", 0))

DOWNLOAD_DIR = "downloaded_media"
DELAY_SECONDS = 1.0  # Slightly longer delay to match browser pacing
# ----------------------------------------

def create_download_dir(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)

def download_file(url, folder):
    try:
        filename = url.split('/')[-1].split('?')[0]
        if not filename: return False

        file_path = os.path.join(folder, filename)
        if os.path.exists(file_path): 
            print(f"[~] Already exists: {filename}")
            return True

        headers = {
            "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8,video/*",
            "Referer": MEDIA_BASE_URL, 
            "Origin": MEDIA_BASE_URL,
            "Accept-Language": "en-US,en;q=0.9",
        }
        if COOKIE_STRING:
            headers["Cookie"] = COOKIE_STRING
        
        # impersonate="chrome" mimics a real Chrome TLS/JA3 fingerprint perfectly
        response = requests.get(
            url, 
            headers=headers, 
            impersonate="chrome", 
            timeout=30
        )
        response.raise_for_status()

        content_type = response.headers.get('Content-Type', '').lower()
        if 'text/html' in content_type:
            print(f"[-] Blocked by Firewall: Received HTML instead of media for {filename}")
            return False

        with open(file_path, "wb") as f:
            f.write(response.content)
                
        actual_size_kb = os.path.getsize(file_path) / 1024
        print(f"[+] Downloaded: {filename} ({actual_size_kb:.1f} KB)")
        return True

    except Exception as e:
        print(f"[-] Failed to download {url}: {e}")
        return False

def get_api_page(page_num):
    target_url = API_URL.replace("{page}", str(page_num))
    headers = {
        "Accept": "application/json, text/plain, */*",
        "Referer": MEDIA_BASE_URL,
        "Accept-Language": "en-US,en;q=0.9",
    }
    if COOKIE_STRING:
        headers["Cookie"] = COOKIE_STRING
    
    try:
        response = requests.get(
            target_url, 
            headers=headers, 
            impersonate="chrome", 
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"[-] Failed to fetch API page {page_num}: {e}")
        return None

def main():
    print("[*] Starting Advanced Chrome-Impersonation Scraper.")
    if not COOKIE_STRING:
        print("[!] Warning: COOKIE_STRING secret is missing.")
        
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
            print("[-] API request failed. Stopping execution.")
            break
            
        medias = data.get("medias", [])
        if not medias:
            print("[*] No more media found in JSON. Gallery complete!")
            break
            
        print(f"[*] Found {len(medias)} items on page {current_page}.")

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

    print(f"\n[+] Task complete! Total files secured: {total_files}")

if __name__ == "__main__":
    main()
