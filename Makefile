.PHONY: dev backend frontend install test

install:
	cd backend && python3 -m venv .venv && . .venv/bin/activate && pip install -e ".[dev]"
	cd frontend && npm install

backend:
	cd backend && . .venv/bin/activate && uvicorn app.main:app --reload --port 8000

frontend:
	cd frontend && npm run dev

dev:
	@echo "Starting backend (:8000) and frontend (:5173)..."
	@$(MAKE) -j2 backend frontend

test:
	cd backend && . .venv/bin/activate && pytest -q

build:
	cd frontend && npm run build
