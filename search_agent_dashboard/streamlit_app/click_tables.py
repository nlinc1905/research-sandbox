"""Small, dependency-free Streamlit component for HTML-style row clicks."""

from collections.abc import Callable
from pathlib import Path
from typing import Any

import streamlit as st
import streamlit.components.v2 as components

ASSETS = Path(__file__).resolve().parent / "components"
_table = components.component(
    "MyAgent_click_table",
    html='<div class="table-root"></div>',
    css=(ASSETS / "table.css").read_text(encoding="utf-8"),
    js=(ASSETS / "table.js").read_text(encoding="utf-8"),
)


def click_table(
    columns: list[str],
    rows: list[dict[str, Any]],
    *,
    key: str,
    label: str,
    on_action: Callable[[dict[str, Any]], None] | None = None,
    colors: dict[str, str],
) -> None:
    """Render an interactive HTML table with row click handling via custom Streamlit component.
    
    Wraps a custom JavaScript/CSS component (_table) that renders clickable HTML tables
    without checkboxes. Rows can have optional metadata for trace trees (expanded state,
    selected span, collapsed spans) and other interactive features.
    
    Decision: Actions are only fired if the clicked row ID currently exists in the
    rows list. Stale events from previous renders are ignored to prevent navigation
    to deleted/invisible records.
    
    :param columns: List of column header names (displayed in table header).
    :param rows: List of row dicts, each with "id" and "cells" keys. Cells are
                metric_cell/category_cell dicts with text/level/metric/hint.
                Optional: "trace", "expanded", "selected_span_id", "collapsed_span_ids".
    :param key: Unique Streamlit session state key for this component (e.g. "profiles_table_A").
    :param label: Display label for the table (shown above table).
    :param on_action: Optional callback invoked when user clicks a row.
                     Receives action dict with at least {"id", "kind"} and optional
                     span metadata. Called only if row ID is currently visible.
    :param colors: Dict mapping semantic levels to hex color codes (from METRIC_COLORS).
    :return: None (renders table to Streamlit app).
    """
    def handle_action() -> None:
        """Process click action and call on_action if row is still visible."""
        action = st.session_state.get(key, {}).get("action")
        # Ignore stale events or values that do not refer to a currently visible row.
        if on_action is not None and isinstance(action, dict) and any(row["id"] == action.get("id") for row in rows):
            on_action(action)

    _table(
        data={"columns": columns, "rows": rows, "label": label, "colors": colors, "interactive": on_action is not None},
        key=key,
        on_action_change=handle_action,
        width="stretch",
        height="content",
    )