"""
Autonomous Email Intelligence Agent — Streamlit Frontend
=========================================================
Interactive dashboard for the AI email agent.
Workflow: Read Emails → Detect Intent → Draft Reply → Approve/Edit/Reject
"""

import streamlit as st
import requests
import json
import time
from typing import Optional

# ── Config ────────────────────────────────────────────────────────────────────
BACKEND_URL = "http://localhost:8000"

INTENT_COLORS = {
    "meeting_request":      "#4A90D9",
    "follow_up":            "#7B68EE",
    "support_query":        "#E8813A",
    "partnership_proposal": "#27AE60",
    "job_opportunity":      "#16A085",
    "deadline_reminder":    "#E74C3C",
    "general_inquiry":      "#95A5A6",
    "spam":                 "#BDC3C7",
    "newsletter":           "#BDC3C7",
}

INTENT_ICONS = {
    "meeting_request":      "📅",
    "follow_up":            "🔄",
    "support_query":        "🛠️",
    "partnership_proposal": "🤝",
    "job_opportunity":      "💼",
    "deadline_reminder":    "⏰",
    "general_inquiry":      "💬",
    "spam":                 "🚫",
    "newsletter":           "📰",
}

# ── Page setup ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AI Email Intelligence Agent",
    page_icon="✉️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* Main background */
