# quilter-home

a small python api containerized and deployed to a local kubernetes cluster via terraform. comes with a cli (`./dev`) that handles initialization, builds, deploys, environments, and cluster interactions.

## getting started

### prerequisites

you'll need these installed before anything else:

| tool | install |
|------|---------|
| **docker** | [docs.docker.com](https://docs.docker.com/get-docker/) |
| **minikube** | [minikube.sigs.k8s.io](https://minikube.sigs.k8s.io/docs/start/) |
| **terraform** | [developer.hashicorp.com](https://developer.hashicorp.com/terraform/install) |
| **poetry** | [python-poetry.org](https://python-poetry.org/docs/#installation) |
| **python 3.12+** | [python.org](https://www.python.org/downloads/) |

> if you use [asdf](https://asdf-vm.com/) or [mise](https://mise.jdx.dev/), the `.tool-versions` file has you covered.

### first run

```bash
# start minikube, init terraform, the whole thing
./dev init

# build, test, and deploy to the default environment
./dev deploy

# open port forwarding to hit the app
./dev k8s forward
# then: curl http://localhost:8000/healthz
```

that's it. `./dev` is a thin bash wrapper that checks your tools are installed, sets up poetry if needed, copies `.env.example` → `.env`, and then hands off to the python cli. if you have an existing minikube cluster, you can skip the `./dev init` step by setting the `MINIKUBE_CONTEXT` in `.env` to your cluster/profile name.

## cli usage

run `./dev` with no args for help. here are the common ones:

```bash
./dev init                    # start minikube + init terraform
./dev build                   # build docker image into minikube
./dev deploy                  # test + build + terraform apply
./dev deploy --no-test        # skip tests
./dev deploy -v 1.2.3         # deploy a specific version

./dev spin-up staging         # create 'staging' env and deploy into it
./dev teardown                # destroy resources in current env
./dev teardown staging        # destroy resources in a specific env
./dev down                    # stop minikube
./dev down --delete           # delete the minikube cluster entirely

./dev local                   # run fastapi locally with live reload
./dev test                    # run pytest
./dev test --cov              # run pytest with coverage

./dev env list                # list environments
./dev env select staging      # switch to an environment

./dev k8s logs                # stream pod logs
./dev k8s logs --no-follow    # dump logs without streaming
./dev k8s forward             # port-forward to the app
./dev k8s restart             # restart the deployment
./dev k8s versions            # show deployed versions across envs
./dev k8s pt -- get pods      # passthrough to kubectl
```

## project layout

```
.
├── app/                  # the api
│   ├── main.py           # fastapi app — /healthz and /version
│   └── Dockerfile        # multi-stage build, non-root user
├── cli/                  # the dev cli
│   ├── main.py           # typer commands (build, deploy, env, k8s, etc)
│   └── log.py            # colored logging helper
├── tf/                   # terraform config
│   ├── main.tf           # k8s deployment, service, namespace
│   ├── provider.tf       # kubernetes provider config
│   └── variables.tf      # app_name, app_version, context
├── tests/                # pytest suite
│   └── test_main.py      # api endpoint tests
├── dev                   # cli entrypoint (bash wrapper)
├── pyproject.toml        # poetry config, dependencies, cli script
├── .env.example          # default env vars (minikube context, port)
└── .tool-versions        # pinned tool versions for asdf/mise
```

## environments

environments are implemented as terraform workspaces, each mapping to a kubernetes namespace. the default workspace is `dev`.

```bash
./dev spin-up my-feature       # creates workspace + namespace, then deploys
./dev env list                 # see what's out there
./dev env select my-feature    # switch to it
./dev teardown my-feature      # tear it down when you're done
```

this makes it easy to run multiple versions side-by-side — handy for testing or demoing feature branches.

## how it works (briefly)

1. **init** — starts a minikube cluster (profile name from `.env`) and runs `terraform init`
2. **build** — points your local docker at minikube's daemon (`minikube docker-env`), then builds the image with a version tag baked in
3. **deploy** — runs tests, builds, then `terraform apply` against the current workspace. the image version is passed as a terraform variable
4. **environments** — each terraform workspace creates its own k8s namespace, so resources are isolated per environment

## architecture & design decisions

#### why python for the cli?

Initially, it seemed like it would be nice to gain the benefits from typer for the cli. For the majority of the implementation this was true, but the k8s specific commands were a bit of a pain to implement in python. There was going to be a nice requests command to make direct requests from the cli but the complexity of working with k8s slowed things down too much.

#### why poetry?

Poetry simplifies the dependency management and development environment greatly. This made it possible to functionally not worry about the user's python setup, just ensuring they have poetry installed.

#### why workspaces as the unit of deployment?

Workspaces provide a natural way to isolate environments and manage their lifecycle. They are a first class concept in terraform and make it easy to reason about the state of each environment. By linking each workspace to a namespace, we can easily reason about the state of each environment and manage their lifecycle. Banning the use of default was probably overkill, but it forces a certain discipline in thinking about environments.

#### why is it so in-depth?

Honestly, mostly was just thinking about what would be nice to have if I was doing development. Ideally this kind of cli would be a build and maintain once proposition that then can be passed around to different projects as needed.
