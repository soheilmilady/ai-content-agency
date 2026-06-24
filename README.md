# پلتفرم محتوای هوشمند (AI Content Agency)

پلتفرمی برای تولید، ویرایش، بررسی سئو و انتشار مقالات فارسی با کمک هوش مصنوعی. شامل پنل مدیریت کاربران، تولید محتوا با استریم زنده، ویرایشگر Rich Text، و انتشار مستقیم در وردپرس.

**Live Demo:** [https://demo.ai-content-agency.example.com](https://demo.ai-content-agency.example.com) *(placeholder)*

---

## معماری سیستم

```
┌─────────────┐     REST / SSE      ┌──────────────┐
│  Next.js 14 │ ◄─────────────────► │  FastAPI     │
│  Frontend   │   JWT + Cookie      │  Backend     │
└─────────────┘                     └──────┬───────┘
                                           │
              ┌────────────────────────────┼────────────────────────────┐
              │                            │                            │
              ▼                            ▼                            ▼
        ┌──────────┐              ┌─────────────────┐           ┌─────────────┐
        │  SQLite  │              │  Groq           │           │  Serper     │
        │  (users, │              │  (LLM Gateway)  │           │  (تحقیق وب) │
        │ articles)│              └─────────────────┘           └─────────────┘
        └──────────┘                            │
                                                ▼
                                       ┌─────────────────┐
                                       │  WordPress REST │
                                       │  API (انتشار)   │
                                       └─────────────────┘
```

**جریان تولید مقاله:**

1. **تحقیق وب** — جستجو در Serper و استخراج تیترهای رقبا
2. **طراحی ساختار** — تولید outline سئو (H1، بخش‌ها، meta description)
3. **نگارش** — نوشتن هر بخش با LLM
4. **بررسی سئو** — امتیازدهی و بهبود خودکار (حداکثر ۲ بار)
5. **ذخیره / انتشار** — پیش‌نویس در DB یا انتشار در وردپرس

**نقش‌های کاربری:** `admin`، `editor`، `writer`، `viewer`

---

## اجرا با Docker

### پیش‌نیاز

- Docker و Docker Compose
- فایل `backend/.env` (از روی `.env.example` کپی کنید)

```bash
cp backend/.env.example backend/.env
# مقادیر API key و WordPress را ویرایش کنید
```

### راه‌اندازی

```bash
docker-compose up -d
```

| سرویس | آدرس |
|--------|------|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| Swagger Docs | http://localhost:8000/docs |
| Health Check | http://localhost:8000/health |

**ورود پیش‌فرض ادمین:**

- ایمیل: `admin@agency.com`
- رمز: `Admin1234!`

> **نکته:** برای درخواست‌های مرورگر، در production مقدار `NEXT_PUBLIC_API_URL` باید از دید کلاینت قابل دسترس باشد (مثلاً `http://localhost:8000/api/v1`). در صورت نیاز، هنگام build فرانت‌اند این متغیر را تنظیم کنید.

---

## اجرا در Development

### Backend (Python 3.11)

```bash
cd backend
py -3.11 -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux/macOS
pip install -r requirements.txt
cp .env.example .env
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend (Node 20)

```bash
cd frontend
npm install
cp .env.local.example .env.local
npm run dev
```

فرانت‌اند روی http://localhost:3000 و API روی http://localhost:8000 اجرا می‌شود.

---

## متغیرهای محیطی

### Backend (`backend/.env`)

| متغیر | توضیح | پیش‌فرض |
|--------|--------|---------|
| `DATABASE_URL` | اتصال دیتابیس | `sqlite:///./app.db` |
| `SECRET_KEY` | کلید JWT | `change-me-in-production` |
| `ALGORITHM` | الگوریتم JWT | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | انقضای توکن (دقیقه) | `1440` |
| `GROQ_API_KEY` | کلید Groq | — |
| `SERPER_API_KEY` | کلید Serper (جستجو) | — |
| `WP_URL` | آدرس سایت وردپرس | — |
| `WP_USERNAME` | نام کاربری وردپرس | — |
| `WP_APP_PASSWORD` | Application Password | — |
| `DEFAULT_LLM_MODEL` | مدل پیش‌فرض LLM | `llama-3.3-70b-versatile` |

### Frontend (`frontend/.env.local`)

| متغیر | توضیح | پیش‌فرض |
|--------|--------|---------|
| `NEXT_PUBLIC_API_URL` | آدرس API | `http://localhost:8000/api/v1` |

---

## API Documentation

مستندات تعاملی Swagger UI:

**http://localhost:8000/docs**

ReDoc:

**http://localhost:8000/redoc**

### endpointهای اصلی

| Method | Path | توضیح |
|--------|------|-------|
| POST | `/api/v1/auth/login` | ورود و دریافت JWT |
| GET | `/api/v1/auth/me` | اطلاعات کاربر جاری |
| PATCH | `/api/v1/auth/me` | ویرایش پروفایل (ایمیل، رمز) |
| GET/POST/PUT/DELETE | `/api/v1/users` | مدیریت کاربران (admin) |
| POST | `/api/v1/articles/generate` | تولید مقاله |
| POST | `/api/v1/articles/generate-stream` | تولید با SSE |
| GET/PATCH | `/api/v1/articles/{id}` | مشاهده / ویرایش |
| POST | `/api/v1/articles/{id}/publish` | انتشار در وردپرس |

---

## ساختار پروژه

```
ai-content-agency/
├── backend/                 # FastAPI + SQLAlchemy
│   ├── app/
│   │   ├── api/v1/          # REST endpoints
│   │   ├── core/            # config, security
│   │   ├── db/              # session
│   │   ├── models/          # User, Article
│   │   └── services/        # LLM, SEO, research
│   ├── main.py
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/                # Next.js 14 + Shadcn/UI
│   ├── src/
│   │   ├── app/             # pages (App Router)
│   │   ├── components/      # UI, TipTap editor
│   │   └── lib/             # API client
│   └── Dockerfile
├── docker-compose.yml
└── README.md
```

---

## توقف سرویس‌ها

```bash
docker-compose down
```

برای rebuild بعد از تغییرات:

```bash
docker-compose up -d --build
```
