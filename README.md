# ATLAS - AI Toolkit for Lead Activation & Stewardship

ATLAS is a lightweight, self-hosted BD aide Adam Phillips uses to stay on top of contacts, interactions, notes, outcomes, and next actions. It layers in OpenAI models to draft outreach in Adam's tone, distil raw meeting notes into structured bullets, and turn company homepages into BD-ready snapshots - all while reflecting the philosophy of "forethought first, technology second; start small -> prove value -> scale what works."

---

## Feature overview

- **Contact management** - Capture name, company, role, email, LinkedIn, website, source (`referral`, `cold_linkedin`, `event`, `other`), and status (`prospect`, `meeting_booked`, `proposal_sent`, `client`).
- **Interaction logging** - Email/LinkedIn/call/meeting/note entries with summaries, outcomes, optional outcome notes, next actions, and due dates (new entries default to seven days out). Full timeline appears on the contact detail page with edit/delete controls.
- **Notes workspace** - Store raw notes plus optional processed summaries per meeting date. Contact pages include a Raw/Structured toggle that defaults to Structured whenever at least one summary exists.
- **Structured note summaries** - "Generate / Refresh structured summary" buttons run the BD_NOTES_SUMMARISER agent inline and overwrite the stored processed summary.
- **Intelligence helpers** - Notes and interactions trigger CRM fact extraction (stored in `crm_facts`), and the Next Action Assistant suggests/apply-ready next steps when enabled.
- **Next Actions board** - `/next-actions` shows every next action due today or overdue, grouped with the originating interaction and linked back to the contact, with a Completed button to archive items once handled.
- **Outcomes dashboard** - `/metrics/outcomes` aggregates interaction outcomes (pending, no reply, positive variants, negatives) for quick pipeline health checks.
- **Contact list filters** - `/contacts` filters by status and keyword search across name + company for quick segmentation.
- **Website intelligence** - The website analyser fetches the contact's homepage and produces "What they do" plus "Credible AI pilots" bullets used across drafting workflows and surfaced on the custom email page.
- **Email drafting helpers** - Contact detail actions trigger inline drafting for first-touch and follow-up emails; drafts appear in a textarea ready for editing.
- **Custom email studio** - Dedicated page with purpose/tone selectors, space for briefs/context, website snapshot preview, and copy-to-clipboard controls. Drafts are starting points only-emails are never sent automatically.

---

## Architecture & LLM stack

- **Backend:** FastAPI application (`app/main.py`) with SQLAlchemy models (`app/models.py`) and Pydantic schemas (`app/schemas.py`).
- **Database:** PostgreSQL by default via SQLAlchemy engine configured in `app/database.py` (`DATABASE_URL` override supported; SQLite works for local experiments).
- **Templating & UI:** Jinja2 templates under `app/templates/` rendered server-side with lightweight CSS defined in `layout.html`.
- **LLM access:** `app/llm.py` wraps the OpenAI Python SDK. `_invoke_model` prefers the Responses API with a chat-completions fallback and now injects the shared `ADAM_GLOBAL_STYLE` system text for every call.
- **Shared style & guardrails:** `ADAM_GLOBAL_STYLE` keeps every agent in Adam's voice (professional, warm, concise, problem-first), emphasises measurable outcomes, repeats "forethought first, start small -> prove value -> scale what works," and reinforces assistive AI guardrails (human review, read-only data, audit logs, no hype).
- **Style guides:** Real email examples in `app/context/*.md` act as tone/cadence references for the drafting agents (content is never copied verbatim).
- **Models in use:** `gpt-5-mini-2025-08-07` handles website summaries plus all email drafting helpers, while `gpt-5-nano-2025-08-07` powers BD_NOTES_SUMMARISER.
- **Async UX:** Email drafting buttons and "Generate / Refresh structured summary" actions make asynchronous POST calls and update the page without reloads.

---

## Using ATLAS

### Contacts & interactions

