# from requests_html import HTMLSession
from datetime import datetime
import hashlib
import asyncio
import aiohttp
from colorama import init, Fore, Back, Style
from bs4 import BeautifulSoup
from urllib.parse import urlsplit, urlunsplit, urljoin, parse_qs, urlencode
init(autoreset=True)

def generate_content_hash(content):
    return hashlib.md5(content.encode('utf-8')).hexdigest()

def line_print(bg_color, text,end='\n\n'):
    print(bg_color + Style.BRIGHT  + text, end=end)

class AsyncCrawler:
    def __init__(self, base_url, max_concurrency = 5,max_page_crawled = 1000) -> None:
        self.base_url = base_url
        self.page_datas = {}
        self.lock = asyncio.Lock()
        self.max_concurrency = max_concurrency
        self.semaphore = asyncio.Semaphore(max_concurrency)
        self.session = None
        self.errors = []
        self.max_crawled = max_page_crawled
        self.crawl_ctr = 0

    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10))
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session is not None:
            await self.session.close()
    
    async def add_page_visit(self, url_to_crawl):
        async with self.lock:
            if url_to_crawl in self.page_datas:
                self.errors.append(f"url {url_to_crawl} is already on page_data, Skipped!")
                return False
            print(Fore.GREEN + f"added to page_data {url_to_crawl}")
            self.page_datas[url_to_crawl] = None
            return True

    async def get_html(self, url):
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
    
    async def crawl_page(self, url_to_crawl):
        if self.crawl_ctr > self.max_crawled:
            # self.errors.append(f"{url_to_crawl} skipped, due to max crawl")
            return
        self.crawl_ctr += 1
        # 
        line_print(Back.BLUE, f"starting to crawl {url_to_crawl}")
        is_new = await self.add_page_visit(url_to_crawl)
        if not is_new:
            return
        
        url_html = await self.get_html(url_to_crawl)
        if url_html is None:
            return
        
        page_data = self.extract_data_from_html(url_html, url_to_crawl)
        if page_data is None:
            return

        self.page_datas[url_to_crawl] = page_data

        task = []
        for href_link in page_data['links']:
            try:
                link = href_link['href']
                absolute_link = normalize_url(link,base_url=self.base_url)
                new_task = asyncio.create_task(self.crawl_page(absolute_link))
                task.append(new_task)
            except:
                self.errors.append(f"Error trying to crawl task, url : {href_link}")
        await asyncio.gather(*task)

    async def crawl(self):
        await self.crawl_page(self.base_url)
        return self.page_datas

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

# async def testing_Bs():
#     url = 'https://python.org'
#     session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10))
#     html = None
#     try:
#         async with session.get(url) as response: # type: ignore
#             html = await response.text()   
#     except aiohttp.ClientError as e:
#             print(f"Error fetching {url}: {e}")
    
#     if html is None:
#         return
    
#     soup = BeautifulSoup(html,'lxml')
#     # title = soup.find('title').get_text(strip=True)
#     result = {
#         "url" : url,
#         "title" : soup.find('title').get_text(strip=True), # type: ignore
#         "header_metadata" : soup.find('head'),
#         "body_text" : soup.find('body').get_text(strip=True), # type: ignore
#         "links" : soup.find('body').find_all('a',href=True), # type: ignore
#         "encoding" : soup.find('head').find('meta', charset=True), # type: ignore
#         # 'iframe' : soup.find_all('iframe'),
#         "image_metadata" : soup.find_all('img'),
#         "created_at" : datetime.now(),
#         "updated_at" : datetime.now(),
#     }
    
#     for link in result['links']:
#         absolute_url = normalize_url(link['href'],'https://python.org')
#         print(absolute_url)
#     await session.close()
    
async def crawl_site_async(seed_url, max_concurrency = 3, max_crawled=100):
    async with AsyncCrawler(base_url=seed_url,max_concurrency=max_concurrency, max_page_crawled=max_crawled) as crawler:
        result = await crawler.crawl()
        print(result['https://python.org/events'])
        # print(result['https://xon.sh'])

        line_print(Back.RED , "Here are the error that occured during crawling : ")
        for error in crawler.errors:
            print(Fore.RED,error)

if __name__ == "__main__":
    # asyncio.run(crawl_site_async('https://python.org/'))
    seed_url = 'https://python.org'
    asyncio.run(crawl_site_async(seed_url))

