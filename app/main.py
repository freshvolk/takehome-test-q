import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from pydantic import BaseModel, Field

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


class HealthResponse(BaseModel):
    status: str = Field(default="ok")


class VersionResponse(BaseModel):
    version: str = Field(
        default="unset", examples=["1.0.0", "1.0.0-dev.bb100e8.1771010967"]
    )


@app.get("/healthz", response_model=HealthResponse)
async def health_check():
    logger.info("health check success")
    return {"status": "ok"}


@app.get("/version", response_model=VersionResponse)
async def version():
    logger.info(f"returning version: {app.version}")
    return {"version": app.version}
