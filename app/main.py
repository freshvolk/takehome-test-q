import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI

VERSION_ENV = "APP_VERSION"

logger = logging.getLogger("uvicorn")
logger.info("logger intialized")


@asynccontextmanager
async def lifespan(app: FastAPI):
    version = os.getenv(VERSION_ENV, "unset")
    app.version = version
    logger.info(f"started with version {version}")
    yield


app = FastAPI(lifespan=lifespan)
logger.info("app initialized")


@app.get("/healthz")
async def health_check():
    logger.info("health check success")
    return {"status": "ok"}


@app.get("/version")
async def version():
    logger.info(f"returning version: {app.version}")
    return {"version": app.version}
