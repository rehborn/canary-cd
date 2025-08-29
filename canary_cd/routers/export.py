from socket import gethostbyname

from _socket import gaierror
from fastapi import APIRouter, Request, Response, HTTPException, Depends
from fastapi.responses import JSONResponse
from sqlmodel import select

from canary_cd.database import Database, Page, Redirect
from canary_cd.settings import HTTPD
from canary_cd.utils.httpd_conf import TraefikConfig


async def local_or_httpd_container(request: Request):
    whitelist = []
    for name in ['localhost', HTTPD]:
        try:
            whitelist.append(gethostbyname(name))
        except gaierror:
            pass

    if request.client.host not in whitelist:
        raise HTTPException(status_code=400, detail='Unauthorized')


router = APIRouter(prefix='/export',
                   tags=['export'],
                   dependencies=[Depends(local_or_httpd_container)],
                   responses={404: {"description": "Not found"}},
                   )


@router.get('/traefik.json', summary="traefik config provider")
async def traefik_config(db: Database) -> Response:
    tc = TraefikConfig(default_service=True)

    pages = db.exec(select(Page)).all()
    for page in pages:
        tc.add_page(page.fqdn, page.cors_hosts, add_service=False)

    redirects = db.exec(select(Redirect)).all()
    for redirect in redirects:
        tc.add_redirect(redirect.source, redirect.destination)

    return JSONResponse(tc.render())
