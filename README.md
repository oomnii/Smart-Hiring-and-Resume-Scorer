# ScreenerAI — Intelligent Resume Screening Tool
## 📊 Estimated Impact

### Assumptions

The following scenario estimates the screening process for **100 resumes**:

- Manual screening time: **6 minutes per resume**
- ScreenerAI setup and upload time: **15 minutes**
- Candidates shortlisted by ScreenerAI: **Top 20**
- Recruiter verification time: **4 minutes per shortlisted resume**

### Calculations

#### 1. Manual Screening Time

```text
Manual Time = Total Resumes × Time per Resume
            = 100 × 6
            = 600 minutes
            = 10 hours
```

#### 2. ScreenerAI-Assisted Screening Time

```text
Assisted Time = Setup Time + (Shortlisted Resumes × Verification Time)
              = 15 + (20 × 4)
              = 95 minutes
              = 1.58 hours
```

#### 3. Total Time Saved

```text
Time Saved = Manual Time - Assisted Time
           = 600 - 95
           = 505 minutes
           = 8.42 hours
```

#### 4. Percentage Reduction in Screening Time

```text
Time Reduction = (Time Saved ÷ Manual Time) × 100
               = (505 ÷ 600) × 100
               = 84.2%
```

#### 5. Screening Capacity Improvement

```text
Manual Capacity = Total Resumes ÷ Manual Time
                = 100 ÷ 10
                = 10 resumes/hour

ScreenerAI-Assisted Capacity = Total Resumes ÷ Assisted Time
                             = 100 ÷ 1.58
                             = 63.3 resumes/hour

Capacity Improvement = Assisted Capacity ÷ Manual Capacity
                     = 63.3 ÷ 10
                     = 6.3×
```

#### 6. Manual Workload Reduction

```text
Workload Reduction = ((Total Resumes - Shortlisted Resumes) ÷ Total Resumes) × 100
                   = ((100 - 20) ÷ 100) × 100
                   = 80%
```

### Final Results

| Metric | Manual Process | ScreenerAI-Assisted | Estimated Impact |
|---|---:|---:|---:|
| Recruiter active time | 10 hours | 1.58 hours | **84.2% reduction** |
| Time saved per 100 resumes | — | 8.42 hours | **505 minutes saved** |
| Screening capacity | 10 resumes/hour | 63.3 resumes/hour | **6.3× higher** |
| Resumes manually reviewed | 100 | 20 shortlisted | **80% less workload** |
| Evaluation method | Reviewer-dependent | Same five-factor formula | **Consistent first-pass scoring** |

### Technical Results

- Generates explainable **0–100 match scores** using five weighted factors.
- Uses **384-dimensional MiniLM embeddings** with cosine similarity.
- Supports **PDF, DOCX, and TXT** resume formats.
- Provides separate workflows for **Admin, Recruiter, and Candidate** roles.
- Runs the primary scoring pipeline locally without requiring a paid AI API.

> **Note:** These figures are scenario-based estimates of recruiter active time, not measured production benchmarks. Actual results depend on resume volume, shortlist size, hardware, and recruiter workflow.

## Quick Start (Local Dev)

### 1. Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Copy env file
cp .env.example .env
# Edit .env if needed (defaults work for local dev with SQLite)

# Start server
uvicorn app.main:app --reload --port 8000

# Seed sample data (optional but recommended)
python seed_data.py
```

### 2. Frontend Setup

```bash
cd frontend
npm install

# Set API URL
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local

