"""
Run the server locally
"""

from api import app, api_init

# Load Database config
DATABASE = dict(
    engine=  "playhouse.pool.PooledMySQLDatabase",
    name=    "bob",
    user=    "the",
    passwd=  "dinosaur",
    max_connections= 32, stale_timeout=600)

app.config.from_object(__name__)

api_init()

# By default, run debug mode
app.debug = True
app.run(port=8080)