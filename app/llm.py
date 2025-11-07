import os
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Optional, Sequence

import requests
from bs4 import BeautifulSoup
from openai import OpenAI

from . import models

_DRAFTING_MODEL = "gpt-5-mini-2025-08-07"
_SUMMARISER_MODEL = "gpt-5-nano-2025-08-07"

ADAM_GLOBAL_STYLE = """
You are ATLAS, a drafting assistant for Adam Phillips, an AI consultant.
Write in Adam's voice: professional, warm, concise, and problem-first. Start from the contact's business context and pains, then introduce AI as a tool - never as magic. Emphasise measurable outcomes (time saved, reduced rework, improved first-pass approval, better traceability) and simple comparisons (e.g. "1 unit of time upstream vs 100 units downstream").
AI assists; it does not replace people. Whenever you propose AI use, make it clear that AI drafts and humans review/approve; no AI in control loops; data access is read-only; decisions should be logged for auditability.
Use short paragraphs and bullet points. Avoid hype, jargon, and grand claims. Never invent facts; use only the information supplied. If something is missing or unclear, write "(unclear)" or "(needs confirmation)" rather than guessing.
""".strip()

_DEFAULT_SYSTEM_MESSAGE = ADAM_GLOBAL_STYLE

CONTEXT_DIR = Path(__file__).parent / "context"


def _load_example(filename: str) -> str:
    """Best-effort load for style-reference markdown files."""
    try:
        return (CONTEXT_DIR / filename).read_text(encoding="utf-8").strip()
    except OSError:
        return ""


INTRO_EMAIL_EXAMPLE = _load_example("intro_email_emerson.md")
FOLLOWUP_EMAIL_EXAMPLE = _load_example("followup_workshop_emerson.md")
SPITFIRE_FOLLOWUP_EXAMPLE = _load_example("followup_spitfire.md")


CONTACT_SOURCE_DESCRIPTIONS = {
    "referral": "Referred by a mutual contact or client (specific name may be unclear).",
    "cold_linkedin": "Identified via LinkedIn outreach; Adam initiated the conversation directly.",
    "event": "Met briefly at an event; reference that shared touchpoint without overstating.",
    "other": "Self-initiated research; Adam reached out after independent digging.",
}


def _shorten_snippet(value: Optional[str], *, limit: int = 180, placeholder: str = "(unclear)") -> str:
    if not value:
        return placeholder
    compact = " ".join(value.split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 3].rstrip() + "..."


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

    # BD_WEBSITE_ANALYSER turns homepage excerpts into BD intel and grounded pilot ideas.
    prompt = f"""
You are BD_WEBSITE_ANALYSER. Work only with the homepage excerpt provided.

Company name: {company_name}
Website URL: {url}

Homepage excerpt:
\"\"\"{truncated}\"\"\"

Output these sections in order:
What they do
- Provide 5-7 bullets (<= 20 words) covering evidenced offerings, typical customers or sectors, and clear differentiators.

Likely priorities / pressures
- Provide 3-5 bullets inferred from the excerpt (growth, compliance, delivery reliability, margin, etc.).
- Prefix speculative bullets with "Possible:".

Credible AI pilots for Adam to explore
- Provide exactly 3 bullets unless the homepage is too generic. If so, write "No grounded pilots identified - homepage too generic." and explain why.
- For each pilot: name it, describe the workflow in one sentence, state what is measured (hours saved, fewer cut-offs, faster prep, etc.), and nod to guardrails (human sign-off, audit logs, read-only data).
- Propose only pilots that are plausible for this organisation and align with Adam's skills (RAG, semantic search, workflow automation, agentic co-pilots).

Rules:
- Use only information from the excerpt; append (unclear) where details are missing.
- Be explicit when marketing language is vague.
- Prefer concrete, operational wording over slogans.
""".strip()

    return _invoke_model(prompt, model=_DRAFTING_MODEL, system_message=ADAM_GLOBAL_STYLE)


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


def _describe_contact_source(source: Optional[str]) -> str:
    """Return a short phrase describing how Adam found the contact."""
    if not source:
        return "Self-initiated research; keep context general if specifics are missing."
    return CONTACT_SOURCE_DESCRIPTIONS.get(
        source,
        "Self-initiated research; keep context general if specifics are missing.",
    )


