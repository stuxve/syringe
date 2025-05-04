# main.py

import argparse
from modules.syringe import PayloadInjector
from modules.crawler import WebCrawler
def read_urls_from_file(filename):
    try:
        with open(filename, "r") as f:
            return [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print(f"[-] File not found: {filename}")
        return []
    except Exception as e:
        print(f"[-] Error reading file: {e}")
        return []
def main():
    parser = argparse.ArgumentParser(description="Payload injector and optional crawler")
    parser.add_argument("--crawl", action="store_true", help="Enable crawling before scanning")
    parser.add_argument("--url", help="Target URL to scan or start crawling from")
    parser.add_argument("--crawled-list-name", help="Filename to save crawled URLs")
    parser.add_argument("--custom-headers", help="Custom headers to include in requests, comma-separated (e.g., 'Authorization: Bearer <token>, User-Agent: CustomAgent')")
    parser.add_argument("--only-crawl",action="store_true", help="Enable only crawling")
    parser.add_argument("--file", help="Filname of targets to scan and crawl")


    args = parser.parse_args()

    if args.crawl and (not args.url or not args.file):
        print("[-] You must specify --url or --file when using --crawl.")
        return
    elif args.crawl and (not args.url or not args.file):
        print("Usage: python main.py --crawled-list-name crawled-list-name")
        return
    elif args.only_crawl and (not args.url and not args.file):
        print("[-] You must specify --url or --file when using --only-crawl.")
        return

    scanner = PayloadInjector()
    crawler = None

    if args.file:
        urls = read_urls_from_file(args.file)
        if not urls:
            print("[-] No valid URLs found in the file.")
            return
        else:
            crawler = WebCrawler(urls, multidomain=True)
    else:
        crawler = WebCrawler(args.url)

    if args.crawl:
        #crawler = WebCrawler(args.url)
        url = crawler.crawl()
        if args.crawled_list_name:
            crawler.export_results(args.crawled_list_name)
            print(f"[+] Crawled URLs saved to {args.crawled_list_name}")
    elif args.only_crawl:
        #crawler = WebCrawler(args.url)
        url = crawler.crawl()
        if args.crawled_list_name:
            crawler.export_results(args.crawled_list_name)
            print(f"[+] Crawled URLs saved to {args.crawled_list_name}")
        return
    else:
        url = [args.url]


    print(f"\n[*] Scanning: {url}")
    results = scanner.scan_url(url)

    print("\n[+] Scan complete. Summary:\n")
    for result in results:
        if "error" in result:
            print(f"[!] Error on {result['url']}: {result['error']}")
        else:
            status = "Reflected" if result['reflected_as_html'] else "Not reflected"
            print(f"[{status}] {result['url']} | Payload: {result['payload']} | Status: {result['status_code']}")

if __name__ == "__main__":
    main()
