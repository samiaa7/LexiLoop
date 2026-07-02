# LexiLoop backend

FastAPI backend for LexiLoop: JWT auth, MongoDB Atlas, a CNN handwriting
reversal detector (reused from the Handwriting Analyzer project), a T5
text-simplification pipeline (reused from Dyslexia Buddy), and a
LangChain tool-calling reading-tutor agent running LLaMA3 via Groq.

## 1. Setup

```bash
cd lexiloop_backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## 2. Configure secrets

```bash
cp .env.example .env
```

Then open `.env` and fill in:
- `MONGODB_URI` — your MongoDB Atlas connection string
- `GROQ_API_KEY` — your Groq API key (regenerate if you ever pasted one
  in a chat or committed it anywhere — treat any exposed key as burned)
- `JWT_SECRET` — any long random string, e.g. output of
  `python -c "import secrets; print(secrets.token_hex(32))"`

**Never commit `.env`.** It's already in `.gitignore`.

## 3. Add the trained CNN checkpoint

This repo includes `model.py` and `analyzer.py` but not a trained
`model.pth` (that file is large and shouldn't live in git). Train it:

```bash
cd app/ai/handwriting
python model.py --train
```

This downloads EMNIST Letters and trains for ~15 epochs. Move the
resulting `model.pth` into `app/ai/handwriting/checkpoints/model.pth`
(or update `CNN_MODEL_PATH` in `.env` to point at wherever you put it).
If no checkpoint is found, the analyzer automatically falls back to a
heuristic (non-CNN) mode — the API still works, just less accurately.

## 4. Run the server

```bash
uvicorn app.main:app --reload
```

Visit `http://127.0.0.1:8000/docs` for interactive Swagger docs — this
is the fastest way to test every endpoint by hand before the React
frontend exists.

## 5. Endpoint map

| Endpoint | Method | Purpose |
|---|---|---|
| `/auth/signup`, `/auth/login` | POST | Get a JWT |
| `/children` | POST, GET | Create/list child profiles |
| `/children/{id}` | GET | Get one child profile |
| `/detect/{child_id}` | POST | Upload handwriting photo → reversal report |
| `/simplify` | POST | Simplify a piece of text |
| `/simplify/readability` | POST | Readability scores only |
| `/chat` | POST | Talk to the LangChain reading tutor agent |
| `/exercises` | POST | Generate a personalized reading exercise |

All endpoints except `/auth/*` require a Bearer token from login/signup.

## 6. What's stubbed / what's next

- **Frontend**: not built yet — this is backend only (Phase 1-4 from
  the project workflow doc). Endpoints are designed to be called
  directly from React via `fetch`/`axios` with the JWT in an
  `Authorization: Bearer <token>` header.
- **Story library**: 6 short original stories in
  `app/ai/agent/stories/`, spanning beginner to advanced. Add more
  `.txt` files there (same `Title: ...` / `Level: ...` header format)
  to expand the RAG pool — no code changes needed.
- **CNN checkpoint**: must be trained locally (step 3 above) — not
  included in this handoff since it's a large binary file.
- **Azure deployment**: out of scope for this phase; see the project
  workflow document, Phase 7.
