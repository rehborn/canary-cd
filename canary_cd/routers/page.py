import shutil
import tempfile
from starlette.requests import Request
from canary_cd.utils.tasks import extract_page, page_traefik_config

from fastapi import APIRouter, status, BackgroundTasks, Query

from canary_cd.dependencies import *

router = APIRouter(prefix='/page',
                   tags=['Page'],
                   dependencies=[Depends(validate_admin)],
                   responses={404: {"description": "Not found"}},
                   )


# list page
@router.get('/', summary="List all pages")
async def page_list(db: Database,
                    offset: int = 0,
                    limit: Annotated[int, Query(le=100)] = 100
                    ) -> list[PageDetails]:
    return db.exec(select(Page).order_by(col(Page.fqdn).asc()).offset(offset).limit(limit)).all()


# create page
@router.post('/', status_code=status.HTTP_201_CREATED, summary="Create a new page")
async def page_create(page: PageBase, db: Database, background_tasks: BackgroundTasks) -> PageDetails:
    if db.exec(select(Page).where(Page.fqdn == page.fqdn)).first():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail='Page already exists')

    db_redirect_source = db.exec(select(Redirect).where(Redirect.source == page.fqdn)).first()
    if db_redirect_source:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail='Already in use by Redirect source {db_redirect_source.source}')

    db_page = Page.model_validate(PageBase(fqdn=page.fqdn))
    db.add(db_page)
    db.commit()
    db.refresh(db_page)

    os.makedirs(PAGES_CACHE / page.fqdn, exist_ok=True)
    os.makedirs(DYN_CONFIG_CACHE / page.fqdn, exist_ok=True)

    # Create config
    background_tasks.add_task(page_traefik_config, db_page.fqdn)

    return db_page


# delete page
@router.delete('/{fqdn}')
async def page_delete(fqdn: str, db: Database) -> {}:
    page = db.exec(select(Page).where(Page.fqdn == fqdn)).first()
    if not page:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Page not found')

    db.delete(page)
    db.commit()

    # Cleanup static files and config
    shutil.rmtree(PAGES_CACHE / fqdn)
    os.remove(PAGES_CACHE / 'dynamic' / f'{fqdn}.yml')

    return {"detail": f"{fqdn} deleted"}


# refresh page token
@router.get("/{fqdn}/refresh-token")
async def page_deploy_key(fqdn: str, db: Database):
    page_db = db.exec(select(Page).where(Page.fqdn == fqdn)).first()
    if not page_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Page not found')

    token = random_string(64)
    page_db.token = ch.hash(token)

    db.commit()
    db.refresh(page_db)

    return {"token": token}


@router.post("/{fqdn}/deploy", summary="Deploy a page")
async def page_deploy_stream(fqdn: str, request: Request, background_tasks: BackgroundTasks):
    job_id = uuid.uuid4()
    logger.debug(f"Page {job_id}: uploading ")

    temp_dir = tempfile.TemporaryDirectory(delete=False)
    with open(Path(temp_dir.name) / "stream-upload", "wb") as f:
        async for chunk in request.stream():
            f.write(chunk)

    background_tasks.add_task(extract_page, fqdn, temp_dir, job_id)

    return {"detail": f"{fqdn} uploaded"}