def draft_first_email(contact: models.Contact, website_summary: Optional[str]) -> str:
    """Draft the first outreach email in Adam's voice."""
    greeting = _build_greeting(contact)
    source_context = _describe_contact_source(getattr(contact, 'source', None))
    if website_summary:
        cleaned_summary = website_summary.strip()
        website_section = f"Website summary from BD_WEBSITE_ANALYSER:\n{cleaned_summary}"
    else:
        website_section = "Website summary unavailable; acknowledge the gap instead of guessing."

    reference_block = ""
    if INTRO_EMAIL_EXAMPLE:
        reference_block = (
            "\nReference example for tone and cadence (do not copy wording or mention Emerson/Marcin):\n"
            f"\"\"\"{INTRO_EMAIL_EXAMPLE}\"\"\"\n"
        )

    # BD_FIRST_EMAIL_WRITER drafts first-touch outreach grounded in contact context and Adam's philosophy.
    prompt = f"""
You are BD_FIRST_EMAIL_WRITER. Draft Adam Phillips' first outreach email in his tone and philosophy.
{reference_block}

Contact snapshot:
- Name: {contact.name}
- Role: {contact.role}
- Company: {contact.company_name}
- How Adam found them: {source_context}
- Immediate goal: Book a 20-30 minute intro conversation next week.
- Website insight: {website_section}
Greeting to use verbatim: {greeting}

Output requirements:
- Subject line: <= 7 words, plain English.
- Body: 3-6 short paragraphs (no bullets unless they improve clarity).

Paragraph plan:
1. Opening (1-2 sentences): Warm greeting, context on how Adam found them, and one line showing awareness of their world (grounded in the website summary or note that it's missing).
2. Why AI is relevant now (2-3 sentences): Tie AI to likely priorities such as productivity, traceability, quality, risk, or delivery; include one light credibility marker for Adam (RAG, workflow co-pilots) without hype.
3. Potential opportunity (2-3 sentences): Give 1-2 concrete, modest examples of AI co-pilots for organisations like theirs (dispatch-risk spotting, assembling traceability packs, summarising logs with citations, etc.).
4. Call to action (1-2 sentences): Invite a 20-30 minute conversation next week; keep timing flexible unless specific availability was provided (none supplied here).

Rules:
- 110-180 words total.
- Plain English with measurable outcomes; avoid buzzwords.
- Never fabricate company facts; if website insight is missing, say so lightly instead of guessing.
- Reinforce that Adam designs AI systems that assist people, keep humans in the loop, and measure value.
- Drafts are starting points for Adam to edit; never imply the email is auto-sent.
""".strip()

    return _invoke_model(prompt, model=_DRAFTING_MODEL, system_message=ADAM_GLOBAL_STYLE)

