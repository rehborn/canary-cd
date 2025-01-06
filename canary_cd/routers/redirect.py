from fastapi import APIRouter, status, BackgroundTasks, Query

from canary_cd.dependencies import *
from canary_cd.utils.tasks import redirect_traefik_config

router = APIRouter(prefix='/redirect',
                   tags=['Redirect'],
                   dependencies=[Depends(validate_admin)],
                   responses={404: {"description": "Not found"}},
                   )


# list redirects
@router.get('/', summary='List Redirects')
async def redirect_list(db: Database,
                        offset: int = 0,
                        limit: Annotated[int, Query(le=100)] = 100
                        ) -> list[RedirectDetails]:
    return db.exec(select(Redirect).offset(offset).limit(limit)).all()


# create redirects
@router.post('/', status_code=status.HTTP_201_CREATED, summary="Create a new Redirect")
async def redirect_create(redirect: RedirectCreate, db: Database, background_tasks: BackgroundTasks) -> RedirectDetails:
    if db.exec(select(Redirect).where(Redirect.source == redirect.source)).first():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail='Redirect already exists')

    if db.exec(select(Page).where(Page.fqdn == redirect.source)).first():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail='Page with this FQDN already exists')

    db_redirect = Redirect.model_validate(redirect)
    db.add(db_redirect)
    db.commit()
    db.refresh(db_redirect)

    background_tasks.add_task(redirect_traefik_config, db_redirect.source, db_redirect.destination)

    return db_redirect

@router.put('/{fqdn}', status_code=status.HTTP_200_OK, summary="Update a Redirect")
async def redirect_update(fqdn: str, redirect: RedirectUpdate, db: Database, background_tasks: BackgroundTasks) -> RedirectDetails:
    db_redirect = db.exec(select(Redirect).where(Redirect.source == fqdn)).first()
    if not db_redirect:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Redirect not found')

    db_redirect.destination = redirect.destination
    db.add(db_redirect)
    db.commit()
    db.refresh(db_redirect)

    # Creat config
    background_tasks.add_task(redirect_traefik_config, db_redirect.source, db_redirect.destination)

    return db_redirect

@router.delete('/{fqdn}', status_code=status.HTTP_200_OK, summary="Delete a Redirect")
async def redirect_delete(fqdn: str, db: Database):
    db_redirect = db.exec(select(Redirect).where(Redirect.source == fqdn)).first()
    if not db_redirect:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Redirect not found')

    db.delete(db_redirect)
    db.commit()

    # Cleanup config
    os.remove(PAGES_CACHE / 'dynamic' / f'{fqdn}.yml')

    return {"detail": f"{fqdn} deleted"}
