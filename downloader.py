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

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "*/*"
        }
        
        response = requests.get(url, headers=headers, stream=True, timeout=15)
        response.raise_for_status()

        with open(file_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk: f.write(chunk)
                
        print(f"[+] Downloaded: {filename}")
        return True

    except requests.RequestException as e:
        print(f"[-] Failed to download {url}: {e}")
        return False

def get_api_page(page_num):
    # Replaces the {page} placeholder with the actual number
    target_url = API_URL.replace("{page}", str(page_num))
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Accept": "application/json"
    }
    
    try:
        response = requests.get(target_url, headers=headers, timeout=15)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"[-] Failed to fetch API page {page_num}: {e}")
        return None

def main():
    print(f"[*] Starting API scraper.")
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
            
        # The JSON structure you provided has a list called "medias"
        medias = data.get("medias", [])
        
        if not medias:
            print("[*] No more media found in this page. Gallery complete!")
            break
            
        print(f"[*] Found {len(medias)} files on page {current_page}.")

        for item in medias:
            if MAX_FILES > 0 and total_files >= MAX_FILES:
                break 

            # Extract the relative file path from the JSON and build the full link
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
