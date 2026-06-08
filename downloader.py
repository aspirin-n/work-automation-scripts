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
    headers = {}
    if not raw_text:
        return headers
        
    for line in raw_text.splitlines():
        line = line.strip()
        if not line or line.startswith("GET ") or line.startswith("POST "):
            continue
        if ":" in line:
            key, val = line.split(":", 1)
            if key.strip().startswith(":"):
                continue
            headers[key.strip()] = val.strip()
            
    return headers

def inject_age_cookies(headers):
    """Forcefully injects your exact working browser age cookie."""
    # This is the exact string your browser uses to clear the gate
    exact_age_cookie = "age-verification=true"
    
    current_cookie = headers.get("Cookie", "")
    if current_cookie:
        # If headers already have cookies, append yours to the end
        if exact_age_cookie not in current_cookie:
            headers["Cookie"] = f"{current_cookie}; {exact_age_cookie}"
    else:
        # If no cookies were loaded, use this one exclusively
        headers["Cookie"] = exact_age_cookie
        
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
            return True

        response = requests.get(
            url, 
            headers=session_headers, 
            impersonate="chrome", 
            timeout=30
        )
        
        if response.status_code != 200:
            return False

        content_type = response.headers.get('Content-Type', '').lower()
        if 'text/html' in content_type:
            return False

        with open(file_path, "wb") as f:
            f.write(response.content)
                
        actual_size_kb = os.path.getsize(file_path) / 1024
        print(f"[+] Downloaded: {filename} ({actual_size_kb:.1f} KB)")
        return True
    except Exception:
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
            print(f"[-] Server responded with Status Code: {response.status_code}")
            return None
            
        content_type = response.headers.get('Content-Type', '').lower()
        if 'text/html' in content_type:
            print(f"[-] Blocked: Server redirected request to verification wall.")
            print(f"[DIAGNOSTIC LOG] Source Snip:\n{response.text[:200]}\n---")
            return None

        return response.json()
    except Exception as e:
        print(f"[-] Request crash: {e}")
        return None

def main():
    print("[*] Starting Age-Gate Bypass Scraper.")
    
    custom_headers = parse_raw_headers(RAW_HEADERS_TEXT)
    
    # Force the specific verified cookie change
    custom_headers = inject_age_cookies(custom_headers)
    print("[+] Injected explicit bypass cookie: age-verification=true")

    create_download_dir(DOWNLOAD_DIR)
    current_page = START_PAGE
    total_files = 0

    while True:
        if MAX_FILES > 0 and total_files >= MAX_FILES:
            break 

        print(f"\n[*] Processing Page {current_page}...")
        data = get_api_page(current_page, custom_headers)
        
        if not data:
            break
            
        medias = data.get("medias", [])
        if not medias:
            print("[*] Gallery complete!")
            break
            
        print(f"[*] Found {len(medias)} items on page {current_page}.")

        for item in medias:
            if MAX_FILES > 0 and total_files >= MAX_FILES:
                break 

            file_path = item.get("file_path")
            if not file_path: continue
                
            full_media_url = urljoin(MEDIA_BASE_URL, file_path)
            if download_file(full_media_url, DOWNLOAD_DIR, custom_headers):
                total_files += 1

        current_page += 1
        time.sleep(DELAY_SECONDS)

    print(f"\n[+] Task complete! Total files secured: {total_files}")

if __name__ == "__main__":
    main()
