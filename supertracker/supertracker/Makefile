# =====================================================================
# SuperTracker — atajos de operación
# Uso:  make <objetivo>
# Requiere: Docker + Docker Compose v2
# =====================================================================

# Permite usar tanto "docker compose" (v2) como "docker-compose" (v1).
COMPOSE ?= docker compose

.PHONY: help env up build down stop logs ps restart clean

help: ## Muestra esta ayuda
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

env: ## Crea .env a partir de .env.example si no existe
	@test -f .env || (cp .env.example .env && echo "Creado .env desde .env.example")

up: env ## Levanta todo el sistema (build + arranque)
	$(COMPOSE) up --build -d
	@echo "Listo. Frontend: http://localhost  ·  API: http://localhost/api  ·  RabbitMQ UI: http://localhost:15672"

build: ## Construye las imágenes sin arrancar
	$(COMPOSE) build

down: ## Detiene y elimina contenedores y redes (conserva volúmenes)
	$(COMPOSE) down

stop: ## Detiene los contenedores sin eliminarlos
	$(COMPOSE) stop

restart: ## Reinicia todos los servicios
	$(COMPOSE) restart

logs: ## Sigue los logs de todos los servicios
	$(COMPOSE) logs -f

ps: ## Lista el estado de los servicios
	$(COMPOSE) ps

clean: ## Detiene y elimina TODO, incluidos los volúmenes (¡borra la base de datos!)
	$(COMPOSE) down -v
