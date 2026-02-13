#### todo

- [x] poetry config
- [x] app
- [x] tests
- [x] cli - basic
  - [x] wrapper
    - [x] check deps: poetry, doker, tf, minikube
    - [x] run poetry install
    - [x] copy .env.example to .env
    - [x] run cli through poetry
  - [x] local: fastapi dev
  - [x] test: pytest
- [x] dockerfile
- [x] cli-init: minikube start (profile name from .env)
- [x] cli-build: minikube docker-env | docker build (use labels)
- [x] cli-down: stop/delete minikube, clean docker
- [x] terraform
- [x] cli-deploy: build + terraform (namespace based on tf workspace)
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
