# 🌳 Project Dependency Graph

> **Structural Module Hierarchy**: Maintained in accordance with Rule 2. Defines architectural roots, branches, parents/children, and consumer relationships across the full-stack system.

---

## 1. System Architecture Overview

```text
[Frontend: Next.js Client / SSR (Atomic SEO Components)]
       │
       ▼ (HTTP / SSE / JSON - with Bounded Pagination & Interceptors)
[Backend: FastAPI Transport Layer + SlowAPI Limiter]
       │
       ├─────────────────────────────────┐
       ▼                                 ▼
[Domain Services Layer]          [Data Access Layer (SQLAlchemy ORM)]
(Article Orchestrator, LLM,               │ (Connection Pool: size=10, pre_ping=True)
 Web Research, SEO Critic)                ▼
       │                        [Database: PostgreSQL / SQLite]
       ▼
[Google AI Studio Gemini API]
```

---

## 2. Backend Module Dependency Tree

```text
backend/app/main.py (Root Application Entrypoint)
├── app/core/
│   ├── config.py (Settings singleton loaded from .env)
│   ├── security.py (Passlib password hasher, PyJWT encode/decode)
│   │   └── Consumer: app/api/v1/endpoints/auth.py, app/api/v1/deps.py
│   ├── limiter.py (SlowAPI rate limiter with custom IP/user key extractor)
│   │   ├── Dependencies: app/core/config.py, app/db/session.py, app/models/setting.py
│   │   └── Consumers: app/main.py, app/api/v1/endpoints/auth.py, app/api/v1/endpoints/articles.py, app/api/v1/endpoints/seo.py
│   └── network_security.py (SSRF guardian & private subnet/metadata IP resolver)
│       └── Consumers: app/api/v1/endpoints/articles.py, app/services/web_researcher.py
├── app/db/
│   └── session.py (SQLAlchemy DeclarativeBase, Engine with Connection Pool, SessionLocal, get_db generator)
│       ├── Dependencies: app/core/config.py
│       └── Consumers: app/main.py, app/api/v1/deps.py, app/models/*
├── app/models/ (SQLAlchemy Declarative Entity Mappings with Indexes)
│   ├── user.py (User table with credentials, roles, and article relationship)
│   ├── article.py (Article table with indexed FKs, status, and created_at)
│   ├── article_editor.py (ManyToMany join table between articles and editor users)
│   └── setting.py (Key-value system configuration store)
├── app/schemas/ (Pydantic v2 Serialization & Request Contracts)
│   ├── user.py (UserCreate, UserUpdate, UserResponse, Token)
│   ├── article.py (GenerateRequest, ArticleResponse, ArticleListResponse, ArticleUpdate)
│   ├── seo.py (ClusterRequest, ClusterResponse, ClusterItem with suggested_h1, target_audience, resilient defaults)
│   └── setting.py (SettingResponse, SettingUpdate)
├── app/services/ (Pure Business & Algorithmic Domain Logic)
│   ├── article_orchestrator.py (Central generation orchestrator, state manager, streaming pipeline)
│   │   ├── Dependencies: app/core/config.py, app/models/*, app/services/llm_gateway.py, app/services/seo_generator.py, app/services/web_researcher.py
│   │   └── Consumers: app/api/v1/endpoints/articles.py
│   ├── llm_gateway.py (Async HTTPX REST & SSE gateway to Google Gemini with provider-prefix stripping & automatic fallback)
│   │   ├── Dependencies: app/core/config.py
│   │   └── Consumers: app/services/article_orchestrator.py, app/services/seo_generator.py, app/services/seo_critic.py, app/api/v1/endpoints/seo.py
│   ├── json_utils.py (Robust markdown/JSON extractor and parser)
│   │   └── Consumers: app/services/seo_generator.py, app/api/v1/endpoints/seo.py
│   ├── web_researcher.py (Serper Google Search client & content scraper)
│   │   ├── Dependencies: app/core/config.py, httpx, bs4
│   │   └── Consumers: app/services/article_orchestrator.py
│   ├── seo_critic.py (Multi-metric SEO evaluation engine with fallback heuristics)
│   │   └── Dependencies: app/services/llm_gateway.py
│   └── seo_generator.py (Fact deduplication, outline generator, section drafter, ArticleState)
│       └── Dependencies: app/services/llm_gateway.py, app/services/json_utils.py
└── app/api/v1/ (HTTP Transport & Endpoints)
    ├── deps.py (Dependency injection: get_db, get_current_user, require_admin, require_editor)
    │   └── Dependencies: app/core/security.py, app/core/config.py, app/db/session.py, app/models/user.py
    └── endpoints/
        ├── auth.py (POST /auth/login [10/min], GET /auth/me)
        ├── users.py (GET /users [paginated: skip, limit], POST, PUT, DELETE /users)
        ├── settings.py (GET, PUT /settings/{key})
        ├── seo.py (POST /seo/cluster [_normalize_cluster_data, Rate-Limited: dynamic_daily_limit])
        └── articles.py (POST /articles/generate-stream, GET /articles [paginated: skip, limit], GET/PATCH/DELETE /articles/{id})
```

