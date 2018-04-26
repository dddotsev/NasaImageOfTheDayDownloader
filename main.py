from os import makedirs
from os.path import exists

from time import sleep
from urllib.request import urlopen, urlretrieve
from urllib.error import URLError
from json import load, dumps

from bs4 import BeautifulSoup
from progressbar import ProgressBar

MAIN_URL = 'https://apod.nasa.gov/apod/'
MAIN_PAGE = 'archivepix.html'

DOWNLOAD_PATH = 'Images/'
DOWNLOADED_LIST_FILE_PATH = 'downloaded.txt'
IMAGE_NOT_FOUND_FILE_PATH = 'image_not_found.txt'

LOADED_IMAGE_LINKS_FILE_PATH = 'loaded_links.json'

IMAGE_EXTENSIONS = ['jpg', 'jpeg', 'bmp', 'png', 'tiff', 'tif', 'gif']

REQUEST_REPEAT_COUNT = 15
REQUEST_REPEAT_INITIAL_SECONDS = 5
OVERWRITE_EXISTING = False


def get_image_pages(take, skip):
    html = get_request(MAIN_URL + MAIN_PAGE)
    soup = get_html_soup(html)

    anchors = soup.find('b').findAll("a")
    links = []

    if not take == 0 or not skip == 0:
        anchors = anchors[skip:skip+take]

    for anchor in anchors:
        links.append(anchor.get('href'))
    return links


def get_image_links(image_pages):
    progressbar = ProgressBar(0, len(image_pages))

    image_links = []
    image_not_found_file = open(IMAGE_NOT_FOUND_FILE_PATH, "a")

    bar_progress = 0
    for page in image_pages:
        found_image = False

        html = get_request(MAIN_URL + page)
        soup = get_html_soup(html)

        imgs = soup.findAll('img')
        for img in imgs:
            parent = img.parent
            if parent.name == 'a':
                parent_href = parent.get('href')

                if is_image_link(parent_href):
                    image_links.append((page, parent_href))
                    found_image = True
                    continue

                img_src = img.get('src')
                if is_image_link(img_src):
                    image_links.append((page, img_src))
                    found_image = True
                    continue

        if not found_image:
            image_not_found_file.write('\n')
            image_not_found_file.write(page)
            image_not_found_file.flush()

        bar_progress += 1
        progressbar.update(bar_progress)

    image_not_found_file.close()

    return image_links


def is_image_link(link):
    if link[link.rfind('.')+1:] in IMAGE_EXTENSIONS:
        return True

    return False


def download_images(image_links):
    progressbar = ProgressBar(0, len(image_links))
    downloaded_list_file = open(DOWNLOADED_LIST_FILE_PATH, "a")

    bar_progress = 0
    for link in image_links:
        image_page = link[0]
        image_link = link[1]
        image_name = image_link[image_link.rfind('/') + 1:]

        path = DOWNLOAD_PATH + image_name
        if OVERWRITE_EXISTING or not exists(path):
            download_request(MAIN_URL + image_link, path)

        downloaded_list_file.write('\n')
        downloaded_list_file.write(image_page)
        downloaded_list_file.flush()
        bar_progress += 1
        progressbar.update(bar_progress)

    downloaded_list_file.close()


def get_downloaded():
    downloaded_list_file = open(DOWNLOADED_LIST_FILE_PATH, "r")

    downloaded = []
    for line in downloaded_list_file:
        downloaded.append(line.strip())

    return downloaded


def get_not_found():
    image_not_found_file = open(IMAGE_NOT_FOUND_FILE_PATH, "r")

    not_found = []
    for line in image_not_found_file:
        not_found.append(line.strip())

    return not_found


def exclude(pages):
    downloaded = get_downloaded()
    not_found = get_not_found()
    not_downloaded = []

    for page in pages:
        if page not in downloaded and page not in not_found and not page == '' and not page.isspace():
            not_downloaded.append(page)

    return not_downloaded


def exclude_from_links(links):
    downloaded = get_downloaded()
    not_found = get_not_found()
    not_downloaded = []

    for link in links:
        image_page = link[0]
        image_link = link[1]

        if image_page not in downloaded and image_page not in not_found and not image_page == '' and not image_page.isspace():

            not_downloaded.append((image_page, image_link))

    return not_downloaded


def get_html_soup(html):
    return BeautifulSoup(html, "html.parser")


def get_request(url):
    retry = 0
    sleep_time = REQUEST_REPEAT_INITIAL_SECONDS

    while True:
        try:
            req = urlopen(url)
            if req.getcode() == 404:
                return False

            return urlopen(url).read()
        except URLError as ex:
            if retry < REQUEST_REPEAT_COUNT:
                retry += 1
                sleep_time *= 2
                print('Download retry num. ' + str(retry))
                print('Trying to get: ' + url)
                print('Retry in ' + str(sleep_time) + 'seconds')
                print(ex.args)
                print(ex.strerror)
                print(ex)
                sleep(sleep_time)
            else:
                raise


def download_request(url, path):
    retry = 0
    sleep_time = REQUEST_REPEAT_INITIAL_SECONDS

    while True:
        try:
            urlretrieve(url, path)
        except URLError as ex:
            if ex.reason == "Not Found":
                return
            elif retry < REQUEST_REPEAT_COUNT:
                retry += 1
                sleep_time *= 2
                print('Download retry num. ' + str(retry))
                print('Trying to download: ' + url)
                print('Retry in ' + str(sleep_time) + 'seconds')
                print(ex.args)
                print(ex.strerror)
                print(ex)
                sleep(sleep_time)
            else:
                raise


def write_links_to_file(links):
    image_links_file = open(LOADED_IMAGE_LINKS_FILE_PATH, "w+")

    links_json = dumps(links)
    image_links_file.write(links_json)

    image_links_file.close()


def load_links_from_file():
    image_links_file = open(LOADED_IMAGE_LINKS_FILE_PATH, "r")

    links = load(image_links_file)

    image_links_file.close()

    return links


def main(take, skip):
    if not exists(DOWNLOAD_PATH):
        makedirs(DOWNLOAD_PATH)

    if not exists(DOWNLOADED_LIST_FILE_PATH):
        open(DOWNLOADED_LIST_FILE_PATH, "w+").close()

    if not exists(IMAGE_NOT_FOUND_FILE_PATH):
        open(IMAGE_NOT_FOUND_FILE_PATH, "w+").close()

    pages = get_image_pages(take, skip)
    pages = exclude(pages)
    print("To download: " + str(len(pages)))

    print('')
    print("Getting image links:")
    links = get_image_links(pages)
    print('')
    print('')
    print('Writing links to file')
    write_links_to_file(links)

    # print('')
    # print('Loading links from file')
    # links = load_links_from_file()
    # print('')
    # print('')
    # print('Exclude downloaded')
    # links = exclude_from_links(links)
    print('')
    print('')
    print('Downloading images:')
    download_images(links)

    return

main(10, 0)
