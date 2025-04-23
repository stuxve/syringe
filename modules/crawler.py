import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, parse_qsl, urlencode
import re

class WebCrawler:
    def __init__(self, base_url):
        self.base_url = base_url.rstrip('/')
        self.domain = urlparse(self.base_url).netloc
        self.visited = set()
        self.to_visit = set([(self.base_url, 'GET')])
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

        for tag in soup.find_all(True):
            handle_attr(tag, 'href')
            handle_attr(tag, 'src')

        for form in soup.find_all('form'):
            action = form.get('action') or current_url
            method = form.get('method', 'get').upper()
            full_url = urljoin(current_url, action)
            if not self.is_valid(full_url):
                continue

            data = {}
            for input_tag in form.find_all(['input', 'textarea', 'select']):
                name = input_tag.get('name')
                value = input_tag.get('value', '')
                if name:
                    data[name] = value

            param_string = urlencode(sorted(data.items()))
            norm_url = self.normalize_url(full_url)
            entry = f"{method}|{norm_url}"
            if param_string:
                entry += f"|{param_string}"
            if entry not in self.found_entries:
                self.found_entries.add(entry)
                if method == 'POST':
                    data_tuple = tuple(sorted(data.items()))
                    self.to_visit.add((norm_url, 'POST', data_tuple))
                else:
                    self.to_visit.add((norm_url, 'GET'))

        self.detect_ajax_requests(soup, current_url)

    def detect_ajax_requests(self, soup, current_url):
        for script in soup.find_all('script'):
            if 'ajax' in script.text.lower() or '$.ajax' in script.text:
                self.extract_ajax_data(script.text, current_url)

    def extract_ajax_data(self, script_text, current_url):
        ajax_pattern = re.compile(r'(\$\.ajax\s*\([^\)]*\)|\$\.\w+\s*\([^\)]*\)|new\s+XMLHttpRequest\s*\(\))', re.DOTALL)
        matches = ajax_pattern.findall(script_text)
        for match in matches:
            #print(f"[DEBUG] Detected AJAX pattern: {match}")
            self.parse_ajax_request(match, current_url)

    def parse_ajax_request(self, match, current_url):
        url = None
        data = {}

        url_pattern = re.compile(r"url\s*[:=]\s*['\"]([^'\"]+)['\"]")
        data_pattern = re.compile(r"data\s*[:=]\s*\{([^}]+)\}")

        url_match = url_pattern.search(match)
        if url_match:
            url = url_match.group(1)

        data_match = data_pattern.search(match)
        if data_match:
            raw_data = data_match.group(1)
            pairs = raw_data.split(',')
            for pair in pairs:
                if ':' in pair:
                    key, value = pair.split(':', 1)
                    key = key.strip().strip('"\'')
                    value = value.strip().strip('"\'')
                    data[key] = value

        if url:
            final_url = urljoin(current_url, url)
            #print(f"[INFO] Detected AJAX POST to {final_url} with data {data}")
            self.to_visit.add((final_url, 'POST', tuple(sorted(data.items()))))
            self.found_entries.add(f"POST|{final_url}|{urlencode(data)}")
            self.send_ajax_post(final_url, data)

    def send_ajax_post(self, current_url, data):
        try:
            response = requests.post(current_url, data=data, timeout=5, allow_redirects=True)
            if response.status_code == 200:
                print(f"  [+] Successfully sent POST request to {current_url}")
                self.extract_links_and_forms(response.text, response.url)
        except requests.RequestException as e:
            print(f"  [!] Error sending POST request: {e}")

    def crawl(self):
        while self.to_visit:
            url, method, *data = self.to_visit.pop()
            visit_key = f"{method}|{url}"
            if visit_key in self.visited:
                continue
            self.visited.add(visit_key)

            if method == 'GET':
                print(f"[+] Crawling ({method}): {url}")
                try:
                    response = requests.get(url, timeout=5, allow_redirects=True)
                    if response.status_code == 200:
                        final_url = response.url
                        if final_url != url:
                            norm_final_url = self.normalize_url(final_url)
                            if self.is_valid(norm_final_url):
                                redirect_entry = f"GET|{norm_final_url}"
                                if redirect_entry not in self.found_entries:
                                    self.found_entries.add(redirect_entry)
                                    self.to_visit.add((norm_final_url, 'GET'))
                        self.extract_links_and_forms(response.text, final_url)
                except requests.RequestException:
                    continue

            elif method == 'POST' and data:
                print(f"[+] Crawling ({method}): {url} with data {dict(data[0])}")
                try:
                    response = requests.post(url, data=dict(data[0]), timeout=5, allow_redirects=True)
                    if response.status_code == 200:
                        final_url = response.url
                        if final_url != url:
                            norm_final_url = self.normalize_url(final_url)
                            if self.is_valid(norm_final_url):
                                redirect_entry = f"POST|{norm_final_url}"
                                if redirect_entry not in self.found_entries:
                                    self.found_entries.add(redirect_entry)
                                    self.to_visit.add((norm_final_url, 'POST', data[0]))
                        self.extract_links_and_forms(response.text, final_url)
                except requests.RequestException:
                    continue

    def export_results(self, filename="results/crawled.txt"):
        with open(filename, 'w') as f:
            for entry in sorted(self.found_entries):
                f.write(entry + '\n')

    def load_targets(self, file_path):
        with open(file_path, 'r') as file:
            return [line.strip() for line in file if line.strip()]