---

## 3. Frontend Module Dependency Tree

```text
frontend/src/ (Next.js Application Root)
├── middleware.ts (Edge routing guard; redirects unauthenticated users from /dashboard)
├── lib/
│   ├── api.ts (Central Axios instance, JWT token interceptors, typed API client with optional pagination)
│   └── utils.ts (Tailwind cn utility)
├── hooks/
│   └── useGoogleSuggest.ts (Alphabet soup scraper, recursive suggestion generator, translation)
├── components/
│   ├── ui/ (Atomic Design System Primitives)
│   │   ├── button.tsx, card.tsx, input.tsx, label.tsx, select.tsx, badge.tsx, checkbox.tsx
│   ├── editor/
│   │   └── TipTapEditor.tsx (Rich text WYSIWYG editor with DOMPurify sanitization)
│   ├── seo/
│   │   ├── KeywordSearchForm.tsx (Search parameter inputs, scan type selectors, run/stop buttons)
│   │   ├── KeywordResultsTable.tsx (Tabular keyword list, badges, copy/google actions, magic bridge, pagination)
│   │   ├── KeywordAnalyticsCard.tsx (Visual metrics for keyword frequency and distribution)
│   │   └── TopicClusterCard.tsx (Interactive accordion rendering cluster H1 & H2 pills)
│   └── dashboard/
│       └── ArticleGenerator.tsx (SSE generation form, model selector, outline and section stream)
└── app/ (Next.js App Router Pages)
    ├── layout.tsx (Root layout, Geist fonts, ThemeProvider)
    ├── globals.css (Tailwind CSS custom directives and color variables)
    ├── (auth)/
    │   └── login/page.tsx (Login form, JWT authentication storage)
    └── dashboard/
        ├── layout.tsx (Dashboard shell, sidebar navigation, user profile badge, logout)
        ├── page.tsx (Dashboard overview metrics, recent articles table, quick action cards)
        ├── articles/
        │   ├── page.tsx (Article management list, status filter, glassmorphism action modals)
        │   ├── [id]/page.tsx (Article editor, revision history, WordPress publisher, AI improver)
        │   └── new/page.tsx (Magic Bridge target; mounts ArticleGenerator with URL params)
        ├── keyword-research/page.tsx (Modular coordinator page; wires KeywordSearchForm, ResultsTable, Clusters)
        ├── users/page.tsx (Admin user management, role assignments, publish toggles)
        └── profile/page.tsx (User profile, password update form)
```

---

## 4. Consumer Contracts & Cross-Boundary Coupling

| Consumer Module | Dependent Provider | Coupling Type | Data Contract |
| :--- | :--- | :--- | :--- |
| `frontend/src/lib/api.ts` | `backend/app/api/v1/*` | REST / SSE HTTP | JSON payloads conforming to `schemas/*` with optional `skip`/`limit` |
| `frontend/ArticleGenerator.tsx` | `backend/articles/generate-stream` | SSE Stream | Line-delimited `data: {"step": ..., "content": ...}` |
| `frontend/keyword-research` | `frontend/components/seo/*` | Component Composition | React Props (`KeywordSearchFormProps`, `KeywordResultsTableProps`) |
| `backend/endpoints/articles.py` | `backend/services/article_orchestrator.py` | Python Service Orchestration | `ArticlePipeline(db, user, model).execute_stream()` |
| `backend/services/article_orchestrator.py` | `backend/services/llm_gateway.py` | Python Class Dependency | `LLMGateway.generate()` Async Generator |
| `backend/services/article_orchestrator.py` | `backend/services/seo_generator.py` | Python Class Dependency | `SEOGenerator.draft_section_stream()` |
| `backend/services/seo_generator.py`| `backend/services/llm_gateway.py` | Python Class Dependency | System instructions & JSON mode prompt payloads |
