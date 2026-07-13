# Risk Reduction Follow-Ups Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Finish the remaining reliability, contract, and maintainability work after the current security/correctness hardening pass.

**Architecture:** Prioritize residual production risk before ergonomics. Tighten the backend API contract first, then remove dead or misleading auth UX, then decompose oversized frontend surfaces and code-split the bundle.

**Tech Stack:** FastAPI, SQLAlchemy, PostgreSQL, Alembic, React 19, Vite 7, Vitest

---

### Task 1: Database And Deploy Safety

**Files:**
- Modify: `backend/alembic/versions/*`
- Modify: `backend/railway.toml`
- Modify: `backend/README.md` or deployment docs if needed
- Test: `backend/tests/unit/test_auth_service.py`

- [ ] Add an Alembic migration that creates an index on `refresh_tokens.expires_at`.
- [ ] Add any missing migration for schema drift discovered while comparing models to live tables.
- [ ] Update Railway startup so migrations run before app boot, or document the manual deploy step explicitly if auto-run is not acceptable.
- [ ] Verify locally with: `cd backend && alembic upgrade head`
- [ ] Verify cleanup test with: `DATABASE_URL=postgresql://user:pass@localhost/testdb venv/bin/pytest --confcutdir=tests/unit tests/unit/test_auth_service.py -q`

### Task 2: Facebook API Contract Hardening

**Files:**
- Modify: `backend/app/api/v1/facebook.py`
- Modify: `backend/app/schemas/facebook.py`
- Modify: `backend/app/services/facebook_service.py`
- Test: `backend/tests/unit/test_facebook.py`
- Test: `backend/tests/unit/test_facebook_schemas.py`

- [ ] Add explicit `response_model=` declarations to the Facebook routes that return stable local objects.
- [ ] Introduce response schemas for the external Facebook passthrough routes where the payload shape is predictable enough to document.
- [ ] Normalize error taxonomy so user-correctable Facebook errors surface as 4xx with useful details and true backend faults stay 500.
- [ ] Add unit tests for camelCase input, snake_case normalization, and representative response payload validation.
- [ ] Verify with: `cd backend && DATABASE_URL=postgresql://user:pass@localhost/testdb venv/bin/pytest --confcutdir=tests/unit tests/unit/test_facebook_schemas.py -q`

### Task 3: Auth UX Alignment

**Files:**
- Modify: `frontend/src/App.jsx`
- Modify: `frontend/src/context/AuthContext.jsx`
- Modify: `frontend/src/pages/Register.jsx`
- Modify: `frontend/src/pages/UserManagement.jsx`
- Test: `frontend/src/context/AuthContext.test.jsx`

- [ ] Decide whether the product supports self-serve signup or admin-only provisioning.
- [ ] If admin-only: remove the public register page and any dead links or dead helpers.
- [ ] If self-serve: make `/auth/register` public and return tokens directly, then add a login-on-register regression test.
- [ ] Make the UI copy match the chosen model so users are not sent to flows they cannot complete.
- [ ] Verify with: `cd frontend && npm run test:unit -- src/context/AuthContext.test.jsx`

### Task 4: Frontend API Layer Extraction

**Files:**
- Create: `frontend/src/api/facebook.js`
- Create: `frontend/src/api/generatedAds.js`
- Create: `frontend/src/api/auth.js`
- Modify: `frontend/src/pages/FacebookCampaigns.jsx`
- Modify: `frontend/src/pages/GeneratedAds.jsx`
- Modify: `frontend/src/context/AuthContext.jsx`

- [ ] Move repeated `authFetch` call sites into focused API modules.
- [ ] Centralize request/response shaping, error parsing, and URL construction.
- [ ] Keep page components responsible for state and rendering only.
- [ ] Verify with: `cd frontend && npm run build`

### Task 5: Large Page Decomposition And Bundle Size

**Files:**
- Modify: `frontend/src/pages/Research.jsx`
- Modify: `frontend/src/pages/ImageAds.jsx`
- Modify: `frontend/src/pages/GeneratedAds.jsx`
- Create: `frontend/src/components/research/*`
- Create: `frontend/src/components/image-ads/*`
- Create: `frontend/src/components/generated-ads/*`

- [ ] Split each oversized page into view components plus one stateful hook per domain.
- [ ] Add lazy loading for the heaviest route groups to reduce the current large production chunk.
- [ ] Re-run the build and confirm the main bundle warning is reduced or justified.
- [ ] Verify with: `cd frontend && npm run build`
