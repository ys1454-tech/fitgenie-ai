# FitGenie AI

**Personalized fitness and nutrition planning powered by Amazon Bedrock.**

FitGenie AI is a college Applied Generative AI project that collects a user's personal fitness profile and uses an LLM to generate a tailored 7-day workout and meal plan. Users can modify the plan through a conversational chat interface and request exercise or food substitutions.

---

## Technology Stack

| Layer       | Technology                |
|-------------|---------------------------|
| Frontend    | React.js (v18)            |
| Backend     | Python 3.11+, FastAPI     |
| LLM         | Amazon Bedrock (Claude)   |
| Database    | SQLite                    |

---

## Project Structure

```
gen ai project/
├── backend/
│   ├── main.py                  # FastAPI entry point
│   ├── requirements.txt         # Python dependencies
│   ├── .env.example             # Configuration template (copy → .env)
│   ├── api/
│   │   └── routes/
│   │       └── health.py        # GET /api/health
│   ├── core/
│   │   └── config.py            # Reads .env settings
│   ├── database/                # SQLite layer (Stage 2)
│   ├── models/                  # Pydantic request/response models (Stage 4)
│   └── prompts/                 # Prompt templates (Stage 3)
│
├── frontend/
│   ├── package.json
│   ├── .env                     # REACT_APP_API_URL
│   ├── public/
│   │   └── index.html
│   └── src/
│       ├── index.js
│       ├── App.js               # Router + layout
│       ├── App.css              # Global styles
│       ├── pages/
│       │   └── HomePage.jsx     # Landing page
│       ├── components/
│       │   └── Disclaimer.jsx   # Wellness disclaimer
│       └── services/
│           └── api.js           # API service layer
│
└── README.md
```

---

## Getting Started

### Prerequisites

- **Python 3.11+** installed
- **Node.js 18+** and **npm** installed

---

### Backend Setup

```bash
# 1. Navigate to the backend folder
cd backend

# 2. (Recommended) Create and activate a virtual environment
python -m venv venv

# On Windows:
venv\Scripts\activate

# On macOS/Linux:
source venv/bin/activate

# 3. Install CPU-only PyTorch, then the backend dependencies
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt

# 4. Create your .env file from the template
copy .env.example .env        # Windows
# cp .env.example .env        # macOS/Linux

# 5. Open .env and fill in your AWS credentials

# 6. Start the backend server
uvicorn main:app --reload --port 8000
```

The first NLP request downloads the `all-MiniLM-L6-v2` Transformer model from Hugging Face (about 90 MB). It is cached locally for subsequent runs. The local Transformer handles intent classification; Gemini remains responsible for profile extraction and plan generation.

The backend will be available at: **http://localhost:8000**

- API docs (Swagger UI): http://localhost:8000/docs
- Health check: http://localhost:8000/api/health

---

### Frontend Setup

```bash
# 1. Navigate to the frontend folder
cd frontend

# 2. Install dependencies
npm install

# 3. Start the development server
npm start
```

The frontend will be available at: **http://localhost:3000**

---

## API Endpoints (Stage 1)

| Method | Endpoint       | Description                  |
|--------|---------------|------------------------------|
| GET    | `/`           | Welcome message              |
| GET    | `/api/health` | Backend health check         |
| GET    | `/docs`       | Swagger UI (auto-generated)  |

More endpoints will be added in Stages 2–4.

---

## Development Stages

| Stage | Description                       | Status      |
|-------|-----------------------------------|-------------|
| 1     | Project scaffolding               | ✅ Complete  |
| 2     | SQLite database layer             | ⏳ Planned  |
| 3     | Amazon Bedrock + prompt templates | ⏳ Planned  |
| 4     | Backend plan generation APIs      | ⏳ Planned  |
| 5     | Frontend profile form             | ⏳ Planned  |
| 6     | Frontend 7-day plan display       | ⏳ Planned  |
| 7     | Chat modification + substitution  | ⏳ Planned  |
| 8     | Polish + error handling           | ⏳ Planned  |

---

## Important Notes

- **AWS credentials** must be placed in `backend/.env` — never commit this file.
- The `.env.example` file is a safe template with no real credentials.
- The frontend never contacts Amazon Bedrock directly — all LLM calls go through the FastAPI backend.
- This project is for educational purposes. Generated plans are not medical advice.
