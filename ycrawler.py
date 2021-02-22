import time
import asyncio
import hashlib

import os
import aiohttp
import aiofiles
import aiofiles.os
from bs4 import BeautifulSoup


BASE_URL = 'https://news.ycombinator.com'
MAX_REQUESTS = 5


async def get_page_content(url):
    print(f'do request to {url}')
    async with aiohttp.ClientSession() as session:
        resp = await session.request('GET', url)
        return await resp.read()


async def save_page_content(url, output_folder):
    print(f'save page {url}')
    content = await get_page_content(url)
    hash_ = hashlib.sha256(url.encode()).hexdigest()
    output_path = os.path.join(output_folder, hash_)
    async with aiofiles.open(output_path, 'wb') as f:
        await f.write(content)


def parse_main_page(page_content):
    """ returns dict of {id: url} """
    soup = BeautifulSoup(page_content, 'html.parser')
    ids_with_urls = {}
    for news_block in soup.find_all('tr', class_='athing'):
        id_ = news_block['id']
        a = news_block.find('a', class_='storylink')
        url = a['href']
        if url.startswith('item'):
            url = f'{BASE_URL}/{url}'
        ids_with_urls[id_] = url

    return ids_with_urls


def parse_comments_urls(page_content):
    # => list of urls
    pass


async def create_folders(output_folder, news_ids):
    print('create folders', output_folder, news_ids)
    todo = [aiofiles.os.mkdir(os.path.join(output_folder, str(id_)))
            for id_ in news_ids]

    await asyncio.wait(todo)


async def do_requests(already_seen_news, output_folder):
    main_page_content = await get_page_content(BASE_URL + '/newest')
    news_ids_with_urls = parse_main_page(main_page_content)
    # TODO DO FILTER
    await create_folders(output_folder, news_ids_with_urls.keys())
    # comment_urls = [f'{BASE_URL}/item?id={id_}' for id_ in news_ids_with_urls]
    todo = [save_page_content(url, os.path.join(output_folder, str(id_)))
            for id_, url in news_ids_with_urls.items()]
    # todo += [get_page_content(url) for url in comment_urls]
    await asyncio.wait(todo)
    # coments_tasks = [get_page_content(url) for url in news_urls]
    # for task in news_tasks:
    #   queue for save
    #   load comments page
    # queue for save
    # wait requests
    # wait queue


def main():
    already_seen_news = set()
    out_folder = 'out'
    while True:
        asyncio.run(do_requests(already_seen_news, out_folder), debug=True)
        break
        time.sleep(3)


if __name__ == '__main__':
    main()
