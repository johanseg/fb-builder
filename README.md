<p align="center">
  <img src="frontend/public/tsi_logo.svg" alt="Townsquare Interactive" width="120" />
</p>

<h1 align="center">Townsquare Interactive - Ad Creative Studio</h1>

<p align="center">
  <strong>AI-powered ad creative platform for local business marketing</strong><br>
  From competitor research to ad generation and campaign management
</p>

<p align="center">
  <a href="#features">Features</a> •
  <a href="#quick-start">Quick Start</a> •
  <a href="#documentation">Documentation</a> •
  <a href="#deployment">Deployment</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.11+-blue.svg" alt="Python 3.11+">
  <img src="https://img.shields.io/badge/node-18+-green.svg" alt="Node 18+">
  <img src="https://img.shields.io/badge/react-19-61dafb.svg" alt="React 19">
  <img src="https://img.shields.io/badge/fastapi-0.100+-009688.svg" alt="FastAPI">
  <img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="MIT License">
</p>

<p align="center">
  Created by <strong>Jason Akatiff</strong><br>
  <a href="https://iscale.com">iSCALE.com</a> • <a href="https://a4d.com">A4D.com</a><br>
  <a href="https://t.me/jasonakatiff">Telegram</a> • <a href="mailto:jason@jasonakatiff.com">jason@jasonakatiff.com</a>
</p>

---

## Overview

Facebook Ad Builder is a full-stack application that streamlines the entire Facebook advertising workflow. Use AI to research competitors, generate compelling ad copy and images, and manage campaigns—all from one platform.

### Key Capabilities

- **Competitor Intelligence** — Scrape and analyze ads from the Facebook Ad Library
- **AI Content Generation** — Create ad copy and images using Google Gemini and Fal.ai
- **Brand Management** — Maintain consistent brand voice, colors, and assets
- **Template System** — Deconstruct winning ads into reusable blueprints
- **Campaign Management** — Create and manage Facebook campaigns via API

---

## Features

### 🔍 Competitor Research
Scrape ads directly from Facebook's Ad Library. Analyze competitor strategies, track active campaigns, and identify winning ad formats.

### 🎨 Brand Management
Create and manage brand profiles with:
- Brand voice and messaging guidelines
- Color palettes (primary, secondary, highlight)
- Logo and visual assets
- Multiple products per brand

### 🤖 AI-Powered Ad Generation
Generate high-converting ads using AI:
- **Copy Generation** — Compelling headlines, body text, and CTAs
- **Image Generation** — AI-created visuals via Fal.ai
- **Ad Remix** — Transform winning competitor ads into your brand style

### 📋 Template Library
Build a library of proven ad structures:
- Deconstruct successful ads into blueprints
- Reuse templates across brands and products
- Track performance by template type

### 📊 Campaign Management
Manage Facebook campaigns directly:
- Create campaigns, ad sets, and ads
- Upload creative assets
- Monitor campaign status
- Sync with Facebook Ads Manager

---

## Quick Start

### Prerequisites

