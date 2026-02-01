run:
	python -m escrow_bot.app

test:
	pytest

lint:
	ruff check escrow_bot tests

docker-build:
	docker build -t escrow-bot .

docker-up:
	docker compose up -d

docker-logs:
	docker compose logs -f

docker-down:
	docker compose down

docker-restart:
	docker compose down && docker compose up -d

backup-db:
	@mkdir -p backups
	@ts=$$(date +%Y%m%d%H%M%S); cp data/escrow.db backups/escrow-$$ts.db

restore-db:
	@echo "Usage: make restore-db FILE=path"
	@test -n "$(FILE)"
	@cp $(FILE) data/escrow.db
