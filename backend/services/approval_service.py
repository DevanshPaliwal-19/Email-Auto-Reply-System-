"""
ApprovalService — human-in-the-loop approval gate.
Manages draft state and orchestrates actual sending via GmailService.
"""

from __future__ import annotations
import logging
from typing import Optional
from utils.logger import setup_logger
from services.gmail_service import GmailService

logger = setup_logger(__name__)

# In-memory draft store (replace with Redis/DB in production)
_DRAFT_STORE: dict[str, dict] = {}


class ApprovalService:
    def __init__(self):
        self._gmail = GmailService()

    def store_draft(self, draft: dict):
        """Register a draft for later approval."""
        _DRAFT_STORE[draft["draft_id"]] = dict(draft)
        logger.info(f"Draft stored: {draft['draft_id']}")

    async def process(
        self,
        draft_id: str,
        email_id: str,
        action: str,
        edited_body: Optional[str] = None,
    ) -> dict:
        """
        Process a human approval decision.

        Actions:
          approve — send the draft as-is via Gmail
          reject  — discard the draft
          edit    — update draft body, return for re-review
        """
        draft = _DRAFT_STORE.get(draft_id)

        # If draft not found in store, create a minimal record from request params
        if not draft:
            logger.warning(f"Draft {draft_id} not in store — operating on provided data")
            draft = {
                "draft_id": draft_id,
                "email_id": email_id,
                "to": "unknown@example.com",
                "subject": "Re: (unknown)",
                "body": edited_body or "",
                "status": "pending_review",
            }

        action = action.lower().strip()

        if action == "approve":
            return await self._approve(draft)
        elif action == "reject":
            return self._reject(draft)
        elif action == "edit":
            return self._edit(draft, edited_body)
        else:
            logger.error(f"Unknown action: {action}")
            return {
                "draft_id": draft_id,
                "email_id": email_id,
                "action": action,
                "status": "error",
                "message": f"Unknown action '{action}'. Must be approve | reject | edit.",
            }

    # ── Action handlers ───────────────────────────────────────────────────────

    async def _approve(self, draft: dict) -> dict:
        logger.info(f"Approving draft {draft['draft_id']} → sending to {draft['to']}")
        try:
            gmail_id = await self._gmail.send_email(
                to=draft["to"],
                subject=draft["subject"],
                body=draft["body"],
            )
            draft["status"] = "sent"
            _DRAFT_STORE[draft["draft_id"]] = draft
            return {
                "draft_id": draft["draft_id"],
                "email_id": draft["email_id"],
                "action": "approve",
                "status": "sent",
                "message": f"Email sent successfully to {draft['to']}.",
                "gmail_message_id": gmail_id,
            }
        except Exception as e:
            logger.error(f"Send failed for draft {draft['draft_id']}: {e}")
            return {
                "draft_id": draft["draft_id"],
                "email_id": draft["email_id"],
                "action": "approve",
                "status": "error",
                "message": f"Failed to send: {e}",
            }

    def _reject(self, draft: dict) -> dict:
        logger.info(f"Rejecting draft {draft['draft_id']}")
        draft["status"] = "rejected"
        _DRAFT_STORE[draft["draft_id"]] = draft
        return {
            "draft_id": draft["draft_id"],
            "email_id": draft["email_id"],
            "action": "reject",
            "status": "rejected",
            "message": "Draft discarded. No email was sent.",
        }

    def _edit(self, draft: dict, edited_body: Optional[str]) -> dict:
        if not edited_body:
            return {
                "draft_id": draft["draft_id"],
                "email_id": draft["email_id"],
                "action": "edit",
                "status": "error",
                "message": "edited_body is required for action='edit'.",
            }
        logger.info(f"Editing draft {draft['draft_id']}")
        draft["body"] = edited_body
        draft["status"] = "pending_review"
        _DRAFT_STORE[draft["draft_id"]] = draft
        return {
            "draft_id": draft["draft_id"],
            "email_id": draft["email_id"],
            "action": "edit",
            "status": "updated",
            "message": "Draft updated. Ready for re-review and approval.",
        }
