import shutil

from sqlmodel import col
from canary_cd.utils.tasks import page_init

from fastapi import APIRouter, status, BackgroundTasks, Query

from canary_cd.dependencies import *

router = APIRouter(prefix='/page',
                   tags=['Page'],
                   dependencies=[Depends(validate_admin)],
                   responses={404: {"description": "Not found"}},
                   )


# list page
@router.get('', summary="List all pages")
async def page_list(db: Database,
                    offset: Optional[int] = 0,
                    limit: Annotated[int, Query(le=100)] = 100,
                    filter_by: Optional[str] = '',
                    ordering: Optional[str] = 'fqdn',
                    ) -> list[PageDetails]:
    return db.exec(select(Page)
                   .order_by(desc(ordering))
                   .filter(column("fqdn").contains(filter_by))
                   .offset(offset)
                   .limit(limit)
                   ).all()


# get page details
@router.get('/{fqdn}', summary='Get Page Details')
async def page_get(fqdn: str, db: Database) -> PageDetails:
    page = db.exec(select(Page).where(Page.fqdn == fqdn)).first()
    if not page:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Page does not exists')
    return page

# create page
@router.post('', status_code=status.HTTP_201_CREATED, summary="Create a new page")
async def page_create(page: PageCreate, db: Database, background_tasks: BackgroundTasks) -> PageDetails:
    if db.exec(select(Page).where(Page.fqdn == page.fqdn)).first():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail='Page already exists')

    db_redirect_source = db.exec(select(Redirect).where(Redirect.source == page.fqdn)).first()
    if db_redirect_source:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail='Already in use by Redirect source {db_redirect_source.source}')

    db_page = Page.model_validate(PageCreate(fqdn=page.fqdn, cors_hosts=page.cors_hosts))  # TODO
    db.add(db_page)
    db.commit()
    db.refresh(db_page)

    background_tasks.add_task(page_init, page.fqdn, page.cors_hosts)

    return PageDetails(**db_page.model_dump())


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
    if HTTPD_CONFIG_DUMP and HTTPD == 'traefik':
        os.remove(DYN_CONFIG_CACHE / f'{fqdn}.yml')

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
