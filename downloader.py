import os
import time
import sys
from urllib.parse import urljoin
from curl_cffi import requests

# --- CONFIGURATION via GITHUB ACTIONS ---
API_URL = os.getenv("API_URL", "").strip().strip('"').strip("'")
MEDIA_BASE_URL = os.getenv("MEDIA_BASE_URL", "").strip().strip('"').strip("'")
RAW_HEADERS_TEXT = os.getenv("RAW_HEADERS", "").strip()

if not API_URL or not MEDIA_BASE_URL:
    print("[-] Error: API_URL or MEDIA_BASE_URL environment variable is missing.")
    sys.exit(1)

START_PAGE = int(os.getenv("START_PAGE", 1))
MAX_FILES = int(os.getenv("MAX_FILES", 0))

DOWNLOAD_DIR = "downloaded_media"
DELAY_SECONDS = 1.0  
# ----------------------------------------

def parse_raw_headers(raw_text):
    """Parses raw browser request headers into a valid dictionary."""
    headers = {}
    if not raw_text:
        return headers
        
    for line in raw_text.splitlines():
        line = line.strip()
        if not line or line.startswith("GET ") or line.startswith("POST "):
            continue  # Skip HTTP method lines
        if ":" in line:
            key, val = line.split(":", 1)
            # Ignore pseudo-headers that curl_cffi generates natively
            if key.strip().startswith(":"):
                continue
            headers[key.strip()] = val.strip()
            
    return headers

def create_download_dir(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)

def download_file(url, folder, session_headers):
    try:
        url = url.strip()
        filename = url.split('/')[-1].split('?')[0]
        if not filename: return False

        file_path = os.path.join(folder, filename)
        if os.path.exists(file_path): 
            print(f"[~] Already exists: {filename}")
            return True

        response = requests.get(
            url, 
            headers=session_headers, 
            impersonate="chrome", 
            timeout=30
        )
        
        if response.status_code != 200:
            print(f"[-] Failed downloading file {filename}. Status: {response.status_code}")
            return False

        content_type = response.headers.get('Content-Type', '').lower()
        if 'text/html' in content_type:
            print(f"[-] Blocked on file download ({filename}). Server replied with HTML instead of media.")
            return False

        with open(file_path, "wb") as f:
            f.write(response.content)
                
        actual_size_kb = os.path.getsize(file_path) / 1024
        print(f"[+] Downloaded: {filename} ({actual_size_kb:.1f} KB)")
        return True

    except Exception as e:
        print(f"[-] Error downloading {url}: {e}")
        return False

def get_api_page(page_num, session_headers):
    target_url = API_URL.replace("{page}", str(page_num)).strip()
    
    try:
        print(f"[*] Fetching target: {target_url}")
        response = requests.get(
            target_url, 
            headers=session_headers, 
            impersonate="chrome", 
            timeout=30
        )
        
        if response.status_code != 200:
            print(f"[-] API Page {page_num} returned Status Code: {response.status_code}")
            return None
            
        content_type = response.headers.get('Content-Type', '').lower()
        if 'text/html' in content_type:
            print(f"[-] Blocked: Server redirected API request to login/verification HTML page.")
            print(f"[DIAGNOSTIC LOG] Response snippet:\n{response.text[:300]}\n---")
            return None

        return response.json()
    except Exception as e:
        print(f"[-] Request crash on API page {page_num}: {e}")
        return None

def main():
    print("[*] Starting Header-Cloned Scraper.")
    
    # Generate the header payload parsed from the browser clone
    custom_headers = parse_raw_headers(RAW_HEADERS_TEXT)
    if not custom_headers:
        print("[!] Warning: No raw headers detected. Using basic requests.")
    else:
        print(f"[+] Successfully loaded {len(custom_headers)} browser authentication headers.")

    create_download_dir(DOWNLOAD_DIR)
    
    current_page = START_PAGE
    total_files = 0

    while True:
        if MAX_FILES > 0 and total_files >= MAX_FILES:
            print(f"\n[*] Hit file limit ({MAX_FILES}). Stopping.")
            break 

        print(f"\n[*] Processing Page {current_page}...")
        data = get_api_page(current_page, custom_headers)
        
        if not data:
            print("[-] API read failed. Stopping execution.")
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
            if download_file(full_media_url, DOWNLOAD_DIR, custom_headers):
                total_files += 1

        current_page += 1
        time.sleep(DELAY_SECONDS)

    print(f"\n[+] Task complete! Total files secured: {total_files}")

if __name__ == "__main__":
    main()
