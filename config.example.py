"""
Configuration file for the FAForever Python Web Api
"""

DATABASE = dict(
    engine=  "playhouse.pool.PooledMySQLDatabase",
    name=    "bob",
    user=    "the",
    passwd=  "dinosaur",
    max_connections= 32, stale_timeout=600)

HOST_NAME = 'dinosaur.bob'

AVATAR_FOLDER = 'avatars'
AVATAR_URL = 'http://content.faforever.com/faf/avatars'
