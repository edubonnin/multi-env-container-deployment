SHELL := /bin/zsh

COMPOSE_DEV := docker compose --env-file .env.dev -f docker-compose.dev.yml
COMPOSE_PROD := docker compose --env-file .env.prod -f docker-compose.prod.yml

.PHONY: dev-up dev-down dev-build dev-logs dev-psql dev-restart dev-stop dev-db-test \
	prod-up prod-down prod-build prod-logs prod-stop prod-restart prod-psql prod-redis-cli prod-set-message help

dev-up: ## Levanta el entorno de desarrollo en segundo plano
	$(COMPOSE_DEV) up -d --build

dev-down: ## Detiene y elimina los contenedores de desarrollo
	$(COMPOSE_DEV) down --remove-orphans

dev-build: ## Construye las imágenes del entorno de desarrollo
	$(COMPOSE_DEV) build

dev-logs: ## Muestra los logs agregados del entorno de desarrollo
	$(COMPOSE_DEV) logs -f --tail=100

dev-psql: ## Abre una consola psql contra la base de datos de desarrollo
	$(COMPOSE_DEV) exec postgres sh -c 'PGPASSWORD="$$POSTGRES_PASSWORD" psql -U "$$POSTGRES_USER" -d "$$POSTGRES_DB"'

dev-restart: ## Reinicia todos los servicios del entorno de desarrollo
	$(COMPOSE_DEV) restart

dev-stop: ## Detiene los servicios del entorno de desarrollo (sin eliminar volúmenes)
	$(COMPOSE_DEV) stop

dev-db-test: ## Comprueba la conectividad con PostgreSQL en desarrollo
	$(COMPOSE_DEV) exec postgres pg_isready -U "$$POSTGRES_USER" -d "$$POSTGRES_DB"

prod-up: ## Levanta el entorno de producción en segundo plano
	$(COMPOSE_PROD) up -d --build

prod-down: ## Detiene y elimina los contenedores de producción
	$(COMPOSE_PROD) down --remove-orphans

prod-build: ## Construye las imágenes del entorno de producción
	$(COMPOSE_PROD) build

prod-logs: ## Muestra los logs agregados del entorno de producción
	$(COMPOSE_PROD) logs -f --tail=100

prod-stop: ## Detiene los servicios del entorno de producción (sin eliminar volúmenes)
	$(COMPOSE_PROD) stop

prod-restart: ## Reinicia todos los servicios del entorno de producción
	$(COMPOSE_PROD) restart

prod-psql: ## Abre una consola psql contra la base de datos de producción
	$(COMPOSE_PROD) exec postgres sh -c 'PGPASSWORD="$$POSTGRES_PASSWORD" psql -U "$$POSTGRES_USER" -d "$$POSTGRES_DB"'

prod-redis-cli: ## Inicia una consola redis-cli en el entorno de producción
	$(COMPOSE_PROD) exec redis redis-cli

prod-set-message: ## Guarda un mensaje en Redis (usar: make prod-set-message MESSAGE="Hola")
	$(COMPOSE_PROD) exec --env MESSAGE="$(MESSAGE)" redis sh -c 'redis-cli set "$${REDIS_MESSAGE_KEY:-app:message}" "$${MESSAGE:-Hola desde Redis}"'
