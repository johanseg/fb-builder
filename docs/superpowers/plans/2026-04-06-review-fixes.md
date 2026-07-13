# Review Findings Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the security, correctness, and product-alignment issues found in the codebase review without disturbing unrelated in-flight work.

**Architecture:** Patch the backend contract first where the highest-risk issues live: file handling, URL resolution, research deduplication, and test harness isolation. Then align the frontend auth and brand-selection behavior with the intended product model and eliminate the React hook/runtime defects already flagged by lint.

**Tech Stack:** FastAPI, SQLAlchemy, PostgreSQL, React 19, Vite 7, Vitest, ESLint

---

### Task 1: Backend Regression Coverage

**Files:**
- Modify: `backend/tests/unit/test_utils.py`
- Create: `backend/tests/unit/test_research_service.py`
- Create: `backend/tests/unit/test_upload_resolution.py`

- [ ] Add unit tests for any new upload URL normalization helpers, including acceptance of trusted remote URLs and rejection of raw local filesystem paths.
- [ ] Add a research deduplication regression test that proves ads with the same copy but different creative/media identifiers are treated as distinct.
- [ ] Keep these tests isolated from `app.main` so they can run with a lightweight `DATABASE_URL` stub.
- [ ] Verify with: `cd backend && DATABASE_URL=postgresql://user:pass@localhost/testdb python3 -m pytest --confcutdir=tests/unit tests/unit/test_utils.py tests/unit/test_research_service.py tests/unit/test_upload_resolution.py -q`

### Task 2: Facebook Upload Hardening

**Files:**
- Modify: `backend/app/services/facebook_service.py`
- Modify: `backend/app/api/v1/uploads.py`
- Modify: `backend/app/core/utils.py`
- Modify: `frontend/src/lib/facebookApi.js`

- [ ] Remove the server-side fallback that treats arbitrary client input as a local file path in the Facebook image/video upload service.
- [ ] Introduce a narrow helper that resolves only two legal cases: a trusted remote URL or a backend-managed upload URL.
- [ ] Make backend-managed upload URLs resolve to the real file under `backend/uploads` in dev and remain usable when the frontend is deployed.
- [ ] Keep the frontend blob upload workflow intact by passing a URL the backend can safely resolve.
- [ ] Verify with the Task 1 backend tests plus: `cd frontend && npm run test:unit`

### Task 3: Research Deduplication And Analytics Accuracy

**Files:**
- Modify: `backend/app/services/research_service.py`
- Modify: `backend/app/api/v1/research.py`

- [ ] Expand the deduplication fingerprint to include stable creative/media identity so copy-only variants do not collapse into one ad.
- [ ] Keep the grouped analytics endpoints consistent with the new uniqueness rule.
- [ ] Preserve existing duplicate suppression when the exact same ad reappears across searches.
- [ ] Verify with: `cd backend && DATABASE_URL=postgresql://user:pass@localhost/testdb python3 -m pytest --confcutdir=tests/unit tests/unit/test_research_service.py -q`

### Task 4: Auth, Brand Selection, And Product-Model Alignment

**Files:**
- Modify: `frontend/src/App.jsx`
- Modify: `frontend/src/pages/Register.jsx`
- Modify: `frontend/src/context/AuthContext.jsx`
- Modify: `frontend/src/context/BrandContext.jsx`
- Modify: `backend/tests/conftest.py`

- [ ] Remove or quarantine the dead self-serve register surface so the UI matches the backend’s admin-only registration contract.
- [ ] Make active-brand selection deterministic for single-brand mode instead of choosing the first unordered DB row.
- [ ] Fix the backend test harness so unit and API tests can use `TEST_DATABASE_URL` cleanly without importing the production engine first.
- [ ] Verify with: `cd frontend && npm run test:unit` and `cd backend && TEST_DATABASE_URL=postgresql://user:pass@localhost/testdb python3 -m pytest --confcutdir=tests tests/unit/test_auth.py -q`

### Task 5: React Runtime Defects And Lint Failures

**Files:**
- Modify: `frontend/src/context/ToastContext.jsx`
- Modify: `frontend/src/pages/ResearchSettings.jsx`
- Modify: `frontend/src/pages/ImageAds.jsx`
- Modify: `frontend/src/pages/VideoAds.jsx`
- Modify: any directly related components surfaced by lint during verification

- [ ] Fix the function-before-declaration bugs flagged in `ToastContext` and `ResearchSettings`.
- [ ] Fix the conditional-hook ordering bug in `ImageAds`.
- [ ] Fix the state-setting-in-effect issue in `VideoAds`.
- [ ] Triage the remaining lint errors and fix the real behavior-affecting ones, not just cosmetic warnings.
- [ ] Verify with: `cd frontend && npm run lint && npm run test:unit`
