import shutil
from typing import Annotated

from fastapi import APIRouter, status, BackgroundTasks, Depends, HTTPException, Query, UploadFile
from sqlalchemy.orm.sync import update

from canary_cd.dependencies import *

# from src.models.project import *
# from src.models.env import *

router = APIRouter(prefix='/config',
                   tags=['Config'],
                   dependencies=[Depends(validate_admin)],
                   responses={404: {"description": "Not found"}},
                   )


# list config
@router.get('/', summary='List Config')
async def list_config(db: Database) -> list[Config]:
    config = db.exec(select(Config).where(Config.key != 'ROOT_KEY')).all()
    return config

# set config
@router.put('/', summary='Set Config')
async def config_set(data: Config, db: Database) -> Config:
    if data.key not in CONFIG_KEYS:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Invalid Config key')

    if data.key == 'ROOT_KEY':
        data.value = CryptoHelper(SALT).hash(data.value)

    q = select(Config).where(Config.key == data.key)
    config = db.exec(q).first()
    if not config:
        config = Config(key=data.key)

    config.value = data.value

    db.add(config)
    db.commit()
    db.refresh(config)

    return config


@router.delete('/{key}', summary='Unset Config')
async def config_delete(key: str, db: Database) -> {}:
    if key == 'ROOT_KEY':
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='ROOT_KEY cannot be deleted')
    q = select(Config).where(Config.key == key)
    config = db.exec(q).first()
    if not config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f'{key} not found')

    db.delete(config)
    db.commit()

    return {'detail': f'Config Key {key} deleted'}
