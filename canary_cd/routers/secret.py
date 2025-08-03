import shutil
from typing import Annotated

from fastapi import APIRouter, status, BackgroundTasks, Depends, HTTPException, Query, UploadFile
from sqlalchemy.orm.sync import update

from canary_cd.dependencies import *

# from src.models.project import *
# from src.models.env import *

router = APIRouter(prefix='/secret',
                   tags=['Secrets'],
                   dependencies=[Depends(validate_admin)],
                   responses={404: {"description": "Not found"}},
                   )


# list secrets for project
@router.get('/{project}', summary='List Secrets')
async def secret_list(db: Database,
                      project: str,
                      offset: int = 0,
                      limit: Annotated[int, Query(le=100)] = 100) -> list[VariableValueDetails]:
    db_project = db.exec(select(Project).where(Project.name == project)).first()
    if not db_project:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Project does not exists')

    secrets = db.exec(select(Secret).where(Secret.project_id == db_project.id).offset(offset).limit(limit)).all()
    variables = [
        VariableValueDetails(
            id=v.id,
            # project_id=v.project_id,
            key=v.key,
            value=ch.decrypt(v.nonce, v.ciphertext),
            created_at=v.created_at,
            updated_at=v.updated_at,
        )
        for v in secrets
    ]
    return variables


# set environment variable
@router.put('/{project}', summary='Update Secret')
async def secret_set(project: str, data: VariableUpdate, db: Database) -> VariableDetails:
    q = select(Project).where(Project.name == project)
    db_project = db.exec(q).first()
    if not db_project:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Project does not exists')

    db_var = db.exec(select(Secret).where(Secret.key == data.key.upper())).first()

    if not db_var:
        data.key = data.key.upper()
        db_var = Secret(key=data.key.upper(), project_id=db_project.id)

    db_var.nonce, db_var.ciphertext = ch.encrypt(data.value)
    db.add(db_var)
    db.commit()
    db.refresh(db_var)
    return db_var


# delete secret
@router.delete('/{project}/{variable}', summary='Delete Secret')
async def secret_delete(project: str, variable: str, db: Database) -> {}:
    db_project = db.exec(select(Project).where(Project.name == project)).first()
    if not db_project:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Project does not exists')

    q = select(Secret).where(Secret.project == db_project).where(Secret.key == variable.upper())
    db_var = db.exec(q).first()

    if not db_var:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Variable does not exists')

    db.delete(db_var)
    db.commit()
    return {"detail": f"{variable} deleted"}
