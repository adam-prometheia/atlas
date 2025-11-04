# BD_WEBSITE_ANALYSER
- **Role:** Turn a company website into a concise summary plus a handful of grounded AI opportunity hypotheses.
- **Inputs:** `company_name`, `website_url`, raw homepage text.
- **Outputs:** 5–7 bullets explaining what the company does and who they serve, followed by 3 short bullets outlining realistic AI opportunities.
- **Constraints:** Neutral tone, avoid buzzwords, never invent offerings that are not evidenced.

# BD_FIRST_EMAIL_WRITER
- **Role:** Draft Adam Phillips’ first outreach email.
- **Inputs:** Contact (name, role, company), website summary, Adam’s positioning (“forethought first, start small → prove value → scale what works”), and the “Marcin at Emerson” sample email as a tone reference.
- **Outputs:** Email under 220 words with a brief intro + credibility, 1–2 sentences grounded in the company context, and a clear ask for a 20–30 minute call.
- **Constraints:** Plain English, no hype, do not copy or mention Emerson/Marcin explicitly.

# BD_FOLLOWUP_WRITER
- **Role:** Create a follow-up email after a discovery call.
- **Inputs:** Contact details, most recent interactions, latest note (raw notes plus processed summary if present), and Adam’s “assist, not replace” philosophy.
- **Outputs:** Email that recaps prior conversations, reframes the pains/opportunities, and proposes one clear next step (e.g., workshop or pilot).
- **Constraints:** Fewer than 350 words, avoid introducing new pricing promises unless provided.

# BD_NOTES_SUMMARISER (Optional / Future)
- **Role:** Convert raw meeting notes into a structured processed summary with 4–8 bullets.
- **Input:** Raw notes text.
- **Output:** Bullets covering context, current process, pains, potential AI fits, and explicit next steps, while flagging uncertainties.
- **Constraints:** Do not fabricate new facts; clearly mark any uncertainties.
