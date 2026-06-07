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
MAX_FILES = int(os.getenv("MAX_FILES", 0))
CSS_SELECTOR = os.getenv("CSS_SELECTOR", "").strip()
MIN_SIZE_KB = int(os.getenv("MIN_SIZE_KB", 100))

DOWNLOAD_DIR = "downloaded_media"
DELAY_SECONDS = 0.5
MAX_DEAD_PAGES = 5  # Stops scraping if 5 numbers in a row don't exist
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
        # If the page returns a 404 Not Found, we handle it gracefully
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return BeautifulSoup(response.text, "html.parser")
    except requests.RequestException:
        return None

def is_file_large_enough(url):
    if MIN_SIZE_KB <= 0: return True
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.head(url, headers=headers, allow_redirects=True, timeout=10)
        content_length = response.headers.get('Content-Length')
        if content_length:
            if (int(content_length) / 1024) < MIN_SIZE_KB:
                return False
        return True
    except Exception:
        return True

def download_file(url, folder):
    try:
        filename = os.path.basename(urlparse(url).path)
        if not filename: return False

        file_path = os.path.join(folder, filename)
        if os.path.exists(file_path): return True

        if not is_file_large_enough(url):
            return False

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
    
    search_area = page_soup
    if CSS_SELECTOR:
        selected_area = page_soup.select_one(CSS_SELECTOR)
        if selected_area:
            search_area = selected_area

    # Find Images
    for img in search_area.find_all("img", src=True):
        src = img.get("src")
        # STRICT BLOCK on .webp files
        if src.lower().endswith('.webp') or '.webp?' in src.lower():
            continue
        media_urls.add(urljoin(page_url, src))
        
    # Find Videos
    for video in search_area.find_all(["video", "source"], src=True):
        src = video.get("src")
        if src.lower().endswith('.webp') or '.webp?' in src.lower():
            continue
        media_urls.add(urljoin(page_url, src))
        
    return media_urls

def main():
    # Clean up base URL to ensure smooth formatting
    clean_base_url = BASE_URL.rstrip('/')
    print(f"[*] Starting sequential scraper for: {clean_base_url}")
    
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
            print("  [-] Page not found or unreachable.")
            dead_pages += 1
            if dead_pages >= MAX_DEAD_PAGES:
                print(f"[*] Hit {MAX_DEAD_PAGES} dead pages in a row. Assuming no more media exists. Stopping.")
                break
            current_number -= 1
            continue
            
        # Reset dead page counter if page exists
        dead_pages = 0

        media_urls = extract_media_from_page(sub_soup, sub_link)
        
        for media_url in media_urls:
            # Final check to ensure we don't exceed limit mid-page
            if MAX_FILES > 0 and total_files >= MAX_FILES:
                break 

            if download_file(media_url, DOWNLOAD_DIR):
                total_files += 1

        # Move to the previous number
        current_number -= 1
        time.sleep(DELAY_SECONDS)

    print(f"\n[+] Task complete! Total main files secured: {total_files}")

if __name__ == "__main__":
    main()
