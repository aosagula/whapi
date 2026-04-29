# Repository Guidelines

## Project Structure & Module Organization
This repository is split into `backend/` and `frontend/`. The backend is a FastAPI service with application code in `backend/app/`, organized by `api/`, `services/`, `models/`, `schemas/`, and `core/`. Database migrations live in `backend/alembic/versions/`. Backend tests are in `backend/tests/`.

The frontend is a Next.js 14 app. Routes live under `frontend/app/`, shared UI in `frontend/components/`, and API helpers in `frontend/lib/`. Unit tests are in `frontend/__tests__/`, end-to-end tests in `frontend/e2e/`, and static assets in `frontend/public/`. Supporting flow definitions live in `n8n-flows/`; longer specs and deployment notes are in `docs/`.

## Build, Test, and Development Commands
Use Docker Compose for the full local stack:

- `docker compose up --build`: starts frontend on `:3001` and backend on `:8001`.
- `cd frontend && npm run dev`: runs the Next.js app locally.
- `cd frontend && npm run build`: creates the production frontend build.
- `cd frontend && npm test`: runs Jest unit tests.
- `cd frontend && npm run test:e2e`: runs Playwright specs.
- `cd backend && pytest`: runs backend tests.
- `cd backend && ruff check .`: runs Python linting.

## Coding Style & Naming Conventions
Frontend code uses TypeScript with 2-space indentation, PascalCase for React components (`UserMenu.tsx`), and route folders that follow Next.js conventions. Prefer colocating route-specific UI under `app/` only when it is not reused elsewhere.

Backend Python follows Ruff defaults with a 100-character line limit. Use `snake_case` for modules, functions, and test files such as `test_pedidos.py`. Keep service logic in `app/services/` and HTTP handlers thin in `app/api/`.

## Testing Guidelines
Add backend tests under `backend/tests/` using `test_*.py`. Add frontend unit tests under `frontend/__tests__/` using `*.test.ts` or `*.test.tsx`, matching the current Jest config. Add browser flows to `frontend/e2e/` as `*.spec.ts`. Cover new API behavior, UI state changes, and regression paths before opening a PR.

## Commit & Pull Request Guidelines
Recent history favors short, imperative Spanish commit subjects, for example: `Agregar Fase 11...` or `Corregir integración WPPConnect...`. Keep commits focused and descriptive.

PRs should include a brief summary, affected areas (`backend`, `frontend`, `n8n-flows`, or `docs`), linked issues when applicable, and screenshots or recordings for UI changes. Note any required `.env` or migration changes explicitly.

## Security & Configuration Tips
Configuration is loaded from the root `.env`; do not commit secrets. Review `docker-compose.yml` before changing ports or host integrations, especially the PostgreSQL tunnel and `host.docker.internal` settings used by the backend container.
