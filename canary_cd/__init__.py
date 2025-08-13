__version__ = '0.0.0'

from tomllib import load as toml_load

try:
    data = toml_load(open("pyproject.toml", "rb"))
    __version__ = data['project']['version']
except FileNotFoundError:
    print("pyproject.toml not found")
    exit(1)
