import json
import requests

def make_session(hook_url):
    s = requests.Session()
    return Slack(hook_url, s)

class Slack:
    def __init__(self, hook_url, session):
        self._slack_url = hook_url
        self._session = session

    def send_message(self, username='FAForever', text=''):
        return self._session.post(self._slack_url,
                                  data=json.dumps(dict(
                                      username=username,
                                      text=text)))