- **Node.js** 18+ ([download](https://nodejs.org))
- **Python** 3.11+ ([download](https://python.org))
- **PostgreSQL** 15+ (local or cloud: [Railway](https://railway.app), [Supabase](https://supabase.com))

### Option 1: Interactive Setup (Recommended)

Run the setup wizard which will guide you through the entire configuration:

```bash
git clone https://github.com/yourusername/facebook_ad_builder.git
cd facebook_ad_builder
./setup.sh
```

The wizard will:
1. Check all prerequisites
2. Walk you through configuring API keys
3. Set up the database
4. Create your admin account

### Option 2: Manual Setup

<details>
<summary>Click to expand manual setup instructions</summary>

#### 1. Clone and Install

```bash
git clone https://github.com/yourusername/facebook_ad_builder.git
cd facebook_ad_builder

# Backend
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Frontend
cd ../frontend
npm install
```

#### 2. Configure Environment

```bash
cp .env.example .env.local
```

Edit `.env.local` with your credentials. See [Environment Variables](#environment-variables) for details.

#### 3. Initialize Database

```bash
cd backend
source venv/bin/activate
python init_db.py
```

#### 4. Start the Application

```bash
# Terminal 1: Backend
cd backend
source venv/bin/activate
uvicorn app.main:app --reload --port 8000

# Terminal 2: Frontend
cd frontend
npm run dev
```

</details>

### Access the Application

| Service | URL |
|---------|-----|
| Frontend | http://localhost:5173 |
| Backend API | http://localhost:8000 |
| API Documentation | http://localhost:8000/api/v1/docs |

---

## External Services

### Required Services

| Service | Purpose | Setup Guide |
|---------|---------|-------------|
| **PostgreSQL** | Database | Local install, [Railway](https://railway.app), or [Supabase](https://supabase.com) |
| **Google Gemini** | AI text generation & vision | [Get API Key](https://aistudio.google.com/app/apikey) |

### Optional Services

| Service | Purpose | Setup Guide |
|---------|---------|-------------|
| **Facebook Marketing API** | Campaign management, Ad Library | [Developer Portal](https://developers.facebook.com) |
| **Fal.ai** | AI image generation | [fal.ai](https://fal.ai) |
| **Cloudflare R2** | Image/video storage | [Cloudflare Dashboard](https://dash.cloudflare.com) |

### Facebook Developer Setup

<details>
<summary>Click to expand Facebook API setup</summary>

1. Go to [developers.facebook.com](https://developers.facebook.com)
2. Create a new app → Select "Business" type
3. Add the "Marketing API" product
4. Go to Tools → Graph API Explorer
5. Generate a User Access Token with these permissions:
   - `ads_management`
   - `ads_read`
   - `business_management`
6. Find your Ad Account ID in [Ads Manager](https://adsmanager.facebook.com) → Settings

```bash
# Add to .env.local
FACEBOOK_ACCESS_TOKEN=your-token
FACEBOOK_AD_ACCOUNT_ID=act_123456789
FACEBOOK_APP_ID=your-app-id
FACEBOOK_APP_SECRET=your-app-secret
```

> **Note:** Access tokens expire after ~60 days. For production, implement token refresh.

</details>

### Cloudflare R2 Setup

<details>
<summary>Click to expand R2 storage setup</summary>

1. Go to [Cloudflare Dashboard](https://dash.cloudflare.com) → R2
2. Create a bucket (e.g., `facebook-ads`)
3. Go to R2 → Manage R2 API Tokens → Create API token
4. Grant read/write permissions for your bucket
5. Enable public access: Bucket Settings → Public Access → Enable R2.dev subdomain

```bash
# Add to .env.local
R2_ACCOUNT_ID=your-account-id
R2_ACCESS_KEY_ID=your-access-key
R2_SECRET_ACCESS_KEY=your-secret-key
R2_BUCKET_NAME=facebook-ads
R2_PUBLIC_URL=https://pub-xxx.r2.dev
```

</details>

---

## Environment Variables

Create a `.env.local` file in the project root:

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | ✅ | PostgreSQL connection string |
| `SECRET_KEY` | ✅ | JWT signing key (generate random string) |
| `GEMINI_API_KEY` | ✅ | Google Gemini API key |
| `ALLOWED_ORIGINS` | Production | Comma-separated CORS origins |
| `FACEBOOK_ACCESS_TOKEN` | For FB features | Facebook Marketing API token |
| `FACEBOOK_AD_ACCOUNT_ID` | For FB features | Facebook Ad Account ID |
| `R2_*` | For uploads | Cloudflare R2 credentials |
| `FAL_AI_API_KEY` | For image gen | Fal.ai API key |

See `.env.example` for all available options.

---

## Usage Guide

### 1. Create a Brand

Navigate to **Brands** → **New Brand**

- Enter brand name and description
- Upload logo
- Set brand colors (primary, secondary, highlight)
- Define brand voice/tone guidelines

### 2. Add Products

Navigate to **Products** → **New Product**

- Select the parent brand
- Add product name and description
- Upload product images
- Set default landing page URL

### 3. Research Competitors

Navigate to **Research** → **Scrape Brand Ads**

- Enter a competitor's Facebook Page ID or URL
- View their active ads
- Save interesting ads for reference
- Analyze ad copy and creative patterns

### 4. Generate Ads

Navigate to **Create Ads**

- Select brand and product
- Choose a template or start fresh
- AI generates multiple ad variations
- Edit and refine as needed
- Export or push to Facebook

### 5. Manage Campaigns

Navigate to **Campaigns**

- Create new campaigns
- Set up ad sets with targeting
- Add ads with your generated creative
- Monitor performance

---

## Architecture

### System Overview

```mermaid
graph TB
    subgraph Frontend["Frontend — React 19 + Vite + TailwindCSS"]
        UI[Browser Client]
        Auth[AuthContext<br/>JWT + Refresh]
        Brand[BrandContext]
        Campaign[CampaignContext]
        Toast[ToastContext]
    end

    subgraph Backend["Backend — FastAPI + SQLAlchemy"]
        API[API Gateway<br/>CORS · Rate Limiting · JWT Auth]

        subgraph Routes["API Routes /api/v1/"]
            R_Auth[auth]
            R_Brands[brands]
            R_Products[products]
            R_Research[research]
            R_Facebook[facebook]
            R_CopyGen[copy_generation]
            R_AdRemix[ad_remix]
            R_Uploads[uploads]
            R_GenAds[generated_ads]
            R_Templates[templates]
            R_Dashboard[dashboard]
            R_Users[users]
        end

        subgraph Services["Business Logic Services"]
            S_FB[FacebookService<br/>Campaign Management]
            S_Scraper[Scraper<br/>API + Chromium Fallback]
            S_Research[ResearchService<br/>Search & Dedup]
            S_Remix[AdRemixService<br/>Deconstruct/Reconstruct]
            S_BrandScraper[BrandScraper<br/>Competitor Monitoring]
        end
    end

    subgraph External["External Services"]
        FB_API[Facebook<br/>Marketing API]
        FB_ADS[Facebook<br/>Ads Library API]
        GEMINI[Google Gemini<br/>Copy & Vision AI]
        FAL[Fal.ai<br/>Image Generation]
    end

    subgraph Storage["Data Storage"]
        PG[(PostgreSQL<br/>Railway)]
        R2[Cloudflare R2<br/>Media Storage]
    end

    UI -->|authFetch| API
    API --> Routes
    R_Facebook --> S_FB
    R_Research --> S_Research
    R_Research --> S_BrandScraper
    R_AdRemix --> S_Remix
    R_CopyGen --> GEMINI
    S_FB --> FB_API
    S_Scraper --> FB_ADS
    S_Research --> S_Scraper
    S_Remix --> GEMINI
    S_BrandScraper --> R2
    S_BrandScraper --> FB_ADS
    R_Uploads --> R2
    R_GenAds --> FAL
    Routes --> PG

    style Frontend fill:#1a1a2e,stroke:#16213e,color:#e2e8f0
    style Backend fill:#0f3460,stroke:#16213e,color:#e2e8f0
    style External fill:#533483,stroke:#16213e,color:#e2e8f0
    style Storage fill:#1a1a2e,stroke:#e94560,color:#e2e8f0
```

### Ad Creation Pipeline

```mermaid
sequenceDiagram
    participant U as User
    participant FE as React Frontend
    participant API as FastAPI Backend
    participant G as Google Gemini
    participant F as Fal.ai
    participant DB as PostgreSQL
    participant R2 as Cloudflare R2

    U->>FE: Select Brand + Product
    FE->>API: POST /copy_generation/generate
    API->>G: Generate ad copy variations
    G-->>API: Headlines, body text, CTAs
    API-->>FE: Return copy options

    U->>FE: Request image generation
    FE->>API: POST /generated_ads
    API->>F: Generate AI images
    F-->>API: Image URLs
    API->>R2: Upload images
    API->>DB: Save GeneratedAd record
    API-->>FE: Return ad with media

    U->>FE: Push to Facebook
    FE->>API: POST /facebook/campaigns
    API->>API: POST /facebook/adsets
    API->>API: POST /facebook/ads
    API->>DB: Sync campaign hierarchy
    API-->>FE: Campaign live
```

### Competitor Research Pipeline

```mermaid
flowchart LR
    A[User enters<br/>search keywords] --> B{Scraper Service}
    B -->|Primary| C[Facebook Ads<br/>Library API]
    B -->|Fallback: blocked<br/>or throttled| D[Chromium<br/>Browser Scraper]
    C --> E[Deduplication<br/>& Filtering]
    D --> E
    E --> F[(PostgreSQL<br/>SavedSearch +<br/>ScrapedAd)]
    F --> G[Research Page<br/>Browse & Analyze]
    G --> H[Save as<br/>WinningAd Template]
    H --> I[Ad Remix:<br/>Deconstruct Blueprint]
    I --> J[Reconstruct with<br/>Your Brand Data]

    style B fill:#e94560,stroke:#16213e,color:#fff
    style E fill:#0f3460,stroke:#16213e,color:#e2e8f0
    style I fill:#533483,stroke:#16213e,color:#e2e8f0
```

### Database Entity Relationships

```mermaid
erDiagram
    User ||--o{ RefreshToken : has
    User }o--o{ Role : has
    Role }o--o{ Permission : grants

    Brand ||--o{ Product : contains
    Brand }o--o{ CustomerProfile : targets
    Brand ||--o{ GeneratedAd : produces

    GeneratedAd }o--|| Product : for
    GeneratedAd }o--o| WinningAd : "based on template"

    WinningAd ||--|| ScrapedAd : "derived from"

    SavedSearch ||--o{ ScrapedAd : contains
    SavedSearch }o--o| Vertical : categorized

    FacebookCampaign ||--o{ FacebookAdSet : has
    FacebookAdSet ||--o{ FacebookAd : has

    BrandScrape ||--o{ BrandScrapedAd : contains
```

### Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | React 19, Vite 7, TailwindCSS |
| Backend | Python 3.11+, FastAPI 0.104, SQLAlchemy 2.0 |
| Database | PostgreSQL 15+ (Railway) |
| AI | Google Gemini (copy & vision), Fal.ai (images) |
| Storage | Cloudflare R2 (production), local uploads (dev) |
| Auth | JWT access tokens (30min) + refresh tokens (7 days) |
| Deployment | Railway (3 services) |

---

## API Reference

Interactive API documentation is available at `/api/v1/docs` when running the backend.

### Key Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/auth/login` | Authenticate user |
| `GET` | `/api/v1/brands` | List all brands |
| `POST` | `/api/v1/brands` | Create a brand |
| `GET` | `/api/v1/products` | List all products |
| `POST` | `/api/v1/research/scrape` | Scrape competitor ads |
| `POST` | `/api/v1/ad-remix/generate` | Generate ad variations |
| `POST` | `/api/v1/facebook/campaigns` | Create Facebook campaign |

---

## Testing

### E2E Tests (agent-browser)

```bash
cd frontend

# Run all smoke tests
npm run test:smoke

# Run with authentication
TEST_EMAIL=user@example.com TEST_PASSWORD=xxx npm run test
```

### Unit Tests

```bash
# Frontend
cd frontend
npm run test:unit

# Backend
cd backend
pytest
```

---

## Deployment

### Railway (Recommended)

Deploy to [Railway](https://railway.app) in minutes:

1. Fork this repo to your GitHub account
2. [Create a new Railway project](https://railway.app/new)
3. Click "Deploy from GitHub repo" and select your fork
4. Add a PostgreSQL database: **+ New** → **Database** → **PostgreSQL**
5. Set environment variables in both services (see `.env.example`)
6. Set `ALLOWED_ORIGINS` to your frontend URL
7. Deploy!

> **Tip:** Railway auto-detects the `railway.toml` config and creates both backend and frontend services.

📖 **[Full Deployment Guide →](./RAILWAY_DEPLOYMENT.md)**

### Docker

```bash
# Backend
cd backend
docker build -t fb-ad-backend .
docker run -p 8000:8000 --env-file ../.env.local fb-ad-backend

# Frontend
cd frontend
docker build -t fb-ad-frontend .
docker run -p 5173:5173 fb-ad-frontend
```

---

## Troubleshooting

<details>
<summary><strong>DATABASE_URL environment variable is required</strong></summary>

- Ensure `.env.local` exists in the project root
- Verify the DATABASE_URL format: `postgresql://user:pass@host:5432/dbname`
- Check PostgreSQL is running: `pg_isready`

</details>

<details>
<summary><strong>CORS errors in browser</strong></summary>

- Add your frontend URL to `ALLOWED_ORIGINS` in `.env.local`
- Restart the backend server

</details>

<details>
<summary><strong>Facebook API errors</strong></summary>

- Check if your access token has expired (they last ~60 days)
- Verify Ad Account ID format: `act_123456789`
- Ensure required permissions are granted

</details>

<details>
<summary><strong>AI generation not working</strong></summary>

- Verify `GEMINI_API_KEY` is set correctly
- Check API quota at [Google AI Studio](https://aistudio.google.com)
- For image generation, ensure `FAL_AI_API_KEY` is configured

</details>

---

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Commit your changes: `git commit -m 'Add amazing feature'`
4. Push to the branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

---

## Author


## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

<p align="center">
  Built with ❤️ by <a href="https://iscale.com">iSCALE</a> using FastAPI, React, and AI
</p>
