import gzip
import json
import logging
import os
import sys
from contextlib import asynccontextmanager
from typing import Any, Dict

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.types import ASGIApp, Receive, Scope, Send

from .db import engine
from .database import Base


LOG_LEVEL = os.environ.get("ZOTERO_LOG_LEVEL", "INFO").upper()
_log_level = getattr(logging, LOG_LEVEL, logging.INFO)

_formatter = logging.Formatter(
    "%(asctime)s [%(levelname)s] %(name)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
_handler = logging.StreamHandler(sys.stdout)
_handler.setFormatter(_formatter)

_srv_logger = logging.getLogger("zotero")
_srv_logger.setLevel(_log_level)
_srv_logger.handlers = [_handler]


class GzipRequestBodyMiddleware:
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] == "http":
            headers = dict(scope.get("headers", []))
            content_encoding = headers.get(b"content-encoding", b"").decode("latin-1").lower()
            if content_encoding == "gzip":
                scope = dict(scope)
                new_headers = [(k, v) for k, v in scope["headers"] if k != b"content-encoding"]
                scope["headers"] = new_headers

                original_receive = receive
                received = False

                async def receive_decompressed():
                    nonlocal received
                    if received:
                        return {"type": "http.disconnect"}
                    received = True
                    body_parts = []
                    more_body = True
                    while more_body:
                        msg = await original_receive()
                        body_parts.append(msg.get("body", b""))
                        more_body = msg.get("more_body", False)
                    full_body = b"".join(body_parts)
                    decompressed = gzip.decompress(full_body)
                    return {"type": "http.request", "body": decompressed, "more_body": False}

                await self.app(scope, receive_decompressed, send)
                return

        await self.app(scope, receive, send)


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(lifespan=lifespan)

app.add_middleware(GzipRequestBodyMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _shorten(data: Any, max_len: int = 2000) -> str:
    s = json.dumps(data, ensure_ascii=False) if not isinstance(data, str) else data
    if len(s) > max_len:
        return s[:max_len] + f"...({len(s)} chars total)"
    return s


@app.middleware("http")
async def add_common_headers(request: Request, call_next):
    method = request.method
    url = str(request.url)
    headers = dict(request.headers)
    safe_headers = {k: v for k, v in headers.items()
                    if k.lower() not in ("authorization", "cookie", "zotero-api-key")}

    _srv_logger.info("REQUEST %s %s headers=%s", method, url, json.dumps(safe_headers, ensure_ascii=False))

    response = await call_next(request)

    _srv_logger.info(
        "RESPONSE %s %s status=%s version=%s",
        method, url, response.status_code,
        response.headers.get("Last-Modified-Version", "-")
    )

    response.headers["Zotero-API-Version"] = "3"
    response.headers["Access-Control-Allow-Origin"] = "*"
    if request.method == "OPTIONS":
        response.headers["Access-Control-Allow-Headers"] = (
            "Content-Type, Zotero-API-Key, Zotero-API-Version, "
            "Zotero-Write-Token, If-Unmodified-Since-Version, "
            "If-Modified-Since-Version, Authorization"
        )
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, PATCH, HEAD, OPTIONS"
    return response


from .routers import admin, collections, deleted, groups, items, keys, mappings, searches, settings, stubs, tags  # noqa: E402

app.include_router(keys.router, tags=["keys"])
app.include_router(items.router, tags=["items"])
app.include_router(collections.router, tags=["collections"])
app.include_router(searches.router, tags=["searches"])
app.include_router(settings.router, tags=["settings"])
app.include_router(deleted.router, tags=["deleted"])
app.include_router(groups.router, tags=["groups"])
app.include_router(tags.router, tags=["tags"])
app.include_router(mappings.router, tags=["mappings"])
app.include_router(stubs.router, tags=["stubs"])
app.include_router(admin.router, tags=["admin"])


@app.get("/")
async def index():
    return {"message": "Zotero Sync Server"}


def main():
    import uvicorn
    import os
    port = int(os.environ.get("ZOTERO_PORT", "8080"))
    uvicorn.run(
        "zotero_server.main:app",
        host="0.0.0.0",
        port=port,
        reload=False,
    )


if __name__ == "__main__":
    main()
