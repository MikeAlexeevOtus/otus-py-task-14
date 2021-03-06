import asyncio
import hashlib
import logging
import os
import sys
import time

import aiohttp
import aiofiles
import aiofiles.os
from bs4 import BeautifulSoup


BASE_URL = 'https://news.ycombinator.com'
SLEEP_SECONDS = 5
MAX_REQUESTS = 5

logging.basicConfig(level=logging.INFO)


def get_logger():
    return logging.getLogger()


async def get_page_content(url, semaphore):
    await semaphore.acquire()
    get_logger().info(f'do request to {url}')
    try:
        async with aiohttp.ClientSession() as session:
            resp = await session.request('GET', url)
            return await resp.read()
    finally:
        get_logger().info('semaphore released')
        semaphore.release()


async def save_page_content(url, output_folder, semaphore):
    get_logger().info(f'save page {url}')
    content = await get_page_content(url, semaphore)
    hash_ = hashlib.sha256(url.encode()).hexdigest()
    output_path = os.path.join(output_folder, hash_)
    async with aiofiles.open(output_path, 'wb') as f:
        await f.write(content)


async def save_pages_content_from_comments(url, output_folder, semaphore):
    get_logger().info(f'save from comments {url}')
    comments_content = await get_page_content(url, semaphore)
    external_links = parse_comments_page(comments_content)
    if external_links:
        get_logger().info(f'external_links: {external_links}')
        todo = [save_page_content(url_, output_folder, semaphore) for url_ in external_links]
        await asyncio.wait(todo)


def parse_comments_page(page_content):
    soup = BeautifulSoup(page_content, 'html.parser')
    comments_tree = soup.find('table', class_='comment-tree')
    if not comments_tree:
        return []

    out_links = []
    for a_elem in comments_tree.find_all('a'):
        link = a_elem['href']
        if not link.startswith('http'):
            continue
        out_links.append(link)

    return out_links


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


async def create_folders(output_folder, news_ids):
    todo = [aiofiles.os.mkdir(os.path.join(output_folder, str(id_)))
            for id_ in news_ids]

    await asyncio.wait(todo)


async def do_requests(already_seen_news, output_folder):
    semaphore = asyncio.Semaphore(MAX_REQUESTS)
    main_page_content = await get_page_content(BASE_URL + '/newest', semaphore)
    news_ids_with_urls = {id_: url for id_, url in parse_main_page(main_page_content).items()
                          if id_ not in already_seen_news}

    if not news_ids_with_urls:
        get_logger().info('no new news')
        return

    await create_folders(output_folder, news_ids_with_urls.keys())
    news_ids_with_comment_urls = {id_: f'{BASE_URL}/item?id={id_}' for id_ in news_ids_with_urls}
    todo = [save_page_content(url, os.path.join(output_folder, str(id_)), semaphore)
            for id_, url in news_ids_with_urls.items()]

    todo += [save_pages_content_from_comments(url, os.path.join(output_folder, str(id_)), semaphore)
             for id_, url in news_ids_with_comment_urls.items()]

    await asyncio.wait(todo)
    already_seen_news.update(news_ids_with_urls.keys())


def main():
    already_seen_news = set()
    out_folder = sys.argv[1]
    os.makedirs(out_folder, exist_ok=True)
    while True:
        asyncio.run(do_requests(already_seen_news, out_folder), debug=True)
        time.sleep(SLEEP_SECONDS)


if __name__ == '__main__':
    main()
