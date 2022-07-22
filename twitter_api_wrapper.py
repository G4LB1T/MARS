import requests
from utils import twitter_bearer_token, twitter_search_url, verify_ssl
import time


def make_bearer_oauth(r):
    """
    Method required by bearer token authentication.
    """

    r.headers["Authorization"] = f"Bearer {twitter_bearer_token}"
    r.headers["User-Agent"] = "v2RecentSearchPython"

    return r


def do_search(query_params, max_res_len):
    """
    Sends the HTTP API request with query_params, returns at most max_res_len
    """

    response = requests.get(twitter_search_url, auth=make_bearer_oauth, params=query_params, verify=verify_ssl)
    if response.status_code != 200:
        try:
            print(f"TImer reset at:{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(int(response.headers['x-rate-limit-reset'])))}")
        except:
            print('unknown error')
        raise Exception(response.status_code, response.text)
    elif 'data' not in response.json():
        # a bit of a cheat, might break some stuff
        return {}
    results = response.json()['data']

    while 'meta' in response.json() and 'next_token' in response.json()['meta'] and len(results) <= max_res_len:
        next_token = response.json()['meta']['next_token']
        query_params['next_token'] = next_token
        try:
            response = requests.get(twitter_search_url, auth=make_bearer_oauth, params=query_params, verify=verify_ssl)
        except:
            print(f'Twitter request failed with HTTP code {response.status_code}, reset header is'
                  '{response.headers["x-rate-limit-reset"]}')
        if 'data' in response.json():
            results += (response.json()['data'])

    return results
