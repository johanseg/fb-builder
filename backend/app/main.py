"""
Townsquare Interactive Ad Creative Studio - Backend API

Created by Jason Akatiff
iSCALE.com | A4D.com
Telegram: @jasonakatiff
Email: jason@jasonakatiff.com
"""

import os
import re
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import Response
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from app.core.config import settings
from app.core.rate_limit import limiter

_is_dev = os.getenv("ENVIRONMENT", "production") != "production"

app = FastAPI(
    title="TSI Ad Creative Studio API",
    version="1.0.0",
    openapi_url="/api/v1/openapi.json" if _is_dev else None,
    docs_url="/api/v1/docs" if _is_dev else None,
)

# Register rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Security headers middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response: Response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "0"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; connect-src 'self' https:;"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    if not _is_dev:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response

# Trust proxy headers (Railway uses reverse proxy)
# Set TRUSTED_PROXIES env var to a comma-separated list of trusted IPs
trusted_proxies_env = os.getenv("TRUSTED_PROXIES")
trusted_hosts = [p.strip() for p in trusted_proxies_env.split(",") if p.strip()] if trusted_proxies_env else ["127.0.0.1"]
app.add_middleware(ProxyHeadersMiddleware, trusted_hosts=trusted_hosts)

# CORS origins from env var; localhost origins only in non-production
default_origins = [
    "http://localhost:5173",
    "http://localhost:3000",
] if _is_dev else []
extra_origins = os.getenv("ALLOWED_ORIGINS", "").split(",")
allowed_origins = default_origins + [o.strip() for o in extra_origins if o.strip()]

# CORS Middleware - explicit methods and headers
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
    expose_headers=["X-Total-Count"],
    max_age=600,
)

@app.get("/")
async def root():
    return {"message": "Welcome to the TSI Ad Creative Studio API"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# Database Connection Validation
@app.on_event("startup")
async def startup_event():
    """Validate PostgreSQL connection on startup"""
    from app.database import engine
    from sqlalchemy import text
    
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.scalar()
            print(f"✅ Connected to PostgreSQL")
            print(f"   Version: {version}")
    except Exception as e:
        # Sanitize DATABASE_URL - hide password
        sanitized_url = re.sub(r'://[^:]+:[^@]+@', '://***:***@', settings.DATABASE_URL)
        print(f"❌ Failed to connect to database: {e}")
        print(f"   DATABASE_URL: {sanitized_url}")
        raise RuntimeError(f"Database connection failed: {e}")


# Include Routers
from app.api.v1 import brands, products, research, generated_ads, templates, facebook, uploads, dashboard, copy_generation, profiles, ad_remix, prompts, ad_styles, auth, users, modular_generation, ad_modules, naming_service, performance, personas

app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(users.router, prefix="/api/v1/users", tags=["users"])
app.include_router(brands.router, prefix="/api/v1/brands", tags=["brands"])
app.include_router(products.router, prefix="/api/v1/products", tags=["products"])
app.include_router(research.router, prefix="/api/v1/research", tags=["research"])
app.include_router(generated_ads.router, prefix="/api/v1/generated-ads", tags=["generated-ads"])
app.include_router(templates.router, prefix="/api/v1/templates", tags=["templates"])
app.include_router(facebook.router, prefix="/api/v1/facebook", tags=["facebook"])
app.include_router(uploads.router, prefix="/api/v1/uploads", tags=["uploads"])
app.include_router(dashboard.router, prefix="/api/v1/dashboard", tags=["dashboard"])
app.include_router(copy_generation.router, prefix="/api/v1/copy-generation", tags=["copy-generation"])
app.include_router(profiles.router, prefix="/api/v1/profiles", tags=["profiles"])
app.include_router(ad_remix.router, prefix="/api/v1/ad-remix", tags=["ad-remix"])
app.include_router(prompts.router, prefix="/api/v1/prompts", tags=["prompts"])
app.include_router(ad_styles.router, prefix="/api/v1/ad-styles", tags=["ad-styles"])
app.include_router(modular_generation.router, prefix="/api/v1/modular-generation", tags=["modular-generation"])
app.include_router(ad_modules.router, prefix="/api/v1/ad-modules", tags=["ad-modules"])
app.include_router(naming_service.router, prefix="/api/v1/naming", tags=["naming-service"])
app.include_router(performance.router, prefix="/api/v1/performance", tags=["performance"])
app.include_router(personas.router, prefix="/api/v1/personas", tags=["personas"])

# Mount static files for uploads
uploads_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")
os.makedirs(uploads_dir, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")
