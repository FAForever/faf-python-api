"""
Phusion Passenger WSGI entrypoint
"""

import sys

if sys.version_info.major != 3:
    raise RuntimeError(
        "FAForever API requires python 3.\n"
        "Refer to passenger documentation on how to accomplish that.\n"
        "Good luck.")

from api import app, api_init

import sys
import logging
logger = logging.getLogger()

logger.addHandler(logging.StreamHandler(stream=sys.stderr))

app.config.from_object('config')

api_init()

application = app
