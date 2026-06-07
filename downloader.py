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

MAX_PAGES = int(os.getenv("MAX_PAGES", 0))
MAX_FILES = int(os.getenv("MAX_FILES", 0))

TARGET_DOMAIN = urlparse(BASE_URL).netloc
DOWNLOAD_DIR = "downloaded_media"
DELAY_SECONDS = 0.5
# ----------------------------------------


def create_download_dir(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)


def get_soup(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        return BeautifulSoup(response.text, "html.parser")
    except requests.RequestException as e:
        print(f"[-] Error fetching {url}: {e}")
        return None


def download_file(url, folder):
    """Returns True if the file was downloaded or already exists, False if it failed."""
    try:
        parsed_url = urlparse(url)
        filename = os.path.basename(parsed_url.path)

        if not filename:
            return False

        file_path = os.path.join(folder, filename)
        if os.path.exists(file_path):
            return True

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        response = requests.get(url, headers=headers, stream=True, timeout=15)
        response.raise_for_status()

        with open(file_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        print(f"[+] Downloaded: {filename}")
        return True

    except requests.RequestException as e:
        print(f"[-] Failed to download {url}: {e}")
        return False


def extract_sub_links(main_soup, base_url):
    sub_links = set()
    for link in main_soup.find_all("a", href=True):
        href = link["href"]
        absolute_url = urljoin(base_url, href)
        if urlparse(absolute_url).netloc == TARGET_DOMAIN:
            sub_links.add(absolute_url)
    return list(sub_links)


def extract_media_from_page(page_soup, page_url):
    media_urls = set()
    for img in page_soup.find_all("img", src=True):
        media_urls.add(urljoin(page_url, img.get("src")))
    for video in page_soup.find_all(["video", "source"], src=True):
        media_urls.add(urljoin(page_url, video.get("src")))
    return media_urls


def main():
    print(f"[*] Starting scraper for: {BASE_URL}")
    if MAX_PAGES > 0: print(f"[*] Limit set to {MAX_PAGES} pages.")
    if MAX_FILES > 0: print(f"[*] Limit set to {MAX_FILES} total files.")
    
    create_download_dir(DOWNLOAD_DIR)

    main_soup = get_soup(BASE_URL)
    if not main_soup:
        print("[-] Could not parse main page. Exiting.")
        sys.exit(1)

    sub_links = extract_sub_links(main_soup, BASE_URL)
    print(f"[*] Found {len(sub_links)} sub-links to investigate.")

    total_files_downloaded = 0

    for index, sub_link in enumerate(sub_links, 1):
        # Check page limit
        if MAX_PAGES > 0 and index > MAX_PAGES:
            print(f"\n[*] Reached maximum page limit ({MAX_PAGES}). Stopping page scans.")
            break

        print(f"\n[*] Processing sub-link ({index}/{len(sub_links)}): {sub_link}")
        sub_soup = get_soup(sub_link)
        if not sub_soup:
            continue

        media_urls = extract_media_from_page(sub_soup, sub_link)
        print(f"[i] Found {len(media_urls)} media items on this page.")

        for media_url in media_urls:
            # Check file limit before each download
            if MAX_FILES > 0 and total_files_downloaded >= MAX_FILES:
                print(f"\n[*] Reached maximum file limit ({MAX_FILES}). Stopping all downloads.")
                break 

            if download_file(media_url, DOWNLOAD_DIR):
                total_files_downloaded += 1

        # Double check file limit to break out of the main page loop as well
        if MAX_FILES > 0 and total_files_downloaded >= MAX_FILES:
            break
        
        time.sleep(DELAY_SECONDS)

    print(f"\n[+] Scraping task completed! Total files secured: {total_files_downloaded}")


if __name__ == "__main__":
    main()
