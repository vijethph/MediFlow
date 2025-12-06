# healthcare-patient-management-system

This repository will be renamed later.

### Basic instructions to develop

1. Clone repository (or fork and raise a PR if you want to do it the complex way)
2. Create new branch using the name of your service in kebab case
3. Use any tool to build your service, but at the end of the day anyone in the team should be able to clone it and run it. Start with simple features, and then move on to writing tests, and containerize it in Docker.
4. Use Zoom whiteboard for architecture diagrams, and shared Google doc to draft project report for your service

### Draft architecture diagram

![Healthcare Patient Management System](/docs/healthcare-architecture.drawio.png "Draft architecture for the system")

#### Quick testing of billing-service

Local development verification:

```bash
# 1. Install dependencies
pipenv install
pipenv shell

# 2. Set up PostgreSQL database locally
# Option A: Use Docker
docker run --name billing-postgres -e POSTGRES_PASSWORD=billing_secure_password -e POSTGRES_DB=billing_db -p 5432:5432 -d postgres:13

# Option B: Use local PostgreSQL
createdb billing_db

# 3. Run database initialization script
./scripts/init_billing_db.sh

# 4. Start RabbitMQ (for event handling)
docker run --name billing-rabbitmq -p 5672:5672 -p 15672:15672 -e RABBITMQ_DEFAULT_USER=admin -e RABBITMQ_DEFAULT_PASS=rabbitmq_secure_password -d rabbitmq:4.0-management-alpine

# 5. Run the service
cd services/billing-service
uvicorn main:app --reload --port 8004

# 6. Access API docs
# Open http://localhost:8004/docs

## stop and clean up everything ##

# Docker compose:
./scripts/test_docker_setup.sh

## stop and clean up everything ##

# K8s
minikube start --cpus=4 --memory=8192
minikube docker-env
eval $(minikube -p minikube docker-env)
minikube addons enable metrics-server

./scripts/k8s_manage.sh infra

# Build service image
./scripts/k8s_manage.sh build

# Deploy billing service
./scripts/k8s_manage.sh deploy
./scripts/k8s_manage.sh test

./scripts/test_k8s_deployment.sh

## stop and clean up everything ##
./scripts/k8s_manage.sh clean
```

### Quick testing of entire application

```bash
# docker compose
./scripts/docker_manage.sh start patient-service # individual service

./scripts/docker_manage.sh start all # all services

./scripts/docker_manage.sh test all # test all services

## Access API docs: https://localhost:8000/billing/docs  - billing service

./scripts/docker_manage.sh logs patient-service  # Specific service logs

./scripts/docker_manage.sh clean # clean up everything



# kubernetes

minikube start --cpus=4 --memory=8192
minikube docker-env
eval $(minikube -p minikube docker-env)
minikube addons enable metrics-server

./scripts/k8s_manage.sh infra

# Build service image
./scripts/k8s_manage.sh build

# Deploy billing service
./scripts/k8s_manage.sh deploy
./scripts/k8s_manage.sh test

## Access Kong gateway
minikube service -n kong kong-proxy --url

## Open the URL shown in terminal output (example: http://127.0.0.1:45389/billing/docs) with the suffix "<service-name>/docs" to access Swagger)

## Access services:

./scripts/test_k8s_deployment.sh

## stop and clean up everything ##
./scripts/k8s_manage.sh clean

```
