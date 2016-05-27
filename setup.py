from distutils.core import setup

import api

setup(
    name='Forged Alliance Forever API',
    version=api.__version__,
    packages=['api'],
    url='http://www.faforever.com',
    license=api.__license__,
    author=api.__author__,
    author_email=api.__contact__,
    description='API project'
)
