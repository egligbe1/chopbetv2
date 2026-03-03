# ⚽ ChopBet — AI-Powered Football Prediction Platform

ChopBet uses **Google Gemini AI** to analyze daily football fixtures from BBC Sport and Goal.com, generating high-confidence match predictions with automated result tracking.

## Architecture

```
chop-bet2/
├── backend/          # FastAPI + Python
│   ├── main.py             # App entry point, middleware, CORS
│   ├── gemini_engine.py    # Gemini AI prediction engine
│   ├── results_checker.py  # Automated result verification
│   ├── scheduler.py        # APScheduler cron jobs
│   ├── search_utils.py     # BBC & Goal.com scrapers
│   ├── models.py           # SQLAlchemy ORM models
│   ├── database.py         # DB engine & session config
│   └── routes/
│       ├── predictions.py  # /predictions/* endpoints
│       ├── stats.py        # /stats/* endpoints
│       └── admin.py        # /admin/* endpoints
├── frontend/         # Next.js 16 + React 19
│   ├── app/
│   │   ├── page.tsx        # Home — today's predictions
│   │   ├── stats/          # Performance analytics
│   │   ├── results/        # Historical results browser
│   │   ├── admin/          # Admin dashboard
│   │   └── about/          # About page
│   ├── components/         # Reusable UI components
│   └── lib/api.ts          # API client with retry logic
└── README.md
```

| Layer | Tech |
|-------|------|
| **Backend** | Python · FastAPI · SQLAlchemy · APScheduler |
| **AI Engine** | Google Gemini 2.5 Flash (structured JSON output) |
| **Database** | PostgreSQL (Neon) with Alembic migrations |
| **Frontend** | Next.js 16 · React 19 · Tailwind CSS 4 · Recharts |
| **Data Sources** | BBC Sport · Goal.com |

## Getting Started

### Prerequisites

- Python 3.10+
- Node.js 18+
- PostgreSQL database (e.g. [Neon](https://neon.tech))
- [Google Gemini API key](https://aistudio.google.com/apikey)

### Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux
pip install -r requirements.txt
alembic upgrade head
uvicorn main:app --reload
```

Create a `backend/.env` file:

```env
DATABASE_URL=postgresql://user:pass@host/dbname
GEMINI_API_KEY=your_gemini_api_key
FALLBACK_GEMINI_API_KEY=optional_backup_key
ADMIN_API_KEY=your_admin_secret
TAVILY_API_KEY=your_tavily_key
FRONTEND_URL=http://localhost:3000
ENV=development
PORT=8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Create a `frontend/.env.local` file:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Features

### Prediction Engine
- Scrapes daily fixtures from **BBC Sport** and **Goal.com**
- Sends fixtures to **Gemini 2.5 Flash** for batch analysis
- Generates predictions with confidence scores, odds, and reasoning
- Deduplicates across sources before saving
- Markets: HT Over 0.5, Total Over 1.5, BTTS, 1X2

### Automated Scheduling
| Job | Time (UTC) | Description |
|-----|-----------|-------------|
| Predictions | 07:00 | Generate daily football predictions |
| Results | 23:00 | Verify match outcomes via Google Search |

### Admin Dashboard
- Manually trigger prediction generation
- Manually trigger results checking
- Clear pending predictions
- Protected by `X-Admin-Key` header

### Analytics
- Overall accuracy tracking
- Breakdown by league and market type
- Daily accuracy trend charts
- Win streak tracking

### Frontend UX
- Daily accumulator card (top 5 picks)
- Predictions grouped by league
- Historical results browser with date picker
- Background auto-refresh with retry on failure
- Responsive, dark-themed glassmorphism design

## API Endpoints

### Predictions
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/predictions/today` | Today's predictions |
| `GET` | `/predictions/date/{date}` | Predictions by date |
| `GET` | `/predictions/accumulator` | Daily top-5 accumulator |
| `GET` | `/predictions/history` | Paginated history |

### Stats
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/stats/accuracy` | Overall accuracy stats |
| `GET` | `/stats/accuracy/league` | Accuracy by league |
| `GET` | `/stats/accuracy/market` | Accuracy by market |
| `GET` | `/stats/daily` | Daily chart data |

### Admin
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/admin/trigger-predictions` | Run prediction engine |
| `POST` | `/admin/trigger-results` | Run results checker |
| `POST` | `/admin/clear-pending` | Delete pending predictions |

## Disclaimer

Predictions are AI-generated for informational purposes only. Not financial advice. Use at your own risk.
