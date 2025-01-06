import shutil

from fastapi import APIRouter, status, BackgroundTasks, Query

from canary_cd.dependencies import *
from canary_cd.utils.tasks import deploy_init, deploy_status

router = APIRouter(prefix='/project',
                   tags=['Project'],
                   dependencies=[Depends(validate_admin)],
                   responses={404: {"description": "Not found"}},
                   )


# list projects
@router.get('/', summary='List Projects')
async def project_list(db: Database,
                       offset: int = 0,
                       limit: Annotated[int, Query(le=100)] = 100
                       ) -> list[ProjectDetails]:
    return db.exec(select(Project).order_by(col(Project.name).asc()).offset(offset).limit(limit)).all()


# get project details
@router.get('/{name}', summary='Get Project Details')
async def project_get(name: str, db: Database) -> ProjectDetails:
    project = db.exec(select(Project).where(Project.name == name)).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Project does not exists')
    return project


# create project
@router.post('/', status_code=status.HTTP_201_CREATED, summary='Create a Project')
async def project_create(data: ProjectCreate, db: Database) -> ProjectCreatedDetails:
    if db.exec(select(Project).where(Project.name == data.name)).first():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Project already exists')

    project_db = Project.model_validate(data)

    if data.key:
        key = db.exec(select(GitKey).where(GitKey.name == data.key)).first()
        if not key:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Key does not exist')
        project_db.git_key = key

    token = random_string(64)
    project_db.token = ch.hash(token)

    db.add(project_db)
    db.commit()
    db.refresh(project_db)

    project_db.token = token
    return project_db


# update project
@router.put('/{name}', summary='Update a Project')
async def project_update(name: str, data: ProjectUpdate, db: Database) -> ProjectDetails:
    project_db = db.exec(select(Project).where(Project.name == name)).first()
    if not project_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Project not found')

    project_data = data.model_dump(exclude_unset=True)
    project_db.sqlmodel_update(project_data)

    if data.key:
        key = db.exec(select(GitKey).where(GitKey.name == data.key)).first()
        if not key:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Key does not exist')
        project_db.git_key = key

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


# deploy project
@router.get('/{name}/deploy/{environment}')
async def project_deploy(name: str, environment: str, db: Database, background_tasks: BackgroundTasks) -> {}:
    project = db.exec(select(Project).where(Project.name == name)).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Project not found')

    q = select(Environment).where(Environment.project == project).where(Environment.name == environment)
    db_env = db.exec(q).first()
    if not db_env:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Environment not found')

    background_tasks.add_task(deploy_init, db, db_env.id)

    return {"detail": f"deployment started on environment {environment}"}


# get project status
@router.get('/{name}/status/{environment}')
async def project_status(name: str, environment: str, db: Database) -> {}:
    project = db.exec(select(Project).where(Project.name == name)).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Project not found')

    q = select(Environment).where(Environment.project == project).where(Environment.name == environment)
    db_env = db.exec(q).first()
    if not db_env:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Environment not found')

    repo_path = REPO_CACHE / db_env.project.name / f"{db_env.name}-{db_env.branch}"
    result = await deploy_status(repo_path)

    return result
