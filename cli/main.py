import datetime
import os
import subprocess
from pathlib import Path
from typing import Any, Literal, Optional, overload

import typer

from cli.log import log

CTX_ENV = "MINIKUBE_CONTEXT"
APP_ENV = "APP_NAME"
APP_DEFAULT = "quilter-home-app"

TF_DIR = "tf"

app = typer.Typer(no_args_is_help=True, rich_markup_mode=None)


def _env_config():
    config = {}
    config["ctx_name"] = os.getenv(CTX_ENV, "")
    config["app_name"] = os.getenv(APP_ENV, APP_DEFAULT)
    return config


def _ephemeral_version() -> str:
    return os.getenv("EPHEM_VERSION", f"{datetime.datetime.now():%Y%m%d%H%M%S}")


@overload
def _mkcmd(
    *args: str, profile: str, return_cmd: Literal[True], **kwargs: Any
) -> list[str]: ...
@overload
def _mkcmd(
    *args: str,
    profile: str,
    return_cmd: Literal[False] = False,
    check: bool = True,
    **kwargs: Any,
) -> subprocess.CompletedProcess[Any]: ...
def _mkcmd(
    *args, profile: str, return_cmd: bool = False, check: bool = True, **kwargs
) -> list[str] | subprocess.CompletedProcess[str]:
    cmd = ["minikube", f"-p={profile}"] + list(args)
    if return_cmd:
        return cmd
    return subprocess.run(cmd, check=check, **kwargs)


def _tfcmd(
    *args: str, tfvars: dict[str, str] | None = None, check: bool = True, **kwargs
):
    cmd = ["terraform", f"-chdir={TF_DIR}"] + list(args)
    if tfvars:
        cmd += [f"-var={var}={value}" for var, value in tfvars.items()]
    log.debug(cmd)
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

    if not Path(f"{TF_DIR}/.terraform").exists():
        _tfcmd("init")

    # use dev if only default exists

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


@app.command()
def build(
    version: Optional[str] = typer.Argument(
        None, help="explicitly defined version to build image as"
    ),
):
    """build the docker image"""
    config = _env_config()

    if not version:
        version = _ephemeral_version()

    log.info(f"building version: {version}")

    docker_build_cmd = [
        "docker",
        "build",
        "-t",
        f"{config['app_name']}:{version}",
        "--label",
        "from-quilter-cli=true",
        "--build-arg",
        f"BUILD_VERSION={version}",
        "-f",
        "app/Dockerfile",
        ".",
    ]

    minikube_env_cmd = _mkcmd(
        "docker-env", "--shell", "bash", return_cmd=True, profile=config["ctx_name"]
    )

    log.debug(minikube_env_cmd)

    log.debug(docker_build_cmd)

    eval_cmd = f"eval $({' '.join(minikube_env_cmd)}) && {' '.join(docker_build_cmd)}"

    log.debug(eval_cmd)

    subprocess.run(
        eval_cmd,
        check=True,
        shell=True,
        executable="/bin/bash",
    )
    log.info(f"built: {config['app_name']}:{version}")


@app.command()
def deploy(
    version: Optional[str] = typer.Option(
        None,
        "--version",
        "-v",
        help="version to build, default: dev version in the form <project>-dev.gitsha.timestamp will be generated",
    ),
    no_build: bool = typer.Option(
        False, "--no-build", help="skip build, requires version"
    ),
    no_test: bool = typer.Option(False, help="skip tests"),
):
    """optionally test and build then deploy specified [version]. if no version is provided, must build"""
    config = _env_config()

    if not version:
        if no_build:
            raise typer.BadParameter("if you skip build, you must provide a version")
        version = _ephemeral_version()

    if not no_test:
        test()

    if not no_build:
        build(version)

    tfvars = {
        "app_version": version,
        "app_name": config["app_name"],
        "kubectl_context": config["ctx_name"],
    }

    _tfcmd("apply", "-auto-approve", tfvars=tfvars)
