"""
DraftService — generates AI draft email replies.
Uses LangChain + OpenAI when available, falls back to template-based generation.
"""

from __future__ import annotations
import os
import uuid
import logging
from typing import Dict, Any, Optional

from utils.logger import setup_logger

logger = setup_logger(__name__)

try:
    from langchain_ollama import ChatOllama
    from langchain_core.messages import HumanMessage, SystemMessage
    from langchain_core.prompts import ChatPromptTemplate
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False

# ── Draft templates (fallback) ────────────────────────────────────────────────

TEMPLATES = {
    "meeting_request": (
        "Thank you for reaching out regarding the {subject}.\n\n"
        "I would be happy to schedule some time to connect. "
        "I am available the following slots next week:\n"
        "  • Monday 10:00–11:00 AM\n"
        "  • Wednesday 2:00–3:00 PM\n"
        "  • Friday 9:00–10:00 AM\n\n"
        "Please let me know which works best for you, or feel free to suggest an alternative.\n\n"
        "Looking forward to speaking with you.\n\nBest regards"
    ),
    "follow_up": (
        "Thank you for following up.\n\n"
        "I apologise for the delayed response. I have reviewed your previous message and "
        "will get back to you with a detailed response by end of day tomorrow.\n\n"
        "Best regards"
    ),
    "support_query": (
        "Thank you for contacting our support team.\n\n"
        "I understand you are experiencing an issue and I sincerely apologise for the "
        "inconvenience. Our technical team has been alerted and we are investigating the matter.\n\n"
        "Expected resolution time: within 4 business hours.\n"
        "I will keep you updated on progress.\n\n"
        "Best regards,\nSupport Team"
    ),
    "partnership_proposal": (
        "Thank you for your interest in exploring a partnership.\n\n"
        "We have reviewed your proposal and find it intriguing. "
        "We would like to schedule an introductory call to discuss synergies in more detail.\n\n"
        "Could you please share a few time slots that work for you over the next two weeks?\n\n"
        "Best regards"
    ),
    "job_opportunity": (
        "Thank you for reaching out about this opportunity.\n\n"
        "I am interested in learning more. I would appreciate the chance to discuss the role "
        "and understand how my background aligns with your requirements.\n\n"
        "Please find attached my updated résumé. I am available for an initial call at your convenience.\n\n"
        "Best regards"
    ),
    "deadline_reminder": (
        "Thank you for the reminder.\n\n"
        "I acknowledge the deadline and am on track to deliver by the specified time. "
        "I will reach out immediately if any blockers arise.\n\n"
        "Best regards"
    ),
    "general_inquiry": (
        "Thank you for your message.\n\n"
        "I have received your inquiry and will respond with a detailed answer within 1–2 business days.\n\n"
        "Best regards"
    ),
}

TONE_INSTRUCTIONS = {
    "professional": "Write in a formal, polished, professional tone.",
    "friendly": "Write in a warm, friendly, approachable tone while remaining professional.",
    "concise": "Write very concisely — keep it to 2–3 short sentences maximum.",
    "empathetic": "Write with empathy, showing genuine understanding of the sender's situation.",
}


class DraftService:
    def __init__(self):
        self._llm = None
        ollama_model = os.getenv("OLLAMA_MODEL", "llama3.1")
        if LANGCHAIN_AVAILABLE:
            try:
                self._llm = ChatOllama(
                    model=ollama_model,
                    temperature=0.4,
                )
                logger.info(f"DraftService: using LangChain + Ollama ({ollama_model})")
            except Exception as e:
                logger.warning(f"LLM init failed ({e}) — using template drafts")
        else:
            logger.info("DraftService: using template-based drafts")

    async def generate(
        self,
        email_id: str,
        subject: str,
        body: str,
        sender: str,
        intent: str,
        entities: Dict[str, Any],
        tone: str = "professional",
    ) -> Dict[str, Any]:
        if self._llm:
            draft_body = await self._llm_draft(subject, body, sender, intent, entities, tone)
        else:
            draft_body = self._template_draft(subject, intent, entities, tone)

        # Extract sender email for "To" field
        to_email = _extract_email(sender)
        reply_subject = subject if subject.lower().startswith("re:") else f"Re: {subject}"

        return {
            "draft_id": str(uuid.uuid4()),
            "email_id": email_id,
            "to": to_email,
            "subject": reply_subject,
            "body": draft_body,
            "intent": intent,
            "tone": tone,
            "word_count": len(draft_body.split()),
            "status": "pending_review",
        }

    # ── Template fallback ─────────────────────────────────────────────────────

    def _template_draft(
        self, subject: str, intent: str, entities: Dict[str, Any], tone: str
    ) -> str:
        template = TEMPLATES.get(intent, TEMPLATES["general_inquiry"])
        draft = template.format(subject=subject, **{k: v for k, v in entities.items() if isinstance(v, str)})
        if tone == "concise" and intent not in ("general_inquiry",):
            # Trim to first paragraph for concise tone
            draft = draft.split("\n\n")[0] + "\n\nBest regards"
        return draft

    # ── LLM draft ─────────────────────────────────────────────────────────────

    async def _llm_draft(
        self,
        subject: str,
        body: str,
        sender: str,
        intent: str,
        entities: Dict[str, Any],
        tone: str,
    ) -> str:
        tone_instruction = TONE_INSTRUCTIONS.get(tone, TONE_INSTRUCTIONS["professional"])
        system = (
            "You are an expert email assistant. Write ONLY the body of a reply email. "
            "Do NOT include subject lines, headers, or meta-commentary. "
            f"{tone_instruction} "
            "Sign off generically as 'Best regards' — do not add a specific name."
        )
        user_prompt = (
            f"Original email from {sender}:\n"
            f"Subject: {subject}\n\n"
            f"{body[:1200]}\n\n"
            f"Intent: {intent}\n"
            f"Extracted entities: {entities}\n\n"
            "Write a helpful, appropriate reply."
        )
        try:
            messages = [SystemMessage(content=system), HumanMessage(content=user_prompt)]
            response = await self._llm.ainvoke(messages)
            return response.content.strip()
        except Exception as e:
            logger.error(f"LLM draft failed: {e} — falling back to template")
            return self._template_draft(subject, intent, entities, tone)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _extract_email(sender: str) -> str:
    """Extract bare email address from 'Name <email>' format."""
    import re
    match = re.search(r"<(.+?)>", sender)
    return match.group(1) if match else sender
