"""
Run the server locally
"""

from api import app, api_init

app.config.from_object('config')

api_init()

# By default, run debug mode
app.debug = True
app.run(port=8080)