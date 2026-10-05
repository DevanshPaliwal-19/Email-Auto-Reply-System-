# ✉️ Autonomous Email Intelligence Agent

> AI-powered email triage, intent detection, and safe draft generation — with human-in-the-loop approval.

---

## 🎯 What This Project Demonstrates

| Skill Area | How It's Shown |
|---|---|
| **FastAPI** | Four REST endpoints with full request/response schemas, CORS, error handling |
| **LangChain + OpenAI Functions** | Structured intent detection via function-calling; graceful fallback |
| **Gmail API (OAuth 2.0)** | Secure read + send; demo mock mode when credentials absent |
| **Responsible AI** | Zero auto-send — every draft requires human approval |
| **Streamlit** | Interactive, multi-step workflow dashboard with real-time status |
| **Modular architecture** | `/backend/services/` layer; clean separation of concerns |
| **Production readiness** | Pydantic schemas, logging, env-based config, error recovery |

---

## 🏗️ Architecture

```
email-agent/
├── backend/
│   ├── main.py                  ← FastAPI app & route definitions
│   ├── models/
│   │   └── schemas.py           ← Pydantic request/response models
│   ├── services/
│   │   ├── gmail_service.py     ← Gmail API wrapper (live + mock)
│   │   ├── intent_service.py    ← LangChain intent classifier
│   │   ├── draft_service.py     ← AI draft generation
│   │   └── approval_service.py ← Human-in-the-loop gate
│   └── utils/
│       └── logger.py            ← Structured logging
├── frontend/
│   └── app.py                   ← Streamlit dashboard
└── docs/
    └── demo.py                  ← Recruiter walkthrough script
```

---

## ⚡ Quick Start

### 1. Install Dependencies

```bash
# Backend
cd backend
pip install -r requirements.txt

# Frontend
cd ../frontend
pip install -r requirements.txt
```

### 2. Configure Environment (optional — runs in mock mode without)

```bash
cp .env.example .env
# Edit .env:
#   OPENAI_API_KEY=sk-...
#   GMAIL_CREDENTIALS_PATH=credentials.json
```

### 3. Start the Backend

```bash
cd backend
uvicorn main:app --reload --port 8000
```
API docs available at: **http://localhost:8000/docs**

### 4. Start the Frontend

```bash
cd frontend
streamlit run app.py
```
Dashboard at: **http://localhost:8501**

### 5. Run the Demo Script

```bash
cd docs
python demo.py
```

---

## 🔌 REST API Reference

### `POST /read_emails`
Fetches emails from Gmail inbox (or mock data in demo mode).

```json
Request:  { "max_results": 5, "label": "INBOX", "query": "is:unread" }
Response: [ { "email_id": "...", "subject": "...", "sender": "...", "body": "..." }, ... ]
```

### `POST /detect_intent`
Classifies email intent using LangChain + OpenAI Functions.

```json
Request:  { "email_id": "abc", "subject": "...", "body": "...", "sender": "..." }
Response: { "intent": "meeting_request", "confidence": 0.95, "summary": "...", "entities": {} }
```

**Supported intents:** `meeting_request` · `follow_up` · `support_query` · `partnership_proposal` · `job_opportunity` · `deadline_reminder` · `general_inquiry` · `spam` · `newsletter`

### `POST /draft_reply`
Generates an AI draft reply (never sent automatically).

```json
Request:  { "email_id": "...", "intent": "meeting_request", "tone": "professional", ... }
Response: { "draft_id": "uuid", "to": "...", "subject": "Re: ...", "body": "...", "status": "pending_review" }
```

### `POST /route_approval`
Human-in-the-loop gate — controls whether the draft is sent, edited, or discarded.

```json
Request:  { "draft_id": "uuid", "email_id": "...", "action": "approve|reject|edit", "edited_body": "..." }
Response: { "status": "sent|rejected|updated", "message": "...", "gmail_message_id": "..." }
```

---

## 🛡️ Responsible AI Design

```
Gmail Inbox
    │
    ▼
/read_emails ──► email objects (read-only)
    │
    ▼
/detect_intent ──► intent + confidence + entities
    │
    ▼
/draft_reply ──► AI draft (status: "pending_review")
    │
    ▼
Human reviews in Streamlit UI
    │
    ├── Approve ──► /route_approval (action: "approve") ──► Gmail sends
    ├── Edit    ──► /route_approval (action: "edit")    ──► draft updated, re-review
    └── Reject  ──► /route_approval (action: "reject")  ──► draft discarded, nothing sent
```

**Key safety property:** The `/draft_reply` endpoint only *returns* a draft. Actual sending only occurs when a human explicitly calls `/route_approval` with `action: "approve"`.

---

## 🎛️ Configuration

| Environment Variable | Default | Description |
|---|---|---|
| `OPENAI_API_KEY` | *(none)* | Enables LangChain/OpenAI intent + drafts |
| `GMAIL_CREDENTIALS_PATH` | `credentials.json` | OAuth 2.0 credentials file path |
| `GMAIL_TOKEN_PATH` | `token.json` | Stored OAuth token path |

**Without any env vars:** The agent runs in full mock/demo mode — all features work with realistic sample data.

---

## 🚀 Recruiter Appeal

This project showcases production-level thinking across the full AI engineering stack:

- **LLM Integration** — OpenAI Functions via LangChain with graceful fallback
- **API Design** — Clean REST endpoints with Pydantic validation and FastAPI autodocs
- **Security** — OAuth 2.0 for Gmail, zero auto-send principle, human approval gate
- **Frontend** — Polished Streamlit dashboard with real-time workflow state
- **Error handling** — Every service layer catches, logs, and degrades safely
- **Demo-ready** — Works out of the box without any API keys or Gmail setup

---

## 📄 License

MIT
