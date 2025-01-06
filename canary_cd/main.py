"""
Main application entry point.
"""
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request

from canary_cd.settings import REPO_CACHE, PAGES_CACHE, DYN_CONFIG_CACHE
from canary_cd import __version__
from canary_cd.routers import routers
from canary_cd.database import create_db_and_tables


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """lifespan context manager."""
    # startup
    for cache in [REPO_CACHE, PAGES_CACHE, DYN_CONFIG_CACHE]:
        os.makedirs(cache, exist_ok=True)
    await create_db_and_tables()
    yield
    # shutdown


fastapi_options = {
    'lifespan': lifespan,
    'title': 'CanaryCD API',
    'description': "",
    'version': __version__,
    'license': {
        'name': 'MIT',
        'identifier': 'MIT',
    }
}

app = FastAPI(**fastapi_options)
for router in routers:
    app.include_router(router)


@app.get('/', status_code=418, include_in_schema=False)
async def coffeepot(request: Request):
    """Coffeepot Entrypoint"""
    return {
        "detail": "I'm a Coffeepot!",
        "ip": request.client[0]
    }


def main():
    host = os.environ.get('CANARY_HOST', '127.0.0.1')
    port = os.environ.get('CANARY_PORT', 8001)
    import uvicorn
    uvicorn.run(app, host=host, port=int(port))


if __name__ == "__main__":
    main()
