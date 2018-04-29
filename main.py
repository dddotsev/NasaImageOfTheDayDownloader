from os import makedirs
from os.path import exists

from time import sleep
from urllib.request import urlopen
from urllib.error import URLError
from json import load, dumps

from bs4 import BeautifulSoup
from progressbar import ProgressBar

from PIL import Image
from PIL import ImageFont
from PIL import ImageDraw

from io import BytesIO

MAIN_URL = 'https://apod.nasa.gov/apod/'
MAIN_PAGE = 'archivepix.html'

DOWNLOAD_PATH = '/data/data/com.termux/files/home/storage/external-1/NasaImages/'
DOWNLOADED_LIST_FILE_PATH = 'downloaded.txt'
IMAGE_NOT_FOUND_FILE_PATH = 'image_not_found.txt'

LOADED_IMAGE_LINKS_FILE_PATH = 'loaded_links.json'

IMAGE_EXTENSIONS = ['jpg', 'jpeg', 'bmp', 'png', 'tiff', 'tif']

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
                img_src = img.get('src')
                found_image_here = False

                if is_image_link(parent_href):
                    found_image = True
                    found_image_in_a = True
                else:
                    parent_href = None

                if is_image_link(img_src):
                    found_image = True
                    found_image_in_a = True
                else:
                    img_src = None

                if found_image_in_a:
                    image_links.append((page, parent_href, img_src))

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
        page, href, src = link

        downloaded = False

        if href is not None:
            downloaded = download_image(page, href)

        if src is not None and not downloaded:
            downloaded = download_image(page, src)

        downloaded_list_file.write('\n')
        downloaded_list_file.write(page)
        downloaded_list_file.flush()
        bar_progress += 1
        progressbar.update(bar_progress)

    downloaded_list_file.close()

def download_image(page, link):
    date = page[2:-5]
    image_name = date + link[-1 * (len(link) - link.rfind('.')):]
    path = DOWNLOAD_PATH + image_name

    if not OVERWRITE_EXISTING and exists(path):
        return True

    image_req = get_request(MAIN_URL + link)
    if image_req == False:
        return False


    imageBytes = BytesIO(image_req)

    img = Image.open(imageBytes)
    draw = ImageDraw.Draw(img)
    font = ImageFont.truetype("Roboto-Black.ttf", 64)
    draw.text((0, 0), date, (255), font)
    img.save(path)

    return True

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
        page, _, _ = link;

        if page not in downloaded and page not in not_found and not page == '' and not page.isspace():
            not_downloaded.append(link)

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
            if ex.reason == "Not found":
                return False
            elif retry < REQUEST_REPEAT_COUNT:
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


def main(take, skip, loaded):
    if not exists(DOWNLOAD_PATH):
        makedirs(DOWNLOAD_PATH)

    if not exists(DOWNLOADED_LIST_FILE_PATH):
        open(DOWNLOADED_LIST_FILE_PATH, "w+").close()

    if not exists(IMAGE_NOT_FOUND_FILE_PATH):
        open(IMAGE_NOT_FOUND_FILE_PATH, "w+").close()

    links = None

    if not loaded:
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
    else:
        print('')
        print('Loading links from file')
        links = load_links_from_file()
        print('')
        print('')
        print('Exclude downloaded')
        links = exclude_from_links(links)

    print('')
    print('')
    print('Downloading images:')
    download_images(links)

    return

main(10, 0, False)
