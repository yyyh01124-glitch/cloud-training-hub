import requests
import hashlib
import time
from datetime import datetime

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

TIMEOUT = 10


def crawl_url(url, source_type='tech_article'):
    """Fetch and parse a URL. Returns list of dicts with raw data."""
    results = []
    try:
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        resp.raise_for_status()
        resp.encoding = resp.apparent_encoding or 'utf-8'

        if source_type == 'opensource':
            results = _parse_github_trending(resp)
        elif source_type == 'job':
            results = _parse_generic(resp)
        else:
            results = _parse_tech_articles(resp)
    except requests.RequestException as e:
        print(f'Crawl error: {e}')
        return results

    for r in results:
        r['source_type'] = source_type
        r['data_hash'] = hashlib.sha256(
            (r.get('title', '') + r.get('url', '')).encode()
        ).hexdigest()
    return results


def _parse_tech_articles(resp):
    """Parse tech article listings. Generic HTML parser."""
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(resp.text, 'html.parser')
    results = []
    for item in soup.select('article, .post, .item, .entry, .story, tr.athing')[:20]:
        link = item.select_one('a[href]')
        title = item.select_one('h1, h2, h3, .title, .storylink')
        desc = item.select_one('p, .summary, .description, .excerpt')

        title_text = title.get_text(strip=True) if title else (link.get_text(strip=True) if link else '')
        url = link.get('href', '') if link else ''
        if url and not url.startswith('http'):
            from urllib.parse import urljoin
            url = urljoin(resp.url, url)
        if title_text:
            results.append({
                'title': title_text[:500],
                'url': url[:1000],
                'summary': desc.get_text(strip=True)[:1000] if desc else '',
                'pub_date': '',
            })
    return results


def _parse_github_trending(resp):
    """Parse GitHub trending page."""
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(resp.text, 'html.parser')
    results = []
    for repo in soup.select('article.Box-row, .repo-list-item, .Box-row')[:20]:
        title_el = repo.select_one('h1, h2, h3, .wb-break-word')
        desc_el = repo.select_one('p')
        link = repo.select_one('a[href]')
        title = title_el.get_text(strip=True) if title_el else ''
        url = 'https://github.com' + link.get('href', '') if link and link.get('href', '').startswith('/') else ''
        if title:
            results.append({
                'title': title[:500],
                'url': url[:1000],
                'summary': desc_el.get_text(strip=True)[:1000] if desc_el else '',
                'pub_date': '',
            })
    return results


def _parse_generic(resp):
    """Generic page parsing."""
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(resp.text, 'html.parser')
    results = []
    for item in soup.select('article, .card, .job-item, .position, .listing')[:15]:
        title_el = item.select_one('h1, h2, h3, h4, .title, .job-title')
        desc_el = item.select_one('p, .description, .summary, .job-desc')
        link = item.select_one('a[href]')
        title = title_el.get_text(strip=True) if title_el else ''
        url = link.get('href', '') if link else ''
        if title:
            results.append({
                'title': title[:500],
                'url': url[:1000],
                'summary': desc_el.get_text(strip=True)[:1000] if desc_el else '',
                'pub_date': '',
            })
    return results
