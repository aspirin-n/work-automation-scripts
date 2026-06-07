import os
import time
import sys
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup

# --- CONFIGURATION via GITHUB ACTIONS ---
BASE_URL = os.getenv("TARGET_URL")
if not BASE_URL:
    print("[-] Error: TARGET_URL environment variable is missing.")
    sys.exit(1)

MAX_FILES = int(os.getenv("MAX_FILES", 0))
CSS_SELECTOR = os.getenv("CSS_SELECTOR", "").strip()
MIN_SIZE_KB = int(os.getenv("MIN_SIZE_KB", 100))

TARGET_DOMAIN = urlparse(BASE_URL).netloc
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
        response.raise_for_status()
        return BeautifulSoup(response.text, "html.parser")
    except requests.RequestException as e:
        print(f"[-] Error fetching {url}: {e}")
        return None

def is_file_large_enough(url):
    """Sends a HEAD request to check file size without downloading it."""
    if MIN_SIZE_KB <= 0:
        return True
        
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.head(url, headers=headers, allow_redirects=True, timeout=10)
        
        content_length = response.headers.get('Content-Length')
        if content_length:
            size_kb = int(content_length) / 1024
            if size_kb < MIN_SIZE_KB:
                print(f"[~] Skipping (Too small: {size_kb:.1f}KB): {url.split('/')[-1]}")
                return False
        # If server doesn't provide content length, we assume it's valid and download anyway
        return True
    except Exception:
        # If HEAD request fails, try downloading anyway to be safe
        return True

def download_file(url, folder):
    """Returns True if file downloaded/exists, False if it failed/skipped."""
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

def extract_sub_links(main_soup, base_url):
    sub_links = set()
    for link in main_soup.find_all("a", href=True):
        absolute_url = urljoin(base_url, link["href"])
        if urlparse(absolute_url).netloc == TARGET_DOMAIN:
            sub_links.add(absolute_url)
    return list(sub_links)

def extract_media_from_page(page_soup, page_url):
    media_urls = set()
    
    # Target specific container if provided, otherwise search whole page
    search_area = page_soup
    if CSS_SELECTOR:
        selected_area = page_soup.select_one(CSS_SELECTOR)
        if selected_area:
            search_area = selected_area
            print(f"  [i] Found specific container matching '{CSS_SELECTOR}'")
        else:
            print(f"  [-] Could not find container '{CSS_SELECTOR}'. Searching whole page.")

    for img in search_area.find_all("img", src=True):
        media_urls.add(urljoin(page_url, img.get("src")))
    for video in search_area.find_all(["video", "source"], src=True):
        media_urls.add(urljoin(page_url, video.get("src")))
        
    return media_urls

def main():
    print(f"[*] Starting scraper for: {BASE_URL}")
    create_download_dir(DOWNLOAD_DIR)

    main_soup = get_soup(BASE_URL)
    if not main_soup:
        sys.exit(1)

    sub_links = extract_sub_links(main_soup, BASE_URL)
    print(f"[*] Found {len(sub_links)} sub-links on the initial page load.")

    total_files = 0

    for index, sub_link in enumerate(sub_links, 1):
        print(f"\n[*] Checking link ({index}/{len(sub_links)}): {sub_link}")
        sub_soup = get_soup(sub_link)
        if not sub_soup: continue

        media_urls = extract_media_from_page(sub_soup, sub_link)
        
        for media_url in media_urls:
            if MAX_FILES > 0 and total_files >= MAX_FILES:
                print(f"\n[*] Hit file limit ({MAX_FILES}). Stopping.")
                break 

            if download_file(media_url, DOWNLOAD_DIR):
                total_files += 1

        if MAX_FILES > 0 and total_files >= MAX_FILES:
            break
        
        time.sleep(DELAY_SECONDS)

    print(f"\n[+] Task complete! Total main files secured: {total_files}")

if __name__ == "__main__":
    main()
