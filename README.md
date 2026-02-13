#### todo

- [x] poetry config
- [ ] app
- [ ] tests
- [ ] cli - basic
  - [ ] wrapper
    - [ ] check deps: poetry, doker, tf, minikube
    - [ ] run poetry install
    - [ ] copy .env.example to .env
    - [ ] run cli through poetry
  - [ ] local: fastapi dev
- [ ] dockerfile
- [ ] cli-init: minikube start (profile name from .env)
- [ ] cli-build: minikube docker-env | docker build (use labels)
- [ ] cli-down: stop/delete minikube, clean docker
- [ ] terraform
- [ ] cli-deploy: build + terraform (namespace based on tf workspace)
- [ ] cli-spin-up: deploy
- [ ] cli-teardown: terraform destroy on current or --all
- [ ] cli-env list: terraform workspace list (plus status?)
- [ ] cli-env select: terraform workspace select
  - [ ] env delete: teardown and destroy workspace
- [ ] passthrough k8s commands
- [ ] cli-k8s
  - [ ] log
  - [ ] versions
  - [ ] restart
  - [ ] request
  - [ ] tunnel
- [ ] readme


# quilter-app