.stApp { background: #0F1117; }

/* Metric cards */
.metric-card {
    background: linear-gradient(135deg, #1E2130 0%, #252840 100%);
    border: 1px solid #2D3250;
    border-radius: 12px;
    padding: 20px;
    text-align: center;
    margin-bottom: 12px;
}
.metric-card h2 { font-size: 2.2rem; margin: 0; }
.metric-card p  { color: #8892B0; font-size: 0.85rem; margin: 4px 0 0; }

/* Email card */
.email-card {
    background: #1A1D2E;
    border: 1px solid #2D3250;
    border-radius: 10px;
    padding: 16px;
    margin-bottom: 10px;
    cursor: pointer;
    transition: border-color .2s;
}
.email-card:hover { border-color: #4A90D9; }
.email-card.selected { border-color: #4A90D9; background: #1F2540; }

/* Intent badge */
.intent-badge {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 20px;
    font-size: 0.75rem;
    font-weight: 600;
    margin-bottom: 6px;
}

/* Workflow step */
.step-box {
    background: #1A1D2E;
    border: 1px solid #2D3250;
    border-radius: 8px;
    padding: 14px 18px;
    margin: 6px 0;
}
.step-box.active  { border-color: #4A90D9; }
.step-box.done    { border-color: #27AE60; }

/* Draft area */
.draft-box {
    background: #12151F;
    border: 1px solid #2D3250;
    border-radius: 8px;
    padding: 16px;
    font-family: 'Courier New', monospace;
    font-size: 0.9rem;
    color: #CDD6F4;
    white-space: pre-wrap;
}

/* Divider */
.divider { border-top: 1px solid #2D3250; margin: 18px 0; }

/* Status pill */
.status-sent     { color: #27AE60; font-weight: 700; }
.status-rejected { color: #E74C3C; font-weight: 700; }
.status-pending  { color: #F39C12; font-weight: 700; }

/* Hide Streamlit branding */
#MainMenu, footer, header { visibility: hidden; }
</style>
""", unsafe_allow_html=True)


# ── State management ──────────────────────────────────────────────────────────
def init_state():
    defaults = {
        "emails": [],
        "selected_email": None,
        "intent_result": None,
        "draft_result": None,
        "approval_result": None,
        "workflow_step": 0,       # 0=init 1=emails 2=intent 3=draft 4=approval
        "edited_draft": "",
        "backend_ok": False,
        "status_msg": "",
        "status_type": "info",
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()


# ── API helpers ───────────────────────────────────────────────────────────────
def api(method: str, endpoint: str, payload: dict = None, timeout: int = 30):
    url = f"{BACKEND_URL}{endpoint}"
    try:
        if method == "GET":
            r = requests.get(url, timeout=timeout)
        else:
            r = requests.post(url, json=payload, timeout=timeout)
        r.raise_for_status()
        return r.json(), None
    except requests.exceptions.ConnectionError:
        return None, "❌ Cannot connect to backend. Is FastAPI running on port 8000?"
    except requests.exceptions.Timeout:
        return None, "⏱️ Request timed out."
    except Exception as e:
        return None, f"❌ API error: {e}"


def check_backend():
    data, err = api("GET", "/health")
    st.session_state.backend_ok = data is not None
    return data, err


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ✉️ Email AI Agent")
    st.markdown("*Autonomous Intelligence with Human Approval*")
    st.markdown("---")

    # Backend status
    if st.button("🔌 Check Backend", use_container_width=True):
        data, err = check_backend()
        if data:
            st.success("Backend connected ✅")
        else:
            st.error(err)

    # Health indicator
    health_icon = "🟢" if st.session_state.backend_ok else "🔴"
    st.markdown(f"{health_icon} Backend status")
    st.markdown("---")

    # Fetch params
    st.markdown("### ⚙️ Fetch Settings")
    max_results = st.slider("Max emails", 1, 20, 5)
    label_filter = st.selectbox("Label", ["INBOX", "SENT", "SPAM", "STARRED"])
    query_filter = st.text_input("Search query (optional)", placeholder="from:boss@company.com")

    st.markdown("---")
    st.markdown("### 📋 Workflow")
    steps = ["① Fetch Emails", "② Detect Intent", "③ Generate Draft", "④ Approve / Send"]
    for i, s in enumerate(steps):
        icon = "✅" if st.session_state.workflow_step > i else ("▶️" if st.session_state.workflow_step == i else "⬜")
        st.markdown(f"{icon} {s}")

    st.markdown("---")
    st.markdown("### 🛡️ Safety")
    st.info("**No email is sent without your explicit approval.** All AI drafts require human review.")

    if st.button("🔄 Reset Workflow", use_container_width=True):
        for k in ["selected_email", "intent_result", "draft_result", "approval_result",
                  "workflow_step", "edited_draft", "status_msg"]:
            st.session_state[k] = 0 if k == "workflow_step" else (None if k != "edited_draft" else "")
        st.rerun()


# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("# 🤖 Autonomous Email Intelligence Agent")
st.markdown("*AI-powered triage · Intent detection · Safe draft generation · Human-in-the-loop approval*")

if st.session_state.status_msg:
    fn = {"success": st.success, "error": st.error, "warning": st.warning, "info": st.info}
    fn.get(st.session_state.status_type, st.info)(st.session_state.status_msg)

st.markdown("---")


# ── Metrics row ───────────────────────────────────────────────────────────────
emails = st.session_state.emails
unread = sum(1 for e in emails if not e.get("is_read", True))
m1, m2, m3, m4 = st.columns(4)
m1.markdown(f"<div class='metric-card'><h2>{len(emails)}</h2><p>Emails Loaded</p></div>", unsafe_allow_html=True)
m2.markdown(f"<div class='metric-card'><h2>{unread}</h2><p>Unread</p></div>", unsafe_allow_html=True)
m3.markdown(f"<div class='metric-card'><h2>{'✅' if st.session_state.intent_result else '—'}</h2><p>Intent Detected</p></div>", unsafe_allow_html=True)
m4.markdown(f"<div class='metric-card'><h2>{'📝' if st.session_state.draft_result else '—'}</h2><p>Draft Ready</p></div>", unsafe_allow_html=True)

st.markdown("---")

# ── Main layout: left = email list, right = workflow panel ───────────────────
col_emails, col_workflow = st.columns([2, 3], gap="large")

# ════════════════════════════════════════════════════════════════════
# LEFT PANEL — Email List
# ════════════════════════════════════════════════════════════════════
with col_emails:
    st.markdown("## 📥 Inbox")

    if st.button("📬 Fetch Emails", type="primary", use_container_width=True):
        with st.spinner("Connecting to Gmail..."):
            payload = {"max_results": max_results, "label": label_filter}
            if query_filter:
                payload["query"] = query_filter
            data, err = api("POST", "/read_emails", payload)
        if err:
            st.error(err)
        else:
            st.session_state.emails = data
            st.session_state.workflow_step = max(st.session_state.workflow_step, 1)
            st.session_state.status_msg = f"✅ Fetched {len(data)} emails"
            st.session_state.status_type = "success"
            st.rerun()

    if not st.session_state.emails:
        st.markdown("""
        <div style='text-align:center; padding:40px; color:#8892B0;'>
            <div style='font-size:3rem'>📭</div>
            <p>No emails loaded yet.<br>Click <b>Fetch Emails</b> to start.</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        for email in st.session_state.emails:
            eid = email["email_id"]
            is_selected = (st.session_state.selected_email or {}).get("email_id") == eid
            intent_info = ""
            if st.session_state.intent_result and st.session_state.intent_result.get("email_id") == eid:
                intent = st.session_state.intent_result["intent"]
                icon = INTENT_ICONS.get(intent, "💬")
                color = INTENT_COLORS.get(intent, "#95A5A6")
                intent_info = f"<span class='intent-badge' style='background:{color}22; color:{color}'>{icon} {intent.replace('_',' ').title()}</span><br>"

            unread_dot = "🔵 " if not email.get("is_read") else ""
            card_class = "email-card selected" if is_selected else "email-card"

            st.markdown(f"""
            <div class='{card_class}'>
                {intent_info}
                <strong>{unread_dot}{email['subject'][:55]}</strong><br>
                <small style='color:#8892B0'>From: {email['sender'][:40]}</small><br>
                <small style='color:#636880'>{email['date'][:22]}</small><br>
                <small style='color:#8892B0'>{email['snippet'][:80]}…</small>
            </div>
            """, unsafe_allow_html=True)

            if st.button(f"Select →", key=f"sel_{eid}"):
                st.session_state.selected_email = email
                st.session_state.intent_result = None
                st.session_state.draft_result = None
                st.session_state.approval_result = None
                st.session_state.edited_draft = ""
                st.session_state.workflow_step = 1
                st.rerun()


# ════════════════════════════════════════════════════════════════════
# RIGHT PANEL — Workflow
# ════════════════════════════════════════════════════════════════════
with col_workflow:
    st.markdown("## 🔄 AI Workflow")

    if not st.session_state.selected_email:
        st.markdown("""
        <div style='text-align:center; padding:60px; color:#8892B0;'>
            <div style='font-size:3rem'>👈</div>
            <p>Select an email from the inbox<br>to start the AI workflow.</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        email = st.session_state.selected_email

        # ── Email preview ──────────────────────────────────────────────────
        with st.expander("📧 Selected Email", expanded=True):
            c1, c2 = st.columns([2, 1])
            with c1:
                st.markdown(f"**Subject:** {email['subject']}")
                st.markdown(f"**From:** `{email['sender']}`")
                st.markdown(f"**Date:** {email['date']}")
            with c2:
                badge = "🔵 Unread" if not email.get("is_read") else "✅ Read"
                st.markdown(f"**Status:** {badge}")
            st.markdown("**Body:**")
            st.markdown(f"<div class='draft-box'>{email['body'][:600]}</div>", unsafe_allow_html=True)

        st.markdown("<div class='divider'></div>", unsafe_allow_html=True)

        # ── STEP 2: Detect Intent ──────────────────────────────────────────
        st.markdown("### 🧠 Step 1 — Detect Intent")
        if st.button("🔍 Detect Intent", type="primary", use_container_width=True,
                     disabled=st.session_state.intent_result is not None):
            with st.spinner("Analysing email intent with AI..."):
                payload = {
                    "email_id": email["email_id"],
                    "subject": email["subject"],
                    "body": email["body"],
                    "sender": email["sender"],
                }
                data, err = api("POST", "/detect_intent", payload)
            if err:
                st.error(err)
            else:
                st.session_state.intent_result = data
                st.session_state.workflow_step = max(st.session_state.workflow_step, 2)
                st.rerun()

        if st.session_state.intent_result:
            ir = st.session_state.intent_result
            intent = ir["intent"]
            color = INTENT_COLORS.get(intent, "#95A5A6")
            icon = INTENT_ICONS.get(intent, "💬")
            conf_pct = int(ir.get("confidence", 0) * 100)

            st.markdown(f"""
            <div class='step-box done'>
                <span class='intent-badge' style='background:{color}22; color:{color}; font-size:1rem'>
                    {icon} {intent.replace('_',' ').title()}
                </span>
                &nbsp;&nbsp;Confidence: <b>{conf_pct}%</b><br>
                <small><b>Summary:</b> {ir.get('summary','')}</small><br>
                <small><b>Suggested tone:</b> {ir.get('suggested_tone','')}</small> &nbsp;
                <small><b>Reply needed:</b> {'Yes' if ir.get('requires_reply') else 'No'}</small>
            </div>
            """, unsafe_allow_html=True)

            if ir.get("entities"):
                with st.expander("🔖 Extracted Entities"):
                    st.json(ir["entities"])

        st.markdown("<div class='divider'></div>", unsafe_allow_html=True)

        # ── STEP 3: Generate Draft ─────────────────────────────────────────
        st.markdown("### ✍️ Step 2 — Generate Draft Reply")
        tone_choice = st.select_slider(
            "Reply tone",
            options=["concise", "professional", "friendly", "empathetic"],
            value=st.session_state.intent_result.get("suggested_tone", "professional")
                  if st.session_state.intent_result else "professional",
        )
        if st.button("✨ Generate Draft", type="primary", use_container_width=True,
                     disabled=not st.session_state.intent_result):
            with st.spinner("Generating AI draft reply..."):
                ir = st.session_state.intent_result
                payload = {
                    "email_id": email["email_id"],
                    "subject": email["subject"],
                    "body": email["body"],
                    "sender": email["sender"],
                    "intent": ir.get("intent", "general_inquiry"),
                    "entities": ir.get("entities", {}),
                    "tone": tone_choice,
                }
                data, err = api("POST", "/draft_reply", payload)
            if err:
                st.error(err)
            else:
                st.session_state.draft_result = data
                st.session_state.edited_draft = data["body"]
                st.session_state.workflow_step = max(st.session_state.workflow_step, 3)
                st.rerun()

        if st.session_state.draft_result:
            dr = st.session_state.draft_result
            st.markdown(f"**To:** `{dr['to']}`")
            st.markdown(f"**Subject:** {dr['subject']}")
            st.markdown(f"**Tone:** {dr['tone']} &nbsp;|&nbsp; **Words:** {dr['word_count']}")
            st.markdown("**Draft Body** *(editable below)*:")
            edited = st.text_area(
                "Edit draft before approving:",
                value=st.session_state.edited_draft,
                height=200,
                key="draft_edit_area",
                label_visibility="collapsed",
            )
            st.session_state.edited_draft = edited

        st.markdown("<div class='divider'></div>", unsafe_allow_html=True)

        # ── STEP 4: Approval ───────────────────────────────────────────────
        st.markdown("### 🛡️ Step 3 — Human Approval Gate")
        st.markdown(
            "<small style='color:#8892B0'>Your decision controls what happens next. "
            "No email is sent without <b>Approve</b>.</small>",
            unsafe_allow_html=True,
        )

        if not st.session_state.draft_result:
            st.markdown(
                "<div class='step-box'><small style='color:#636880'>Generate a draft first.</small></div>",
                unsafe_allow_html=True,
            )
        elif st.session_state.approval_result:
            ar = st.session_state.approval_result
            status = ar.get("status", "")
            icon = {"sent": "✅", "rejected": "🚫", "updated": "📝"}.get(status, "ℹ️")
            css_cls = {"sent": "status-sent", "rejected": "status-rejected"}.get(status, "status-pending")
            st.markdown(f"""
            <div class='step-box done'>
                <span class='{css_cls}'>{icon} {status.upper()}</span><br>
                <small>{ar.get('message','')}</small>
                {f"<br><small>Gmail ID: <code>{ar['gmail_message_id']}</code></small>" if ar.get('gmail_message_id') else ''}
            </div>
            """, unsafe_allow_html=True)

            if st.button("🔁 Start New Reply", use_container_width=True):
                st.session_state.approval_result = None
                st.session_state.draft_result = None
                st.session_state.intent_result = None
                st.session_state.edited_draft = ""
                st.session_state.workflow_step = 1
                st.rerun()
        else:
            ba, be, brej = st.columns(3)
            with ba:
                if st.button("✅ Approve & Send", type="primary", use_container_width=True):
                    with st.spinner("Sending email..."):
                        dr = st.session_state.draft_result
                        # Save edited body first
                        if st.session_state.edited_draft != dr["body"]:
                            api("POST", "/route_approval", {
                                "draft_id": dr["draft_id"],
                                "email_id": dr["email_id"],
                                "action": "edit",
                                "edited_body": st.session_state.edited_draft,
                            })
                        data, err = api("POST", "/route_approval", {
                            "draft_id": dr["draft_id"],
                            "email_id": dr["email_id"],
                            "action": "approve",
                        })
                    if err:
                        st.error(err)
                    else:
                        st.session_state.approval_result = data
                        st.session_state.workflow_step = 4
                        st.rerun()
            with be:
                if st.button("📝 Save Edits", use_container_width=True):
                    with st.spinner("Saving edited draft..."):
                        dr = st.session_state.draft_result
                        data, err = api("POST", "/route_approval", {
                            "draft_id": dr["draft_id"],
                            "email_id": dr["email_id"],
                            "action": "edit",
                            "edited_body": st.session_state.edited_draft,
                        })
                    if err:
                        st.error(err)
                    else:
                        st.success("Draft saved. Review and approve when ready.")
            with brej:
                if st.button("🚫 Reject", use_container_width=True):
                    with st.spinner("Discarding draft..."):
                        dr = st.session_state.draft_result
                        data, err = api("POST", "/route_approval", {
                            "draft_id": dr["draft_id"],
                            "email_id": dr["email_id"],
                            "action": "reject",
                        })
                    if err:
                        st.error(err)
                    else:
                        st.session_state.approval_result = data
                        st.session_state.workflow_step = 4
                        st.rerun()


# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    "<center><small style='color:#636880'>Autonomous Email Intelligence Agent · "
    "Built with FastAPI + LangChain + Streamlit · Human-in-the-loop safety by design</small></center>",
    unsafe_allow_html=True,
)
