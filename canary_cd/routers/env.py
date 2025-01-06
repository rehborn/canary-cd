import shutil
from typing import Annotated

from fastapi import APIRouter, status, BackgroundTasks, Depends, HTTPException, Query, UploadFile
from sqlalchemy.orm.sync import update

from canary_cd.dependencies import *
# from src.models.project import *
# from src.models.env import *

router = APIRouter(prefix='/env',
                   tags=['Environment'],
                   dependencies=[Depends(validate_admin)],
                   responses={404: {"description": "Not found"}},
                   )


# list environments for project
@router.get('/{project}/')
async def envs_list(db: Database,
                    project: str,
                    offset: int = 0,
                    limit: Annotated[int, Query(le=100)] = 100) -> list[EnvDetails]:
    db_project = db.exec(select(Project).where(Project.name == project)).first()
    if not db_project:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Project does not exists')
    query = select(Environment).where(Environment.project_id == db_project.id).offset(offset).limit(limit)
    return db.exec(query).all()


# create environment for project
@router.post('/{project}/', status_code=status.HTTP_201_CREATED)
async def env_create(project: str, env: EnvBase, db: Database) -> EnvDetails:
    q = select(Project).where(Project.name == project)
    db_project = db.exec(q).first()
    if not db_project:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Project does not exists')
    if db.exec(select(Environment).where(Environment.project == db_project).where(Environment.name == env.name)).first():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Environment for Project already exists')

    db_env = Environment.model_validate(env)
    db_env.project_id = db_project.id
    db.add(db_env)
    db.commit()
    db.refresh(db_env)
    return db_env

# update environment
@router.put('/{project}/{environment}/', summary='Update Environment')
async def env_update(project: str, environment: str, data: EnvUpdate, db: Database) -> EnvDetails:
    q = select(Project).where(Project.name == project)
    db_project = db.exec(q).first()
    if not db_project:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Project does not exists')

    q = select(Environment).where(Environment.project_id == db_project.id).where(Environment.name == environment)
    env_db = db.exec(q).first()
    if not env_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Environment not found')

    env_db.sqlmodel_update(data.model_dump(exclude_unset=True))
    db.add(env_db)
    db.commit()
    db.refresh(env_db)

    return env_db


# delete environment
@router.delete('/{project}/{environment}/', summary='Delete Environment')
async def env_delete(project: str, environment: str, db: Database) -> {}:
    db_project = db.exec(select(Project).where(Project.name == project)).first()
    if not db_project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Project not found')

    query = select(Environment)\
        .where(Environment.project_id == db_project.id)\
        .where(Environment.name == environment)
    db_env = db.exec(query).first()
    if not db_env:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Environment not found')

    repo_path = REPO_CACHE / db_project.name / f"{db_env.name}-{db_env.branch}"

    # Cleanup
    try:
        shutil.rmtree(repo_path)
    except FileNotFoundError:
        pass

    db.delete(db_env)
    db.commit()

    return {"detail": f"{environment} deleted"}


# list variables for environment
@router.get('/{project}/{environment}/', summary='List Variables')
async def variable_list(db: Database,
                   project: str,
                   environment: str,
                   offset: int = 0,
                   limit: Annotated[int, Query(le=100)] = 100) -> list[VariableValueDetails]:
    db_project = db.exec(select(Project).where(Project.name == project)).first()
    if not db_project:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Project does not exists')

    query = select(Environment) \
        .where(Environment.project_id == db_project.id) \
        .where(Environment.name == environment)
    db_env = db.exec(query).first()
    if not db_env:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Environment does not exists')

    db_variables = db.exec(select(Variable).where(Variable.environment_id == db_env.id).offset(offset).limit(limit)).all()
    variables = [
        VariableValueDetails(
            id=v.id,
            environment_id=v.environment_id,
            key=v.key,
            value=ch.decrypt(v.nonce, v.ciphertext),
            created_at=v.created_at,
            updated_at=v.updated_at,
        )
        for v in db_variables
    ]
    return variables


# set environment variable
@router.put('/{project}/{environment}/', summary='Set or Update Environment Variable')
async def variable_set(project: str,
                  environment: str,
                  data: VariableUpdate,
                  db: Database) -> VariableDetails:

    q = select(Project).where(Project.name == project)
    db_project = db.exec(q).first()
    if not db_project:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Project does not exists')

    q = select(Environment).where(Environment.project == db_project).where(Environment.name == environment)
    db_env = db.exec(q).first()
    if not db_env:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Env does not exists')

    db_var = db.exec(select(Variable).where(Variable.key == data.key.upper())).first()

    if not db_var:
        data.key = data.key.upper()
        db_var = Variable(key=data.key.upper(), environment_id=db_env.id)

    db_var.nonce, db_var.ciphertext = ch.encrypt(data.value)
    db.add(db_var)
    db.commit()
    db.refresh(db_var)
    return db_var


# unset environment variable
@router.delete('/{project}/{environment}/{variable}/')
async def variable_unset(project: str, environment: str, variable: str, db: Database) -> {}:
    db_project = db.exec(select(Project).where(Project.name == project)).first()
    if not db_project:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Project does not exists')

    q = select(Environment).where(Environment.project == db_project).where(Environment.name == environment)
    db_env = db.exec(q).first()

    if not db_env:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Environment does not exists')

    q = select(Variable).where(Variable.environment == db_env).where(Variable.key == variable.upper())
    db_var = db.exec(q).first()

    if not db_var:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Variable does not exists')

    db.delete(db_var)
    db.commit()
    return {"detail": f"{variable} deleted"}
