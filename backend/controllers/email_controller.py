import logging
from fastapi import APIRouter, HTTPException

from models.schemas import (
    ReadEmailsRequest, DetectIntentRequest, DraftReplyRequest,
    RouteApprovalRequest, EmailResponse, IntentResponse,
    DraftResponse, ApprovalResponse
)
from services.gmail_service import GmailService
from services.intent_service import IntentService
from services.draft_service import DraftService
from services.approval_service import ApprovalService
from utils.logger import setup_logger

logger = setup_logger(__name__)

router = APIRouter()

# ── Service singletons ────────────────────────────────────────────────────────
gmail_service   = GmailService()
intent_service  = IntentService()
draft_service   = DraftService()
approval_service = ApprovalService()


@router.get("/health")
async def health_check():
    return {"status": "healthy", "service": "Email Intelligence Agent"}


@router.post("/read_emails", response_model=list[EmailResponse])
async def read_emails(request: ReadEmailsRequest):
    """
    Fetch emails from Gmail inbox.
    Returns a list of parsed email objects with metadata.
    """
    try:
        logger.info(f"Reading emails | max_results={request.max_results} label={request.label}")
        emails = await gmail_service.fetch_emails(
            max_results=request.max_results,
            label=request.label,
            query=request.query,
        )
        logger.info(f"Fetched {len(emails)} emails")
        return emails
    except Exception as e:
        logger.error(f"read_emails failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/detect_intent", response_model=IntentResponse)
async def detect_intent(request: DetectIntentRequest):
    """
    Use LangChain + OpenAI Functions to classify intent and extract entities
    from the provided email body.
    """
    try:
        logger.info(f"Detecting intent for email_id={request.email_id}")
        result = await intent_service.detect(
            email_id=request.email_id,
            subject=request.subject,
            body=request.body,
            sender=request.sender,
        )
        logger.info(f"Intent detected: {result.intent} (confidence={result.confidence:.2f})")
        return result
    except Exception as e:
        logger.error(f"detect_intent failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/draft_reply", response_model=DraftResponse)
async def draft_reply(request: DraftReplyRequest):
    """
    Generate an AI draft reply using LangChain.
    Draft is NOT sent — it is returned for human review.
    """
    try:
        logger.info(f"Drafting reply for email_id={request.email_id} intent={request.intent}")
        draft = await draft_service.generate(
            email_id=request.email_id,
            subject=request.subject,
            body=request.body,
            sender=request.sender,
            intent=request.intent,
            entities=request.entities,
            tone=request.tone,
        )
        logger.info(f"Draft generated | draft_id={draft.draft_id}")
        return draft
    except Exception as e:
        logger.error(f"draft_reply failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/route_approval", response_model=ApprovalResponse)
async def route_approval(request: RouteApprovalRequest):
    """
    Human-in-the-loop approval gate.
    action: 'approve' → sends the draft via Gmail API
            'reject'  → discards draft
            'edit'    → stores edited body, returns for re-review
    """
    try:
        logger.info(f"Routing approval | draft_id={request.draft_id} action={request.action}")
        result = await approval_service.process(
            draft_id=request.draft_id,
            email_id=request.email_id,
            action=request.action,
            edited_body=request.edited_body,
        )
        logger.info(f"Approval result: {result.status}")
        return result
    except Exception as e:
        logger.error(f"route_approval failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
