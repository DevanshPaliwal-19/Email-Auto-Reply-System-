"""
IntentService — LangChain + OpenAI Functions for intent detection.
Gracefully degrades to a rule-based classifier when no API key is set.
"""

from __future__ import annotations
import os
import json
import re
import logging
from typing import Dict, Any

from utils.logger import setup_logger

logger = setup_logger(__name__)

# Optional LangChain / Ollama imports
try:
    from langchain_ollama import ChatOllama
    from langchain_core.messages import HumanMessage, SystemMessage
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    logger.warning("LangChain/Ollama not installed — using rule-based intent classifier")

INTENT_FUNCTION = {
    "name": "classify_email_intent",
    "description": "Classify the intent of an email and extract key entities",
    "parameters": {
        "type": "object",
        "properties": {
            "intent": {
                "type": "string",
                "enum": [
                    "meeting_request", "follow_up", "support_query",
                    "partnership_proposal", "job_opportunity", "deadline_reminder",
                    "general_inquiry", "spam", "newsletter"
                ],
                "description": "The primary intent of the email",
            },
            "confidence": {
                "type": "number",
                "description": "Confidence score between 0.0 and 1.0",
            },
            "entities": {
                "type": "object",
                "description": "Extracted named entities (dates, names, companies, etc.)",
            },
            "summary": {
                "type": "string",
                "description": "One-sentence summary of the email",
            },
            "suggested_tone": {
                "type": "string",
                "enum": ["professional", "friendly", "concise", "empathetic"],
                "description": "Recommended tone for the reply",
            },
            "requires_reply": {
                "type": "boolean",
                "description": "Whether this email needs a reply",
            },
        },
        "required": ["intent", "confidence", "summary", "suggested_tone", "requires_reply"],
    },
}

# ── Rule-based fallback ───────────────────────────────────────────────────────

KEYWORD_RULES = [
    (["interview", "schedule", "availability", "slot"], "meeting_request"),
    (["meeting", "call", "sync", "chat", "connect"], "meeting_request"),
    (["follow up", "following up", "follow-up", "checking in"], "follow_up"),
    (["support", "error", "bug", "issue", "problem", "help", "login", "unable"], "support_query"),
    (["partnership", "collaborate", "integration", "proposal", "opportunity"], "partnership_proposal"),
    (["job", "position", "role", "hiring", "career", "engineer"], "job_opportunity"),
    (["deadline", "due", "reminder", "submit", "eod"], "deadline_reminder"),
    (["unsubscribe", "newsletter", "promotion", "offer"], "newsletter"),
]

TONE_MAP = {
    "meeting_request":      "professional",
    "follow_up":            "friendly",
    "support_query":        "empathetic",
    "partnership_proposal": "professional",
    "job_opportunity":      "professional",
    "deadline_reminder":    "concise",
    "general_inquiry":      "professional",
    "spam":                 "concise",
    "newsletter":           "concise",
}


def _rule_based_classify(subject: str, body: str) -> Dict[str, Any]:
    text = (subject + " " + body).lower()
    for keywords, intent in KEYWORD_RULES:
        if any(k in text for k in keywords):
            return {
                "intent": intent,
                "confidence": 0.75,
                "entities": {},
                "summary": f"Email about {intent.replace('_', ' ')}.",
                "suggested_tone": TONE_MAP.get(intent, "professional"),
                "requires_reply": intent not in ("spam", "newsletter"),
            }
    return {
        "intent": "general_inquiry",
        "confidence": 0.55,
        "entities": {},
        "summary": "General email inquiry.",
        "suggested_tone": "professional",
        "requires_reply": True,
    }


# ── Service ───────────────────────────────────────────────────────────────────

class IntentService:
    def __init__(self):
        self._llm = None
        ollama_model = os.getenv("OLLAMA_MODEL", "llama3.1")
        if LANGCHAIN_AVAILABLE:
            try:
                self._llm = ChatOllama(
                    model=ollama_model,
                    temperature=0,
                ).bind_tools([{"type": "function", "function": INTENT_FUNCTION}])
                logger.info(f"IntentService: using Ollama Functions via LangChain ({ollama_model})")
            except Exception as e:
                logger.warning(f"LLM init failed ({e}) — using rule-based classifier")
        else:
            logger.info("IntentService: using rule-based classifier (LANGCHAIN_AVAILABLE=False)")

    async def detect(
        self, email_id: str, subject: str, body: str, sender: str
    ) -> Dict[str, Any]:
        if self._llm:
            return await self._llm_detect(email_id, subject, body, sender)
        result = _rule_based_classify(subject, body)
        result["email_id"] = email_id
        return result

    async def _llm_detect(
        self, email_id: str, subject: str, body: str, sender: str
    ) -> Dict[str, Any]:
        prompt = (
            f"From: {sender}\nSubject: {subject}\n\n{body[:1500]}"
        )
        try:
            messages = [
                SystemMessage(content="You are an expert email classifier. Use the provided function."),
                HumanMessage(content=prompt),
            ]
            response = await self._llm.ainvoke(messages)
            # Extract tool call arguments
            for tool_call in (response.tool_calls or []):
                if tool_call["name"] == "classify_email_intent":
                    args = tool_call["args"]
                    args["email_id"] = email_id
                    return args
        except Exception as e:
            logger.error(f"LLM intent detection failed: {e} — falling back to rules")
        result = _rule_based_classify(subject, body)
        result["email_id"] = email_id
        return result
