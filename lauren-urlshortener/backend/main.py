"""Lauren URL Shortener — ASGI entry point."""

from __future__ import annotations

import os

from lauren import LaurenFactory
from lauren.logging import default_logger

from app.modules import AppModule


def create_app():
    return LaurenFactory.create(
        AppModule,
        logger=default_logger(),
        docs_url="/docs",
        openapi_info={
            "title": "Lauren URL Shortener API",
            "version": "1.0.0",
            "description": "URL shortener built with the Lauren framework — no pydantic.",
        },
    )


app = create_app()

if __name__ == "__main__":
    import uvicorn

    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run("main:app", host=host, port=port, reload=True)
