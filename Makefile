APP_MODULE=app.main:app
HOST=127.0.0.1
PORT=8001
ALEMBIC=alembic
ALEMBIC_CONFIG=alembic.ini
GCP_INSTANCE := instance-free
GCP_ZONE     := us-central1-c

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

expose:
	ssh -p 443 -R0:localhost:$(PORT) qr@free.pinggy.io

## SSH into VM and run prod.sh non-interactively
deploy:
	gcloud compute ssh $(GCP_INSTANCE) --zone=$(GCP_ZONE) \
		--command='cd ~/whisp && sudo bash prod.sh'