npm run dev
```

### 3. Visit

- Frontend: http://localhost:3000
- API Docs: http://localhost:8000/docs

### Demo Credentials

After running `seed_data.py`:

- **Admin**: `admin@screener.dev` / `admin123`
- **Recruiter**: `recruiter@screener.dev` / `recruiter123`

---

## Docker Compose (Full Stack)

```bash
docker compose up --build
```

---

## Environment Variables

### Backend `.env`

| Variable           | Default                        | Description                         |
| ------------------ | ------------------------------ | ----------------------------------- |
| `SECRET_KEY`       | dev-key                        | JWT secret — change in production   |
| `DATABASE_URL`     | sqlite:///./resume_screener.db | SQLite (dev) or PostgreSQL (prod)   |
| `OPENAI_API_KEY`   | (empty)                        | Optional — enables LLM explanations |
| `UPLOAD_DIR`       | ./uploads                      | Resume file storage                 |
| `MAX_FILE_SIZE_MB` | 10                             | Max upload size                     |

### Frontend `.env.local`

| Variable              | Default               | Description     |
| --------------------- | --------------------- | --------------- |
| `NEXT_PUBLIC_API_URL` | http://localhost:8000 | Backend API URL |

---

## How Scoring Works

Each resume is scored against the job description using 5 weighted components:

| Component                | Weight | Method                                                                  |
| ------------------------ | ------ | ----------------------------------------------------------------------- |
| **Semantic Similarity**  | 40%    | Cosine similarity of sentence-transformer embeddings (all-MiniLM-L6-v2) |
| **Skill Keyword Match**  | 35%    | NLP skill extraction with synonym normalization                         |
| **Experience Alignment** | 15%    | Years of experience vs JD requirement                                   |
| **Education Alignment**  | 5%     | Degree/certification detection                                          |
| **Formatting & Clarity** | 5%     | Section detection heuristics                                            |

**Seniority** is estimated from years of experience and role keywords: Intern → Junior → Mid → Senior → Staff/Principal.

**Evidence snippets** are extracted by finding sentences that contain matched skills and top-similarity resume chunks.

---

## Fairness Guardrails

- PII (email, phone) is **masked before embedding** — not used in scoring
- Names, locations, age are **not used** in any scoring component
- Fairness Guardrails Enabled" is displayed on every candidate analysis
- The system scores only: skills, experience patterns, and semantic relevance to the JD
- **GitHub Validation**: (New) Automatically validates project claims by fetching repository data for linked profiles.

---

## Key Features

- **AI Resume Screening**: Semantic-aware matching using local transformer embeddings.
- **GitHub Analyzer**: Deep project-level analysis including star counts and repo descriptions.
- **Dynamic Resume Review**: Personalized AI feedback quoting actual resume segments.
- **Unified Search**: Search across candidates and jobs using semantic queries.
- **Market Recommendations**: Personalized skill suggestions based on live job demand.

---

## Sample Data

5 sample resumes included in `backend/samples/resumes/`:

- `alice_chen_senior_backend.txt` — Strong match (Senior, 7yr, Python/AWS/K8s)
- `bob_martinez_mid_backend.txt` — Moderate match (Mid, 4yr, Python/Django)
- `carol_johnson_frontend_mismatch.txt` — Weak match (Frontend engineer)
- `david_kim_overqualified.txt` — High match, 14yr (Principal/Staff level)
- `emma_patel_junior.txt` — Low match (Recent grad, entry-level)

---

## API Endpoints

```
POST   /auth/signup
POST   /auth/login
GET    /auth/me

POST   /jobs
GET    /jobs
GET    /jobs/{id}
DELETE /jobs/{id}

POST   /jobs/{id}/resumes   (multipart upload)
GET    /jobs/{id}/resumes
DELETE /resumes/{id}

POST   /jobs/{id}/screen
GET    /jobs/{id}/results
PATCH  /results/{id}

GET    /analytics/jobs/{id}
GET    /analytics/admin      (admin only)

GET    /candidate/profile
POST   /candidate/profile    (multipart resume upload)
POST   /candidate/apply/{id}
GET    /candidate/applications
GET    /candidate/resume-tips
GET    /candidate/skills-suggestions
GET    /candidate/recommendations
```

---

## Running Tests

```bash
cd backend
pytest tests/ -v
```

---

## Deployment

**Frontend → Vercel**

```bash
cd frontend
npx vercel --prod
# Set NEXT_PUBLIC_API_URL to your backend URL
```

**Backend → Render / Fly.io**

```bash
# Set DATABASE_URL to PostgreSQL (Supabase/Neon)
# Set SECRET_KEY to a secure random string
# Deploy via Dockerfile
```

**Database → Supabase / Neon (PostgreSQL)**

```
DATABASE_URL=postgresql://user:pass@host:5432/dbname
```

---

## Tech Stack

| Layer          | Technology                               |
| -------------- | ---------------------------------------- |
| Frontend       | Next.js 14 (App Router) + TypeScript     |
| Styling        | TailwindCSS + Custom CSS Variables       |
| Backend        | FastAPI (Python 3.11)                    |
| Database       | SQLite (dev) / PostgreSQL (prod)         |
| ML Embeddings  | sentence-transformers (all-MiniLM-L6-v2) |
| PDF Parsing    | pypdf + pdfminer.six                     |
| DOCX Parsing   | python-docx                              |
| Auth           | JWT (python-jose + passlib/bcrypt)       |
| LLM (optional) | OpenAI GPT-3.5 with template fallback    |

---

## Design System: Editorial Terminal Noir

- **Display font**: Fraunces (expressive serif)
- **Body font**: IBM Plex Sans
- **Mono accent**: JetBrains Mono
- **Background**: Near-black with brown-ink undertone `#0e0b08`
- **Accent**: Acid lime `#c8f23a`
- **Grid overlay**: Subtle 40px grid with lime tint
- **Cards**: "Printed dossier" with terminal overlay hover effects
- **Buttons**: Brutalist clip-path chamfered corners
