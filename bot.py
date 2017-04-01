import praw
import re
import urllib.request
import urllib.error
import json
import http.client
import getpass

BARE_URLS = (
    'bit.ly',
    'tinyurl.com',
    'goo.gl',
    'youtu.be',
    'youtube.com'
)

DOMAIN_ALLOWED_CHARS = '[a-z]'  # Characters allowed in the domain name
PATH_ALLOWED_CHARS = '[a-z0-9%=./+-]'  # Characters allowed in the path

URL_RE = re.compile(
    (
        r'(?:[(,.[]|^)?((?:(?:(?:https?:)?//|www\.)(?:{1}+\.)'
        r'*{1}+|{0})(?:\/{2}*?\??{2}*?#?{2}*?))(?:[),.\]]|$)'
    ).format('|'.join(BARE_URLS).replace('.', r'\.'),
             DOMAIN_ALLOWED_CHARS, PATH_ALLOWED_CHARS),
    re.IGNORECASE)


def get_urls(comment, default_protocol='http:'):
    for match in map(URL_RE.search, comment.split()):
        if match:
            url = match.group(1)
            if url.startswith('//'):
                yield default_protocol + url
            elif url.startswith('https://') or url.startswith('http://'):
                yield url
            else:
                yield default_protocol + '//' + url


def quote(url):
    return url[:9] + urllib.parse.quote(url[9:])


YOUTUBE_RE = re.compile(
    r'^(?:https?:?/?/?|//?)??(?:www\.)?youtu(?:\.be/|be\.co(?:m|\.(?:uk))(?:/[^'
    r'?#]*)\?(?:v=|[^&#]*&v=))([a-z0-9\-_]{11})(?:&.*|#.*)?$', re.IGNORECASE
)

COMMENT_TEMPLATE = "Don't click on the link! The link may be an attempted " \
                   "rick roll.\n\nI am a bot. I was made by u/lakhanmankan" \
                   "i. [Source code](https://github.com/lakhanmankani/anti" \
                   "-rick-roll-bot)"


def rick_rolls_in_text(id_, body):
    print(body)
    for url in get_urls(body):
        try:
            req = urllib.request.Request(quote(url), method='HEAD')
            req.add_header('User-Agent', 'Anti Rick Roll Bot')
            url = urllib.request.urlopen(req).geturl()
        except urllib.error.HTTPError:
            continue
        except urllib.error.URLError:
            continue
        except http.client.BadStatusLine:
            continue

        video_id = YOUTUBE_RE.match(url)
        if video_id is None:
            continue  # No video id in url or not a YouTube link
        video_id = video_id.group(1)
        api_link = 'https://www.googleapis.com/youtube/v3/videos?id=' + \
                   video_id + '+&key=' + google_api_key + \
                   '&fields=items(snippet(title))&part=snippet'
        response = urllib.request.urlopen(api_link)
        data = json.loads(response.read().decode())
        video_title = data['items'][0]['snippet']['title'].lower()

        for word in key_words:
            if word in video_title:
                id_.reply(COMMENT_TEMPLATE)
                rick_rolls_found.add(id_)
                break

def main():
    reddit_client_id = getpass.getpass("Enter your reddit client id: ")
    reddit_client_secret = getpass.getpass("Enter your reddit client secret: ")
    google_api_key = getpass.getpass("Enter your google api key: ")
    reddit_username = input("Enter your reddit username: ")
    reddit_password = getpass.getpass("Enter your reddit password: ")

    reddit = praw.Reddit(client_id=reddit_client_id,
                         client_secret=reddit_client_secret,
                         user_agent='Anti Rick Roll Bot',
                         username=reddit_username,
                         password=reddit_password)

    key_words = ("rick roll", "rick astley", "never gonna give you up")

    try:
        with open('replied_to.txt', 'r+') as f:
            rick_rolls_found = {line.rstrip('\n') for line in f}
    except FileNotFoundError:
        rick_rolls_found = set()

    subreddit = reddit.subreddit('all')
    for submission in subreddit.hot(limit=1000):
        post_title = submission.title
        for word in key_words:
            if word in post_title.lower() and post_title not in rick_rolls_found:
                rick_rolls_found.add(post_title)

        rick_rolls_in_text(submission, submission.selftext)

        if submission.media is not None:
            media_title = submission.media['oembed']['title']
            found = False
            for word in key_words:
                if word in media_title.lower() and post_title not in \
                        rick_rolls_found:
                    found = True
            if found:
                    rick_rolls_found.add(submission)

        comments = submission.comments
        submission.comments.replace_more(limit=0)
        comment_queue = submission.comments[:]
        for comment in comment_queue:
            if comment in rick_rolls_found:
                continue
            comment_body = comment.body
            rick_rolls_in_text(comment, comment_body)
            comment_queue.extend(comment.replies)

    with open('replied_to.txt', 'w') as f:
        for rick_roll in rick_rolls_found:
            f.write(str(rick_roll) + '\n')

