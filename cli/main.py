import datetime
import os
import subprocess

import typer

from cli.log import log

CTX_ENV = "MINIKUBE_CONTEXT"
APP_ENV = "APP_NAME"
APP_DEFAULT = "quilter-home-app"

app = typer.Typer(no_args_is_help=True, rich_markup_mode=None)


def _env_config():
    config = {}
    config["ctx_name"] = os.getenv(CTX_ENV, "")
    config["app_name"] = os.getenv(APP_ENV, APP_DEFAULT)
    return config


def _ephemeral_version() -> str:
    return os.getenv("EPHEM_VERSION", f"{datetime.datetime.now():%Y%m%d%H%M%S}")


def _mkcmd(
    *args, profile: str, check: bool = True, **kwargs
) -> subprocess.CompletedProcess[str]:
    cmd = ["minikube", f"-p={profile}"] + list(args)
    return subprocess.run(cmd, check=check, **kwargs)


@app.command()
def init():
    """initializes minikube environment"""
    config = _env_config()
    mk_profile = config["ctx_name"]
    if mk_profile == "":
        log.error(
            f"{CTX_ENV} not set, .env might be missing. be sure to run via ./dev in project root"
        )
        raise typer.Exit(1)
    status = _mkcmd(
        "status",
        profile=mk_profile,
        capture_output=True,
        text=True,
        check=False,
    )
    if status.returncode == 0:
        log.info(f"found running {mk_profile}")
    elif typer.confirm(f"start minikube cluster '{mk_profile}'?", default=True):
        log.info("starting minikube...")
        _mkcmd("start", profile=mk_profile, check=True)
    else:
        log.error("initialization aborted")
        raise typer.Exit(1)

    # kubectl use context
    # tf init

    log.info("environment initialized!")


@app.command()
def down(
    delete: bool = typer.Option(False, "--delete", help="delete minikube cluster"),
):
    """stops or deletes"""
    config = _env_config()
    if not delete:
        _mkcmd("stop", profile=config["ctx_name"])
    else:
        _mkcmd("delete", profile=config["ctx_name"])


@app.command()
def local():
    """run fast api locally for live reload"""
    env = os.environ.copy()
    env["APP_VERSION"] = _ephemeral_version()
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
