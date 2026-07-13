# TSI Ad Creative Studio - Comprehensive Codebase Review

**Review Date:** April 1, 2026  
**Scope:** Full-stack review (Backend + Frontend)  
**Focus:** Bad code, bad logic, unused code, duplicates, inefficiencies, improvements

---

## 🔴 CRITICAL ISSUES

### 1. **Duplicate `_validate_url` Function**
**Location:**
- `backend/app/api/v1/generated_ads.py:17`
- `backend/app/services/facebook_service.py:18`

**Issue:** The exact same URL validation function is duplicated in two files. This violates DRY principles and creates maintenance overhead.

**Fix:** Move to a shared utility module:
```python
# backend/app/core/utils.py
from urllib.parse import urlparse
import ipaddress

def validate_url(url: str, allowed_domains: list[str] | None = None) -> bool:
    """Validate URL is safe - not pointing to internal networks."""
    ...
```

---

### 2. **Poor Exception Handling Pattern (Generic 500 Errors)**
**Location:** `backend/app/api/v1/facebook.py` (throughout)

**Issue:** Every endpoint has the same anti-pattern:
```python
try:
    result = service.some_method()
    return result
except Exception as e:
    print(f"Error: {e}")  # <-- Just prints, doesn't log properly
    raise HTTPException(status_code=500, detail="Internal server error")  # <-- Hides real errors
```

**Problems:**
- All errors become generic "Internal server error" - impossible to debug in production
- Using `print()` instead of proper logging
- No error tracking/monitoring possible
- Facebook API errors are masked

**Fix:** Implement proper error handling:
```python
import logging
from fastapi import HTTPException

logger = logging.getLogger(__name__)

@router.get("/campaigns")
def read_campaigns(...):
    try:
        return service.get_campaigns(ad_account_id)
    except FacebookAPIError as e:  # Specific exception
        logger.error(f"Facebook API error: {e}", extra={"account_id": ad_account_id})
        raise HTTPException(status_code=502, detail=f"Facebook API error: {str(e)}")
    except Exception as e:
        logger.exception("Unexpected error fetching campaigns")
        raise HTTPException(status_code=500, detail="Failed to fetch campaigns")
```

---

### 3. **Memory Leak: Database Sessions in Background Tasks**
**Location:** `backend/app/api/v1/research.py:456-474`

**Issue:** Background task creates a new DB session but has risky error handling:
```python
async def run_scrape():
    from app.database import SessionLocal
    scrape_db = SessionLocal()
    try:
        scraper = BrandScraperService(scrape_db)
        ...
    except Exception as e:
        print(f"Background scrape error: {e}")  # Just prints!
        ...
    finally:
        scrape_db.close()
```

**Problems:**
- If `scrape_db.commit()` fails, the error is logged but the session may be in a bad state
- Multiple `scrape_db.commit()` calls without proper transaction management
- No rollback on error before the final close

**Fix:**
```python
async def run_scrape():
    scrape_db = SessionLocal()
    try:
        scraper = BrandScraperService(scrape_db)
        await scraper.scrape_brand(scrape_record)
        scrape_db.commit()
    except Exception as e:
        scrape_db.rollback()  # Explicit rollback
        logger.error(f"Background scrape error: {e}")
        # Update status to failed
        raise
    finally:
        scrape_db.close()
```

---

### 4. **Race Condition in Rate Limiter**
**Location:** `backend/app/services/rate_limiter.py:14-44`

**Issue:** The rate limiter has a race condition between `check_limit()` and actual API call:
```python
allowed, remaining, reset = rate_limiter.check_limit(db)
if not allowed:
    raise HTTPException(429, ...)
# <-- Another request could sneak in here!
ads = await scraper.search_ads(...)  # API call happens after check
```

**Problem:** Two concurrent requests could both pass the check, then both make API calls, exceeding the limit.

**Fix:** Use atomic operations or distributed locking (Redis-based rate limiter).

---

## 🟠 HIGH SEVERITY ISSUES

### 5. **Inefficient Repeated Hash Computation**
**Location:** `backend/app/services/research_service.py:67`

