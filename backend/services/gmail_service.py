"""
GmailService — wraps Google Gmail API v1.
Falls back to realistic mock data when credentials are absent,
enabling demo / recruiter walkthrough without live Gmail setup.
"""

from __future__ import annotations
import os
import base64
# import json
# import logging
from typing import List, Optional
from email.mime.text import MIMEText

from utils.logger import setup_logger

logger = setup_logger(__name__)

# Optional Gmail SDK imports — gracefully degraded
try:
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    GMAIL_AVAILABLE = True
except ImportError:
    GMAIL_AVAILABLE = False
    logger.warning("Google API client libs not installed — running in MOCK mode")

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
]

MOCK_EMAILS = [
    {
        "email_id": "18f3a1b2c4d5e6f7",
        "thread_id": "18f3a1b2c4d5e6f7",
        "subject": "Interview Invitation — Senior AI Engineer",
        "sender": "hr@techcorp.io",
        "recipient": "you@gmail.com",
        "date": "Thu, 30 Apr 2026 09:15:00 +0000",
        "snippet": "We were impressed by your profile and would like to schedule a technical interview...",
        "body": (
            "Hi,\n\nWe were impressed by your profile and would like to schedule a "
            "technical interview for the Senior AI Engineer position.\n\n"
            "Could you please share your availability for next week (May 5–9)?\n"
            "The interview will be ~90 minutes via Zoom.\n\n"
            "Best regards,\nSarah — TechCorp Talent Team"
        ),
        "labels": ["INBOX", "UNREAD"],
        "is_read": False,
    },
    {
        "email_id": "29a4b5c6d7e8f901",
        "thread_id": "29a4b5c6d7e8f901",
        "subject": "Project Deadline Reminder — Q2 Report",
        "sender": "manager@company.com",
        "recipient": "you@gmail.com",
        "date": "Thu, 30 Apr 2026 08:00:00 +0000",
        "snippet": "Just a reminder that the Q2 report is due this Friday...",
        "body": (
            "Hi Team,\n\nJust a reminder that the Q2 report is due this Friday, May 2nd.\n"
            "Please make sure your sections are submitted by EOD Thursday.\n\n"
            "Let me know if you have any blockers.\n\nThanks,\nAlex"
        ),
        "labels": ["INBOX"],
        "is_read": True,
    },
    {
        "email_id": "37c5d6e7f8091a2b",
        "thread_id": "37c5d6e7f8091a2b",
        "subject": "Support Request — Unable to login to dashboard",
        "sender": "client@startup.co",
        "recipient": "support@yourproduct.com",
        "date": "Wed, 29 Apr 2026 17:30:00 +0000",
        "snippet": "I've been unable to log in since yesterday evening. I keep getting a 401 error...",
        "body": (
            "Hello Support,\n\nI've been unable to log in since yesterday evening. "
            "I keep getting a 401 Unauthorized error after entering my credentials.\n\n"
            "My account email is client@startup.co. Could you please investigate?\n\n"
            "Urgently needed — our team depends on this.\n\nRegards,\nMike Chen"
        ),
        "labels": ["INBOX", "UNREAD"],
        "is_read": False,
    },
    {
        "email_id": "46d7e8f90a1b2c3d",
        "thread_id": "46d7e8f90a1b2c3d",
        "subject": "Partnership Proposal — AI Integration Opportunity",
        "sender": "partnerships@aiventure.com",
        "recipient": "you@gmail.com",
        "date": "Wed, 29 Apr 2026 14:00:00 +0000",
        "snippet": "We believe there's a compelling opportunity to integrate our AI platform with your product...",
        "body": (
            "Dear Team,\n\nWe believe there's a compelling opportunity to integrate "
            "our AI platform with your product suite.\n\n"
            "Our platform handles 10M+ API calls/day and we'd love to explore a "
            "white-label or co-marketing arrangement.\n\n"
            "Would you be open to a 30-minute intro call next week?\n\n"
            "Best,\nJamie — AIVenture Partnerships"
        ),
        "labels": ["INBOX"],
        "is_read": True,
    },
    {
        "email_id": "55e8f90a1b2c3d4e",
        "thread_id": "55e8f90a1b2c3d4e",
        "subject": "Follow-up: Proposal Sent Last Week",
        "sender": "sales@vendor.com",
        "recipient": "you@gmail.com",
        "date": "Tue, 28 Apr 2026 11:00:00 +0000",
        "snippet": "I wanted to follow up on the proposal I sent last week. Have you had a chance to review?",
        "body": (
            "Hi,\n\nI wanted to follow up on the proposal I sent last week. "
            "Have you had a chance to review it?\n\n"
            "Happy to jump on a quick call to answer any questions.\n\nBest,\nRyan"
        ),
        "labels": ["INBOX"],
        "is_read": True,
    },
]


