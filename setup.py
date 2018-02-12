from setuptools import setup, find_packages
from sinopey import __version__,\
    __author__, \
    __email__, \
    __license__,\
    __description__

setup(
    name='sinopey',
    version=__version__,
    packages=find_packages(),
    url='https://github.com/bkanuka/sinopey',
    license=__license__,
    author=__author__,
    author_email=__email__,
    description=__description__,
    install_requires=['requests', 'PyYAML']
)