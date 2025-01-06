from fastapi import APIRouter, status, File, BackgroundTasks, Depends, HTTPException, UploadFile, Query

from canary_cd.dependencies import *
from canary_cd.utils.tasks import generate_ssh_keypair, generate_ssh_pubkey

router = APIRouter(prefix='/git-key',
                   tags=['Git Key'],
                   dependencies=[Depends(validate_admin)],
                   responses={404: {"description": "Not found"}},
                   )


@router.get('/', summary="List all Git Keys")
async def git_key_list(db: Database,
                       offset: int = 0,
                       limit: Annotated[int, Query(le=100)] = 100
                       ) -> list[GitKeyDetails]:
    return db.exec(select(GitKey).offset(offset).limit(limit)).all()


@router.get('/{name}', summary='Get Git Key Details')
async def git_key_get(name: str, db: Database) -> GitKeyDetails:
    key = db.exec(select(GitKey).where(GitKey.name == name)).first()
    if not key:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Key does not exists')
    return key


@router.post('/', status_code=status.HTTP_201_CREATED, summary='Create a Git Key')
async def git_key_create(data: GitKeyCreate, db: Database) -> GitKeyDetails:
    if db.exec(select(GitKey).where(GitKey.name == data.name)).first():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Git Key already exists')

    if data.auth_type not in ['ssh', 'pat']:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail='Invalid auth type, valid options: ssh, pat')

    public_key = None
    if data.auth_type == 'ssh':
        if data.auth_key:
            public_key = await generate_ssh_pubkey(data.auth_key)
        else:
            data.auth_key, public_key = await generate_ssh_keypair(data.name)

    if not data.auth_key:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='No key provided')

    db_key = GitKey(name=data.name, auth_type=data.auth_type, public_key=public_key)
    db_key.nonce, db_key.ciphertext = ch.encrypt(data.auth_key)
    db.add(db_key)
    db.commit()
    db.refresh(db_key)
    return db_key


@router.delete('/{name}', summary='Delete a Key')
async def git_key_delete(name: str, db: Database) -> {}:
    git_key = db.exec(select(GitKey).where(GitKey.name == name)).first()
    if not git_key:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Git Key not found')

    db.delete(git_key)
    db.commit()

    return {"detail": f"{name} deleted"}
