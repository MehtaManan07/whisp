# Makefile for FastAPI + Alembic project

help:
	@echo "Usage:"
	@echo "  make run             - Run the FastAPI server"
	@echo "  make migrate         - Apply Alembic migrations"
	@echo "  make makemigration msg='message' - Create migration"
	@echo "  make test            - Run tests"


# Configs
APP_MODULE=app.main:app
HOST=127.0.0.1
PORT=8000
ALEMBIC=alembic
ALEMBIC_CONFIG=alembic.ini

# Run FastAPI server
run:
	uvicorn $(APP_MODULE) --host $(HOST) --port $(PORT) --reload

# Alembic commands
migrate:
	$(ALEMBIC) -c $(ALEMBIC_CONFIG) upgrade head

# Create Alembic revision with a custom message: make makemigration msg="your message"
makemigration:
ifndef msg
	$(error You must provide a message using msg="your message")
endif
	$(ALEMBIC) -c $(ALEMBIC_CONFIG) revision --autogenerate -m "$(msg)"


downgrade:
	$(ALEMBIC) -c $(ALEMBIC_CONFIG) downgrade -1

# Show Alembic current version
dbversion:
	$(ALEMBIC) -c $(ALEMBIC_CONFIG) current

# Clean __pycache__ and .pyc files
clean:
	find . -type d -name '__pycache__' -exec rm -r {} +
	find . -type f -name '*.pyc' -delete
