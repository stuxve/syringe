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

        # Add cookies here
        self.cookies = {
            "aliyungf_tc": "3b87eba4937c06811b78ffc2a5f0317824babd0e3ca7357c9a3fd47e1dca0358",
            "acw_tc": "0a0e01d317463512331865668e0c2664cd111f79ccb9d450ca2554ea717893",
            "_gcl_au": "1.1.1362624715.1746351236",
            "_gid": "GA1.2.263641552.1746351237",
            "Hm_lvt_fa63e8b11e5e93f5baec4cef8eb8be0a": "1746351238",
            "HMACCOUNT": "B5A1F3BD401E1B6B",
            "XSRF-TOKEN": "eyJpdiI6ImhlVUlOQnR5VGhsclJ6bm51XC9TV0F3PT0iLCJ2YWx1ZSI6IjdJVFFcL1orVWgzaElmaTlFa3N1MjU1b1cxTHdzT3Z3cDFVUmNxeDhFaHJTVWFyNkxad2d0dXU3cm1VRXdMRWtoIiwibWFjIjoiMWQ2MTU1NWEwMGE1M2VlMDVhZDQwOTZlYTljNDZlN2U5Y2Y3NzViZGM3NDI1YzZiMjZhZDEwZjk4YzBlYjEzYiJ9",
            "laravel_session": "eyJpdiI6Im9VNjlpaWtodDB4ZXJWTmx3WGVkRUE9PSIsInZhbHVlIjoibFdMNnVSaGV3bFQ0UjFUNnAwVlRyV0RGeHQ4MXFmc0NqanV5NjNhNW5CSmJ3cHFualhzMzlabkdUQUxWM3FibyIsIm1hYyI6IjQwYTFjNzM2ODg3MzYzOWQ4NTk3MTZkNWNlZjJiNDJmZDdhY2FiNzdiMTdmZDRlMWI1OGRiY2U1NTFkZTIyYzQifQ%3D%3D",
            "_ga": "GA1.1.1260044508.1746351237",
            "Hm_lpvt_fa63e8b11e5e93f5baec4cef8eb8be0a": "1746351450",
            "SERVERID": "b062e5a03e55c00ae98f59def6f880f3|1746351460|1746351233",
            "_ga_QX3W0G43PC": "GS2.1.s1746351237$o1$g1$t1746352255$j60$l0$h0"
        }
        self.headers = {
            "Host": "www.mgm.mo",
            "Connection": "keep-alive",
            "Cache-Control": "max-age=0",
            "Upgrade-Insecure-Requests": "1",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Sec-Fetch-Site": "cross-site",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-User": "?1",
            "Sec-Fetch-Dest": "document",
            "Referer": "https://bugcrowd.com/",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "es-ES,es;q=0.9",
            "Priority": "u=0, i",
            "Sec-Ch-Ua": '"Google Chrome";v="135", "Not-A.Brand";v="8", "Chromium";v="135"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
        }


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
            self.to_visit.add((final_url, 'POST', tuple(sorted(data.items()))))
            self.found_entries.add(f"POST|{final_url}|{urlencode(data)}")
            self.send_ajax_post(final_url, data)

    def send_ajax_post(self, current_url, data):
        try:
            response = requests.post(current_url, data=data, cookies=self.cookies, timeout=5, allow_redirects=True)
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
                    response = requests.get(url, cookies=self.cookies, headers=self.headers, timeout=5, allow_redirects=True)
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
                    response = requests.post(url, data=dict(data[0]), cookies=self.cookies, timeout=5, allow_redirects=True)
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
