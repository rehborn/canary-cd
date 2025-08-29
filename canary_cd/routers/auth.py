from fastapi import APIRouter, status, Query
from sqlalchemy import desc

from canary_cd.dependencies import *
from canary_cd.utils.tasks import generate_ssh_keypair, generate_ssh_pubkey
from canary_cd.utils.crypto import random_words
from canary_cd.database import Auth
from canary_cd.models import AuthDetails, AuthDetailsCount, AuthCreate

router = APIRouter(prefix='/auth',
                   tags=['Authentication'],
                   dependencies=[Depends(validate_admin)],
                   responses={404: {"description": "Not found"}},
                   )


@router.get('', summary="List all Authentication Keys")
async def auth_list(db: Database,
                    offset: Optional[int] = 0,
                    limit: Annotated[int, Query(le=100)] = 100,
                    filter_by: Optional[str] = '',
                    ordering: Optional[str] = 'updated_at',
                    ) -> list[AuthDetails]:
    return db.exec(select(Auth)
                   .order_by(desc(ordering))
                   .filter(column("name").contains(filter_by))
                   .offset(offset)
                   .limit(limit)
                   ).all()


@router.get('/{name}', summary='Get Authentication Key Details')
async def auth_get(name: str, db: Database) -> AuthDetailsCount:
    key = db.exec(select(Auth).where(Auth.name == name)).first()
    if not key:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Key does not exists')
    return key


@router.post('', status_code=status.HTTP_201_CREATED, summary='Create Authentication Key')
async def auth_create(data: AuthCreate, db: Database) -> AuthDetails:
    if db.exec(select(Auth).where(Auth.name == data.name)).first():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Authentication Key already exists')

    if data.auth_type not in ['ssh', 'pat']:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail='Invalid auth type, valid options: ssh, pat')

    if not data.name:
        data.name = random_words()

    public_key = None
    if data.auth_type == 'ssh':
        if data.auth_key:
            public_key = await generate_ssh_pubkey(data.auth_key)
        else:
            data.auth_key, public_key = await generate_ssh_keypair(data.name)

    if not data.auth_key:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='No key provided')

    db_key = Auth(name=data.name, auth_type=data.auth_type, public_key=public_key)
    db_key.nonce, db_key.ciphertext = ch.encrypt(data.auth_key)
    db.add(db_key)
    db.commit()
    db.refresh(db_key)

    return db_key


@router.delete('/{name}', summary='Delete Authentication Key')
async def auth_delete(name: str, db: Database) -> {}:
    auth = db.exec(select(Auth).where(Auth.name == name)).first()
    if not auth:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Authentication Key not found')

    db.delete(auth)
    db.commit()

    return {"detail": f"{name} deleted"}
