import json
from datetime import datetime
import logging

from bot_analytics import do_hunting_for_gist
from github_api_wrapper import post_gist

logging.basicConfig(level=logging.INFO)

if __name__ == '__main__':
    post_gist(f'Crypto fraud bots on Twitter {datetime.today().strftime("%Y-%m-%d %H:%M:%S")}',
              'A list of users and affiliated email and forms addresses, all possibly linked to crypto fraud. Do note '
              'that this data is provided as is and there might be false positives',
              json.dumps(do_hunting_for_gist(1250), indent=4))
