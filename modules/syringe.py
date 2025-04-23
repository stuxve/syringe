import requests
from utils import prepare_injectable_urls
import configparser
import os
from bs4 import BeautifulSoup

class PayloadInjector:
    def __init__(self, config_path='syringe.conf', payload_file='payloads.txt'):
        self.config = self.load_config(config_path)
        self.payloads = self.load_payloads(payload_file)
        self.session = requests.Session()
        self.headers = {"User-Agent": "Mozilla/5.0 (SyringeScanner)"}

    def load_config(self, path):
        config = configparser.ConfigParser()
        config.read(path)
        return config['DEFAULT']

    def load_payloads(self, path):
        if not os.path.exists(path):
            return ["<script>alert(1)</script>", "\"><img src=x onerror=alert(1)>"]
        with open(path, 'r') as f:
            return [line.strip() for line in f if line.strip()]

    def is_html_reflected(self, response_text, payload):
        soup = BeautifulSoup(response_text, 'html.parser')
        return payload in str(soup)

    def scan_url(self, url: str):
        results = []

        if self.config.getboolean('XSS', fallback=False):
            for payload in self.payloads:
                injectable_urls = prepare_injectable_urls(url, payload)

                for test_url in injectable_urls:
                    try:
                        response = self.session.get(test_url, headers=self.headers, timeout=10)
                        reflected = self.is_html_reflected(response.text, payload)

                        results.append({
                            "url": test_url,
                            "payload": payload,
                            "reflected_as_html": reflected,
                            "status_code": response.status_code
                        })

                        print(f"[{'✓' if reflected else '✗'}] {test_url} -> {payload}")

                    except requests.RequestException as e:
                        print(f"[!] Error requesting {test_url}: {e}")
                        results.append({
                            "url": test_url,
                            "error": str(e)
                        })
        else:
            print("[!] XSS injection disabled in config.")
        
        return results
