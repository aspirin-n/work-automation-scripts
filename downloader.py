import os
import time
import sys
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup

# --- CONFIGURATION via GITHUB ACTIONS ---
BASE_URL = os.getenv("BASE_URL")
if not BASE_URL:
    print("[-] Error: BASE_URL environment variable is missing.")
    sys.exit(1)

START_NUMBER = int(os.getenv("START_NUMBER", 100))
KEYWORD = os.getenv("KEYWORD", "").strip().lower()
MAX_FILES = int(os.getenv("MAX_FILES", 0))
MAX_DEAD_PAGES = int(os.getenv("MAX_DEAD_PAGES", 30))

DOWNLOAD_DIR = "downloaded_media"
DELAY_SECONDS = 0.5
# ----------------------------------------

def create_download_dir(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)

def get_soup(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return BeautifulSoup(response.text, "html.parser")
    except requests.RequestException:
        return None

def download_file(url, folder):
    try:
        filename = os.path.basename(urlparse(url).path)
        if not filename: return False

        file_path = os.path.join(folder, filename)
        if os.path.exists(file_path): 
            print(f"[~] Already exists: {filename}")
            return True

        headers = {"User-Agent": "Mozilla/5.0"}
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

def extract_media_from_page(page_soup, page_url):
    media_urls = set()
    
    # Check Images
    for img in page_soup.find_all("img", src=True):
        src = img.get("src")
        src_lower = src.lower()
        
        # 1. Block webp
        if src_lower.endswith('.webp') or '.webp?' in src_lower:
            continue
            
        # 2. Strict Keyword Filter
        if KEYWORD and KEYWORD not in src_lower:
            continue
            
        media_urls.add(urljoin(page_url, src))
        
    # Check Videos
    for video in page_soup.find_all(["video", "source"], src=True):
        src = video.get("src")
        src_lower = src.lower()
        
        # 1. Block webp
        if src_lower.endswith('.webp') or '.webp?' in src_lower:
            continue
            
        # 2. Strict Keyword Filter
        if KEYWORD and KEYWORD not in src_lower:
            continue
            
        media_urls.add(urljoin(page_url, src))
        
    return media_urls

def main():
    clean_base_url = BASE_URL.rstrip('/')
    print(f"[*] Starting sequential scraper for: {clean_base_url}")
    print(f"[*] STRICT FILTER: Media URL must contain the word '{KEYWORD}'")
    
    create_download_dir(DOWNLOAD_DIR)
    
    current_number = START_NUMBER
    total_files = 0
    dead_pages = 0

    while current_number > 0:
        if MAX_FILES > 0 and total_files >= MAX_FILES:
            print(f"\n[*] Hit file limit ({MAX_FILES}). Stopping.")
            break 

        sub_link = f"{clean_base_url}/{current_number}"
        print(f"\n[*] Checking: {sub_link}")
        
        sub_soup = get_soup(sub_link)
        
        if not sub_soup:
            print("  [-] Page not found or unreachable. Skipping...")
            dead_pages += 1
            if dead_pages >= MAX_DEAD_PAGES:
                print(f"[*] Hit {MAX_DEAD_PAGES} missing pages in a row. Assuming gallery is over. Stopping.")
                break
            current_number -= 1
            continue
            
        # Reset dead page counter since we found a valid page
        dead_pages = 0

        media_urls = extract_media_from_page(sub_soup, sub_link)
        
        if not media_urls:
             print("  [-] No matching media found on this page.")

        for media_url in media_urls:
            if MAX_FILES > 0 and total_files >= MAX_FILES:
                break 

            if download_file(media_url, DOWNLOAD_DIR):
                total_files += 1

        current_number -= 1
        time.sleep(DELAY_SECONDS)

    print(f"\n[+] Task complete! Total actual files secured: {total_files}")

if __name__ == "__main__":
    main()
