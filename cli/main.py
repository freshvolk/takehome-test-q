import datetime
import os
import subprocess
import sys

import typer

from cli.log import log

CTX_ENV = "K8S_CONTEXT"
APP_ENV = "APP_NAME"
APP_DEFAULT = "quilter-home-app"

app = typer.Typer(no_args_is_help=True, rich_markup_mode=None)


def env_config():
    config = {}
    config["k8s_ctx"] = os.getenv(CTX_ENV, "")
    config["app_name"] = os.getenv(APP_ENV, APP_DEFAULT)
    return config


def ephemeral_version() -> str:
    return os.getenv("EPHEM_VERSION", f"{datetime.datetime.now():%Y%m%d%H%M%S}")


@app.command()
def local():
    """run fast api locally for live reload"""
    env = os.environ.copy()
    env["APP_VERSION"] = ephemeral_version()
    return subprocess.run(
        ["poetry", "run", "fastapi", "dev"],
        check=True,
        env=env,
    )


@app.command()
def test(cov: bool = typer.Option(False, "--cov")):
    """run the test suite"""
    cmd = ["poetry", "run", "pytest"]
    if cov:
        cmd.append("--cov=app")
    log.info("running tests")
    subprocess.run(cmd, check=True)
