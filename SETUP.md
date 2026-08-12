# ScreenerAI — Setup Guide

## Prerequisites

- Python 3.10+
- Node.js 18+
- Git

## 1. Backend

```bash
cd backend
python -m venv venv

# Windows:
venv\Scripts\activate
# Mac/Linux:
# source venv/bin/activate

pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

API: http://localhost:8000  
Docs: http://localhost:8000/docs

Optional demo data (destructive — resets DB):

```bash
python seed_data.py
```

Demo logins after seed:

- Admin: `admin@screener.dev` / `admin123`
- Recruiter: `recruiter@screener.dev` / `recruiter123`
- Candidate: `candidate@example.com` / `password123`

## 2. Frontend

```bash
cd frontend
npm install
cp .env.local.example .env.local
npm run dev
```

App: http://localhost:3000

## 3. Docker (optional)

From repo root:

```bash
docker compose up --build
```

## Project layout

```
SHRS/
├── backend/
│   ├── app/
│   │   ├── main.py          # FastAPI entry
│   │   ├── config.py        # Settings / env
│   │   ├── database.py      # SQLAlchemy session
│   │   ├── auth/            # JWT + RBAC
│   │   ├── models/          # DB models + schemas
│   │   ├── routes/          # API endpoints
│   │   └── ai/              # Parser, scorer, fraud, GitHub…
│   ├── samples/             # Demo JD + resumes
│   ├── tests/               # pytest
│   ├── seed_data.py
│   └── requirements.txt
├── frontend/
│   ├── app/                 # Next.js pages
│   ├── components/
│   ├── lib/                 # api, store, utils
│   └── package.json
├── docker-compose.yml
├── README.md
└── SETUP.md
```

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `bcrypt` errors | Keep `bcrypt==4.0.1` from requirements.txt |
| Frontend can't reach API | Set `NEXT_PUBLIC_API_URL` in `frontend/.env.local` |
| Port in use | Stop the other process or change port |
| First screening slow | `sentence-transformers` downloads MiniLM once (~80MB) |
