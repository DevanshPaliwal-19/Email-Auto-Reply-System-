"""
Pydantic models / schemas for request & response objects.
"""

from __future__ import annotations
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
import uuid


# ── Shared ────────────────────────────────────────────────────────────────────

class EmailResponse(BaseModel):
    email_id: str
    thread_id: str
    subject: str
    sender: str
    recipient: str
    date: str
    snippet: str
    body: str
    labels: List[str] = []
    is_read: bool = False


# ── /read_emails ──────────────────────────────────────────────────────────────

class ReadEmailsRequest(BaseModel):
    max_results: int = Field(default=10, ge=1, le=50, description="Max emails to fetch")
    label: str = Field(default="INBOX", description="Gmail label filter")
    query: Optional[str] = Field(default=None, description="Gmail search query string")


# ── /detect_intent ────────────────────────────────────────────────────────────

class DetectIntentRequest(BaseModel):
    email_id: str
    subject: str
    body: str
    sender: str


class IntentResponse(BaseModel):
    email_id: str
    intent: str                        # e.g. "meeting_request", "support_query"
    confidence: float = Field(ge=0.0, le=1.0)
    entities: Dict[str, Any] = {}      # extracted named entities
    summary: str = ""
    suggested_tone: str = "professional"
    requires_reply: bool = True


# ── /draft_reply ──────────────────────────────────────────────────────────────

class DraftReplyRequest(BaseModel):
    email_id: str
    subject: str
    body: str
    sender: str
    intent: str
    entities: Dict[str, Any] = {}
    tone: str = Field(default="professional", description="professional | friendly | concise")


class DraftResponse(BaseModel):
    draft_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email_id: str
    to: str
    subject: str
    body: str
    intent: str
    tone: str
    word_count: int = 0
    status: str = "pending_review"     # pending_review | approved | rejected | sent


# ── /route_approval ───────────────────────────────────────────────────────────

class RouteApprovalRequest(BaseModel):
    draft_id: str
    email_id: str
    action: str = Field(description="approve | reject | edit")
    edited_body: Optional[str] = Field(default=None, description="Required when action='edit'")


class ApprovalResponse(BaseModel):
    draft_id: str
    email_id: str
    action: str
    status: str                        # sent | rejected | updated | error
    message: str = ""
    gmail_message_id: Optional[str] = None
