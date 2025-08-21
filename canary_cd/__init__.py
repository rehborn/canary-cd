__version__ = '0.0.0'

import os
from tomllib import load as toml_load
from importlib import metadata

try:
    __version__ = metadata.version('canary-cd')
except metadata.PackageNotFoundError:
    if os.path.isfile("pyproject.toml"):
        data = toml_load(open("pyproject.toml", "rb"))
        __version__ = data['project']['version']
