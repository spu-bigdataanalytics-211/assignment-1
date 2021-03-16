"""
Image Handler Functions
=========================
A set of functions to download data, images, and process images.

Avalable functions:

- create_config_file
- get_images_list
- get_images_df
- download_unsplash_json
- download_images
- create_thumbnail

Usage:

Import first.
>>> import data_prep

Download unsplash meta file as json to data/ json folder.
>>> data_prep.download_unsplash_json()

Get pandas dataframe.
>>> data_prep.get_images_df()

Download images to data/ images folder.
>>> data_prep.download_images()

Create thumbnail images from existing images in data/ images folder.
>>> data_prep.create_thumbnail()

"""
import configparser
import datetime
import functools
import json
import os
import pathlib
import sys

import pandas as pd
import requests
from PIL import Image, UnidentifiedImageError


def add_keyboard_interrupt(func):
    """
    Decorator to detect keyboard interrupts by user.
    """
    @functools.wraps(func)
    def wrapper():
        try:
            func()
        except KeyboardInterrupt:
            print('Operation interrupted by user.')
    return wrapper


def progressbar(it, prefix="", size=60, file=sys.stdout):
    """
    Progress bar function for long processes.
    it      : iterator
    prefix  : custom string to add on progress bar.
    size    : size of the progress bar
    file    : where the progress bar runs.
    For more information, check the original answer from
    stackoverflow, https://stackoverflow.com/a/34482761.
    """
    count = len(it)

    def show(j):
        x = int(size*j/count)
        file.write("%s[%s%s] %i/%i\r" %
                   (prefix, "#"*x, "."*(size-x), j, count))
        file.flush()
    show(0)
    for i, item in enumerate(it):
        yield item
        show(i+1)
    file.write("\n")
    file.flush()


def create_config_file(access_key='', secret_key=''):
    """
    Creates a config file for secret stuff. Option to provide keys.

    Parameters:
    access_key:
        Unsplash access key.
    secret_key:
        Unsplash secret key.
    """
    config = configparser.ConfigParser()

    if not os.path.exists('config.ini'):
        config['UNSPLASH'] = dict(access_key=access_key, secret_key=secret_key)

        with open('config.ini', 'w+') as configfile:
            config.write(configfile)

        print('A new file with name `config.ini` created. Please fill your access_key.')
    else:
        config.read('config.ini')
        client_id = config.get('UNSPLASH', 'access_key', fallback='no_key')

        if client_id in (None, '', 'no_key'):
            print('No key is provided. Please fill your key.')
        else:
            print('Config file setup properly.')


def get_images_list():
    """
    Get a list of all images from `data/json` folder.
    """
    images_list = []

    # find all images
    json_files = sorted(pathlib.Path('data/json').glob('data*.json'))

    # open files and collect all dictionaries
    for json_file in json_files:
        with open(json_file, 'r') as reader:
            raw_json = json.load(reader)
            images_list.extend(raw_json)

    return images_list


def get_images_df():
    """
    Returns a dataframe of the json in data/json folder.
    """
    images_list = get_images_list()

    return pd.DataFrame(images_list)


@add_keyboard_interrupt
def download_images(quality='regular'):
    """
    Downloads images from given image quality.

    Parameters:
    quality : Options are raw | full | regular | small | thumb

    For more information about quality, check unsplash documentation at
    https://unsplash.com/documentation#example-image-use
    """
    images_list = get_images_list()

    for image in progressbar(it=images_list, prefix='Downloading '):
        # build necessary information
        id = image['id']
        url_quality = image['urls'][quality]
        image_path = pathlib.Path(f'data/images/{id}-{quality}.jpg')

        # download images -  this is where downloading happens
        response = requests.get(url_quality, stream=True)
        if response.status_code == 200:
            with open(image_path, 'wb+') as f:
                f.write(response.content)


def download_unsplash_json():
    """
    Downloads images meta information from unsplash website as JSON.
    """
    images_list = []

    config = configparser.ConfigParser()

    if len(config.read('config.ini')) == 0:
        raise Exception('No config file found, you must create config first.')

    client_id = config.get('UNSPLASH', 'access_key', fallback='no_key')

    if client_id in (None, '', 'no_key'):
        raise Exception('No key is provided, please get your key.')

    try:
        for cnt in progressbar(it=range(0, 1500, 30), prefix='Downloading '):
            response = requests.get(
                f'https://api.unsplash.com/photos/random/?count=30',
                headers={
                    'Accept-Version': 'v1',
                    'Authorization': f'Client-ID {client_id}'
                },
                stream=True
            )

            if response.status_code == 200:
                raw_json = json.loads(response.content)
                images_list.extend(raw_json)

            elif response.status_code == 403:
                print('Api limit reached!')
                break
            else:
                print('Something went wrong!')
                break

    except KeyboardInterrupt:
        print('Operation interrupted by user.')
    except Exception as ex:
        print('Something went wrong', ex)
    finally:
        append_timestamp = round(datetime.datetime.now().timestamp())
        with open(f'data/json/data_{append_timestamp}.json', 'w+') as writer:
            json.dump(images_list, writer, indent=4)


@add_keyboard_interrupt
def create_thumbnail(size=(128, 128)):
    """
    Create resized version of the image path given, with the same name 
    extended with _thumbnail.
    """
    images_path_list = list(pathlib.Path(
        f'data/images').glob('**/*[!thumbnail].jpg'))
    Image.MAX_IMAGE_PIXELS = None

    for image_path in progressbar(it=images_path_list, prefix='Processing '):
        try:
            # create thumbnail
            image = Image.open(image_path.absolute())
            image.thumbnail(size)

            # save thumbnail
            new_filename = image_path.parent.joinpath(
                '{0}-thumbnail{1}'.format(image_path.stem, image_path.suffix))
            image.convert('RGB').save(new_filename)
        except UnidentifiedImageError:
            pass
