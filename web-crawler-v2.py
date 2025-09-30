import heapq
import asyncio
import aiohttp
from colorama import init, Fore, Back, Style
import hashlib
from bs4 import BeautifulSoup
from datetime import datetime
from urllib.parse import urlsplit, urlunsplit, urljoin, parse_qs, urlencode

init(autoreset=True)

def generate_content_hash(content):
    return hashlib.md5(content.encode('utf-8')).hexdigest()

def line_print(bg_color, text,end='\n\n'):
    print(bg_color + Style.BRIGHT  + text, end=end)

def normalize_url(url, base_url=None):
    # Handle relative URLs if base_url is provided
    if base_url and not url.startswith(('http://', 'https://')):
        url = urljoin(base_url, url)
    
    # Split URL into components
    parsed = urlsplit(url)
    
    # Normalize components
    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()
    path = parsed.path.rstrip('/')  # Remove trailing slashes
    # Sort query parameters
    query = parse_qs(parsed.query)
    sorted_query = urlencode(sorted(query.items()), doseq=True)
    
    # Reconstruct URL without fragment
    return urlunsplit((scheme, netloc, path, sorted_query, ''))

class WebCrawler:
    def __init__(self, seed_url, max_concurrency = 4,max_crawl=2000):
        self.frontier = []
        self.backlink_counts = {}
        self.visited = set()
        self.frontier_set = set()
        self.semaphore = asyncio.Semaphore(max_concurrency)
        self.seed_url = seed_url
        self.max_crawl = max_crawl
        self.crawl_ctr = 0
        self.session = None
        self.errors = []
        self.page_datas = []
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10))
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session is not None:
            await self.session.close()
    

    async def get_html(self,url):
        await asyncio.sleep(0.25)
        async with self.semaphore:
            line_print(Back.GREEN,f"Trying to fetch {url} <HTML>")
            try:
                async with self.session.get(url) as response: # type: ignore
                    if response.status != 200:
                        print(f"Error: Status {response.status} for {url}")
                        self.errors.append(f"Error: Status {response.status} when getting {url}")
                        return None
                    if 'text/html' not in response.headers.get('Content-Type', ''): # type: ignore
                        print(f"Non-HTML content for {url}")
                        self.errors.append(f"Non-HTML content for {url}")
                        return None
                    return await response.text()   
            except aiohttp.ClientError as e:
                    print(f"Error fetching {url}: {e}")
                    self.errors.append(f"Error fetching {url}: {e}")
                    return None

    def extract_data_from_html(self,html,url) ->dict|None:
        try:
            soup = BeautifulSoup(html,'lxml')
            result = {
                "url" : url,
                "title" : soup.find('title').get_text(strip=True), # type: ignore
                "header_metadata" : soup.find('head'),
                "body_text" : soup.find('body').get_text(strip=True), # type: ignore
                "links" : soup.find('body').find_all('a',href=True), # type: ignore
                "encoding" : soup.find('head').find('meta', charset=True), # type: ignore
                "image_metadata" : soup.find_all('img'),
                "created_at" : datetime.now(),
                "updated_at" : datetime.now(),
                # 'iframe' : soup.find_all('iframe'),
            }
            # result['content_hash'] = generate_content_hash(result['body_text'])
            return result
        except:
            self.errors.append(f"Failed to extract information from {url}")
            return None

    async def start_crawl(self):
        heapq.heappush(self.frontier,(0,self.seed_url))
        self.backlink_counts[self.seed_url] = 1

        # jika isi queue masih ada dan tidak melebihi batas max_crawl
        while self.frontier and self.crawl_ctr <= self.max_crawl:
            priority, url_to_crawl = heapq.heappop(self.frontier)
            # async with self.semaphore:
            asyncio.create_task(self.crawl_page(url_to_crawl))
    
    async def crawl_page(self,url_to_crawl):
        if url_to_crawl in self.visited:
            return
        
        self.visited.add(url_to_crawl)
        self.crawl_ctr +=1
        line_print(Back.BLUE, f"starting to crawl {url_to_crawl}")

        url_html = await self.get_html(url_to_crawl)
        if url_html is None:
            return
        
        page_data = self.extract_data_from_html(url_html, url_to_crawl)
        if page_data is None:
            return
        
        self.page_datas[url_to_crawl] = page_data
        for href_link in page_data['links']:
            try:
                link = href_link['href']
                absolute_link = normalize_url(link,base_url=url_to_crawl)
                if absolute_link not in self.visited and absolute_link not in self.frontier_set:
                    self.backlink_counts[absolute_link] = self.backlink_counts.get(absolute_link,0) + 1
                    priority = -self.backlink_counts[absolute_link]
                    heapq.heappush(self.frontier, (priority, absolute_link))
                    self.frontier_set.add(url_to_crawl)
            except Exception as error:
                self.errors.append(f"Error processing link {href_link}: {error}")
