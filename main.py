# main.py

import argparse
from modules.syringe import PayloadInjector
from modules.crawler import WebCrawler

def main():
    parser = argparse.ArgumentParser(description="Payload injector and optional crawler")
    parser.add_argument("--crawl", action="store_true", help="Enable crawling before scanning")
    parser.add_argument("--url", help="Target URL to scan or start crawling from")
    parser.add_argument("--crawled-list-name", help="Filename to save crawled URLs")
    parser.add_argument("--custom-headers", help="Custom headers to include in requests, comma-separated (e.g., 'Authorization: Bearer <token>, User-Agent: CustomAgent')")
    parser.add_argument("--only-crawl",action="store_true", help="Enable only crawling")


    args = parser.parse_args()

    if args.crawl and not args.url:
        print("[-] You must specify --url when using --crawl.")
        return
    elif not args.crawl and not args.url:
        print("Usage: python main.py --crawled-list-name crawled-list-name")
        return
    elif args.only_crawl and not args.url:
        print("[-] You must specify --url when using --only-crawl.")
        return

    scanner = PayloadInjector()

    if args.crawl:
        crawler = WebCrawler(args.url)
        url = crawler.crawl()
        if args.crawled_list_name:
            crawler.export_results(args.crawled_list_name)
            print(f"[+] Crawled URLs saved to {args.crawled_list_name}")
    elif args.only_crawl:
        crawler = WebCrawler(args.url)
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
