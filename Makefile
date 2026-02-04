.PHONY: start stop restart build rebuild logs clean help pronunciation pronunciations etymology etymologies cleanup-audio

# Default target
help:
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@echo "  start           - Start the Docker stack (detached)"
	@echo "  stop            - Stop the Docker stack"
	@echo "  restart         - Restart the Docker stack"
	@echo "  build           - Build the Docker images"
	@echo "  rebuild         - Force rebuild (no cache)"
	@echo "  logs            - Follow container logs"
	@echo "  clean           - Stop and remove containers, volumes"
	@echo ""
	@echo "  pronunciation   - Generate IPA + audio for a word (usage: make pronunciation WORD=abyss)"
	@echo "  pronunciations  - Generate IPA + audio for all dictionary entries"
	@echo "  etymology       - Fetch etymology for a word (usage: make etymology WORD=abyss)"
	@echo "  etymologies     - Fetch etymology for all dictionary entries"
	@echo "  cleanup-audio   - Remove orphaned audio files (dry run)"
	@echo "  cleanup-audio-delete - Remove orphaned audio files (actually delete)"
	@echo ""
	@echo "  help            - Show this help message"

start:
	docker compose up -d
	@echo ""
	@echo "Server starting at http://localhost:4000"

stop:
	docker compose down

restart: stop start

build:
	docker compose build

rebuild:
	docker compose build --no-cache

logs:
	docker compose logs -f

clean:
	docker compose down -v

# Pronunciation tools (runs in Docker)
PYTHON_DOCKER = docker run --rm -v $(PWD):/app -w /app python:3.12-slim

pronunciation-install:
	$(PYTHON_DOCKER) pip install --root-user-action=ignore -r scripts/requirements.txt

pronunciation:
ifndef WORD
	@echo "Error: WORD is required. Usage: make pronunciation WORD=abyss"
	@exit 1
endif
	$(PYTHON_DOCKER) sh -c "pip install --root-user-action=ignore -q -r scripts/requirements.txt && python scripts/pronunciation.py $(WORD)"

pronunciations:
	$(PYTHON_DOCKER) sh -c "pip install --root-user-action=ignore -q -r scripts/requirements.txt && python scripts/pronunciation.py --all"

pronunciations-force:
	$(PYTHON_DOCKER) sh -c "pip install --root-user-action=ignore -q -r scripts/requirements.txt && python scripts/pronunciation.py --all --force"

# Etymology tools (runs in Docker)
etymology:
ifndef WORD
	@echo "Error: WORD is required. Usage: make etymology WORD=abyss"
	@exit 1
endif
	$(PYTHON_DOCKER) sh -c "pip install --root-user-action=ignore -q -r scripts/requirements.txt && python scripts/etymology.py $(WORD)"

etymologies:
	$(PYTHON_DOCKER) sh -c "pip install --root-user-action=ignore -q -r scripts/requirements.txt && python scripts/etymology.py --all"

etymologies-force:
	$(PYTHON_DOCKER) sh -c "pip install --root-user-action=ignore -q -r scripts/requirements.txt && python scripts/etymology.py --all --force"

# Cleanup tools
cleanup-audio:
	$(PYTHON_DOCKER) sh -c "pip install --root-user-action=ignore -q pyyaml && python scripts/cleanup_audio.py"

cleanup-audio-delete:
	$(PYTHON_DOCKER) sh -c "pip install --root-user-action=ignore -q pyyaml && python scripts/cleanup_audio.py --delete"
