.PHONY: install dev-api dev-web lint format test test-api test-web e2e build docker ci

install:  ## install backend + frontend dependencies
	pip install -r requirements-dev.txt
	cd web && npm ci && npx playwright install chromium

dev-api:  ## API on :8000
	python -m uvicorn index:app --app-dir api --reload --port 8000

dev-web:  ## React dev server on :5173 (proxies /api to :8000)
	cd web && npm run dev

lint:
	ruff check . && ruff format --check .

format:
	ruff check --fix . && ruff format .

test-api:
	pytest --cov --cov-report=term-missing

test-web:
	cd web && npm test

test: test-api test-web

e2e: build
	cd web && npm run e2e

build:
	cd web && npm run build

docker:
	docker compose up --build

ci: lint test e2e  ## what GitHub Actions runs
