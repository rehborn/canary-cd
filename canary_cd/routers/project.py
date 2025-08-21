import shutil

from fastapi import APIRouter, status, Query

from canary_cd.dependencies import *
from canary_cd.utils.crypto import random_words

router = APIRouter(prefix='/project',
                   tags=['Project'],
                   dependencies=[Depends(validate_admin)],
                   responses={404: {"description": "Not found"}},
                   )


# list projects
@router.get('', summary='List Projects')
async def project_list(db: Database,
                       offset: Optional[int] = 0,
                       limit: Annotated[int, Query(le=100)] = 100,
                       filter_by: Optional[str] = '',
                       ordering: Optional[str] = 'updated_at',
                       ) -> list[ProjectDetails]:
    return db.exec(select(Project)
                   .order_by(desc(ordering))
                   .filter(column("name").contains(filter_by))
                   .offset(offset)
                   .limit(limit)
                   ).all()


# get project details
@router.get('/{name}', summary='Get Project Details')
async def project_get(name: str, db: Database) -> ProjectDetails:
    project = db.exec(select(Project).where(Project.name == name)).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Project does not exists')
    return project


# create project
@router.post('', status_code=status.HTTP_201_CREATED, summary='Create a Project')
async def project_create(data: ProjectCreate, db: Database) -> ProjectDetails:
    if db.exec(select(Project).where(Project.name == data.name)).first():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Project already exists')

    def get_random_name(exists=True) -> str:
        while exists:
            name = random_words()
            if not db.exec(select(Project).where(Project.name == name)).first():
                return name

    if not data.name:
        data.name = get_random_name()

    project_db = Project.model_validate(data)

    if data.key:
        key = db.exec(select(Auth).where(Auth.name == data.key)).first()
        if not key:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Key does not exist')
        project_db.auth = key

    token = random_string(64)
    project_db.token = ch.hash(token)

    db.add(project_db)
    db.commit()
    db.refresh(project_db)

    # project = ProjectDetails(**project_db.model_dump())
    # project.token = token
    # return project

    project_db.token = token
    return project_db


# update project
@router.put('/{name}', summary='Update a Project')
async def project_update(name: str, data: ProjectUpdate, db: Database) -> ProjectDetails:
    project_db = db.exec(select(Project).where(Project.name == name)).first()
    if not project_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Project not found')
    print(data)

    project_data = data.model_dump(exclude_unset=True)
    project_db.sqlmodel_update(project_data)

    if data.key:
        key = db.exec(select(Auth).where(Auth.name == data.key)).first()
        if not key:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Key does not exist')
        project_db.auth = key

    project_db.updated_at = now()
    db.add(project_db)
    db.commit()
    db.refresh(project_db)

    return project_db


# delete project
@router.delete('/{name}', summary='Delete a Project')
async def project_delete(name: str, db: Database) -> {}:
    project = db.exec(select(Project).where(Project.name == name)).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Project not found')

    db.delete(project)
    db.commit()

    # Cleanup
    try:
        shutil.rmtree(REPO_CACHE / name)
    except FileNotFoundError:
        pass

    return {"detail": f"{name} deleted"}


# refresh project token
@router.get('/{name}/refresh-token', summary='Refresh Deploy Token')
async def project_refresh_token(name: str, db: Database) -> {}:
    project_db = db.exec(select(Project).where(Project.name == name)).first()
    if not project_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Project not found')

    token = random_string(64)
    project_db.token = ch.hash(token)
    db.commit()
    db.refresh(project_db)

    return {"token": token}

