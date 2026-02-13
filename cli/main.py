import datetime
import os
import subprocess
from pathlib import Path
from typing import Annotated, Any, Literal, Optional, overload

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


def _kubecmd(*args, ns: str | None = None, ctx: str | None = None, **kwargs):
    cmd = ["kubectl"]
    if ctx:
        cmd += ["--context", ctx]
    if ns:
        cmd += ["-n", ns]
    return subprocess.run(cmd + list(args), **kwargs)


def _tfcmd(
    *args: str, tfvars: dict[str, str] | None = None, check: bool = True, **kwargs
):
    cmd = ["terraform", f"-chdir={TF_DIR}"] + list(args)
    if tfvars:
        cmd += [f"-var={var}={value}" for var, value in tfvars.items()]
    log.debug(cmd)
    return subprocess.run(cmd, check=check, **kwargs)


def _tf_switch_workspace(env: str, create: bool = False):
    if create:
        return _tfcmd(
            "workspace", "select", "-or-create", env, capture_output=True, text=True
        )
    else:
        return _tfcmd("workspace", "select", env, capture_output=True, text=True)


def _tf_get_workspaces() -> dict[str, bool]:
    ws_dict = {}
    workspaces = _tfcmd("workspace", "list", capture_output=True, text=True)
    for line in workspaces.stdout.splitlines():
        active = False
        if "default" in line:
            continue
        env_name = line.strip()
        if "*" in line:
            active = True
            env_name = env_name.split()[1]
        ws_dict[env_name] = active

    return ws_dict


def _tf_current_workspace() -> str | None:
    workspaces = _tf_get_workspaces()
    for ws_name in workspaces:
        if workspaces[ws_name]:
            return ws_name
    return None


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

    current_ws = _tf_current_workspace()
    if not current_ws:
        log.info("not on recongized environment, switching to/creating dev")
        _tf_switch_workspace("dev", create=True)

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


@app.command("spin-up")
def spin_up(
    env: Annotated[
        str | None,
        typer.Argument(
            help="environment to spin-up, if it doesn't exist it will be created. defaults to current"
        ),
    ] = None,
    version: str | None = typer.Option(
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
    """spin-up (switch to then deploy into) environment. will create if doesn't exist."""
    if not version:
        if no_build:
            raise typer.BadParameter("if you skip build, you must provide a version")
        version = _ephemeral_version()

    if not no_test:
        test()

    if env:
        _tf_switch_workspace(env, create=True)

    deploy(version, no_build, no_test)


@app.command("teardown")
def teardown(
    env: Annotated[
        str | None,
        typer.Argument(help="environment to teardown. defaults to current"),
    ] = None,
    delete: bool = typer.Option(
        False, help="if you want to delete the environment as well as destroy resources"
    ),
):
    """destroys all resources in environment, will optionally delete the environment as well"""
    config = _env_config()

    envs = _tf_get_workspaces()

    if env not in envs:
        log.error(f"environment '{env}' doesn't appear to exist")
        raise typer.Exit(1)

    current_env = _tf_current_workspace()

    if not current_env:
        log.error(
            "there appears to be no active environment! this really shouldn't happen!"
        )
        raise typer.Exit(7)

    if env == current_env and delete:
        log.error(
            f"environment '{env} is active, please switch to a different environment before deleting"
        )
        raise typer.Exit(1)

    if delete:
        if not typer.confirm(f"teardown and delete '{env}'?", default=False):
            return

    tfvars = {
        "app_version": "any_value_works",
        "app_name": config["app_name"],
        "kubectl_context": config["ctx_name"],
    }

    _tf_switch_workspace(env)

    _tfcmd("destroy", "-auto-approve", tfvars=tfvars)
    log.info(f"destroyed all resources in {env}")

    _tf_switch_workspace(current_env)

    if delete:
        destroy = _tfcmd("workspace", "delete", env, check=False)
        if destroy.returncode == 0:
            log.info(f"deleted {env}")
        else:
            log.error(f"failed to delete env '{env}'")
            log.error(destroy.stdout)
            log.error(destroy.stderr)
            raise typer.Exit(1)


env_app = typer.Typer(help="manage environments")
app.add_typer(env_app, name="env")


@env_app.command("list")
def env_list():
    """lists available and selected envs"""
    envs = _tf_get_workspaces()
    header = "existing environments"
    print(header)
    print("=" * len(header))
    for env in envs:
        print(f"{env}\t{'(selected)' if envs[env] else ''}")


@env_app.command("select")
def env_select(
    env: Annotated[
        str,
        typer.Argument(help="environment to switch to, can't be 'default'"),
    ],
    create: bool = typer.Option(False, help="create if env doesn't exist"),
):
    try:
        _tf_switch_workspace(env, create)
    except subprocess.CalledProcessError as e:
        log.error(
            "make sure the environment exists before you switch to it or use --create to create it if it doesn't"
        )
        raise typer.Exit(1)
    except Exception as e:
        log.error(f"something unexpected happened: {type(e).__name__}")
        raise


k8s_app = typer.Typer(help="kubernetes operations")
app.add_typer(k8s_app, name="k8s")


@k8s_app.command(
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True}
)
def pt(
    ctx: typer.Context,
    env: str | None = typer.Option(
        None, help="environment to target, defaults to current"
    ),
):
    """passthrough to kubectl. usage: dev k8s pt -- get pods"""
    config = _env_config()
    args = ctx.args
    if not env:
        env = _tf_current_workspace()
    ns = env
    log.info(f"kubectl -n {ns}: {' '.join(args)}")
    cmd = ["kubectl", "--context", config["ctx_name"], "-n", ns] + args
    os.execvp("kubectl", cmd)

@k8s_app.command()
def logs(
    env: str = typer.Option(None),
    follow: bool = typer.Option(True, "--follow/--no-follow"),
):
    """stream logs from app pods"""
    config = _env_config()
    
    current_env = _tf_current_workspace()
    
    if not current_env:
        log.error(
            "there appears to be no active environment! this really shouldn't happen!"
        )
        raise typer.Exit(7)
    
    args = ["logs", "-l", f"app={config["app_name"]}"]
    
    if follow:
        args.append("-f")
    _kubecmd(*args, ns=current_env, check=True)