class GmailService:
    def __init__(self):
        self._service = None
        self._mock_mode = True
        if GMAIL_AVAILABLE:
            self._try_init_real_client()

    # ── Initialisation ────────────────────────────────────────────────────────

    def _try_init_real_client(self):
        """Attempt to build authenticated Gmail client. Fall back to mock."""
        creds_path = os.getenv("GMAIL_CREDENTIALS_PATH", "credentials.json")
        token_path = os.getenv("GMAIL_TOKEN_PATH", "token.json")
        try:
            creds = None
            if os.path.exists(token_path):
                creds = Credentials.from_authorized_user_file(token_path, SCOPES)
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                elif os.path.exists(creds_path):
                    flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
                    creds = flow.run_local_server(port=0)
                    with open(token_path, "w") as f:
                        f.write(creds.to_json())
                else:
                    logger.info("credentials.json not found — staying in mock mode")
                    return
            self._service = build("gmail", "v1", credentials=creds)
            self._mock_mode = False
            logger.info("Gmail API client initialised (LIVE mode)")
        except Exception as e:
            logger.warning(f"Gmail init failed ({e}) — falling back to mock mode")

    # ── Public API ────────────────────────────────────────────────────────────

    async def fetch_emails(
        self,
        max_results: int = 10,
        label: str = "INBOX",
        query: Optional[str] = None,
    ) -> List[dict]:
        if self._mock_mode:
            return self._mock_fetch(max_results, query)
        return await self._live_fetch(max_results, label, query)

    async def send_email(self, to: str, subject: str, body: str) -> Optional[str]:
        if self._mock_mode:
            fake_id = "mock_sent_" + os.urandom(4).hex()
            logger.info(f"[MOCK] Email 'sent' to {to} | fake_id={fake_id}")
            return fake_id
        return await self._live_send(to, subject, body)

    def is_mock(self) -> bool:
        return self._mock_mode

    # ── Mock helpers ──────────────────────────────────────────────────────────

    def _mock_fetch(self, max_results: int, query: Optional[str]) -> List[dict]:
        results = MOCK_EMAILS[:max_results]
        if query:
            q = query.lower()
            results = [e for e in results if q in e["subject"].lower() or q in e["body"].lower()]
        return results

    # ── Live helpers ──────────────────────────────────────────────────────────

    async def _live_fetch(self, max_results: int, label: str, query: Optional[str]) -> List[dict]:
        svc = self._service
        q = query or ""
        resp = svc.users().messages().list(
            userId="me", maxResults=max_results, labelIds=[label], q=q
        ).execute()
        messages = resp.get("messages", [])
        emails = []
        for msg in messages:
            detail = svc.users().messages().get(userId="me", id=msg["id"], format="full").execute()
            emails.append(self._parse_message(detail))
        return emails

    def _parse_message(self, msg: dict) -> dict:
        headers = {h["name"]: h["value"] for h in msg["payload"].get("headers", [])}
        body = self._extract_body(msg["payload"])
        return {
            "email_id": msg["id"],
            "thread_id": msg["threadId"],
            "subject": headers.get("Subject", "(no subject)"),
            "sender": headers.get("From", ""),
            "recipient": headers.get("To", ""),
            "date": headers.get("Date", ""),
            "snippet": msg.get("snippet", ""),
            "body": body,
            "labels": msg.get("labelIds", []),
            "is_read": "UNREAD" not in msg.get("labelIds", []),
        }

    def _extract_body(self, payload: dict) -> str:
        if "parts" in payload:
            for part in payload["parts"]:
                if part["mimeType"] == "text/plain":
                    data = part["body"].get("data", "")
                    return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
        data = payload.get("body", {}).get("data", "")
        if data:
            return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
        return ""

    async def _live_send(self, to: str, subject: str, body: str) -> Optional[str]:
        message = MIMEText(body)
        message["to"] = to
        message["subject"] = subject
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        result = self._service.users().messages().send(
            userId="me", body={"raw": raw}
        ).execute()
        return result.get("id")