**Issue:** 
```python
all_hashes = [self.compute_content_hash(ad) for ad in ads if self.compute_content_hash(ad)]
```

**Problem:** `compute_content_hash` is called TWICE for every ad - once for the condition, once for the list.

**Fix:**
```python
all_hashes = []
for ad in ads:
    hash_val = self.compute_content_hash(ad)
    if hash_val:
        all_hashes.append(hash_val)
```

---

### 6. **N+1 Query Problem in Research Service**
**Location:** `backend/app/services/research_service.py:132-169`

**Issue:** For each unique page_id, a separate COUNT query is executed:
```python
page_ids = {ad.facebook_page_id for ad in saved_ads if ad.facebook_page_id}
for page_id in page_ids:  # N iterations
    total = db.query(func.count(ScrapedAd.id)).filter(...).scalar()  # N queries!
```

**Fix:** Use a single grouped query:
```python
from sqlalchemy import func

totals = db.query(
    ScrapedAd.facebook_page_id,
    func.count(ScrapedAd.id).label('total')
).filter(
    ScrapedAd.facebook_page_id.in_(page_ids)
).group_by(ScrapedAd.facebook_page_id).all()

total_map = {p.page_id: p.total for p in totals}
```

---

### 7. **Inline Imports Throughout Codebase**
**Locations:** Multiple files

**Anti-pattern found:**
- `backend/app/services/scraper.py:83` - `from datetime import date` inside function
- `backend/app/services/brand_scraper.py:171` - `import urllib.parse` inside function
- `backend/app/services/facebook_service.py:345-346` - imports inside method
- `backend/app/services/agents/base_agent.py:15` - `from collections import defaultdict` inside method

**Problems:**
- Performance hit (import happens every function call)
- Makes code harder to follow
- Hides dependencies

**Fix:** Move all imports to the top of the file.

---

### 8. **Missing Error Handling in JSON Parsing**
**Location:** `backend/app/services/agents/base_agent.py:26-37`

**Issue:**
```python
def generate_json(self, prompt: str) -> Dict[str, Any]:
    text = self.generate(prompt)
    # ... cleanup ...
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        print(f"Failed to parse JSON...")  # Just prints!
        raise ValueError("Agent failed to return valid JSON.")
```

**Problems:**
- No retry mechanism for flaky AI responses
- Loses the original AI response that failed parsing
- No logging of the actual problematic text

**Fix:**
```python
def generate_json(self, prompt: str, max_retries: int = 2) -> Dict[str, Any]:
    for attempt in range(max_retries):
        text = self.generate(prompt)
        cleaned = self._clean_json(text)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            logger.warning(f"JSON parse failed (attempt {attempt + 1}): {e}")
            if attempt == max_retries - 1:
                logger.error(f"Failed JSON content: {cleaned[:500]}")
                raise ValueError(f"Invalid JSON response: {e}")
```

---

### 9. **Hardcoded Configuration Values**
**Location:** Multiple files

**Issues:**
- `backend/app/services/rate_limiter.py:81` - Hardcoded `max_calls=200, window_minutes=59`
- `backend/app/services/facebook_service.py:502` - Hardcoded timeout values
- `backend/app/services/brand_scraper.py:241` - Hardcoded scroll count logic

**Fix:** Use environment variables or config file for all tunable parameters.

---

## 🟡 MEDIUM SEVERITY ISSUES

### 10. **Inconsistent Pydantic Config Style**
**Location:** Schema files

**Issue:** Mix of old and new Pydantic v2 config styles:
```python
# Old style (deprecated in v2)
class Config:
    from_attributes = True

# New style
model_config = ConfigDict(from_attributes=True)
```

**Files affected:** Most schema files use old style, `ai_persona.py` uses new style.

**Fix:** Standardize on Pydantic v2 style everywhere.

---

### 11. **Unused Models and Dead Code**
**Location:** `backend/app/models.py`

**Potentially unused models:**
- `SearchLog` - Created but never queried for analytics display
- `ApiUsageLog` - Created but aggregation queries are complex

**Verification needed:** Check if these models are actually used in the frontend.

---

