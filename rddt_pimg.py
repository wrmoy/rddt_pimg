import httplib
import json
import logging
import re
import string
from urlparse import urlparse
from sys import exit

# Consts
PICTURE_EXTENSIONS = ['jpg', 'png', 'bmp', 'jpeg', 'gif']

# Set up logging
logging.basicConfig(filename='debug.log', format='%(asctime)s %(message)s',
                    level=logging.DEBUG)

# This will eventually be read from a config file
subreddit = 'earthporn'
is_quality_enforced = False
is_resolution_enforced = False
min_res_X = 1024 # TODO
min_res_Y = 768

# Initiate server connection
rddt_conn = httplib.HTTPConnection('www.reddit.com')
# Send request to server for link data
rddt_conn.putrequest('GET', '/r/' + subreddit + '.json')
rddt_conn.putheader('User-Agent', 'rddt_pimg v0.1 by wrmoy')
rddt_conn.putheader('Accept', 'text/plain')
rddt_conn.putheader('Accept', 'text/html')
rddt_conn.endheaders()
rddt_resp = rddt_conn.getresponse()
logging.debug('Reddit reponse was %s %s', rddt_resp.status, rddt_resp.reason)
if rddt_resp.status != 200:
    logging.error('Reddit response was not OK, closing')
    rddt_conn.close()
    exit(1)

# Parse JSON data
raw_data = rddt_resp.read()
rddt_conn.close()
if raw_data is '':
    logging.error('response data is empty, closing')
    exit(1)
json_data = json.loads(raw_data)

# Some early sanity checking
if 'error' in json_data:
    logging.error('error %s when grabbing JSON, closing', json_data['error'])
    exit(1)
if 'data' not in json_data:
    logging.error('\'data\' field not found in JSON, closing')
    exit(1)
if 'children' not in json_data['data']:
    logging.error('\'children\' field not found in JSON, closing')
    exit(1)
for entry in json_data['data']['children']:
    if 'data' not in entry:
        logging.error('\'entry.children\' field not found in JSON, closing')
        exit(1)
    for needed_field in ['title', 'url', 'score', 'ups', 'downs',
                         'is_self']:
        if needed_field not in entry['data']:
            logging.error('\'data.%s\' field not found in JSON, closing', 
                          needed_field)
            exit(1)

# Determine which image to pull
max_score = 0;
image_url = ''
parsed_img_url = ''
image_title = ''
for entry in json_data['data']['children']:
    logging.debug('Looking at entry %s', entry['data']['title'])
    # ignore self posts
    if entry['data']['is_self'] is True:
        logging.debug('is a self post')
        continue
    # ignore non-HTTP image locations
    parsed_img_url = urlparse(entry['data']['url'])
    if parsed_img_url.scheme != 'http':
        logging.debug('is not HTTP')
        continue
    # ignore anything without a proper extension
    url_extension = string.lower(entry['data']['url']).split(".")[-1]
    if url_extension not in PICTURE_EXTENSIONS:
        logging.debug('does not have an image extension')
        continue
    # ignore anything below a 3:1 vote ratio
    if is_quality_enforced is True:
        logging.info('checking quality of %s', entry['data']['title'])
        if entry['data']['ups'] < entry['data']['downs']*3:
            logging.debug('does not have enough upvotes')
            continue
    # ignore anything but the highest scoring
    if int(entry['data']['score']) < max_score:
        logging.debug('does not have a high enough score')
        continue
    # ignore entries that are below the res standards
    if is_resolution_enforced is True: # do regex here for picture size
        logging.info('checking resolution of %s', entry['data']['title'])
        result = re.search("[<(\[](?P<resX>[0-9]+?)x(?P<resY>[0-9]+?)[>)\]]",
                           entry['data']['title'])
        if not result:
            logging.debug('does not have a correct resolution tag')
            continue # ignore entries without correct resolution tags
        if int(result.group('resX')) < min_res_X:
            logging.debug('X resolution is smaller than %i', min_res_X)
            continue
        if int(result.group('resY')) < min_res_Y:
            logging.debug('Y resolution is smaller than %i', min_res_Y)
            continue
        logging.debug('%s is a %i by %i image', entry['data']['title'],
                       int(result.group('resX')), int(result.group('resY')))
    # set the picture to be downloaded
    max_score = int(entry['data']['score'])
    image_url = entry['data']['url']
    image_title = entry['data']['title']
    logging.debug('%s is a possible match', image_title)
    logging.debug('%s may be downloaded', image_url)

# Connect to image server
parsed_img_url = urlparse(image_url)
img_conn = httplib.HTTPConnection(parsed_img_url.netloc)
# Send request to server for image data
img_conn.putrequest('GET', parsed_img_url.path)
img_conn.putheader('User-Agent', 'rddt_pimg v0.1 by wrmoy')
img_conn.putheader('Accept', 'image/*')
img_conn.endheaders()
img_resp = img_conn.getresponse()
logging.debug('Image server reponse was %s %s', img_resp.status, 
              img_resp.reason)
if img_resp.status != 200:
    logging.error('Reddit response was not OK, closing')
    img_conn.close()
    exit(1)

# Grab image data
raw_data = img_resp.read()
img_conn.close()
if raw_data is '':
    logging.error('response data is empty, closing')
    exit(1)
# TODO: handle the image data

logging.info('Finished up')
