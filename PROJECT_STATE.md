# 🧭 Project State & Living Memory

> **Single Source of Truth**: This logbook tracks current implementation state, architectural decisions, invariants, and technical roadmap. Maintained in accordance with Rule 11.

---

## 1. Core Mission
An enterprise-grade autonomous AI Content Agency platform designed to conduct deep Google Autocomplete SEO keyword research, perform semantic topic clustering to eliminate keyword cannibalization, and autonomously generate comprehensive, long-form, fact-validated, and SEO-optimized articles streamed in real-time.

---

## 2. Active Tech Stack

| Layer | Technologies & Versions | Purpose |
| :--- | :--- | :--- |
| **Backend Framework** | FastAPI `0.111.0`, Python `3.11`, Uvicorn `0.29.0` | Asynchronous REST & SSE streaming API |
| **Domain Services** | Decoupled orchestrators (`article_orchestrator.py`), clean business logic | High-performance generation pipeline |
| **Database & ORM** | SQLAlchemy `2.0.30`, Alembic `1.13.1`, PostgreSQL / SQLite | Thread-safe connection pooled persistence (`pool_pre_ping=True`, `pool_size=10`) |
| **LLM Gateway** | Async `httpx >= 0.27.0` (Direct Google AI Studio REST/SSE API) | Gemini 3.8/3.7/3.6/3.5-flash & 3.1-pro models |
| **Auth & Security** | PyJWT `2.8.0`, Passlib `1.7.4` + Bcrypt `4.0.1`, SlowAPI `0.1.9` | JWT token authentication, dynamic rate limiting, bounded pagination |
| **Frontend Framework** | Next.js `14.2.35` (App Router), React `18`, TypeScript `5` | Modular Atomic Design, High-fidelity SSR/client application |
| **Styling & UI Atoms** | Tailwind CSS `3.4.1`, Radix UI primitives, Lucide React `1.21.0` | Dark/Light Glassmorphism design system |
| **Rich Text Editor** | TipTap `3.27.1` (StarterKit, Placeholder, DOMPurify) | Collaborative article editing & live preview |

---

## 3. Architectural Decisions & Invariants

1. **Clean Layer Decoupling (Anti-God-File Invariant)**:
   - Transport layers (FastAPI routes, Next.js page controllers) must remain thin coordinators. Complex orchestration is extracted to `services/` (e.g. `article_orchestrator.py`), and complex UI views are decomposed into atomic/molecular components (`KeywordSearchForm.tsx`, `KeywordResultsTable.tsx`).
2. **Direct Async HTTPX Gateway (Anti-gRPC Invariant)**:
   - LLM interactions communicate directly with Google AI Studio's REST (`:generateContent`) and SSE (`:streamGenerateContent?alt=sse`) endpoints via `httpx.AsyncClient`. Heavy gRPC client libraries are prohibited.
3. **Deterministic Data Flow (Archetype A)**:
   - Layers follow strict separation: `Presentation (React/Components) -> Transport (FastAPI Routes) -> Domain/Services (LLM Gateway, SEO Critic, Orchestrator) -> Persistence (SQLAlchemy/PostgreSQL)`.
4. **Database Guardrails & N+1 Elimination**:
   - Connection pooling enforced with `pool_pre_ping=True`, `pool_size=10`, `max_overflow=20`. All entity relation queries MUST utilize eager loading (`joinedload` / `selectinload`) to eliminate N+1 queries. Foreign keys and filtered/sorted columns must declare explicit indexes.
5. **Bounded Query & Rate Limiting Invariant**:
   - Unbounded queries (`.all()` without limits) are strictly forbidden across collection endpoints. Collections enforce `skip=0` and `limit=50` (max 100). All LLM-generating or AI-clustering endpoints MUST be guarded by SlowAPI rate limiting.
6. **Strict Secrets & Zero-Trust Boundary**:
   - Secrets (`GEMINI_API_KEY`, `SECRET_KEY`, `DATABASE_URL`) are loaded exclusively from runtime environment variables. All keys are sanitized of quotes/whitespace at runtime.
7. **Resilient Streaming Delivery**:
   - Real-time generation utilizes Server-Sent Events (SSE) with fallback accumulation on disconnects to guarantee zero partial-article loss.

---

## 4. Current Implementation State

