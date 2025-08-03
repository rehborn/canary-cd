import tempfile

from fastapi import APIRouter, status, BackgroundTasks, Query, Path
from starlette.requests import Request

from canary_cd.dependencies import *
from canary_cd.utils.tasks import deploy_init, extract_page, deploy_stop, deploy_status

router = APIRouter(tags=['Deployment'],
                   dependencies=[Depends(validate_admin)],
                   responses={404: {"description": "Not found"}},
                   )


# deploy project
@router.get('/deploy/{name}/start', summary='Deploy a Project')
async def project_deploy(name: str, db: Database, background_tasks: BackgroundTasks) -> {}:
    project = db.exec(select(Project).where(Project.name == name)).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Project not found')

    background_tasks.add_task(deploy_init, db, project.id)

    return {"detail": f"deployment started for {name}"}


# stop deploy project
@router.get('/deploy/{name}/stop', summary='Stop a Project')
async def project_deploy_stop(name: str, db: Database, background_tasks: BackgroundTasks) -> {}:
    project = db.exec(select(Project).where(Project.name == name)).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Project not found')

    background_tasks.add_task(deploy_stop, REPO_CACHE / project.name)

    return {"detail": f"stopping deployment for {name}"}


# get project status
@router.get('/deploy/{name}/status', summary='Status of a Project')
async def project_status(name: str, db: Database) -> {}:
    project = db.exec(select(Project).where(Project.name == name)).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Project not found')

    result = await deploy_status(REPO_CACHE / project.name, project.branch)

    if not result:
        result = {'detail': 'not running'}
    return result


@router.post("/upload/{page}", summary="Upload Page Payload")
async def page_deploy_stream(page: str, request: Request, background_tasks: BackgroundTasks):
    job_id = uuid.uuid4()
    logger.debug(f"Page {job_id}: uploading ")

    temp_dir = tempfile.TemporaryDirectory(delete=False)
    with open(Path(temp_dir.name) / "stream-upload", "wb") as f:
        async for chunk in request.stream():
            f.write(chunk)

    background_tasks.add_task(extract_page, page, temp_dir, job_id)

    return {"detail": f"{page} uploaded"}
