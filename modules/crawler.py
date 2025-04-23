import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, parse_qsl, urlencode

class WebCrawler:
    def __init__(self, base_url):
        self.base_url = base_url.rstrip('/')
        self.domain = urlparse(self.base_url).netloc
        self.visited = set()
        self.to_visit = set([(self.base_url, 'GET')])  # track with method
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
        parsed = urlparse(url)
        return parsed.netloc == self.domain

    def extract_links_and_forms(self, html, current_url):
        soup = BeautifulSoup(html, 'html.parser')

        def handle_attr(tag, attr):
            if tag.has_attr(attr):
                raw_url = tag[attr]
                full_url = urljoin(current_url, raw_url)
                if self.is_valid(full_url):
                    norm_url = self.normalize_url(full_url)
                    entry = f"GET|{norm_url}"
                    if entry not in self.found_entries:
                        self.found_entries.add(entry)
                        self.to_visit.add((norm_url, 'GET'))

        # Handle ALL tags with src or href
        for tag in soup.find_all(True):  # True = all tags
            handle_attr(tag, 'href')
            handle_attr(tag, 'src')

        # Handle forms (for POST and parameter tracking)
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
            if entry not in self.found_entries:
                self.found_entries.add(entry)
                self.to_visit.add((norm_url, method))

    def crawl(self):
        while self.to_visit:
            url, method = self.to_visit.pop()
            visit_key = f"{method}|{url}"
            if visit_key in self.visited:
                continue
            self.visited.add(visit_key)
            print(f"[+] Crawling ({method}): {url}")
            try:
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    self.extract_links_and_forms(response.text, url)
            except requests.RequestException:
                continue

        self.export_results()

    def export_results(self, filename="results/crawled.txt"):
        with open(filename, 'w') as f:
            for entry in sorted(self.found_entries):
                f.write(entry + '\n')

    def load_targets(self, file_path):
        with open(file_path, 'r') as file:
            return [line.strip() for line in file if line.strip()]