def draft_followup_email(
    contact: models.Contact,
    interactions: Sequence[models.Interaction],
    notes: Sequence[models.Note],
) -> str:
    """Draft a follow-up email after prior touchpoints."""
    greeting = _build_greeting(contact)
    latest_interaction = interactions[0] if interactions else None
    if latest_interaction:
        ts = latest_interaction.timestamp
        if isinstance(ts, datetime):
            ts_display = ts.strftime("%Y-%m-%d")
        elif ts:
            ts_display = str(ts)
        else:
            ts_display = "Unknown date"
        last_touch_description = (
            f"{ts_display}: {latest_interaction.type.replace('_', ' ')} - {latest_interaction.summary}"
        )
    else:
        last_touch_description = "No recorded meetings or calls."
    interaction_lines = []
    for interaction in interactions[:10]:
        ts = interaction.timestamp
        if isinstance(ts, datetime):
            ts_display = ts.strftime("%Y-%m-%d")
        elif ts:
            ts_display = str(ts)
        else:
            ts_display = "Unknown date"
        interaction_lines.append(
            f"- {ts_display}: {interaction.type.replace('_', ' ')} - {interaction.summary}"
        )
    interactions_section = "\n".join(interaction_lines) if interaction_lines else "(No prior interactions logged)"

    latest_note = notes[0] if notes else None
    if latest_note and latest_note.meeting_date:
        note_date = latest_note.meeting_date.strftime("%Y-%m-%d")
    elif latest_note:
        note_date = "Unknown date"
    else:
        note_date = "(none)"

    note_raw = latest_note.raw_notes if latest_note else "(none)"
    note_summary = latest_note.processed_summary if latest_note else "(none)"
    followup_intent = "Provide a grounded recap and propose the next step."
    reference_block = ""
    if FOLLOWUP_EMAIL_EXAMPLE:
        reference_block += (
            "\nReference example for tone, structure, and scannability (do not copy wording or mention Emerson/Marcin):\n"
            f"\"\"\"{FOLLOWUP_EMAIL_EXAMPLE}\"\"\"\n"
        )
    if SPITFIRE_FOLLOWUP_EXAMPLE:
        reference_block += (
            "\nReference example for consultant-to-consultant follow-up with 2–3 AI options (do not copy wording or mention Spitfire/Marc/Christian):\n"
            f"\"\"\"{SPITFIRE_FOLLOWUP_EXAMPLE}\"\"\"\n"
        )

    # BD_FOLLOWUP_WRITER assembles detailed follow-ups grounded in logged interactions and notes.
    prompt = f"""
You are BD_FOLLOWUP_WRITER. Build a detailed but readable follow-up email for Adam Phillips.
{reference_block}

Contact details:
- Name: {contact.name}
- Role: {contact.role}
- Company: {contact.company_name}
Greeting to use verbatim: {greeting}

Most recent touchpoint:
{last_touch_description}

Follow-up intent: {followup_intent}

Interaction log (most recent first):
{interactions_section}

Latest note:
- Date: {note_date}
- Raw excerpt: {note_raw}
- Processed summary: {note_summary}

Output requirements:
- Subject line: <= 9 words.
- Body must include these sections, in order:
  1. Thank you + context (1 short paragraph) that thanks them for the conversation and restates the meeting purpose in plain English.
  2. What I heard (1 paragraph + optional 3-5 bullets) summarising their situation and priorities.
  3. Opportunities / options (2-4 bullets) describing concrete pieces of work or workshop segments (e.g. "Examples -> your context", "Assist, not replace", "Interactive mapping", "Champions & quick wins"). Each bullet should explain purpose and value.
  4. Guardrails & measures (short paragraph) reiterating human-in-the-loop, read-only access, auditability, and 2-4 potential measures (hours back, fewer rework loops, better first-pass approval, traceability completeness).
  5. Next steps (1 paragraph) spelling out the proposed next step (e.g. 90-min session, capped workshop, 1-2 page brief) and asking for a 20-30 minute call or scheduled slot next week.

Rules:
- < 350 words.
- Mark any uncertain detail with (needs confirmation) instead of guessing.
- No new pricing, scope, or timeline promises beyond the inputs.
- Keep tone pragmatic and plain English; drafts are for Adam to edit.
""".strip()

    return _invoke_model(prompt, model=_DRAFTING_MODEL, system_message=ADAM_GLOBAL_STYLE)

