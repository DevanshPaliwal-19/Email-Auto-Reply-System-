#!/usr/bin/env python3
"""
demo.py — Recruiter walkthrough script
Demonstrates all four REST endpoints via the running backend.
Run:  python demo.py
"""

import requests
import json
import sys
import time

BASE = "http://localhost:8000"
SEP  = "─" * 60


def p(label: str, data):
    print(f"\n{SEP}")
    print(f"  {label}")
    print(SEP)
    print(json.dumps(data, indent=2))


def check_backend():
    try:
        r = requests.get(f"{BASE}/health", timeout=5)
        r.raise_for_status()
        print(f"\n✅  Backend healthy: {r.json()}")
    except Exception as e:
        print(f"\n❌  Backend not running. Start it first:\n    cd backend && uvicorn main:app --reload\n\nError: {e}")
        sys.exit(1)


def demo_read_emails():
    print("\n━━━  STEP 1: Read Emails  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    r = requests.post(f"{BASE}/read_emails", json={"max_results": 3, "label": "INBOX"})
    emails = r.json()
    p(f"Fetched {len(emails)} emails", [
        {"email_id": e["email_id"], "subject": e["subject"], "sender": e["sender"]}
        for e in emails
    ])
    return emails


def demo_detect_intent(email: dict):
    print("\n━━━  STEP 2: Detect Intent  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    payload = {
        "email_id": email["email_id"],
        "subject": email["subject"],
        "body": email["body"],
        "sender": email["sender"],
    }
    r = requests.post(f"{BASE}/detect_intent", json=payload)
    result = r.json()
    p("Intent Detection Result", result)
    return result


def demo_draft_reply(email: dict, intent_result: dict):
    print("\n━━━  STEP 3: Draft Reply  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    payload = {
        "email_id": email["email_id"],
        "subject": email["subject"],
        "body": email["body"],
        "sender": email["sender"],
        "intent": intent_result["intent"],
        "entities": intent_result.get("entities", {}),
        "tone": intent_result.get("suggested_tone", "professional"),
    }
    r = requests.post(f"{BASE}/draft_reply", json=payload)
    draft = r.json()
    p("Generated Draft", {k: v for k, v in draft.items() if k != "body"})
    print(f"\n  Draft Body:\n  {'─'*50}")
    for line in draft["body"].split("\n"):
        print(f"  {line}")
    return draft


def demo_approval(draft: dict):
    print("\n━━━  STEP 4: Route Approval (simulate reject)  ━━━━━━━━━━━━")
    payload = {
        "draft_id": draft["draft_id"],
        "email_id": draft["email_id"],
        "action": "reject",  # safe for demo — won't actually send
    }
    r = requests.post(f"{BASE}/route_approval", json=payload)
    p("Approval Result", r.json())


def main():
    print("""
╔═══════════════════════════════════════════════════════════╗
║   AUTONOMOUS EMAIL INTELLIGENCE AGENT — DEMO WALKTHROUGH  ║
╚═══════════════════════════════════════════════════════════╝
  Demonstrating: /read_emails · /detect_intent
                 /draft_reply  · /route_approval
    """)

    check_backend()

    emails = demo_read_emails()
    if not emails:
        print("No emails to process.")
        return

    # Use the first email for the demo pipeline
    target = emails[0]
    print(f"\n  Processing: \"{target['subject']}\" from {target['sender']}")
    time.sleep(0.5)

    intent  = demo_detect_intent(target)
    time.sleep(0.5)

    draft   = demo_draft_reply(target, intent)
    time.sleep(0.5)

    demo_approval(draft)

    print(f"""
{SEP}
  DEMO COMPLETE ✅

  Key design decisions demonstrated:
  ┌─────────────────────────────────────────────────────────┐
  │ ✅ Emails are READ (not altered) via Gmail API           │
  │ 🧠 Intent classified by LangChain / rule-based fallback  │
  │ ✍️  Draft generated — returned for human review           │
  │ 🛡️  NOTHING is sent without explicit /route_approval     │
  │ 📊 All actions logged with timestamps                    │
  └─────────────────────────────────────────────────────────┘

  Open Streamlit UI at: http://localhost:8501
{SEP}
""")


if __name__ == "__main__":
    main()
