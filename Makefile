.PHONY: dev dev-bg down backend-test frontend-test lint format migrate makemigrations seed

dev:
	docker compose up --build

dev-bg:
	docker compose up -d

down:
	docker compose down

migrate:
	docker compose exec backend python manage.py migrate

makemigrations:
	docker compose exec backend python manage.py makemigrations

seed:
	docker compose exec backend python manage.py seed_demo_data

backend-test:
	docker compose exec backend pytest -q

frontend-test:
	docker compose exec frontend npm run test

lint:
	docker compose exec backend ruff check .
	docker compose exec backend mypy .
	docker compose exec frontend npm run lint
	docker compose exec frontend npm run typecheck

format:
	docker compose exec backend ruff format .
	docker compose exec frontend npm run format
