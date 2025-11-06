import os
from datetime import datetime
from functools import lru_cache
from typing import Optional, Sequence

import requests
from bs4 import BeautifulSoup
from openai import OpenAI

from . import models

_DRAFTING_MODEL = "gpt-5-mini-2025-08-07"
_SUMMARISER_MODEL = "gpt-5-nano-2025-08-07"
_DEFAULT_SYSTEM_MESSAGE = (
    "You assist Adam Phillips with business development tooling."
    " Stay factual, pragmatic, and concise."
)

_MARCIN_EXAMPLE_EMAIL = """Subject: Exploring pragmatic AI pilots

Hi Marcin,

Appreciated you carving out time for the chat. At Forethought, we have been pairing domain experts with lightweight automation to prove out value quickly. Starting with a narrow pilot lets us measure the wins, build confidence, and only then scale the pieces that deliver.

Given what you shared about Emerson’s reliability commitments, a focused proof around field-service diagnostics felt like the right entry point. Happy to sketch that out with your team and show how we keep humans in the loop.

Would you be open to a 25-minute session next week to map the pilot scope?

Thanks,
Adam"""


def fetch_and_summarise_website(url: str, company_name: str) -> str:
    """Fetch a homepage and derive structured BD notes."""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
    except requests.RequestException as exc:  # pragma: no cover - network guardrail
        raise RuntimeError("Website content could not be fetched reliably.") from exc

    soup = BeautifulSoup(response.text, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    text_content = soup.get_text(separator=" ")
    cleaned = " ".join(text_content.split())
    truncated = cleaned[:5000]

    prompt = f"""
You are BD_WEBSITE_ANALYSER.
A company homepage excerpt is provided. Work only with the evidence below.

Company name: {company_name}
Website URL: {url}

Homepage excerpt:
\"\"\"{truncated}\"\"\"

Output exactly two sections in this format:
What they do
- 5-7 bullets covering offerings, customers, differentiators (≤ 20 words each)

Credible AI pilots
- Exactly 3 bullets describing pragmatic pilots Adam Phillips could propose, echoing "start small → prove value → scale what works"

Rules:
- Use only facts from the excerpt; if something is missing, append (unclear).
- Avoid buzzwords and invention.
- Keep every bullet short and concrete.
""".strip()

    return _invoke_model(prompt, model=_DRAFTING_MODEL)


def _infer_first_name(full_name: str) -> Optional[str]:
    if not full_name:
        return None
    parts = [part for part in full_name.strip().split(" ") if part]
    if not parts:
        return None
    return parts[0]


def _build_greeting(contact: models.Contact) -> str:
    first_name = _infer_first_name(contact.name)
    if first_name:
        return f"Hi {first_name},"
    if contact.name:
        return f"Hi {contact.name},"
    return "Hi there,"


def draft_first_email(contact: models.Contact, website_summary: Optional[str]) -> str:
    """Draft the first outreach email in Adam's voice."""
    greeting = _build_greeting(contact)
    summary_section = (
        f"Website summary available:\n{website_summary}\n"
        if website_summary
        else "Website summary unavailable – acknowledge this lightly."
    )

    prompt = f"""
You are BD_FIRST_EMAIL_WRITER. Draft Adam Phillips' first outreach email.
Use this reference only for tone; do not reuse phrasing or mention Emerson/Marcin.

Reference tone:
\"\"\"{_MARCIN_EXAMPLE_EMAIL}\"\"\"

Contact details:
- Name: {contact.name}
- Role: {contact.role}
- Company: {contact.company_name}

{summary_section}

Output requirements:
Subject: ≤ 7 words, plain English
{greeting}

Paragraph 1: Introduce Adam, establish credibility, restate "forethought first, start small → prove value → scale what works".
Paragraph 2: Tie value to the contact's role and company, using the website summary when available.
Closing sentence: Ask for a 20–30 minute call next week.

Constraints:
- ≤ 220 words.
- Plain English, pragmatic, no hype.
- If the website summary was unavailable, note that gently rather than speculating.
""".strip()

    return _invoke_model(prompt, model=_DRAFTING_MODEL)


def draft_followup_email(
    contact: models.Contact,
    interactions: Sequence[models.Interaction],
    notes: Sequence[models.Note],
) -> str:
    """Draft a follow-up email after prior touchpoints."""
    greeting = _build_greeting(contact)

    if interactions:
        interaction_lines = []
        for interaction in interactions:
            timestamp = interaction.timestamp
            if isinstance(timestamp, datetime):
                ts_display = timestamp.strftime("%Y-%m-%d")
            elif timestamp:
                ts_display = str(timestamp)
            else:
                ts_display = "Unknown date"
            interaction_lines.append(
                f"- {ts_display}: {interaction.type.replace('_', ' ')} — {interaction.summary}"
            )
        interactions_section = "\n".join(interaction_lines)
    else:
        interactions_section = "No prior interactions recorded."

    latest_note = notes[0] if notes else None
    if latest_note and latest_note.meeting_date:
        note_date = latest_note.meeting_date.strftime("%Y-%m-%d")
    elif latest_note:
        note_date = "Unknown date"
    else:
        note_date = None

    note_raw = latest_note.raw_notes if latest_note else ""
    note_summary = latest_note.processed_summary if latest_note else ""

    prompt = f"""
You are BD_FOLLOWUP_WRITER. Create a concise follow-up email from Adam Phillips.
Keep the tone helpful, emphasising Adam's "assist, not replace" mindset and his stance of "forethought first, start small → prove value → scale what works".

Contact details:
- Name: {contact.name}
- Role: {contact.role}
- Company: {contact.company_name}

Recent interactions:
{interactions_section}

Latest note raw text: {note_raw or '(none)'}
Latest note summary: {note_summary or '(none)'}
Latest note date: {note_date or '(none)'}

Output structure:
Subject: ≤ 7 words
{greeting}

Paragraph 1: Recap the last touchpoint(s) with dates.
2-3 bullets: Pains/opportunities surfaced so far, echo "assist, not replace". Mark uncertain items with (need confirmation).
Final paragraph: Offer one clear next step (e.g. workshop or pilot) and ask for a 20–30 minute call next week.

Constraints:
- < 350 words.
- No new pricing promises.
- Plain English, pragmatic tone.
""".strip()

    return _invoke_model(prompt, model=_DRAFTING_MODEL)


def draft_custom_email(
    contact: models.Contact,
    *,
    greeting: str,
    purpose: str,
    tone: str,
    brief: str,
    additional_context: Optional[str],
    website_summary: Optional[str],
) -> str:
    """Draft a custom email based on user-provided intent."""
    purpose_notes = {
        "intro": "Ask for a first conversation next week.",
        "follow_up": "Reference prior exchanges and ask for a progress call next week.",
        "check_in": "Check in on momentum and request a brief sync next week.",
        "other": "Follow the purpose implied by the brief."
    }
    aligned_ask = purpose_notes.get(purpose, "Follow the brief." )

    prompt = f"""
You are BD_CUSTOM_EMAIL_WRITER supporting Adam Phillips.

Contact:
- Name: {contact.name}
- Role: {contact.role}
- Company: {contact.company_name}

Greeting to use verbatim: {greeting}
Purpose: {purpose}
Required ask: {aligned_ask}
Tone: {tone}
Brief / intents: {brief}
Additional context: {additional_context or '(none supplied)'}
Website summary: {website_summary or '(not available — flag gaps with (more detail needed))'}

Output structure:
Subject: ≤ 8 words aligned with the purpose.
{greeting}

Write 2–3 lean paragraphs:
- Reflect the requested tone.
- Preserve all concrete intents from the brief.
- Restate "forethought first, start small → prove value → scale what works" naturally.
- Include a specific next step that matches the purpose (if purpose is "other", infer it from the brief).

Rules:
- No hype. Plain English.
- Do not mention Emerson or Marcin.
- Flag missing context with "(more detail needed)".
""".strip()

    return _invoke_model(prompt, model=_DRAFTING_MODEL)


def summarise_note(note: models.Note, contact: models.Contact) -> str:
    """Produce a structured summary of raw meeting notes."""
    meeting_date = note.meeting_date.strftime("%Y-%m-%d") if note.meeting_date else "(unclear)"
    prompt = f"""
You are BD_NOTES_SUMMARISER. Turn the raw notes into structured bullets.

Contact: {contact.name} ({contact.company_name})
Meeting date: {meeting_date}
Raw notes:
\"\"\"{note.raw_notes}\"\"\"

Output the sections exactly as listed:
Context
- bullets ≤ 18 words each

Current process
- bullets ≤ 18 words each

Pains & risks
- bullets ≤ 18 words each

Potential AI fits
- include only justified items; prefix speculative ideas with "Possible:"; mark gaps with (unclear)

Next steps / decisions
- bullets ≤ 18 words; mark unknowns with (unclear)

Rules:
- Do not invent facts.
- Flag uncertainties with (unclear).
- Keep the tone neutral and factual.
""".strip()

    return _invoke_model(prompt, model=_SUMMARISER_MODEL)


@lru_cache()
def _get_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY environment variable is required to generate email drafts."
        )
    return OpenAI(api_key=api_key)


def _invoke_model(
    prompt: str,
    *,
    model: Optional[str] = None,
    system_message: Optional[str] = None,
) -> str:
    """Call the OpenAI client, preferring the Responses API with a chat fallback."""
    target_model = model or _DRAFTING_MODEL
    system_prompt = system_message or _DEFAULT_SYSTEM_MESSAGE
    client = _get_client()

    if hasattr(client, "responses"):
        response = client.responses.create(
            model=target_model,
            input=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
        )
        return getattr(response, "output_text", "").strip()

    if hasattr(client, "chat") and hasattr(client.chat, "completions"):
        completion = client.chat.completions.create(
            model=target_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
        )
        return completion.choices[0].message.content.strip()

    raise RuntimeError(
        "Installed OpenAI SDK does not support Responses or ChatCompletion APIs required for drafting."
    )
