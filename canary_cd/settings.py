"""Settings"""
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from fastapi.logger import logger

load_dotenv()

BASE_DIR = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = Path(os.getenv('DATA_DIR', BASE_DIR / 'data'))

REPO_CACHE = Path(DATA_DIR / 'repositories')
PAGES_CACHE = Path(DATA_DIR / 'pages')
DYN_CONFIG_CACHE = Path(DATA_DIR / 'dynamic')

STATIC_BACKEND_NAME = os.environ.get('STATIC_BACKEND_NAME', 'http://static-pages')

SQLITE = 'sqlite:///{}/database.sqlite'.format(DATA_DIR.absolute())

# generate salt
SALT = os.getenv("SALT", None)
if SALT is None:
    from canary_cd.utils.crypto import generate_salt
    SALT = generate_salt()
    with open('.env', 'w', encoding='utf-8') as env:
        env.write(f'SALT={SALT}\n')


log_formatter = logging.Formatter("%(levelname)s: %(asctime)s %(name)s: %(message)s")
loglevel = logging.getLevelName(os.environ.get('LOGLEVEL', 'DEBUG'))

# gunicorn logging settings
gunicorn_logger = logging.getLogger('gunicorn.error')
logger.handlers = gunicorn_logger.handlers
logger.setLevel(loglevel)

# create custom handler for INFO msg
stdout_handler = logging.StreamHandler(sys.stdout)
stdout_handler.setLevel(loglevel)
stdout_handler.setFormatter(log_formatter)

logger.addHandler(stdout_handler)
