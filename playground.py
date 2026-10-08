"""Supervisor-facing comparison and review interface. Run with streamlit run playground.py."""

from __future__ import annotations

import os

import httpx
import streamlit as st

API = os.getenv("OPS_API_URL", "http://127.0.0.1:8000").rstrip("/")
st.set_page_config(page_title="EV Service Triage Lab", page_icon="🛠️", layout="wide")
st.title("EV Service Triage Lab")
st.caption("Fictional service requests · Recommendations require supervisor approval")


def call(method: str, path: str, data: dict | None = None):
    try:
        response = httpx.request(method, f"{API}{path}", json=data, timeout=300)
        response.raise_for_status()
        return response.json()
    except (httpx.RequestError, httpx.HTTPStatusError) as error:
        st.error(f"API request failed: {error}")
        return None


def checks(result: dict) -> dict[str, bool]:
    evidence_ids = {item["source_id"] for item in result["evidence"]}
    return {
        "Valid evidence IDs": evidence_ids.issubset(set(result["retrieval_ids"])),
        "Reply present": bool(result["customer_reply"].strip()),
        "Critical case flagged for review": result["priority"] != "critical"
        or result["review_required"],
    }


health = call("GET", "/health")
if health and health.get("provider") == "mock":
    st.warning(
        "Offline mock mode is active. Both prompt versions will produce the same rule-based answer; switch to the live provider to compare prompt quality."
    )

st.info(
    "The checks below verify structure and review rules. They do not prove a diagnosis is correct."
)
with st.form("ticket"):
    description = st.text_area(
        "Service request",
        value="Charging will not start. Code S-CHG-201 appears on the display.",
        height=120,
    )
    code = st.text_input("Diagnostic code (optional)", value="S-CHG-201")
    model = st.text_input("Vehicle model (optional)", value="Demo EV")
    compare = st.form_submit_button("Compare prompt versions", type="primary")

if compare:
    payload = {
        "description": description,
        "diagnostic_code": code or None,
        "vehicle_model": model or None,
        "versions": ["v1", "v2"],
    }
    st.session_state["comparison"] = call("POST", "/v1/compare", payload)

comparison = st.session_state.get("comparison")
if comparison:
    for column, result in zip(st.columns(2), comparison, strict=True):
        with column:
            st.subheader(f"Prompt {result['prompt_version']}")
            rules = checks(result)
            st.metric("Automated checks", f"{sum(rules.values())}/{len(rules)}")
            st.write(
                f"**Route:** {result['recommended_team']} · **Priority:** {result['priority']}"
            )
            st.write(f"**Review required:** {'Yes' if result['review_required'] else 'No'}")
            st.write(result["customer_reply"])
            with st.expander("Evidence and checks"):
                st.json(
                    {
                        "evidence": result["evidence"],
                        "retrieval_ids": result["retrieval_ids"],
                        "checks": rules,
                        "summary": result["diagnostic_summary"],
                    }
                )

st.divider()
st.subheader("Create a request for supervisor review")
if st.button("Save this request"):
    saved = call(
        "POST",
        "/v1/triage",
        {
            "description": description,
            "diagnostic_code": code or None,
            "vehicle_model": model or None,
            "prompt_version": "v2",
        },
    )
    if saved:
        st.session_state["saved"] = saved

saved = st.session_state.get("saved")
if saved:
    st.success(f"Ticket {saved['ticket_id']} is awaiting review")
    st.write(f"Recommended: **{saved['recommended_team']}**, priority **{saved['priority']}**")
    st.write(saved["customer_reply"])
    with st.form("feedback"):
        score = st.slider("How useful was this recommendation?", 1, 5, 3)
        comment = st.text_input("What should improve?")
        if st.form_submit_button("Save feedback") and call(
            "POST",
            "/v1/feedback",
            {"ticket_id": saved["ticket_id"], "score": score, "comment": comment},
        ):
            st.success("Feedback saved")
    with st.form("review"):
        approved = st.checkbox("Approve simulated dispatch")
        teams = ["battery", "charging", "drivetrain", "braking", "connectivity", "general_service"]
        suggested_index = (
            teams.index(saved["recommended_team"]) if saved["recommended_team"] in teams else 0
        )
        team = st.selectbox("Field team", teams, index=suggested_index)
        note = st.text_input("Review note")
        if st.form_submit_button("Submit review"):
            result = call(
                "POST",
                f"/v1/tickets/{saved['ticket_id']}/review",
                {"approved": approved, "team": team if approved else None, "note": note},
            )
            if result:
                st.success(f"Status: {result['status']}")

with st.expander("Simulated field-team queue"):
    queue = call("GET", "/v1/work-orders")
    if queue:
        st.dataframe(queue["items"], use_container_width=True)