- **Architecture & Decoupling (Hardened)**:
  - `ArticlePipeline` completely extracted from `endpoints/articles.py` to `services/article_orchestrator.py`. Endpoint file reduced by ~50% into a pure HTTP routing layer.
  - `keyword-research/page.tsx` decomposed into focused subcomponents: `KeywordSearchForm.tsx` and `KeywordResultsTable.tsx`.
- **Traffic & Query Guardrails (Hardened)**:
  - Bounded pagination enforced on `GET /api/v1/articles` (`skip: int = 0`, `limit: int = 50`) and `GET /api/v1/users` (`skip: int = 0`, `limit: int = 50`).
  - SlowAPI rate limiting added to `POST /api/v1/seo/cluster` via `@limiter.limit(get_dynamic_daily_limit)` preventing LLM token exhaustion.
  - Frontend `api.ts` upgraded with optional pagination parameters for `getArticles` and `getUsers`.
- **Database Layer (Hardened)**:
  - Connection pooling configured with `pool_pre_ping=True`, `pool_size=10`, `max_overflow=20`, `pool_timeout=30`, `pool_recycle=1800` in `session.py`.
  - Zero N+1 queries on article endpoints via `_article_query_with_relations` helper utilizing `joinedload(Article.author)`, `joinedload(Article.last_modified_by)`, and `selectinload(Article.assigned_editors)`.
  - Explicit database indexes on `Article.focus_keyword`, `Article.status`, `Article.author_id`, `Article.last_modified_by_id`, and `Article.created_at`.
- **Authentication & Authorization**:
  - `/api/v1/auth/login`, `/api/v1/auth/me` with JWT Bearer tokens and role-based access control (`admin`, `editor`, `writer`, `viewer`).
  - Next.js Edge Middleware (`middleware.ts`) protecting `/dashboard/*` with zero layout flash.
- **SEO Keyword Research & Clustering**:
  - Multi-layer Alphabet Soup scraper with language/country selection (`useGoogleSuggest.ts`).
  - AI Topic Clustering & Cannibalization Shield (`POST /api/v1/seo/cluster` via Gemini 3.7).
  - Magic Bridge integration directly passing cluster `pillar_keyword` and `h2_keywords` to Article Generator.
- **Autonomous Article Generation**:
  - Real-time SSE streaming (`POST /api/v1/articles/generate-stream`) with Web Research, semantic fact distribution, H2 section drafting, and automated SEO scoring.
  - Multi-model selector with full Gemini 3.8, 3.7, 3.6, 3.5, and 3.1 support.
- **Article & User Management**:
  - Dashboard article list with status workflows (`draft`, `pending_approval`, `approved`, `published`, `archived`).
  - Safe Glassmorphism confirmation dialogs replacing legacy `window.confirm` and `alert`.

---

## 5. Milestone Changelog

- **2026-10-22 (Phase 3 Session Invalidation & Logout Security Completed)**:
  - **Instant Token Revocation via `token_version`**: Integrated `token_version` tracking in `User` model, embedding `"tv"` claim into JWT payloads and enforcing live verification in `deps.py:get_current_user`.
  - **Server-Side Invalidation on Logout**: Added `POST /api/v1/auth/logout` endpoint that increments `token_version`, immediately invalidating all outstanding JWT sessions on all devices.
  - **Event-Driven Revocation**: Automatic `token_version` incrementation when user changes password (`update_me`) or when an administrator updates a user's password, role, or active status (`update_user`, `delete_user`).
  - **Frontend Logout Flow**: Updated `frontend/src/lib/api.ts` and `dashboard/layout.tsx` to execute server-side invalidation before clearing client cookies.
- **2026-10-22 (Phase 2 Auth & Session Hardening Completed)**:
  - **Account Lockout & Brute-Force Shield**: Added `failed_login_attempts` and `locked_until` to `User` model with automatic schema migration in `main.py`. Implemented 5-attempt threshold with a 15-minute lockout cooldown on `/api/v1/auth/login`.
  - **Password Strength Governance**: Enforced complexity rules in `UserCreate`, `UserUpdate`, and `ProfileUpdate` (min 8 chars, mandatory digit and letter, blacklisted common dictionary passwords like `12345678`, `password123`).
  - **Production Bootstrap Guard**: Added production safety check in `seed_admin` to prevent seeding default credentials (`Admin1234!`) when `ENVIRONMENT == "production"`.
  - **API Key Secrecy**: Moved Google Gemini API key transmission from URL query string to `x-goog-api-key` HTTP header in `LLMGateway`, preventing token leakage in proxy logs and APM tracing.