def draft_custom_email(
    contact: models.Contact,
    *,
    greeting: str,
    purpose: str,
    tone: str,
    brief: str,
    additional_context: Optional[str],
    website_summary: Optional[str],
    selected_interactions: Optional[Sequence[models.Interaction]] = None,
    selected_notes: Optional[Sequence[models.Note]] = None,
) -> str:
    """Draft a custom email based on user-provided intent."""
    purpose_notes = {
        "intro": "Ask for a first conversation next week.",
        "follow_up": "Reference prior exchanges and ask for a progress call next week.",
        "check_in": "Check in on momentum and request a brief sync next week.",
        "other": "Follow the purpose implied by the brief.",
    }
    aligned_ask = purpose_notes.get(purpose, "Follow the brief.")
    website_insight = website_summary.strip() if website_summary else "Website summary unavailable; mention gaps rather than guessing."
    interaction_lines = []
    for interaction in selected_interactions or []:
        timestamp = interaction.timestamp.strftime("%Y-%m-%d") if interaction.timestamp else "(undated)"
        interaction_type = (interaction.type or "interaction").replace("_", " ")
        outcome = interaction.outcome or "(unclear)"
        summary = _shorten_snippet(interaction.summary, limit=200)
        interaction_lines.append(f"- {timestamp}: {interaction_type} - outcome={outcome} - summary: {summary}")
    selected_interactions_block = "\n".join(interaction_lines)

    note_lines = []
    for note in selected_notes or []:
        meeting_date = note.meeting_date.strftime("%Y-%m-%d") if note.meeting_date else "(undated)"
        structured = note.processed_summary.strip() if note.processed_summary else ""
        structured_text = _shorten_snippet(structured, limit=170, placeholder="") if structured else ""
        raw_excerpt = _shorten_snippet(note.raw_notes, limit=150)
        if structured_text:
            note_lines.append(f"- {meeting_date}: structured: {structured_text} / raw: {raw_excerpt}")
        else:
            note_lines.append(f"- {meeting_date}: raw: {raw_excerpt}")
    selected_notes_block = "\n".join(note_lines)

    reference_block = ""
    if FOLLOWUP_EMAIL_EXAMPLE:
        reference_block += (
            "\nReference example (workshop-style, long-form follow-up) – use only for cadence and sectioning:\n"
            f"\"\"\"{FOLLOWUP_EMAIL_EXAMPLE}\"\"\"\n"
        )
    if SPITFIRE_FOLLOWUP_EXAMPLE:
        reference_block += (
            "\nReference example (Spitfire AI opportunities) – use only for consultant-to-consultant tone, numbered options, and closing:\n"
            f"\"\"\"{SPITFIRE_FOLLOWUP_EXAMPLE}\"\"\"\n"
        )

    # BD_CUSTOM_EMAIL_WRITER turns briefs + tone guidance into bespoke drafts that stay within Adam's guardrails.
    prompt = f"""
You are BD_CUSTOM_EMAIL_WRITER supporting Adam Phillips.
{reference_block}

Contact context:
- Name: {contact.name}
- Role: {contact.role}
- Company: {contact.company_name}
Greeting to use verbatim: {greeting}
Purpose: {purpose}
Required ask: {aligned_ask}
Tone: {tone}
Brief / intents: {brief}
Additional context: {additional_context or '(none supplied)'}
Website insight: {website_insight}

Selected interaction history (may be empty):
{selected_interactions_block or '(none selected)'}

Selected notes (may be empty):
{selected_notes_block or '(none selected)'}

Output requirements:
- Subject line: <= 8 words aligned with the stated purpose.
- Body: reuse the greeting, then write 2-4 lean paragraphs that preserve every concrete intent, fact, or constraint in the brief.

Paragraph guidance:
- Reorder and tighten Adam's points for clarity while keeping his voice professional, warm, concise, and problem-first.
- Restate "forethought first, start small -> prove value -> scale what works" naturally.
- Weave in the website insight when it exists; if it is missing, flag the gap lightly with (more detail needed).
- End with a clear next step that matches the required ask (infer it from the brief when purpose = "other").
- Use selected interactions and notes to ground the draft in real conversations, decisions, pains, and agreed next steps; summarise only what helps this email.
- Pull through 1-2 concrete pains or opportunities from the selected history when relevant so the email never reads generic.

Rules:
- Plain English; no hype, jargon, or new offers/pricing beyond the brief.
- Never introduce new client names or promises Adam did not mention.
- Do not reuse client names from the examples.
- Do not copy sentences from the examples; mirror structure only.
- History is context, not a new source of truth: do not contradict the brief, and do not invent or overwrite logged details.
- If no history is provided, behave as usual: rely on the brief + optional website summary.
- If the brief lacks key details, include one short line inviting clarification (e.g., "Happy to tighten this once I know more about ___ (more detail needed)").
- Mark uncertainties with "(needs confirmation)" or "(more detail needed)" instead of guessing.
- Keep Adam's guardrails explicit: assistive AI, humans approve drafts, read-only data access, auditability, measurable outcomes.
""".strip()

    return _invoke_model(prompt, model=_DRAFTING_MODEL, system_message=ADAM_GLOBAL_STYLE)

def summarise_note(note: models.Note, contact: models.Contact) -> str:
    """Produce a structured summary of raw meeting notes."""
    meeting_date = note.meeting_date.strftime("%Y-%m-%d") if note.meeting_date else "(unclear)"
    raw_notes = note.raw_notes.strip()

    # BD_NOTES_SUMMARISER turns raw notes into structured sections Adam can scan quickly.
    prompt = f"""
You are BD_NOTES_SUMMARISER. Convert the raw notes into a neutral, structured summary for Adam Phillips.

Contact: {contact.name} ({contact.company_name})
Meeting date: {meeting_date}
Raw notes:
{raw_notes}

Output the following sections, in this exact order. Each section must have 1-4 bullets, each <= 18 words:
1. Context
2. Current process
3. Pains & risks
4. Potential AI fits
5. Next steps / decisions

Section-specific guidance:
- Potential AI fits: include only when the notes justify it. Prefix speculative items with "Possible:". If no AI use was discussed, include one bullet: "No explicit AI opportunities discussed."
- All other sections: keep bullets factual, grounded in the notes, and mark missing information with (unclear).

Rules:
- Never fabricate details or AI opportunities.
- Use the exact headings above and keep the order.
- Prefer short, scannable wording and reference data points only when provided.
""".strip()

    return _invoke_model(prompt, model=_SUMMARISER_MODEL, system_message=ADAM_GLOBAL_STYLE)


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