- **Add contacts:** `/contacts/new` collects the core fields plus source + status dropdowns. Email uniqueness is enforced.
- **Filter & search:** The contacts list filters by status or free-text query (name/company) and sorts newest first.
- **Interaction logging:** From a contact page, "Log Interaction" opens a form with type/status pickers, summary, next action, and due date (prefilled with today + 7). Outcomes drive the `/metrics/outcomes` view.
- **Next actions:** Every interaction's next action + due date rolls onto the contact timeline and the `/next-actions` board. Due dates are optional but required for the board.
- **Editing:** Interactions (and notes) can be edited or deleted inline from the contact table rows.

### Notes & structured summaries

- **Add notes:** "Add Note" captures a meeting date, required raw notes, and optional processed summary text.
- **Raw vs. Structured view:** Contact pages expose both versions; the toggle defaults to Structured whenever any summary exists, otherwise Raw.
- **Generate summaries:** Each note row includes "Generate / Refresh structured summary," calling BD_NOTES_SUMMARISER with raw text + meeting metadata and updating the processed summary column.
- **Raw storage:** Raw notes stay untouched so you can always re-run the summariser if prompts change.

### Intelligence helpers

- **CRM facts:** When `FACT_EXTRACTION_ENABLED=true` (default) and an OpenAI key is configured, every interaction and note create/update kicks off the `CRM_FACT_EXTRACTOR` helper. Facts land in the `crm_facts` table (cascading with the contact) so you can filter/search for intents, timelines, and hinted next steps later.
- **Backfill:** Set `INTEL_ADMIN_TOKEN`, then call `POST /admin/backfill_crm_facts?token=TOKEN&batch_size=25` to re-process older notes/interactions without facts. The route sleeps between calls, logs counts, and respects the same feature flag.
- **Next Action Assistant:** When `INTEL_SUGGESTIONS_ENABLED=true`, contact pages show a "Suggest Next Action" card that hits `GET /contacts/{id}/suggest_next_action`, surfaces the LLM's recommendation + optional draft, and lets you apply it via `POST /contacts/{id}/apply_suggested_next_action`.
- **Apply flow:** Applying a suggestion creates a placeholder interaction with the recommended next action + due date so it immediately rolls onto the Next Actions board; drafts stay local for editing.
- **Example curls:**

```bash
# Fetch a suggestion (requires INTEL_SUGGESTIONS_ENABLED + OPENAI_API_KEY)
curl http://localhost:8000/contacts/12/suggest_next_action

# Apply a suggestion (replace JSON with the payload you just received)
curl -X POST http://localhost:8000/contacts/12/apply_suggested_next_action \
  -H "Content-Type: application/json" \
  -d '{
        "next_action_type": "followup_email",
        "next_action_title": "Send recap + pilot sketch",
        "next_action_description": "Draft a short recap email that ties their traceability pains to two pilot co-pilots.",
        "proposed_email_subject": "Traceability pilot outline",
        "proposed_email_body": "Hi Dana,...",
        "suggested_due_date": "2024-06-14",
        "confidence": 0.78,
        "notes_for_adam": "Grounded in 2024-05 call + latest note."
      }'
```

### Email drafting workflows

- **Draft First Email:** Pulls contact fields, inferred greeting, and (when available) the latest website snapshot to craft a first-touch email in Adam's voice. Draft drops into an inline textarea for editing.
- **Draft Follow-up Email:** Uses the last 10 interactions plus the three most recent notes (raw + structured) to recap prior threads, surface pains/opportunities, and propose a next step.
- **Draft Custom Email:** Opens `/contacts/{id}/draft_custom_email` with purpose/tone selectors, required brief, optional context, live greeting preview, and website snapshot accordion. You can optionally tick any logged interactions and notes; those selections are summarised and sent to the drafting model so it can ground the copy in real history. Drafts stay in-app for you to edit/copy—nothing is ever auto-sent.
- **Starting point only:** All drafts remain local to the UI; you still copy/paste into your email client to send.

