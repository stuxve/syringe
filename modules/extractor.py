# utils.py

from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

def prepare_injectable_urls(url: str, payload: str = 'INJECT_HERE') -> list[str]:
    """
    Takes a URL and returns a list of URLs with each parameter replaced one by one with a payload.
    
    :param url: The original URL.
    :param payload: The payload string to inject (default is 'INJECT_HERE').
    :return: List of URLs with individual parameter injection points.
    """
    parsed_url = urlparse(url)
    query_params = parse_qs(parsed_url.query)

    injectable_urls = []

    for key in query_params:
        modified_params = query_params.copy()
        modified_params[key] = [payload]
        new_query = urlencode(modified_params, doseq=True)
        new_url = urlunparse(parsed_url._replace(query=new_query))
        injectable_urls.append(new_url)

    return injectable_urls
