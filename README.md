# LexiLoop

**An AI-powered adaptive reading companion for children with dyslexia.**

LexiLoop combines computer vision, NLP, and an LLM-powered tutor agent to help children with dyslexia practice reading and writing — detecting handwriting difficulties, simplifying text to match a child's needs, generating personalized reading exercises, and adapting over time based on each child's evolving profile.

---

## The problem

Children with dyslexia don't struggle with just one thing — reading difficulty shows up as letter reversals in handwriting, unfamiliar vocabulary, overly long sentences, and shifting comprehension depending on mood and fatigue. Most tools address only one of these at a time (a spellchecker, a readability score, a worksheet generator). LexiLoop's goal is to treat these as one connected picture: what a child writes, what they read, and how they're doing feed into a single evolving profile that shapes what the app does next.

## What it does

- **Detects handwriting patterns** — a photo of a child's handwriting is analyzed by a custom CNN to flag common dyslexia-related letter confusions (b/d, p/q, n/u, m/w, s/z) and reversal patterns.
- **Simplifies text** — a T5-based ML pipeline (with a rule-based fallback) rewrites text into simpler vocabulary and shorter sentences, scored against Flesch readability metrics.
- **Generates personalized reading exercises** — pulls a level-appropriate story via retrieval-augmented generation and writes comprehension questions tailored to the child's recent error patterns.
- **Tutors conversationally** — a LangChain tool-calling agent (running LLaMA3 via Groq) chats with the child, tracks mood/frustration, and updates the child's profile with what it learns each session.
- **Tracks progress visually** — a parent/teacher dashboard shows each child's journey as a winding path of completed sessions, plus recent mood trends and reversal patterns.

## Architecture

```
User (parent/teacher/child)
        │
        ▼
  React frontend  ──────────────►  FastAPI backend  ──────────────►  MongoDB Atlas
  (dashboard, capture UI,          (JWT auth, routes)                (evolving child
   exercises, chat)                       │                           profiles, sessions)
                                            │
                        ┌───────────────────┴───────────────────┐
                        ▼                                       ▼
              CNN handwriting detector              LangChain reading-tutor agent
              (CNN + Mediapipe,                     (LLaMA3 via Groq)
               reused from the                      Tools: simplify_text, retrieve_story
               Handwriting Analyzer                 (RAG over story library), log_mood,
               project)                              update_child_profile
```

Every module reads from and writes to the same MongoDB-backed child profile, so a detected letter reversal, a logged mood, and a chat exchange all feed into the same evolving picture of that child — this is what makes the exercises and tutor responses adapt over time rather than staying static.

## Tech stack

| Layer | Technology |
|---|---|
| Frontend | React.js, React Router, Vite |
| Backend | FastAPI, JWT authentication, Pydantic |
| Database | MongoDB Atlas, Motor (async driver) |
| Computer vision | Custom CNN (PyTorch), Mediapipe, trained on EMNIST Letters |
| NLP | Hugging Face Transformers (T5-small), NLTK, WordNet, WordFreq, textstat |
| AI agent | LangChain (tool-calling agent), Groq API (LLaMA3), FAISS, sentence-transformers (RAG) |

## Project structure

```
lexiloop_backend/
├── app/
│   ├── main.py                  # FastAPI entrypoint
│   ├── config.py                # environment/settings
│   ├── database.py              # MongoDB collections
│   ├── auth.py                  # JWT auth logic
│   ├── schemas.py                # Pydantic models
│   ├── routers/                 # /auth, /children, /detect, /simplify, /chat, /exercises
│   └── ai/
│       ├── handwriting/         # CNN model + analyzer (reused from Handwriting Analyzer)
│       ├── simplify_engine.py   # T5 pipeline (reused from Dyslexia Buddy)
│       └── agent/               # LangChain agent, tools, story library
└── requirements.txt

lexiloop_frontend/
├── src/
│   ├── pages/                   # Login, Signup, Dashboard, ChildDetail
│   ├── components/              # Navbar, ProgressPath, CaptureTab, ExercisesTab, ChatTab
│   ├── context/                 # Auth state
│   └── api.js                   # Backend API client
└── package.json
```

## Setup

### Backend
```bash
cd lexiloop_backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # fill in MONGODB_URI, GROQ_API_KEY, JWT_SECRET
python app/ai/handwriting/model.py --train   # trains the CNN checkpoint (one-time)
uvicorn app.main:app --reload
```

### Frontend
```bash
cd lexiloop_frontend
npm install
npm run dev
```

Visit `http://localhost:5173`. The backend runs at `http://127.0.0.1:8000` (Swagger docs at `/docs`). MongoDB Atlas and Groq are cloud-hosted — no local services to run beyond the two commands above.

## Status

This is an active project built to demonstrate full-stack AI engineering — from a trained CNN through an LLM agent to a working UI. The CNN checkpoint requires local training (not included, as it's a large binary), and this has been tested component-by-component rather than under real classroom conditions. Next steps: end-to-end testing with sample child profiles, and optional deployment to Azure ML / Azure App Service.

## Credits

Built by Samia, drawing on two earlier standalone projects — **Dyslexia Buddy** (text simplification and readability scoring) and the **Dyslexic Handwriting Analyzer** (CNN-based reversal detection) — combined into one integrated system, with architecture inspired by production patterns used in real internship projects at Mazik Global.