### Metrics & next actions

- **Next Actions board (`/next-actions`):** Lists every due or overdue next action sorted by due date with links back to the originating contact and a Completed button that archives the task (stored alongside the originating interaction) so it drops off the board once done.
- **Outcomes metrics (`/metrics/outcomes`):** Simple aggregation of interaction outcomes to show how outreach is landing (pending, positive meetings/intros, negative responses, etc.).

---

## Setup

### Requirements

- Docker + Docker Compose, or Python 3.11 with `pip`.
- An OpenAI API key with access to `gpt-5-mini-2025-08-07` and `gpt-5-nano-2025-08-07`.

### Environment variables

- `OPENAI_API_KEY` - required for all AI helpers. Loaded automatically (via `python-dotenv`) if stored in a local `.env`.
- `DATABASE_URL` - optional override for the SQLAlchemy engine. Defaults to the Postgres DSN defined in `docker-compose.yml`.
- `FACT_EXTRACTION_ENABLED` - defaults to `true`. Flip to `false` to pause CRM fact extraction (notes/interactions + backfill).
- `INTEL_SUGGESTIONS_ENABLED` - defaults to `true`. Flip to `false` to hide the Next Action Assistant UI and block suggestion/apply endpoints.
- `INTEL_ADMIN_TOKEN` - shared secret required to call `POST /admin/backfill_crm_facts`; set to any non-empty string when you want to run a backfill.

### Run with Docker Compose

```bash
docker compose up --build
```

This starts the FastAPI app on `http://localhost:8000` and a Postgres 16 instance. The web container mounts the repo for live reloads.
The container entrypoint now runs `alembic upgrade head` automatically, so every boot replays any pending migrations before `uvicorn` starts.

### Local development without Docker

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export OPENAI_API_KEY=...
uvicorn app.main:app --reload
```

Point `DATABASE_URL` to your local Postgres (or an SQLite file) before launching `uvicorn`.

### Quality checks

Run these commands locally (the CI workflow mirrors them):

- `python -m scripts.verify_models` – ensures the documented model names match `app/llm.py`.
- `python -m scripts.wait_for_db` – blocks until `DATABASE_URL` is reachable (used in CI).
- `ruff check .` – lightweight lint pass (syntax/name errors).
- `mypy` – static type check focused on the layered business logic (configured via `pyproject.toml`).
- `python -m pytest` – executes the service and API tests using the SQLite fixtures.

### Database migrations

ATLAS now relies on Alembic for schema changes—`Base.metadata.create_all()` is no longer invoked at startup.

1. Install dependencies (Docker image or local venv) so `alembic` is on your PATH.
2. Apply migrations before running the app:
   ```bash
   alembic upgrade head
   ```
3. For schema edits, update `app/models.py`, then generate a migration and review the diff:
   ```bash
   alembic revision --autogenerate -m "describe change"
   ```
4. Commit the new migration script along with the model changes so every environment stays in sync.

---

## Maintenance & conventions

-- **Prompts + models live in `app/llm.py`.** Whenever you adjust prompts, models, or helper names, update `AGENTS.md` and the README model references in the same PR. A lightweight CI check (`scripts/verify_models.py`) now verifies the documented model strings match `app/llm.py` and will fail the workflow if they drift.
- **Routes & UI docs:** Add or change FastAPI routes/templates? Record those behaviours in the README features/workflows section so future Adam (or assistants) can reason about the app quickly.
- **Sync models + docs:** Keep the documented model names in lockstep with `_DRAFTING_MODEL` and `_SUMMARISER_MODEL`.
- **Website + note helpers:** If you tweak how website summaries or structured notes are generated, make sure both README workflows and AGENTS guardrails reflect the actual behaviour.
- **Philosophy first:** All AI helpers should continue to echo "understand first, start small -> prove value -> scale what works." Flag any deviation during reviews.
