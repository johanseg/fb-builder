# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Townsquare Interactive Ad Creative Studio — AI-powered full-stack app for automating Facebook ad lifecycle: competitor research, AI ad generation, campaign management, and performance reporting. Built for Townsquare Interactive's local marketing team.

- **Frontend**: React 19 + Vite 7 + TailwindCSS
- **Backend**: Python FastAPI 0.104
- **Database**: PostgreSQL (Railway) via SQLAlchemy 2.0 + Alembic
- **Storage**: Cloudflare R2 (production), local `uploads/` (dev)
- **AI**: Google Gemini (copy/vision), Fal.ai (images)
- **Hosting**: Railway (3 services: fb-builder, frontend, Postgres)

## Development Commands

### Backend

```bash
cd backend
source venv/bin/activate                    # create: python3 -m venv venv
pip install -r requirements.txt
pip install -r requirements-dev.txt         # black, isort, flake8, bandit, pytest

uvicorn app.main:app --reload --port 8000   # dev server
# API docs at http://localhost:8000/api/v1/docs

python init_db.py                           # create tables + seed roles + admin user (reads ADMIN_EMAIL/ADMIN_PASSWORD env)
alembic upgrade head                        # apply migrations
alembic revision --autogenerate -m "desc"   # generate migration

pytest                                      # all tests
pytest tests/unit/ -v                       # unit only
pytest tests/unit/test_uploads.py -v        # single file
pytest --cov=app                            # with coverage

black app/ && isort app/ && flake8 app/     # format + lint
bandit -r app/                              # security scan
```

### Frontend

```bash
cd frontend
npm install
npm run dev                     # dev server at localhost:5173
npm run build                   # production build
npm run lint                    # eslint
npm run test:unit               # vitest
npm run test:unit:watch         # vitest watch mode
npm run test:smoke              # agent-browser e2e tests
npm run test:all                # unit + smoke
```

### Railway CLI

```bash
railway status                              # current linked project/service
railway service status --all                # all services status
railway variables --service fb-builder      # view backend env vars
railway variables --service frontend        # view frontend env vars
railway variables --set "KEY=value" --service fb-builder  # set env var
railway redeploy --service <name> --yes     # redeploy service
railway service logs --service <name>       # view logs
```

## Architecture

### Backend (`backend/app/`)

- **Entry**: `main.py` — FastAPI app, CORS setup, security headers, rate limiting, registers 20 routers under `/api/v1/`
- **Models**: `models.py` — single file with ~20 SQLAlchemy models
- **Routes**: `api/v1/` — auth, users, brands, products, research, generated_ads, templates, facebook, uploads, dashboard, copy_generation, profiles, ad_remix, prompts, ad_styles
- **Services**: `services/` — facebook_service.py (Marketing API via `facebook-business` SDK), research_service.py, ad_remix_service.py (Gemini Vision), brand_scraper.py, scraper.py
- **Auth**: JWT access tokens (30min) + refresh tokens (7 days, stored in DB). `core/security.py` handles token creation, `core/deps.py` provides `get_current_active_user` dependency
- **RBAC**: User → Roles → Permissions. Predefined roles: admin, manager, editor, viewer
- **Config**: `core/config.py` — validates PostgreSQL, reads all env vars

### Frontend (`frontend/src/`)

- **Routing**: `App.jsx` — React Router v7, public (`/login`) and protected routes wrapped in Layout
- **Context providers** (4):
  - `AuthContext` — JWT state, `login()`, `register()`, `logout()`, `authFetch()` (auto-refreshes on 401), `hasRole()`, `hasPermission()`
  - `BrandContext` — selected brand shared across pages
  - `CampaignContext` — campaign management state
  - `ToastContext` — `useToast()` → `showSuccess/showError/showWarning/showInfo`
- **Pages**: `pages/` — Dashboard, Research, BrandScrapes, CreateAds, ImageAds, VideoAds, GeneratedAds, WinningAds, AdRemix, ModularAds, AdModulesLibrary, FacebookCampaigns, Reporting, CustomerProfiles, AIPersonas, UserManagement, Login, Register, Settings (Note: Brands and Products pages have been removed from the frontend UI; those API routes still exist as legacy backend endpoints)
- **API pattern**: All backend calls use `authFetch()` from AuthContext, which injects Bearer token and handles refresh

### Key Database Relationships

- **Brand** → Products (1:M), CustomerProfiles (M:M), GeneratedAds (1:M)
- **WinningAd** — template with `blueprint_json` for ad remix deconstruction
- **GeneratedAd** — links brand_id, product_id, template_id; grouped by `ad_bundle_id`
- **FacebookCampaign** → FacebookAdSet → FacebookAd (mirrors FB API hierarchy, synced via `fb_*_id` fields)
- **User** → Roles (M:M) → Permissions (M:M); `is_superuser` bypasses all checks
- **SavedSearch** → ScrapedAd; FacebookPage; Vertical (research/scraping system)
- **RefreshToken** — stored per user, hashed, with expiry

### Deployment

- **Backend** (`backend/railway.toml`): Dockerfile (Python 3.11-slim), start command runs `init_db.py` then uvicorn, health check at `/health`
- **Frontend** (`frontend/railway.toml`): Nixpacks (Node 22), builds with Vite, serves with `npx serve dist`
- **CORS**: Backend reads `ALLOWED_ORIGINS` env var. Must include frontend Railway domain.
- **VITE_API_URL**: Build-time env var on frontend, must point to backend's public Railway URL with `/api/v1` suffix

## Critical Rules

- **NEVER** use browser `alert()` or `confirm()`. Use `useToast()` for notifications and custom state-based modals for confirmations (backdrop blur, red buttons for destructive actions).
- **PostgreSQL only** — SQLite is deprecated and blocked in `core/config.py`.
- **CORS**: No wildcard `*` in production. Set specific origins via `ALLOWED_ORIGINS` env var.
- All protected routes use `Depends(get_current_active_user)` from `core/deps.py`.
- File uploads: images only (jpg/png/webp), 10MB max, UUID filenames.
- Frontend env vars require `VITE_` prefix (Vite build-time injection).
- Ad account IDs auto-prefixed with `act_` if missing (`facebook_service.py`).

## Common Gotchas

- `VITE_API_URL` is baked in at build time — changing it requires a frontend redeploy
- Backend `init_db.py` runs on every deploy (idempotent — skips existing tables/users/roles)
- Alembic migrations are NOT run automatically on deploy; only `init_db.py` is. Run `alembic upgrade head` manually or update `railway.toml` start command
- When adding CORS origins: update `ALLOWED_ORIGINS` env var on the backend service
- Frontend and backend share the same Railway PostgreSQL instance
- Changing env vars on Railway auto-triggers a redeploy
