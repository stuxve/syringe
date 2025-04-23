import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, parse_qsl, urlencode

class WebCrawler:
    def __init__(self, base_url):
        self.base_url = base_url.rstrip('/')
        self.visited = set()
        self.to_visit = set([self.base_url])
        self.found_entries = set()

    def normalize_url(self, url):
        parsed = urlparse(url)
        query = parse_qsl(parsed.query)
        query.sort()
        normalized_query = urlencode(query)
        normalized_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        if normalized_query:
            normalized_url += f"?{normalized_query}"
        return normalized_url

    def is_valid(self, url):
        return url.startswith(self.base_url)

    def extract_links_and_forms(self, html, current_url):
        soup = BeautifulSoup(html, 'html.parser')

        for tag in soup.find_all('a', href=True):
            href = tag['href']
            full_url = urljoin(current_url, href)
            if self.is_valid(full_url):
                norm_url = self.normalize_url(full_url)
                entry = f"GET|{norm_url}"
                self.found_entries.add(entry)
                if norm_url not in self.visited:
                    self.to_visit.add(norm_url)

        for form in soup.find_all('form'):
            action = form.get('action') or current_url
            method = form.get('method', 'get').upper()
            full_url = urljoin(current_url, action)
            if not self.is_valid(full_url):
                continue

            inputs = form.find_all(['input', 'textarea', 'select'])
            data = {}
            for input_tag in inputs:
                name = input_tag.get('name')
                value = input_tag.get('value', 'value')
                if name:
                    data[name] = value

            param_string = urlencode(sorted(data.items()))
            norm_url = self.normalize_url(full_url)
            entry = f"{method}|{norm_url}"
            if param_string:
                entry += f"|{param_string}"
            self.found_entries.add(entry)

    def crawl(self):
        while self.to_visit:
            url = self.to_visit.pop()
            if url in self.visited:
                continue
            self.visited.add(url)
            print(f"[+] Crawling: {url}")
            try:
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    self.extract_links_and_forms(response.text, url)
            except requests.RequestException:
                continue

def load_targets(file_path):
    with open(file_path, 'r') as file:
        return [line.strip() for line in file if line.strip()]

def main():
    all_entries = set()
    targets = load_targets("targets.txt")

    for target in targets:
        print(f"\n[=] Starting crawl on: {target}")
        crawler = WebCrawler(target)
        crawler.crawl()
        all_entries.update(crawler.found_entries)

    with open("urls.txt", "w") as output:
        for entry in sorted(all_entries):
            output.write(entry + "\n")
    print(f"\n[✓] Saved {len(all_entries)} unique entries to urls.txt")

if __name__ == "__main__":
    main()
