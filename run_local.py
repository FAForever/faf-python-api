#!/usr/bin/env python3
"""
Run the server locally
"""

from api import app, api_init

app.config.from_object('config')

api_init()

# By default, run debug mode
app.debug = True
app.run(host='0.0.0.0', port=8080)
