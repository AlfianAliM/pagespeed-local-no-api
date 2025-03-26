import subprocess
import csv
import time
import argparse
import requests
import xml.etree.ElementTree as ET
import urllib.parse
import json

def get_urls_from_sitemap(sitemap_url):
    """Mengambil semua URL dari sitemap XML"""
    response = requests.get(sitemap_url)
    urls = []
    if response.status_code == 200:
        root = ET.fromstring(response.text)
        for url in root.findall(".//{http://www.sitemaps.org/schemas/sitemap/0.9}url/{http://www.sitemaps.org/schemas/sitemap/0.9}loc"):
            urls.append(url.text)
    return urls

def run_lighthouse(url):
    """Menjalankan Lighthouse CLI dan mengambil skor Performance & Speed Index"""
    try:
        result = subprocess.run(
            ["lighthouse", url, "--quiet", "--only-categories=performance", "--output=json", "--chrome-flags=--headless"],
            capture_output=True, text=True, timeout=120
        )
        data = result.stdout

        if not data:
            return {"performance": "Error", "speed_index": "Error"}

        json_data = json.loads(data)
        performance = json_data["categories"]["performance"]["score"] * 100
        speed_index = json_data["audits"]["speed-index"]["numericValue"] / 1000  # Convert ke detik

        return {"performance": performance, "speed_index": round(speed_index, 2)}

    except Exception as e:
        print(f"Error checking {url}: {e}")
        return {"performance": "Error", "speed_index": "Error"}

def extract_domain(sitemap_url):
    """Mengambil root domain dari URL sitemap"""
    parsed_url = urllib.parse.urlparse(sitemap_url)
    return parsed_url.netloc.replace("www.", "")

def main():
    parser = argparse.ArgumentParser(description="Bulk PageSpeed Checker pakai Lighthouse CLI")
    parser.add_argument("-sitemap", required=True, help="URL Sitemap XML")
    args = parser.parse_args()

    sitemap_url = args.sitemap
    domain_name = extract_domain(sitemap_url)
    output_csv = f"{domain_name}_pagespeed.csv"

    urls = get_urls_from_sitemap(sitemap_url)
    print(f"Total URLs ditemukan: {len(urls)} dari {sitemap_url}")

    # Buka file CSV sekali di awal dan tulis header
    with open(output_csv, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["URL", "Performance Score", "Speed Index (s)"])  # Header

    # Proses setiap URL satu per satu
    for i, url in enumerate(urls):
        print(f"Checking ({i+1}/{len(urls)}): {url}")
        result = run_lighthouse(url)
        
        # Buka file dalam mode append dan tulis hasilnya
        with open(output_csv, "a", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([url, result["performance"], result["speed_index"]])
        
        print(f"  -> Hasil disimpan: Performance={result['performance']}, Speed Index={result['speed_index']}s")
        time.sleep(2)  # Jeda antar pengukuran

    print(f"Semua pengukuran selesai. Hasil lengkap disimpan di {output_csv}")

if __name__ == "__main__":
    main()