### 12. **Frontend: Missing Error Boundaries**
**Location:** `frontend/src/App.jsx`

**Issue:** There's an ErrorBoundary imported but it's unclear if it properly catches and displays errors. Also, many async operations don't have proper error handling.

---

### 13. **Frontend: LocalStorage Token Storage**
**Location:** `frontend/src/context/AuthContext.jsx`

**Issue:** Storing tokens in localStorage is vulnerable to XSS attacks. While this is a known trade-off, consider:
- Using httpOnly cookies for refresh tokens
- Implementing proper token rotation
- Adding XSS protection headers (already present in backend)

---

### 14. **Magic Numbers and Strings**
**Location:** Throughout codebase

**Examples:**
- `backend/app/services/scraper.py:131` - `batch_size = min(remaining, 300)` - Why 300?
- `backend/app/services/brand_scraper.py:241` - `scroll_count = min(20, limit // 10)` - Why 20? Why // 10?
- `backend/app/core/security.py:44-45` - Token expiry times

**Fix:** Define constants with descriptive names:
```python
FB_API_MAX_BATCH_SIZE = 300
BRAND_SCRAPE_MAX_SCROLLS = 20
SCROLLS_PER_AD_BATCH = 10
```

---

### 15. **Inefficient String Building in Loops**
**Location:** `backend/app/services/scraper.py`

**Issue:**
```python
text_to_check = ' '.join([
    parsed_ad.brand_name or '',
    parsed_ad.headline or '',
    parsed_ad.ad_copy or '',
    parsed_ad.cta_text or ''
]).lower()
```

Called for every keyword check. String joining is relatively expensive.

**Fix:** Pre-compute the search text once per ad.

---

## 🟢 LOW SEVERITY / CODE QUALITY

### 16. **Inconsistent Naming Conventions**
- `ad_copy` vs `adCopy` - Mix of snake_case and camelCase in different contexts
- Model fields use snake_case, API sometimes expects camelCase
- The Pydantic models have both `daily_budget` and `dailyBudget` fields (redundant)

### 17. **Unused Parameters**
**Location:** `backend/app/services/agents/orchestrator.py:32-36`

```python
base_intro = intros[0]['text'] if intros else ""
bridges = self.bridge_agent.generate_bridges(brief, base_intro, count=2)
# base_intro is passed but never used by BridgeAgent
```

### 18. **Missing Type Hints**
Many functions lack proper type hints, especially in the agent services.

### 19. **TODO Comments Without Tracking**
- `backend/app/services/scraper.py:261` - `# TODO: Parse ad_snapshot_url...`

**Fix:** Create GitHub issues for TODOs or remove if not planned.

### 20. **Print Statements in Production Code**
**Location:** Throughout backend

The codebase uses `print()` extensively for debugging. These should be replaced with proper logging:
- `logging.debug()` for development info
- `logging.info()` for operational info
- `logging.warning()` for issues
- `logging.error()` for errors

---

## 📊 ARCHITECTURAL CONCERNS

### 21. **Synchronous Database Calls in Async Context**
**Location:** `backend/app/api/v1/research.py`

**Issue:** Database queries are synchronous (SQLAlchemy sync) but the endpoint is async. This blocks the event loop.

**Fix:** Consider using `databases` library or SQLAlchemy 2.0 async support with asyncpg.

---

### 22. **No Request Timeouts on External APIs**
**Location:** `backend/app/services/facebook_service.py`

The `wait_for_video_ready` function has a timeout parameter, but many other external calls don't have explicit timeouts.

---

### 23. **Large File Sizes**
**Files exceeding 500 lines:**
- `facebook_service.py` - 638 lines
- `brand_scraper.py` - 830 lines
- `research.py` - 515 lines

**Fix:** Consider splitting into smaller modules.

---

### 24. **No Caching Layer**
**Issue:** Repeated requests for the same data (e.g., Facebook campaigns, ad accounts) hit the external API every time.

**Fix:** Implement Redis caching for:
- Facebook ad accounts (rarely change)
- Campaign lists (change infrequently)
- Generated ad templates

---

