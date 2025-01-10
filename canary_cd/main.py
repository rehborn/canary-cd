"""
Main application entry point.
"""
import os
from contextlib import asynccontextmanager
from datetime import datetime

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


@app.get('/', status_code=200, include_in_schema=False)
async def root(request: Request):
    """Root Entrypoint"""
    stat_at = datetime.fromtimestamp(os.path.getctime('/proc/1'))
    uptime = datetime.now() - stat_at
    return {
        "detail": "I'm a Canary!",
        "ip": request.client.host,
        "version": __version__,
        'created_timestamp': stat_at.timestamp(),
        'created_at': stat_at.isoformat(timespec='seconds'),
        'uptime': f'{uptime.days}d {(uptime.seconds // 3600)}h {((uptime.seconds // 60) % 60)}m {uptime.seconds % 60}s',
        'uptime_total_seconds': uptime.total_seconds(),
    }


def main():
    host = os.environ.get('CANARY_HOST', '127.0.0.1')
    port = os.environ.get('CANARY_PORT', 8001)
    import uvicorn
    uvicorn.run(app,
                host=host,
                port=int(port),
                proxy_headers=True,
                forwarded_allow_ips='*',
                log_level="info",
                )

    if __name__ == "__main__":
        main()
