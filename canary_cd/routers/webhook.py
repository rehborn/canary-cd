import tempfile

from fastapi import APIRouter, status, BackgroundTasks, Path, Response, Request
from fastapi.responses import JSONResponse

from canary_cd.dependencies import *
from canary_cd.utils.tasks import deploy_init, extract_page

router = APIRouter(prefix='/webhook',
                   tags=['Webhooks'],
                   responses={404: {"description": "Not found"}},
                   )


# deploy project
@router.post('/project/{token}', summary='Deploy a Project')
async def token_deploy_project(token: str,
                               db: Annotated[Session, Depends(get_session)],
                               background_tasks: BackgroundTasks,
                               ) -> Response:
    project = db.exec(select(Project).where(Project.token == ch.hash(token))).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Project not found')

    background_tasks.add_task(deploy_init, db, project.id)

    return JSONResponse({"detail": f"deployment started {project.name}"})


# deploy page
@router.post('/page/{token}', summary='Upload Page Payload')
async def token_deploy_page(token: str,
                            request: Request,
                            background_tasks: BackgroundTasks,
                            db: Annotated[Session, Depends(get_session)],
                            ) -> Response:
    page = db.exec(select(Page).where(Page.token == ch.hash(token))).first()
    if not page:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Page not found')

    job_id = uuid.uuid4()
    logger.debug(f"Page {job_id}: uploading")

    temp_dir = tempfile.TemporaryDirectory(delete=False)
    with open(Path(temp_dir.name) / "stream-upload", "wb") as f:
        async for chunk in request.stream():
            f.write(chunk)

    background_tasks.add_task(extract_page, page.fqdn, temp_dir, job_id)

    return JSONResponse({"detail": f"{page.fqdn} uploaded"})
