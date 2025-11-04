import os
from datetime import datetime
from functools import lru_cache
from typing import Optional, Sequence

import requests
from bs4 import BeautifulSoup
from openai import OpenAI

from . import models

_MODEL_NAME = "gpt-5-mini-2025-08-07"

_MARCIN_EXAMPLE_EMAIL = """Subject: Exploring pragmatic AI pilots

Hi Marcin,

Appreciated you carving out time for the chat. At Forethought, we have been pairing domain experts with lightweight automation to prove out value quickly. Starting with a narrow pilot lets us measure the wins, build confidence, and only then scale the pieces that deliver.

Given what you shared about Emerson’s reliability commitments, a focused proof around field-service diagnostics felt like the right entry point. Happy to sketch that out with your team and show how we keep humans in the loop.

Would you be open to a 25-minute session next week to map the pilot scope?

Thanks,
Adam"""


def fetch_and_summarise_website(url: str, company_name: str) -> str:
    """Fetches a website and produces a concise business + AI opportunity summary."""
    response = requests.get(url, timeout=10)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    text_content = soup.get_text(separator=" ")
    cleaned = " ".join(text_content.split())
    truncated = cleaned[:5000]

    prompt = f"""
You are BD_WEBSITE_ANALYSER.
Summarise the company below in 5-7 concise bullets describing what they do and who they serve.
Then craft exactly 3 additional bullets highlighting realistic, non-hype AI opportunities you can credibly infer.
Maintain a neutral tone and avoid inventing new offerings.

Company name: {company_name}
Website URL: {url}

Homepage excerpt:
\"\"\"{truncated}\"\"\"
""".strip()

    return _invoke_model(prompt)


def _infer_first_name(full_name: str) -> Optional[str]:
    if not full_name:
        return None
    parts = [part for part in full_name.strip().split(" ") if part]
    if not parts:
        return None
    return parts[0]


def draft_first_email(contact: models.Contact, website_summary: Optional[str]) -> str:
    """Drafts the first outreach email in Adam's voice."""
    first_name = _infer_first_name(contact.name)
    greeting = f"Hi {first_name}," if first_name else f"Hi {contact.name},"

    summary_section = (
        f"\nWebsite summary:\n{website_summary}\n"
        if website_summary
        else "\nWebsite summary unavailable.\n"
    )

    prompt = f"""
You are BD_FIRST_EMAIL_WRITER. Write an email from Adam Phillips.
Use the example email only as a tone/structure reference. Do not copy phrases, and do not reference Emerson or Marcin.

Example email:
\"\"\"{_MARCIN_EXAMPLE_EMAIL}\"\"\"

Contact details:
- Name: {contact.name}
- Role: {contact.role}
- Company: {contact.company_name}

Adam's positioning: forethought first, start small → prove value → scale what works.
Greeting requirement: use "{greeting}".
Structure: one paragraph introducing Adam + credibility, one paragraph grounded in the company's context, and a clear ask for a 20–30 minute conversation.
Word limit: under 220 words.
Tone: plain English, pragmatic, non-hypey.
{summary_section}
""".strip()

    return _invoke_model(prompt)


def draft_followup_email(
    contact: models.Contact,
    interactions: Sequence[models.Interaction],
    notes: Sequence[models.Note],
) -> str:
    """Drafts a follow-up email after previous interactions."""
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
                f"- {ts_display} ({interaction.type}) {interaction.summary}"
            )
        interactions_section = "\n".join(interaction_lines)
    else:
        interactions_section = "No prior interactions recorded."

    if notes:
        latest = notes[0]
        note_summary = latest.processed_summary or "No processed summary available."
        note_section = (
            f"Latest note:\nRaw notes: {latest.raw_notes}\nProcessed summary: {note_summary}"
        )
    else:
        note_section = "Latest note: None recorded."

    prompt = f"""
You are BD_FOLLOWUP_WRITER. Create a concise follow-up email from Adam Phillips.
Keep the tone helpful and pragmatic, highlighting Adam's "assist, not replace" and "forethought first" philosophy.

Contact details:
- Name: {contact.name}
- Role: {contact.role}
- Company: {contact.company_name}

Recent interactions:
{interactions_section}

{note_section}

Requirements:
- Briefly recap the previous touchpoints.
- Reframe 1–2 key problems or opportunities surfaced so far.
- Propose one clear next step (e.g. workshop, pilot).
- Stay under 350 words.
- Avoid introducing new pricing promises unless explicitly provided.
Tone: plain English, collaborative, non-hypey.
""".strip()

    return _invoke_model(prompt)


@lru_cache()
def _get_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY environment variable is required to generate email drafts."
        )
    return OpenAI(api_key=api_key)


def _invoke_model(prompt: str) -> str:
    """Call the OpenAI client, preferring the Responses API with a Chat fallback."""
    client = _get_client()
    if hasattr(client, "responses"):
        response = client.responses.create(model=_MODEL_NAME, input=prompt)
        return getattr(response, "output_text", "").strip()

    if hasattr(client, "chat") and hasattr(client.chat, "completions"):
        completion = client.chat.completions.create(
            model=_MODEL_NAME,
            messages=[
                {"role": "system", "content": "You are an assistant helping with BD emails."},
                {"role": "user", "content": prompt},
            ],
        )
        return completion.choices[0].message.content.strip()

    raise RuntimeError(
        "Installed OpenAI SDK does not support Responses or ChatCompletion APIs required for drafting."
    )
