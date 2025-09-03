from fastapi import APIRouter, Response, status, BackgroundTasks
from fastapi.responses import JSONResponse

from canary_cd.utils.notify import discord_webhook
from canary_cd.dependencies import *
from canary_cd.models import ConfigUpdate
from canary_cd.utils.pattern import CONFIG_KEYS

router = APIRouter(prefix='/config',
                   tags=['Canary Config'],
                   dependencies=[Depends(validate_admin)],
                   responses={404: {"description": "Not found"}},
                   )


# list config
@router.get('', summary='List Full Configuration')
async def list_config(db: Database) -> list[ConfigUpdate]:
    config = db.exec(select(Config).where(Config.key != 'ROOT_KEY')).all()
    return config


# set config
@router.put('', summary='Update Configuration')
async def config_set(data: ConfigUpdate, db: Database, background_task: BackgroundTasks) -> ConfigUpdate:
    if data.key not in CONFIG_KEYS:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Invalid Config key')

    if data.key == 'ROOT_KEY':
        data.value = CryptoHelper(SALT).hash(data.value)

    if data.key == 'DISCORD_WEBHOOK':
        message = f"### :information_source: Notification Setup Successful"
        background_task.add_task(discord_webhook, data.value, message)

    q = select(Config).where(Config.key == data.key)
    config = db.exec(q).first()
    if not config:
        config = Config(key=data.key)

    config.value = data.value

    db.add(config)
    db.commit()
    db.refresh(config)

    return config


@router.delete('/{key}', summary='Delete Configuration')
async def config_delete(key: str, db: Database) -> Response:
    if key == 'ROOT_KEY':
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='ROOT_KEY cannot be deleted')
    q = select(Config).where(Config.key == key)
    config = db.exec(q).first()
    if not config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f'{key} not found')

    db.delete(config)
    db.commit()

    return JSONResponse({'detail': f'{key} deleted'})
