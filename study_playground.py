"""Local participant page for timed manual and AI-assisted routing decisions."""

from __future__ import annotations

import time

import streamlit as st

from ops_ai.retrieval import get_index
from ops_ai.schemas import TicketRequest
from ops_ai.service import triage
from ops_ai.study import StudyStore
from ops_ai.telemetry import record_study_feedback

st.set_page_config(page_title="EV Routing Study", page_icon="⏱️", layout="wide")
st.title("EV Routing Study")
st.caption("Fictional tickets · Pseudonymous responses · About 14 routing decisions")
st.info(
    "This study measures how long routing decisions take. Use no real customer or personal data. "
    "The simulated recommendations must never be used for an actual vehicle."
)

store = StudyStore()
study_id = st.query_params.get("study_id")
session = store.session(study_id) if study_id else None

if session is None:
    with st.form("begin_study"):
        role = st.selectbox(
            "Your role",
            ["Field supervisor", "Service operations", "Other"],
            index=None,
            placeholder="Select your role",
        )
        consent = st.checkbox(
            "I understand that my role, choices, decision times, ratings, and comments will be "
            "stored locally for this fictional study. I will not enter personal information."
        )
        started = st.form_submit_button("Start study", type="primary")
    if started:
        if not consent or role is None:
            st.error("Select a role and confirm the study notice to continue.")
        else:
            role_code = {
                "Field supervisor": "field_supervisor",
                "Service operations": "service_operations",
                "Other": "other",
            }[role]
            st.query_params["study_id"] = store.start(role_code)
            st.rerun()
    st.stop()

completed, total = store.progress(study_id)
st.progress(completed / total, text=f"{completed} of {total} decisions submitted")
task = store.next_task(study_id)
if task is None:
    st.success("Study complete. Thank you for the 14 decisions and feedback.")
    st.write("The project owner can export the anonymized summary using the measurement guide.")
    st.stop()

if task["condition"] == "assisted" and task["ai_response"] is None:
    with st.spinner("Preparing an AI recommendation; this time is recorded separately..."):
        started = time.perf_counter()
        response = triage(
            TicketRequest(
                description=task["description"],
                diagnostic_code=task["diagnostic_code"],
                prompt_version="v2",
                session_id=f"operator-study-{study_id}",
            ),
            persist=False,
        )
        latency_ms = (time.perf_counter() - started) * 1000
        store.attach_ai(study_id, task["sequence"], latency_ms, response.model_dump(mode="json"))
    task = store.next_task(study_id)

store.mark_shown(study_id, task["sequence"])
st.subheader(f"Ticket {completed + 1} of {total}")
st.write(f"**Request:** {task['description']}")
st.write(f"**Diagnostic code:** {task['diagnostic_code'] or 'Not provided'}")

if task["condition"] == "assisted":
    suggestion = task["ai_response"]
    st.success("AI-assisted case: review the recommendation before making your own decision.")
    st.write(
        f"**Suggested route:** {suggestion['recommended_team']} · "
        f"**Priority:** {suggestion['priority']} · "
        f"**Human review:** {'Yes' if suggestion['review_required'] else 'No'}"
    )
    st.write(f"**Reason:** {suggestion['diagnostic_summary']}")
    st.write(f"**Proposed customer reply:** {suggestion['customer_reply']}")
    st.caption("Cited articles: " + ", ".join(item["source_id"] for item in suggestion["evidence"]))
else:
    st.info("Manual case: make a routing decision using the fictional reference below.")

with st.expander("Fictional knowledge reference — available for every case"):
    st.dataframe(
        [
            {
                "Code": article["code"],
                "Article": article["title"],
                "Team": article["team"],
                "Priority": article["priority"],
                "Guidance": article["summary"],
            }
            for article in get_index().documents
        ],
        width="stretch",
        hide_index=True,
    )

with st.form(f"decision-{task['sequence']}"):
    team = st.selectbox(
        "Your final routing team",
        [
            "battery",
            "charging",
            "drivetrain",
            "braking",
            "connectivity",
            "general_service",
            "human_review",
        ],
        index=None,
        placeholder="Choose a team",
    )
    priority = st.selectbox(
        "Your final priority",
        ["routine", "urgent", "critical"],
        index=None,
        placeholder="Choose a priority",
    )
    review = st.radio("Require human review before simulated dispatch?", ["Yes", "No"], index=None)
    confidence = st.slider("Confidence in your decision", 1, 5, 3)
    usefulness = (
        st.slider("How useful was the AI recommendation?", 1, 5, 3)
        if task["condition"] == "assisted"
        else None
    )
    comment = st.text_area(
        "What would improve this workflow? (optional; no personal data)", max_chars=1000
    )
    submitted = st.form_submit_button("Submit decision", type="primary")

if submitted:
    if team is None or priority is None or review is None:
        st.error("Choose a team, priority, and review decision before submitting.")
    else:
        try:
            store.submit(
                study_id,
                task["sequence"],
                team=team,
                priority=priority,
                review=review == "Yes",
                confidence=confidence,
                usefulness=usefulness,
                comment=comment,
            )
        except ValueError as error:
            st.error(str(error))
        else:
            if task["condition"] == "assisted":
                suggestion = task["ai_response"]
                record_study_feedback(
                    suggestion.get("trace_id"),
                    usefulness,
                    team != suggestion["recommended_team"],
                )
            st.rerun()
