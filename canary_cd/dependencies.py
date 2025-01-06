"""Dependencies"""
from typing import Annotated

from fastapi import Depends
from fastapi import HTTPException
from fastapi.security import OAuth2PasswordBearer

# from src.database import Database, select
# from src.models.config import Config
# from src.settings import SALT

# pylint: disable=wildcard-import,unused-wildcard-import
from canary_cd.settings import *
from canary_cd.database import *
from canary_cd.models import *

from canary_cd.utils.crypto import CryptoHelper

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
ch = CryptoHelper(SALT)

async def validate_admin(token: Annotated[str, Depends(oauth2_scheme)], db: Database):
    """Validate Bearer for root"""
    root_key = db.exec(select(Config).where(Config.key == 'ROOT_KEY')).first()

    if not root_key:
        raise HTTPException(status_code=400, detail="ROOT_KEY not set")


    if len(root_key.value) == 0 or not ch.hash_verify(token, root_key.value):
        raise HTTPException(status_code=400, detail='Unauthorized')