## 🚀 RECOMMENDATIONS FOR IMPROVEMENT

### Performance Optimizations

1. **Add Database Indexes**
   - `ScrapedAd.content_hash` - Used for deduplication lookups
   - `ScrapedAd.external_id` - Used for existence checks
   - `GeneratedAd.bundle_code` - Already indexed, good!

2. **Implement Connection Pooling**
   - Current SQLAlchemy engine has basic pooling
   - Consider `pool_pre_ping=True` is already set ✅
   - Monitor pool exhaustion under load

3. **Batch Database Operations**
   - Use `bulk_save_objects()` or `bulk_insert_mappings()` for large inserts

4. **Add Async Support**
   - Migrate to SQLAlchemy 2.0 async with asyncpg
   - Use `aiohttp` or `httpx` consistently (currently mixing sync `requests` and async `httpx`)

### Security Improvements

1. **Input Validation**
   - Some endpoints accept raw dicts without Pydantic validation
   - Add strict validation for all user inputs

2. **Rate Limiting Per User**
   - Current rate limiter is global, not per-user
   - Add user-based rate limiting for expensive operations

3. **Audit Logging**
   - No audit trail for who created/modified campaigns
   - Add audit log table for compliance

### Developer Experience

1. **Add Unit Tests**
   - Current test coverage appears minimal
   - Add tests for critical paths: auth, rate limiting, deduplication

2. **Add API Documentation**
   - FastAPI generates OpenAPI docs, but descriptions are minimal
   - Add docstrings to all endpoints

3. **Add Pre-commit Hooks**
   - black, isort, flake8, mypy
   - Already configured in `.pre-commit-config.yaml` ✅

### Monitoring & Observability

1. **Replace print() with structured logging**
2. **Add metrics collection** (Prometheus/StatsD)
3. **Add health checks** for external dependencies
4. **Add request tracing** (correlation IDs)

---

## 📈 PRIORITY MATRIX

| Priority | Issue | Effort | Impact |
|----------|-------|--------|--------|
| 🔴 P0 | Duplicate `_validate_url` | Low | Maintainability |
| 🔴 P0 | Generic exception handling | Medium | Debuggability |
| 🔴 P0 | Race condition in rate limiter | Medium | Correctness |
| 🟠 P1 | N+1 queries | Low | Performance |
| 🟠 P1 | Inline imports | Low | Performance |
| 🟠 P1 | Repeated hash computation | Low | Performance |
| 🟡 P2 | Pydantic config consistency | Low | Code quality |
| 🟡 P2 | Magic numbers | Low | Maintainability |
| 🟢 P3 | Print to logging | Medium | Observability |
| 🟢 P3 | Add caching | High | Performance |

---

## 🎯 QUICK WINS (Can be done in 1 day)

1. ✅ Consolidate duplicate `_validate_url` function
2. ✅ Fix inline imports
3. ✅ Fix repeated hash computation
4. ✅ Add constants for magic numbers
5. ✅ Replace print statements with logging
6. ✅ Fix Pydantic config style consistency

## 🏗️ MEDIUM TERM (1-2 weeks)

1. Fix exception handling patterns across all API routes
2. Fix N+1 query issues
3. Add proper database transaction handling
4. Add comprehensive logging
5. Add request/response middleware for tracking

## 🔮 LONG TERM (1+ months)

1. Migrate to fully async database operations
2. Implement Redis caching layer
3. Add comprehensive test coverage
4. Add monitoring and alerting
5. Implement audit logging
6. Add request tracing

---

## 💡 POSITIVE NOTES

The codebase has several good practices:

1. ✅ **Proper RBAC implementation** - Good permission/role structure
2. ✅ **Environment-based config** - No hardcoded secrets
3. ✅ **CORS properly configured** - No wildcard in production
4. ✅ **Rate limiting implemented** - Prevents API abuse
5. ✅ **URL validation for SSRF protection** - Good security practice
6. ✅ **Proper JWT implementation** - Access + refresh tokens
7. ✅ **Database connection pooling** - Configured in database.py
8. ✅ **Input sanitization** - UUID-based filenames for uploads

---

*End of Review*
