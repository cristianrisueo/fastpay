# Comandos del proyecto FastPay. Help los lista con su descripción.
.PHONY: help up stop down destroy psql migrate migration rollback run check test test-unit test-integration coverage

# Puerto local de cada API (los mismos que en el contrato HTTP)
PORT_auth = 8001
PORT_wallet = 8002

# Servicios que existen ahora mismo: las carpetas de services/
SERVICES := $(notdir $(wildcard services/*))
# Con s=... los comandos actúan sobre ese servicio; sin s, sobre todos
TARGETS := $(if $(s),$(s),$(SERVICES))

# Falla con un mensaje claro si falta s=. Se usa en los comandos que solo tienen sentido para UN servicio
need-s = $(if $(s),,$(error Falta el servicio: añade s=auth o s=wallet))

# Ejecuta $(CMD) dentro de la carpeta de cada servicio elegido, y para en el primer fallo
EACH = for svc in $(TARGETS); do echo "==> $$svc"; (cd services/$$svc && $(CMD)) || exit 1; done

help:  ## Muestra esta ayuda
	@grep -E '^[a-zA-Z0-9_-]+:.*## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*## "}; {printf "  %-18s %s\n", $$1, $$2}'

# --- Bases de datos (Docker): afectan a las dos ---

up:  ## Levanta las dos bases de datos y espera a que estén sanas
	docker compose up -d --wait

stop:  ## Apaga los contenedores sin borrarlos
	docker compose stop

down:  ## Elimina los contenedores (los datos se conservan en los volúmenes)
	docker compose down

destroy:  ## Elimina los contenedores Y LOS DATOS
	docker compose down -v

psql:  ## Consola SQL de la base de datos de un servicio. Uso: make psql s=auth
	$(need-s)
	docker compose exec db-$(s) psql -U $(s) -d $(s)_db

# --- Migraciones (siempre de un servicio) ---

migrate:  ## Aplica las migraciones pendientes. Uso: make migrate s=auth
	$(need-s)
	cd services/$(s) && uv run alembic upgrade head

migration:  ## Genera una migración desde los modelos. Uso: make migration s=auth m="mensaje"
	$(need-s)
	@test -n "$(m)" || (echo 'Falta el mensaje: make migration s=auth m="crear users"' && exit 1)
	cd services/$(s) && uv run alembic revision --autogenerate -m "$(m)"

rollback:  ## Deshace la última migración. Uso: make rollback s=auth
	$(need-s)
	cd services/$(s) && uv run alembic downgrade -1

# --- Desarrollo ---

run:  ## Arranca la API con recarga automática. Uso: make run s=auth (auth en 8001, wallet en 8002)
	$(need-s)
	cd services/$(s) && uv run uvicorn $(s).main:app --reload --port $(PORT_$(s))

check: CMD = uv run ruff format . && uv run ruff check . && uv run mypy src tests
check:  ## Formatea, pasa el linter y los tipos. Sin s=, en todos los servicios
	@$(EACH)

# --- Tests ---

test: CMD = uv run pytest
test:  ## Unitarios + integración (necesita Docker). Sin s=, en todos los servicios
	@$(EACH)

test-unit: CMD = uv run pytest tests/unit
test-unit:  ## Solo unitarios (sin Docker)
	@$(EACH)

test-integration: CMD = uv run pytest tests/integration
test-integration:  ## Solo integración (PostgreSQL efímero con testcontainers)
	@$(EACH)

coverage: CMD = uv run pytest --cov --cov-report=term --cov-report=html
coverage:  ## Tests con informe de cobertura (terminal y htmlcov/index.html)
	@$(EACH)