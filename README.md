# ATLAS – AI Toolkit for Lead Activation & Stewardship

Internal BD/CRM tool for managing outreach, logging interactions, and using AI to draft emails and summaries.

ATLAS is deliberately simple: it gives you a fast way to capture who you’re talking to, what was said, what happens next – and then uses AI (in your tone) to draft first-touch and follow-up emails.

---

## Features

- **Contacts**
  - Name, company, role, email
  - LinkedIn URL
  - Website URL
  - Source (referral, cold_linkedin, event, other)
  - Status (prospect, meeting_booked, proposal_sent, client)

- **Interactions**
  - Channel: email, LinkedIn, call, meeting, note
  - Summary of what happened
  - Next action + due date
  - Visible as a timeline on each contact
  - `/next-actions` view shows all due/overdue next actions in one place

- **Notes**
  - Date of the conversation
  - **Raw notes** – dump everything (bullets, rough notes, transcripts)
  - **Summary (optional)** – a cleaned-up version in your own words  
    (future: let ATLAS generate this from raw notes)

- **AI helpers**
  - Website fetch + summarisation for a contact’s company
  - First-touch email drafting in Adam’s voice
  - Follow-up email drafting based on interactions + notes
  - Drafts appear inline on the contact page for quick copy-edit → send

---

## Tech stack

- **Backend**: Python 3.11, FastAPI
- **Templates**: Jinja2
- **Database**: PostgreSQL + SQLAlchemy
- **Containerisation**: Docker, docker-compose
- **AI**: OpenAI Python SDK (`gpt-4o-mini` via the Responses API)
- **Other**: `requests`, `beautifulsoup4`, `python-dotenv`, `python-multipart`

Key files:

- `app/main.py` – FastAPI app, routes, HTML rendering
- `app/models.py` – SQLAlchemy models (`Contact`, `Interaction`, `Note`)
- `app/schemas.py` – Pydantic models
- `app/database.py` – engine + session handling
- `app/templates/` – HTML templates
- `app/llm.py` – OpenAI + website summarisation + email drafting
- `AGENTS.md` – design notes for the BD agents
- `docker-compose.yml` – web + Postgres services
- `Dockerfile` – builds the web service image

---

## Getting started

### 1. Prerequisites

- Docker and Docker Compose installed
- An OpenAI API key with access to `gpt-5-mini-2025-08-07` (or any compatible Responses model)

### 2. Clone the repo

```bash
git clone <your-repo-url> atlas
cd atlas
