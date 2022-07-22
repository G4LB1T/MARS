import requests
import re
from twitter_api_wrapper import do_search, make_bearer_oauth
from utils import verify_ssl
import logging

if not verify_ssl:
    requests.packages.urllib3.disable_warnings()

suspicious_domains = [
    'docs.google.com/forms/',
    'forms.gle',
    't.me',
    'instagram.com',
    'wa.me',
    'twitter.com/messages/compose'
]


def find_tweets_with_keywords(keyword='metamask', search_tweets_limit=1500):
    """
    Returns leads to be explored - tweets mentioning the term "metamask" with URLs in their body,
    returns at most max_res_len
    """
    return do_search({'query': keyword, 'tweet.fields': 'author_id,entities,id,conversation_id'}, search_tweets_limit)


def check_google_forms_link_in_tweet(tweet):
    """
    Checks if the tweet contains a link to Google form in multiple ways
    """
    if 'entities' in tweet:
        if 'urls' in tweet['entities']:
            for url in tweet['entities']['urls']:
                if 'unwound_url' in url:
                    if any(domain in url['unwound_url'] for domain in suspicious_domains):
                        return True
                elif 'expanded_url' in url:
                    if any(domain in url['expanded_url'] for domain in suspicious_domains):
                        return True
    return False


def check_email_in_tweet(tweet):
    """
    Checks if a tweet contains an email address as part of its text
    """
    if len(re.findall(r'[\w\.-]+@[\w\.-]+\.[\w]+', tweet['text'])) > 0:
        return True
    else:
        return False


def get_username_from_author_id(author_id):
    """
    Translates author_id to username, requires in order to do followup querys
    """
    tweet_fields = "tweet.fields=author_id,username"
    url = "https://api.twitter.com/2/users?{}".format(f'ids={author_id}')
    response = requests.request("GET", url, auth=make_bearer_oauth, verify=verify_ssl)
    if response.status_code != 200:
        raise Exception(
            "Request returned an error: {} {}".format(
                response.status_code, response.text
            )
        )
    return response.json()['data'][0]['username']


def get_sus_author_ids(tweets):
    """
  Returns author id list of users taking part in conversation associated with keyword
  which also mention a google form or gmail address
  """
    sus_author_ids = set()
    for tweet in tweets:
        if check_email_in_tweet(tweet) or check_google_forms_link_in_tweet(tweet):
            sus_author_ids.add(tweet['author_id'])
    return sus_author_ids


def get_sus_usernames(tweets):
    """
  Abstraction on top of get_sus_author_ids which will return usernames
  instead of author ids
  """
    sus_author_ids = get_sus_author_ids(tweets)
    sus_usernames = []

    for author_id in sus_author_ids:
        sus_usernames.append(get_username_from_author_id(author_id))
    return sus_usernames


def get_user_tweets(username):
    """
    Retrieving tweets by a specific username
    """
    return do_search({'query': f'from:{username}', 'tweet.fields': 'author_id,entities,id,in_reply_to_user_id'}, 100)


def cluster_tweets(tweets):
    """
  Remove links and usernames then try to aggregate tweets by exact match
  Return a dictionary with frequency map
  """
    freq_map = {}
    for tweet in tweets:
        if check_email_in_tweet(tweet) or check_google_forms_link_in_tweet(tweet):
            text = tweet['text']
            text = re.sub('@[^\s]+', '', text).strip()
            text = re.sub('https[^\s]+', '', text).strip()
            if text in freq_map:
                freq_map[text] += 1
            else:
                freq_map[text] = 1
    return freq_map


def get_evidence_links(tweets):
    """
    Extract forms links from tweets
    """
    freq_map = {}
    for tweet in tweets:
        if 'entities' in tweet:
            extracted_url = ''
            if 'urls' in tweet['entities']:
                for url in tweet['entities']['urls']:
                    if 'unwound_url' in url:
                        if any(domain in url['unwound_url'] for domain in suspicious_domains):
                            extracted_url = url['unwound_url'].lower()
                    elif 'expanded_url' in url:
                        if any(domain in url['expanded_url'] for domain in suspicious_domains):
                            extracted_url = url['expanded_url'].lower()
            if extracted_url:
                if extracted_url in freq_map:
                    freq_map[extracted_url] += 1
                else:
                    freq_map[extracted_url] = 1
    return freq_map


def get_evidence_email(tweets):
    """
  Extract email addresses
  """
    freq_map = {}
    for tweet in tweets:
        if check_email_in_tweet(tweet):
            text = tweet['text']
            match = re.search(r'[\w\.-]+@[\w\.-]+\.[\w]+', text)
            try:
                text = match.group(0).lower()
            except:
                text = 'regex email extraction failure'
            if text in freq_map:
                freq_map[text] += 1
            else:
                freq_map[text] = 1
    return freq_map


def do_hunting_for_gist(init_search_size=1500):
    """
    Main function -
    Start by getting tweets which might be related to frauds in replies
    Then Search in replies for fraudsters and try to aggregate their tweets
    """
    all_email_addresses = set()
    all_suspicious_links = set()
    all_sus_users = {}

    logging.info('Collecting potential tweets...')
    sus_tweets = find_tweets_with_keywords('metamask', init_search_size)
    logging.info('DONE!')
    logging.info('Collecting potential usernames...')
    sus_users = get_sus_usernames(sus_tweets)
    logging.info('DONE!')

    logging.info('Pivoting, collecting users tweets...')
    for username in sus_users:
        logging.info(f'Analyzing user {username}...')
        all_sus_users[username] = {}

        tweets = get_user_tweets(username)
        clustered_tweets = dict(sorted(cluster_tweets(tweets).items()))
        all_sus_users[username]['clustered_tweets'] = clustered_tweets

        evidence_gmail = get_evidence_email(tweets)
        all_sus_users[username]['email_accounts'] = evidence_gmail
        for email in evidence_gmail:
            all_email_addresses.add(email.lower())

        evidence_links = get_evidence_links(tweets)
        all_sus_users[username]['forms_links'] = evidence_links

        for link in evidence_links:
            all_suspicious_links.add(link)
    logging.info('DONE!')

    return {'Suspicious email addresses': sorted(list(all_email_addresses)),
            'Suspicious links': sorted(list(all_suspicious_links)),
            'Suspicious usernames': sorted(list(all_sus_users.keys())),
            'Details': all_sus_users
            }
