import requests
import json
import logging
from utils import github_api, github_api_token, verify_ssl


def post_gist(gist_name, desc, content):
    logging.info('Uploading gist...')
    # form a request URL
    url = github_api + "/gists"
    print("Request URL: %s" % url)

    # print headers,parameters,payload
    headers = {'Authorization': 'token %s' % github_api_token}
    params = {'scope': 'gist'}
    payload = {"description": desc, "public": False, "files": {gist_name: {"content": str(content)}}}

    # make a requests
    res = requests.post(url, headers=headers, params=params, data=json.dumps(payload), verify=verify_ssl)

    # print response --> JSON
    print(res.status_code)
    print(res.url)
    print(res.text)
    j = json.loads(res.text)
    logging.info('DONE!')
