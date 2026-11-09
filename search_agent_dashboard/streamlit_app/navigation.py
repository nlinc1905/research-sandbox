"""Navigation state independent of widgets and table row positions."""

from collections.abc import MutableMapping, Sequence
from typing import Any


def initialize(state: MutableMapping[str, Any], profile_ids: Sequence[str]) -> None:
    """Initialize session state with default navigation selections.
    
    Sets up default values for all navigation keys (active_tab, selected_profile_id,
    selected_customer_id, etc) using setdefault, so existing state is not overwritten.
    Called once at app startup to establish the navigation hierarchy.
    
    Default selection:
    - active_tab: "Overview"
    - selected_profile_id: first profile from profile_ids
    - All drilldown levels (customer, batch, document, trace): None
    - Span state (selected_span_id, collapsed_span_ids): None / empty list
    
    :param state: Streamlit session_state dict (mutable mapping).
    :param profile_ids: Sequence of profile IDs to select first from.
    :return: None (modifies state in-place).
    """
    defaults: dict[str, Any] = {
        "active_tab": "Overview",
        "selected_profile_id": profile_ids[0],
        "selected_customer_id": None,
        "selected_batch_id": None,
        "selected_document_id": None,
        "selected_trace_id": None,
        "selected_span_id": None,
        "collapsed_span_ids": [],
    }
    for key, value in defaults.items():
        state.setdefault(key, value)


def navigate(
    state: MutableMapping[str, Any],
    tab: str,
    *,
    profile_id: str | None = None,
    customer_id: str | None = None,
    batch_id: str | None = None,
    document_id: str | None = None,
    trace_id: str | None = None,
) -> None:
    """Navigate to a tab with optional drilldown selections.
    
    Updates session state to change active tab and optionally drill down to a
    specific record. Only updates selections relevant to the target tab:
    - Profiles tab: updates profile/customer/batch/document selections
    - Traces tab: updates trace selection, resets span state
    - Other tabs: only changes active_tab
    
    Decision: Passing profile_id=None does not clear it; only explicitly set
    values update state. This allows breadcrumbs to drill down without re-setting
    other levels that weren't clicked.
    
    :param state: Streamlit session_state dict (mutable mapping).
    :param tab: Target tab name ("Overview", "Profiles", "Sessions", "Traces").
    :param profile_id: Profile ID for Profiles tab (optional, only if changing).
    :param customer_id: Customer ID for Profiles drilldown (optional).
    :param batch_id: Batch ID for Profiles drilldown (optional).
    :param document_id: Document ID for Profiles drilldown (optional).
    :param trace_id: Trace ID for Traces tab (optional).
    :return: None (modifies state in-place).
    """
    state["active_tab"] = tab
    if tab == "Profiles":
        if profile_id is not None:
            state["selected_profile_id"] = profile_id
        state["selected_customer_id"] = customer_id
        state["selected_batch_id"] = batch_id
        state["selected_document_id"] = document_id
    if tab == "Traces":
        state["selected_trace_id"] = trace_id
        state["selected_span_id"] = None
        state["collapsed_span_ids"] = []


def matches_language(language: str, selected: str) -> bool:
    """Check if a record's language matches the global language filter.
    
    Maps filter selection ("All", "English", "German") to language code checks.
    Language field typically contains code(s) like "EN", "DE", or "EN|DE".
    
    :param language: Language code(s) from data record (e.g. "EN", "DE", "EN|DE").
    :param selected: User-selected filter ("All", "English", "German").
    :return: True if record matches filter, False otherwise.
    """
    return selected == "All" or ("EN" if selected == "English" else "DE") in language


def validate(
    state: MutableMapping[str, Any],
    customers: list[dict[str, Any]],
    batches: list[dict[str, Any]],
    documents: list[dict[str, Any]],
    traces: list[dict[str, Any]],
    language: str,
) -> None:
    """Validate and fix navigation state when data changes or language filter changes.
    
    Clears invalid selections without replacing them with arbitrary alternatives.
    For example, if the selected batch is hidden by language filter, clears the
    batch selection (and its descendants) rather than picking a different batch.
    
    Decision: Never silently auto-select a different level. Invalid selections
    are cleared, forcing user to click a visible option to proceed.
    
    Validations:
    1. If selected_customer_id is invalid/hidden or belongs to wrong profile → clear it and descendants
    2. If selected_batch_id is invalid/hidden or doesn't belong to selected customer → clear it and descendants
    3. If selected_document_id is invalid/hidden or doesn't belong to selected batch → clear it
    4. If selected_trace_id is invalid/hidden by language → clear it and span state
    
    :param state: Streamlit session_state dict (mutable mapping).
    :param customers: Full list of customer records with id/profile.
    :param batches: Full list of batch records (filtered by language inside).
    :param documents: Full list of document records (filtered by language inside).
    :param traces: Full list of trace records (filtered by language inside).
    :param language: Current language filter ("All", "English", "German").
    :return: None (modifies state in-place by clearing invalid selections).
    """
    """Clear hidden descendants, never silently select an unrelated first row."""
    visible_batches = [b for b in batches if matches_language(b["lang"], language)]
    customer = next((c for c in customers if c["id"] == state["selected_customer_id"]), None)
    if customer is None or customer["profile"] != state["selected_profile_id"] or not any(
        b["customer_id"] == customer["id"] for b in visible_batches
    ):
        state["selected_customer_id"] = None
        state["selected_batch_id"] = None
        state["selected_document_id"] = None
    batch = next((b for b in visible_batches if b["id"] == state["selected_batch_id"]), None)
    if batch is None or batch["customer_id"] != state["selected_customer_id"]:
        state["selected_batch_id"] = None
        state["selected_document_id"] = None
    if not any(
        d["id"] == state["selected_document_id"]
        and d["batch_id"] == state["selected_batch_id"]
        and matches_language(d["lang"], language)
        for d in documents
    ):
        state["selected_document_id"] = None
    if not any(t["id"] == state["selected_trace_id"] and matches_language(t["lang"], language) for t in traces):
        state["selected_trace_id"] = None
        state["selected_span_id"] = None
        state["collapsed_span_ids"] = []