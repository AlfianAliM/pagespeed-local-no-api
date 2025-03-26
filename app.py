import subprocess
import csv
import time
import argparse
import requests
import xml.etree.ElementTree as ET
import urllib.parse
import json
import os
from datetime import datetime

def get_urls_from_sitemap(sitemap_url):
    """Mengambil semua URL dari sitemap XML"""
    try:
        response = requests.get(sitemap_url, timeout=10)
        response.raise_for_status()
        urls = []
        root = ET.fromstring(response.text)
        namespace = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
        
        for url in root.findall('.//ns:url/ns:loc', namespace):
            urls.append(url.text)
        return urls
    
    except Exception as e:
        print(f"Error fetching sitemap: {e}")
        return []

def default_error_values():
    """Nilai default ketika terjadi error"""
    return {
        "performance": "Error",
        "speed_index": "Error",
        "lcp": "Error",
        "inp": "Error",
        "cls": "Error"
    }

def run_lighthouse(url):
    """Menjalankan Lighthouse CLI dan mengambil berbagai metrik performa"""
    try:
        # Buat nama file report unik
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"lighthouse_report_{timestamp}.json"
        
        # Jalankan Lighthouse
        result = subprocess.run(
            [
                "lighthouse",
                url,
                "--quiet",
                "--only-categories=performance",
                "--output=json",
                f"--output-path={output_file}",
                "--chrome-flags=--headless --no-sandbox",
                "--throttling-method=provided"
            ],
            timeout=180,
            capture_output=True,
            text=True
        )

        # Baca hasil dari file
        with open(output_file) as f:
            data = json.load(f)
        
        # Hapus file report setelah dibaca
        os.remove(output_file)
        
        # Ekstrak metrik dengan error handling
        audits = data.get("audits", {})
        categories = data.get("categories", {})
        
        performance = categories.get("performance", {}).get("score", 0) * 100
        speed_index = audits.get("speed-index", {}).get("numericValue", 0) / 1000
        lcp = audits.get("largest-contentful-paint", {}).get("numericValue", 0) / 1000
        inp = audits.get("interaction-to-next-paint", {}).get("numericValue", 
             audits.get("first-input-delay", {}).get("numericValue", 0))
        cls = audits.get("cumulative-layout-shift", {}).get("numericValue", 0)
        
        return {
            "performance": round(performance, 1),
            "speed_index": round(speed_index, 2),
            "lcp": round(lcp, 2),
            "inp": round(inp, 2),
            "cls": round(cls, 3)
        }
        
    except subprocess.TimeoutExpired:
        print(f"⏰ Timeout saat mengukur {url}")
        return default_error_values()
    except FileNotFoundError:
        print(f"🔧 Lighthouse tidak ditemukan, pastikan sudah diinstall (npm install -g lighthouse)")
        return default_error_values()
    except json.JSONDecodeError:
        print(f"📄 Gagal parsing hasil Lighthouse untuk {url}")
        return default_error_values()
    except Exception as e:
        print(f"❌ Error tidak terduga saat mengukur {url}: {str(e)}")
        return default_error_values()

def extract_domain(sitemap_url):
    """Mengambil root domain dari URL sitemap"""
    parsed_url = urllib.parse.urlparse(sitemap_url)
    return parsed_url.netloc.replace("www.", "").split(":")[0]

def main():
    print("🚀 Memulai Bulk PageSpeed Checker")
    parser = argparse.ArgumentParser(description="Bulk PageSpeed Checker menggunakan Lighthouse CLI")
    parser.add_argument("-sitemap", required=True, help="URL Sitemap XML")
    parser.add_argument("-delay", type=int, default=5, help="Delay antara pengukuran (detik)")
    args = parser.parse_args()

    sitemap_url = args.sitemap
    delay = args.delay
    domain_name = extract_domain(sitemap_url)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_csv = f"{domain_name}_pagespeed_{timestamp}.csv"

    print(f"🔍 Mengambil URL dari sitemap: {sitemap_url}")
    urls = get_urls_from_sitemap(sitemap_url)
    
    if not urls:
        print("❌ Tidak ada URL yang ditemukan di sitemap")
        return

    print(f"📌 Total {len(urls)} URL ditemukan")
    print(f"💾 Hasil akan disimpan di: {output_csv}")

    # Buka file CSV dan tulis header
    with open(output_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "URL", 
            "Performance Score", 
            "Speed Index (s)",
            "LCP (s)",
            "INP (ms)",
            "CLS",
            "Waktu Pengukuran"
        ])

    # Proses setiap URL
    for i, url in enumerate(urls, 1):
        print(f"\n📊 Mengukur URL {i}/{len(urls)}: {url}")
        
        start_time = time.time()
        result = run_lighthouse(url)
        elapsed_time = time.time() - start_time
        
        # Tulis hasil ke CSV
        with open(output_csv, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                url,
                result["performance"],
                result["speed_index"],
                result["lcp"],
                result["inp"],
                result["cls"],
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ])
        
        print(f"✅ Hasil: Perf={result['performance']} | SI={result['speed_index']}s | "
              f"LCP={result['lcp']}s | INP={result['inp']}ms | CLS={result['cls']} | "
              f"Waktu: {elapsed_time:.1f}s")
        
        if i < len(urls):
            print(f"⏳ Menunggu {delay} detik sebelum pengukuran berikutnya...")
            time.sleep(delay)

    print(f"\n🎉 Semua pengukuran selesai! Hasil lengkap disimpan di: {output_csv}")

if __name__ == "__main__":
    main()