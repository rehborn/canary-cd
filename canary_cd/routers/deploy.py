import tempfile

from fastapi import APIRouter, status, BackgroundTasks, Query, Path
from starlette.requests import Request

from canary_cd.dependencies import *
from canary_cd.utils.tasks import deploy_init, extract_page

router = APIRouter(prefix='/deploy',
                   tags=['Deploy-hooks'],
                   responses={404: {"description": "Not found"}},
                   )


# deploy project
@router.get('/project/{token}')
@router.get('/project/{token}/{environment}')
async def token_deploy_project(token: str, db: Database, background_tasks: BackgroundTasks,
                               environment: str = None) -> {}:
    project = db.exec(select(Project).where(Project.token == ch.hash(token))).first()

    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Project not found')

    if not environment:
        environment = 'default'

    q = select(Environment) \
        .where(Environment.project == project) \
        .where(Environment.name == environment)
    db_env = db.exec(q).first()
    if not db_env:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Environment not found')

    background_tasks.add_task(deploy_init, db, db_env.id)

    return {"detail": f"deployment started on environment {environment}"}


# deploy page
@router.post('/page/{token}')
async def token_deploy_page(token: str, request: Request, db: Database, background_tasks: BackgroundTasks) -> {}:
    page = db.exec(select(Page).where(Page.token == ch.hash(token))).first()
    if not page:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Page already exists')

    job_id = uuid.uuid4()
    logger.debug(f"Page {job_id}: uploading")

    temp_dir = tempfile.TemporaryDirectory(delete=False)
    with open(Path(temp_dir.name) / "stream-upload", "wb") as f:
        async for chunk in request.stream():
            f.write(chunk)

    background_tasks.add_task(extract_page, page.fqdn, temp_dir, job_id)

    return {"detail": f"{page.fqdn} uploaded"}
