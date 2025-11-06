# ATLAS Agents

All AI helpers live in `app/llm.py`. `_invoke_model()` centralises calls to the OpenAI Python SDK, preferring the Responses API and falling back to Chat Completions with a neutral system prompt (“You assist Adam Phillips…”). Unless otherwise noted, helpers use `gpt-5-mini-2025-08-07`; BD_NOTES_SUMMARISER uses the cheaper `gpt-5-nano-2025-08-07`. Any time you edit prompts, guardrails, or model names here, update this file and the README in the same change.

---

## BD_WEBSITE_ANALYSER
- **Model:** `gpt-5-mini-2025-08-07`
- **Role:** Turn a company homepage excerpt into BD-ready intelligence for Adam Phillips.
- **Inputs:**
  - `company_name`
  - `website_url`
  - Cleaned homepage text (trimmed to 5k characters)
- **Outputs:**
  - **What they do:** 5–7 bullets, ≤ 20 words each, covering offerings, customers, differentiators.
  - **Credible AI pilots:** Exactly 3 bullets outlining pragmatic pilots that echo “start small → prove value → scale what works”.
- **Key rules:** Use only evidenced facts; append `(unclear)` where details are missing; avoid buzzwords; keep bullets concrete. No free-form prose.
- **Used by:** `app/llm.fetch_and_summarise_website()` which is called from `_try_fetch_website_summary()` in `app/main.py` to support first-email drafting and the custom email page (website snapshot accordion).

---

## BD_FIRST_EMAIL_WRITER
- **Model:** `gpt-5-mini-2025-08-07`
- **Role:** Draft Adam’s first outreach email in his tone and philosophy.
- **Inputs:**
  - Contact (name, role, company) plus inferred greeting.
  - Website summary (if available) or explicit note that it’s missing.
  - Reference email (`_MARCIN_EXAMPLE_EMAIL`) for tone only.
- **Outputs:**
  - Subject line ≤ 7 words.
  - Greeting matching the provided greeting.
  - Paragraph 1 introducing Adam, his credibility, and “forethought first, start small → prove value → scale what works.”
  - Paragraph 2 tying value to the contact/company, using the website summary when present (lightly acknowledging when absent).
  - Closing sentence requesting a 20–30 minute call next week.
- **Key rules:** ≤ 220 words; plain English; pragmatic; never mention Emerson/Marcin; lightly flag missing website info instead of guessing; drafts are starting points.
- **Used by:** `draft_first_email()` → POST `/contacts/{id}/draft_first_email`, rendered inline on the contact detail page.

---

## BD_FOLLOWUP_WRITER
- **Model:** `gpt-5-mini-2025-08-07`
- **Role:** Produce a concise follow-up email grounded in logged interactions and notes.
- **Inputs:**
  - Contact (name, role, company) with greeting.
  - Up to 10 most recent interactions (timestamp, type, summary).
  - Latest note (raw + processed summary + meeting date) when available.
  - Adam’s stance: “assist, not replace” and “forethought first, start small → prove value → scale what works.”
- **Outputs:**
  - Subject line ≤ 7 words.
  - Greeting verbatim.
  - Paragraph 1 recapping the latest touchpoint(s) with dates.
  - 2–3 bullets highlighting pains/opportunities, marking uncertain items with `(need confirmation)` and reinforcing “assist, not replace.”
  - Final paragraph proposing one concrete next step (e.g., workshop/pilot) plus a request for a 20–30 minute call next week.
- **Key rules:** < 350 words; no new pricing promises; plain English; keep sequencing exactly as above even if data is missing (flag gaps instead of inventing).
- **Used by:** `draft_followup_email()` → POST `/contacts/{id}/draft_followup`, rendered inline on the contact detail page.

---

## BD_CUSTOM_EMAIL_WRITER
- **Model:** `gpt-5-mini-2025-08-07`
- **Role:** Draft bespoke outreach that respects a chosen purpose, tone, and human-written brief.
- **Inputs:**
  - Contact context (name, role, company) and greeting to reuse verbatim.
  - Purpose (`intro`, `follow_up`, `check_in`, `other`) mapped to a required ask.
  - Tone option (`warm`, `direct`, `formal`, `enthusiastic`).
  - User brief plus optional additional context.
  - Website summary (or explicit note when missing).
- **Outputs:**
  - Subject line ≤ 8 words aligned with the stated purpose.
  - Greeting reused verbatim.
  - 2–3 lean paragraphs that reflect the chosen tone, preserve every concrete intent from the brief, restate “forethought first, start small → prove value → scale what works,” and include a next step consistent with the purpose (infer from brief when `other`).
- **Key rules:** Plain English; no hype; never mention Emerson/Marcin; flag missing context with `(more detail needed)`; respect the purpose-aligned ask defined in `app/llm.py`.
- **Used by:** `draft_custom_email()` → POST `/contacts/{id}/draft_custom_email`, surfaced on the custom email page with copy-to-clipboard controls.

---

## BD_NOTES_SUMMARISER
- **Model:** `gpt-5-nano-2025-08-07`
- **Role:** Convert raw meeting notes into a structured, succinct summary for Adam.
- **Inputs:**
  - Raw note text.
  - Meeting date (or `(unclear)` when missing).
  - Contact context (name + company).
- **Outputs:** Five sections, each containing 1–3 bullets ≤ 18 words:
  - **Context**
  - **Current process**
  - **Pains & risks**
  - **Potential AI fits** (only when justified; speculative points prefixed with `Possible:`)
  - **Next steps / decisions**
- **Key rules:** Never fabricate; mark gaps with `(unclear)`; keep tone neutral; omit the Potential AI fits section if the notes do not justify it; follow the exact section order shown.
- **Used by:** `summarise_note()` → POST `/notes/{id}/summarise`, triggered by “Generate / Refresh structured summary” buttons on the contact detail page.
