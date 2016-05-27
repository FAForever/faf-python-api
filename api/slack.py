import json
import requests

def make_session(hook_url):
    s = requests.Session()
    return Slack(hook_url, s)

class Slack:
    """
    Slack model for API. It collects the slack URL and session.

    .. py:attribute:: slack_url

        The slack URL

        :type: str

    .. py:attribute:: session

        The session

        :type: str

    """
    def __init__(self, hook_url, session):
        self._slack_url = hook_url
        self._session = session

    def send_message(self, username='FAForever', text=''):
        """
        Slack method to send message.

        :param str username: Username for Slack
        :param str text: Message to send out

        """
        return self._session.post(self._slack_url,
                                  data=json.dumps(dict(
                                      username=username,
                                      text=text)))
