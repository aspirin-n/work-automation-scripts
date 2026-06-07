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

TARGET_DOMAIN = urlparse(BASE_URL).netloc
DOWNLOAD_DIR = "downloaded_media"
DELAY_SECONDS = 0.5  # Reduced delay since GitHub servers are fast
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
    try:
        parsed_url = urlparse(url)
        filename = os.path.basename(parsed_url.path)

        if not filename:
            return

        file_path = os.path.join(folder, filename)
        if os.path.exists(file_path):
            return

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

    except requests.RequestException as e:
        print(f"[-] Failed to download {url}: {e}")


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
    create_download_dir(DOWNLOAD_DIR)

    main_soup = get_soup(BASE_URL)
    if not main_soup:
        print("[-] Could not parse main page. Exiting.")
        sys.exit(1)

    sub_links = extract_sub_links(main_soup, BASE_URL)
    print(f"[*] Found {len(sub_links)} sub-links to investigate.")

    for index, sub_link in enumerate(sub_links, 1):
        print(f"[*] Processing sub-link ({index}/{len(sub_links)}): {sub_link}")
        sub_soup = get_soup(sub_link)
        if not sub_soup:
            continue

        media_urls = extract_media_from_page(sub_soup, sub_link)
        for media_url in media_urls:
            download_file(media_url, DOWNLOAD_DIR)
        
        time.sleep(DELAY_SECONDS)

    print("\n[+] Scraping task completed!")


if __name__ == "__main__":
    main()