- **2026-10-22 (Phase 1 Security & Network Hardening Completed)**:
  - **SSRF & Credential Protection**: Implemented `app/core/network_security.py` with DNS and IP-range validation (`is_safe_external_url`), blocking loopback (`127.0.0.1`), metadata endpoints (`169.254.169.254`), and private subnets across `publish_article` and `WebResearcher`. Enforced credential isolation preventing leakage of `WP_APP_PASSWORD` to arbitrary URLs.
  - **Rate Limit IP Spoofing Neutralized**: Hardened `custom_rate_limit_key` in `app/core/limiter.py` to reject untrusted `X-Forwarded-For` injection and enforce `ipaddress` parsing.
  - **CORS Restricted**: Removed wildcard Vercel subdomain regex in `main.py`, restricting origins strictly to authorized entries.
  - **Unsafe GET Route Removed**: Eliminated `GET /articles/generate-stream`, locking AI generation exclusively to `POST`.
  - **Security Headers Injected**: Added FastAPI middleware and Next.js `headers()` for `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, and `Referrer-Policy: strict-origin-when-cross-origin`.
  - **Information Disclosure Prevented**: Sanitized error responses in `endpoints/seo.py`.
- **2026-10-22 (Full E2E Frontend Audit Completed)**: Automated headless browser testing via CDP across all 7 routes (`/login`, `/dashboard`, `/dashboard/articles`, `/dashboard/articles/[id]`, `/dashboard/articles/new`, `/dashboard/keyword-research`, `/dashboard/users`, `/dashboard/profile`). Zero React hydration errors, 0 network errors. Autonomously resolved 3 UI/UX defects: fixed mobile horizontal card overflow on `/login`, fixed HTML textarea illegibility in dark mode and added `dark:prose-invert` on `/dashboard/articles/[id]`, and fixed squished seed input on mobile in `KeywordSearchForm.tsx`.
- **2026-10-22 (Step 4 Completed)**: Decoupled monolithic files across stack. Extracted `ArticlePipeline` to `services/article_orchestrator.py` eliminating business logic from the HTTP router. Decomposed `keyword-research/page.tsx` into `KeywordSearchForm.tsx` and `KeywordResultsTable.tsx`.
- **2026-10-22 (Step 3 Completed)**: Enforced Unbounded Query Prevention with safe default pagination (`skip=0`, `limit=50`, max `100`) on `GET /articles` and `GET /users`. Protected `POST /seo/cluster` with SlowAPI rate limiting against token exhaustion. Extended frontend `api.ts` with optional pagination parameters.
- **2026-10-22 (Step 2 Completed)**: Resolved critical N+1 query problem across all article endpoints using `_article_query_with_relations` (`joinedload`/`selectinload`). Added connection pooling (`pool_pre_ping=True`, `pool_size=10`, `max_overflow=20`) to `session.py`. Added explicit database indexes on Article foreign keys and frequently filtered/sorted columns.
- **2026-10-22 (Step 1 Completed)**: Executed Architectural Audit against `PROJECT_ARCHITECTURE_STANDARDS.md`. Initiated 4-phase remediation roadmap. Purged backend node artifacts and created living governance files (`PROJECT_STATE.md`, `DEPENDENCY_GRAPH.md`).
- **2026-10-19**: Migrated LLM Gateway to Google AI Studio Gemini models (`gemini-3.7-flash` default). Resolved Dockerfile build dependencies on Render. Fixed `_has_api_key` validator and SSE error propagation.
- **2026-07-06**: Implemented Phase 2.5 AI Topic Clustering & Cannibalization Shield with Magic Bridge and `TopicClusterCard` accordion UI.
- **2026-07-01**: Integrated multi-role permissions, rate limiting via SlowAPI, and TipTap rich-text editing engine.

---

## 6. Next Immediate Steps & Known Blockers

- All 12 Global Engineering & Agentic System Directives are 100% satisfied and verified green.
- Architectural Scaffolding & Layer Decoupling (Steps 1-4) completed: zero God-files, N+1 eliminated, connection pool active, bounded pagination enforced.
- Comprehensive Headless Frontend E2E Audit completed: zero hydration errors, multi-viewport visual defects resolved.
- Full-Spectrum Security & Auth Hardening (Phases 1-3) completed: anti-SSRF shield, IP spoofing prevention, strict CORS, HTTP security headers, Account Lockout, password complexity, and instant session invalidation via `token_version`.
- Ready for deployment or commit upon user confirmation (no remote git push without affirmative instruction).
