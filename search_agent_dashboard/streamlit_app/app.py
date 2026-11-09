from __future__ import annotations

import math
from collections.abc import Callable
from html import escape
from pathlib import Path
from typing import Any, Literal, TypedDict

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from click_tables import click_table as _click_table
from data_adapter import DashboardData, create_adapter, resolve_adapter_config
import navigation

# Metric color policy — illustrative draft targets, NOT calibrated production SLOs.
# Rates/scores are fractions (0..1), time is seconds, cost is USD.
# Higher: green >= good, amber >= warn, red below warn.
# Lower:  green <= good, amber <= warn, red above warn. Boundaries are inclusive.
# Missing, invalid, and non-finite values are neutral, never a successful zero.
METRIC_COLORS = {
    "good": "#3ccf8e", "warn": "#f0a531", "bad": "#ff6b6b", "neutral": "#9aa3b2",
}


class MetricThreshold(TypedDict):
    direction: Literal["higher", "lower"]
    good: float
    warn: float
    unit: str


METRIC_THRESHOLDS: dict[str, MetricThreshold] = {
    "knowledge_base_quality": {"direction": "higher", "good": .85, "warn": .70, "unit": "ratio"},
    "retrieval_performance": {"direction": "higher", "good": .85, "warn": .70, "unit": "ratio"},
    "generation_quality": {"direction": "higher", "good": .90, "warn": .75, "unit": "ratio"},
    "profile_score": {"direction": "higher", "good": .85, "warn": .70, "unit": "ratio"},
    "chunk_score": {"direction": "higher", "good": .80, "warn": .70, "unit": "ratio"},
    "embedding_score": {"direction": "higher", "good": .85, "warn": .75, "unit": "ratio"},
    "hit_rate": {"direction": "higher", "good": .85, "warn": .70, "unit": "ratio"},
    "precision": {"direction": "higher", "good": .85, "warn": .70, "unit": "ratio"},
    "recall": {"direction": "higher", "good": .85, "warn": .70, "unit": "ratio"},
    "faithfulness": {"direction": "higher", "good": .90, "warn": .75, "unit": "ratio"},
    "relevancy": {"direction": "higher", "good": .85, "warn": .70, "unit": "ratio"},
    "field_f1": {"direction": "higher", "good": .85, "warn": .70, "unit": "ratio"},
    "schema_validity": {"direction": "higher", "good": .98, "warn": .90, "unit": "ratio"},
    "null_rate": {"direction": "lower", "good": .05, "warn": .15, "unit": "ratio"},
    "table_accuracy": {"direction": "higher", "good": .90, "warn": .75, "unit": "ratio"},
    "table_structure": {"direction": "higher", "good": .90, "warn": .75, "unit": "ratio"},
    "form_recall": {"direction": "higher", "good": .85, "warn": .70, "unit": "ratio"},
    "thumbs_up_rate": {"direction": "higher", "good": .85, "warn": .70, "unit": "ratio"},
    "retry_rate": {"direction": "lower", "good": .05, "warn": .10, "unit": "ratio"},
    "no_answer_rate": {"direction": "lower", "good": .02, "warn": .05, "unit": "ratio"},
    "latency_seconds": {"direction": "lower", "good": 3, "warn": 5, "unit": "seconds"},
    "throughput_per_minute": {"direction": "higher", "good": 30, "warn": 15, "unit": "/min"},
    "trace_cost": {"direction": "lower", "good": .020, "warn": .030, "unit": "USD"},
    "session_cost": {"direction": "lower", "good": .050, "warn": .100, "unit": "USD"},
    "satisfaction": {"direction": "higher", "good": .85, "warn": .60, "unit": "ratio"},
    "session_retries": {"direction": "lower", "good": 0, "warn": 1, "unit": "count"},
    "session_no_answers": {"direction": "lower", "good": 0, "warn": 1, "unit": "count"},
    # Root spans use the trace budget. Non-root spans use these smaller budgets.
    "span_latency_seconds": {"direction": "lower", "good": 1, "warn": 2, "unit": "seconds"},
    "span_cost": {"direction": "lower", "good": .010, "warn": .020, "unit": "USD"},
    "orphan_rate": {"direction": "lower", "good": .01, "warn": .05, "unit": "ratio"},
    "duplicate_rate": {"direction": "lower", "good": .01, "warn": .05, "unit": "ratio"},
    "split_tables": {"direction": "lower", "good": 0, "warn": 1, "unit": "count"},
}
# Context only: volume/size has no inherent healthy direction. Attribution is a
# share of failures, NOT a failure rate; a low share can still mean many failures.
NEUTRAL_METRICS = {"count", "failure_share", "tokens"}
CATEGORY_LEVELS = {
    "resolved": "good", "partial": "warn", "unresolved": "bad",
    "positive": "good", "neutral": "warn", "frustrated": "bad",
    "up": "good", "down": "bad", "n/a": "neutral",
    "OK": "good", "WARNING": "warn", "ERROR": "bad", "FAILED": "bad",
}

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"


@st.cache_data
def load_dashboard_data(config_items: tuple[tuple[str, str], ...], default_json_dir: str) -> DashboardData:
    """Cache adapter-backed reads so UI reruns do not re-fetch unchanged data.
    
    Wraps adapter instantiation and load() in @st.cache_data to prevent re-fetching
    data on every Streamlit rerun. The decorator requires hashable arguments, so config
    is passed as a tuple of tuples rather than a dict.
    
    :param config_items: Configuration key-value pairs as a tuple of tuples (e.g. from
                         resolve_adapter_config() items()). Determines data source type
                         (json/api/s3/mlflow) and source-specific credentials/paths.
    :param default_json_dir: Fallback data directory for json source if MyAgent_JSON_DIR
                            is not set. Path to local data/ folder.
    :return: DashboardData with all dashboard datasets (overview, profiles, customers,
            batches, documents, sessions, traces) loaded from configured source.
    :raises: Exception if adapter fails to load data (file not found, network error, etc).
             Error is caught in main() and displayed to user.
    """
    adapter = create_adapter(dict(config_items), Path(default_json_dir))
    return adapter.load()


def metric_level(key: str, value: float | None) -> str:
    """Determine semantic health level (good/warn/bad/neutral) for a metric value.
    
    Applies threshold boundaries from METRIC_THRESHOLDS to return semantic status.
    Invalid values (None, NaN, inf, out-of-range) always return "neutral" to avoid
    masking data quality issues as green. Unknown metric keys raise KeyError to
    catch configuration mismatches early.
    
    :param key: Metric name (e.g. "faithfulness", "chunk_score", "retry_rate").
               Must exist in METRIC_THRESHOLDS or NEUTRAL_METRICS, otherwise KeyError.
    :param value: Metric value (float) to classify. If None, NaN, inf, negative,
                 or ratio > 1.0, returns "neutral".
    :return: One of "good", "warn", "bad", "neutral".
            - "neutral" for context-only metrics (count, failure_share, tokens)
            - "neutral" for invalid/missing values
            - "good"/"warn"/"bad" based on threshold comparisons and direction
    :raises KeyError: If key is not in METRIC_THRESHOLDS and not in NEUTRAL_METRICS.
                     Prevents silent fallback to wrong threshold.
    """
    if key in NEUTRAL_METRICS:
        return "neutral"
    rule = METRIC_THRESHOLDS[key]  # Unknown metric keys must not silently use a generic cutoff.
    if value is None or not math.isfinite(value) or value < 0 or (rule["unit"] == "ratio" and value > 1):
        return "neutral"
    if rule["direction"] == "higher":
        return "good" if value >= rule["good"] else "warn" if value >= rule["warn"] else "bad"
    return "good" if value <= rule["good"] else "warn" if value <= rule["warn"] else "bad"


def metric_text(key: str, value: float | None) -> str:
    """Format a metric value as human-readable text with appropriate units.
    
    Converts raw metric values to strings with unit suffixes (%, $, s, /min, count).
    Invalid values return "—" (em-dash). Format depends on unit type from METRIC_THRESHOLDS.
    
    :param key: Metric name to look up unit from METRIC_THRESHOLDS.
    :param value: Numeric value to format. None or non-finite returns "—".
    :return: Formatted string (e.g. "85%", "$0.020", "3.5s", "42/min", "1234", "—").
    """
    if value is None or not math.isfinite(value) or value < 0:
        return "—"
    unit = METRIC_THRESHOLDS[key]["unit"] if key in METRIC_THRESHOLDS else key
    if unit == "ratio":
        return pct(value) if value <= 1 else "—"
    if unit == "USD":
        return f"${value:.3f}"
    if unit == "seconds":
        return f"{value:g}s"
    if unit == "/min":
        return f"{value:g}/min"
    return f"{value:g}"


def metric_hint(key: str) -> str:
    """Generate tooltip hint text explaining the threshold boundaries for a metric.
    
    Constructs human-readable summary of metric's good/warn/bad boundaries for hover
    tooltips. Context metrics (count, failure_share, tokens) get a neutral message.
    Direction (higher/lower) and formatted boundary values are included.
    
    :param key: Metric name to look up thresholds from METRIC_THRESHOLDS.
    :return: Tooltip string (e.g. "Draft target: good ≥ 85%; watch ≥ 70%; otherwise action needed.").
    """
    if key in NEUTRAL_METRICS:
        return "Context only; no health threshold."
    rule = METRIC_THRESHOLDS[key]
    sign = "≥" if rule["direction"] == "higher" else "≤"
    return (f"Draft target: good {sign} {metric_text(key, rule['good'])}; "
            f"watch {sign} {metric_text(key, rule['warn'])}; otherwise action needed.")


def metric_cell(key: str, value: float | None, text: str | None = None) -> dict[str, str]:
    """Create a decorated metric cell dict for table rows and chart payloads.
    
    Combines metric_level() and metric_text() results into a single structured dict
    used by both HTML tables (components/table.js) and span display metrics. This ensures
    consistent coloring and formatting across the entire UI.
    
    :param key: Metric name to classify and format.
    :param value: Numeric value to classify and format.
    :param text: Optional override for display text. If None, text is generated from value.
    :return: Dict with keys:
            - "text": Human-readable formatted value (e.g. "85%", "$0.020")
            - "level": Semantic health level ("good", "warn", "bad", "neutral")
            - "metric": The metric key (for data attributes in HTML)
            - "hint": Tooltip text with threshold limits
    """
    level = metric_level(key, value)
    return {"text": text if text is not None else metric_text(key, value), "level": level,
            "metric": key, "hint": f"{level}: {metric_hint(key)}"}


def category_cell(value: str) -> dict[str, str]:
    """Create a decorated category cell dict for status values (e.g. resolved/positive/OK).
    
    Similar to metric_cell() but for categorical statuses. Maps status strings
    (resolved, partial, unresolved, positive, frustrated, up, down, OK, ERROR, etc)
    to semantic levels via CATEGORY_LEVELS dict.
    
    :param value: Status string to classify (e.g. "resolved", "ERROR", "frustrated").
    :return: Dict with keys:
            - "text": The status string as-is
            - "level": Semantic level ("good", "warn", "bad", "neutral") from CATEGORY_LEVELS
            - "metric": Always "status" (for data attributes)
            - "hint": Tooltip combining status and level
    """
    level = CATEGORY_LEVELS.get(value, "neutral")
    return {"text": value, "level": level, "metric": "status", "hint": f"Status: {value} ({level})"}


def cell_markup(cell: dict[str, str]) -> str:
    """Generate HTML markup for a metric or category cell with semantic styling.
    
    Converts a cell dict (from metric_cell() or category_cell()) into an HTML span
    with semantic color class, data attributes, and title tooltip. Used by render_metric()
    and directly in st.markdown() calls for inline cell display.
    
    :param cell: Dict with "text", "level", "metric", "hint" keys (from metric_cell/category_cell).
    :return: HTML string (e.g. '<span class="metric-number good" ...>85%</span>').
             Content is HTML-escaped to prevent injection.
    """
    return (f"<span class='metric-number {cell['level']}' data-metric='{escape(cell['metric'])}' "
            f"title='{escape(cell['hint'], quote=True)}'>{escape(cell['text'])}</span>")


def render_metric(label: str, key: str, value: float, text: str | None = None) -> None:
    """Render a single metric as a styled card in the current Streamlit container.
    
    Creates a card UI element with label and colored metric value. Used in profile
    and document detail views. Combines metric_cell() with HTML markup for a
    self-contained metric display.
    
    :param label: Display label for the metric (e.g. "Chunk score", "Latency p95").
    :param key: Metric name to classify and format.
    :param value: Numeric metric value.
    :param text: Optional override for display text (default: auto-formatted).
    :return: None (renders directly to Streamlit app).
    """
    st.markdown(f"<div class='metric-card'><div class='muted'>{escape(label)}</div>"
                f"<div class='score'>{cell_markup(metric_cell(key, value, text))}</div></div>", unsafe_allow_html=True)


def click_table(columns: list[str], rows: list[dict[str, Any]], *, key: str, label: str,
                on_action: Callable[[dict[str, Any]], None] | None = None) -> None:
    """Render an interactive HTML table with click-based navigation.
    
    Wrapper around click_tables._click_table that injects the global METRIC_COLORS
    palette so tables render metrics with consistent semantic coloring.
    
    :param columns: List of column header names (displayed in table header row).
    :param rows: List of row dicts, each with "id" and "cells" keys. Cells are
                metric_cell/category_cell dicts. Optional keys: "trace", "expanded",
                "selected_span_id", "collapsed_span_ids" for trace visualization.
    :param key: Unique Streamlit session state key for this table (e.g. "profile_metrics_A").
    :param label: Display label for the table (shown above table).
    :param on_action: Optional callback function called when user clicks a row.
                     Receives action dict with "id", "kind", and optional span metadata.
    :return: None (renders directly to Streamlit app).
    """
    _click_table(columns, rows, key=key, label=label, on_action=on_action, colors=METRIC_COLORS)


def pct(value: float) -> str:
    """Format a fraction (0.0-1.0) as a rounded percentage string.
    
    :param value: Fraction value (e.g. 0.85 → "85%").
    :return: Rounded percentage string without decimal places.
    """
    return f"{round(value * 100)}%"


def matches_language(row_lang: str, selected_lang: str) -> bool:
    """Check if a row's language matches the user's global language filter.
    
    Compares language codes. row_lang typically contains EN, DE, or both (e.g. "EN|DE").
    Used to filter batches, documents, traces, and sessions across all tabs.
    
    :param row_lang: Language code(s) from data record (e.g. "EN", "DE", "EN|DE").
    :param selected_lang: User-selected filter value ("All", "English", "German").
    :return: True if row matches filter, False otherwise.
    """
    if selected_lang == "All":
        return True
    if selected_lang == "English":
        return "EN" in row_lang
    return "DE" in row_lang


def apply_style() -> None:
    """Inject custom CSS into Streamlit app for dark theme and metric styling.
    
    Reads styles.css and injects it with CSS custom property overrides for metric
    colors (good/warn/bad/neutral). Native widget colors are already configured via
    .streamlit/config.toml; this rule covers custom HTML cards and inline styling.
    
    :return: None (renders CSS directly to Streamlit app).
    """
    # Native widget/canvas colors live in .streamlit/config.toml; these rules
    # cover the custom HTML cards and widget chrome without changing layout.
    variables = ";".join(f"--metric-{level}:{color}" for level, color in METRIC_COLORS.items())
    st.markdown(
        f"<style>{(BASE_DIR / 'styles.css').read_text(encoding='utf-8')}\n:root {{{variables}}}</style>",
        unsafe_allow_html=True,
    )


def _go(tab: str, **destination: Any) -> None:
    """Navigate to a specific tab and optionally drill down to a record.
    
    Thin wrapper around navigation.navigate() that updates st.session_state with
    new tab and record selections. Used as on_click handler for navigation buttons
    and breadcrumb links.
    
    :param tab: Target tab name ("Overview", "Profiles", "Batches", "Sessions", "Traces").
    :param destination: Keyword arguments for profile_id, customer_id, batch_id,
                       document_id, trace_id (passed to navigation.navigate).
    :return: None (updates session state, triggers Streamlit rerun).
    """
    navigation.navigate(st.session_state, tab, **destination)


def _init_navigation_state(profiles: list[dict[str, Any]]) -> None:
    """Initialize session state with default navigation selections.
    
    Called once on app startup to set up the navigation hierarchy with first profile
    as default and empty drilldown selections. Does not override existing state
    (uses setdefault in navigation.initialize).
    
    :param profiles: List of profile dicts to extract profile IDs from.
    :return: None (updates st.session_state).
    """
    navigation.initialize(st.session_state, [p["id"] for p in profiles])


def _profile_changed() -> None:
    """Handle profile selectbox change and navigate to Profiles tab.
    
    Callback for profile_filter selectbox on_change event. Updates selected_profile_id
    in navigation state and switches to Profiles tab for drilldown.
    
    :return: None (updates session state, triggers Streamlit rerun).
    """
    _go("Profiles", profile_id=st.session_state.profile_filter)


def _breadcrumbs(profile_id: str, customer: dict[str, Any] | None,
                 batch: dict[str, Any] | None, document: dict[str, Any] | None) -> None:
    """Render breadcrumb navigation showing current drilldown path.
    
    Creates a horizontal row of clickable buttons showing the current hierarchy
    (Profile -> Customer -> Batch -> Document). Only shows levels that are selected.
    Each breadcrumb button navigates back to that level.
    
    :param profile_id: Currently selected profile ID (always shown).
    :param customer: Currently selected customer dict (if any) with name and id.
    :param batch: Currently selected batch dict (if any) with id and version.
    :param document: Currently selected document dict (if any) with name.
    :return: None (renders breadcrumbs to Streamlit app).
    """
    with st.container(horizontal=True, vertical_alignment="center"):
        st.button(f"Profile {profile_id}", key="crumb_profile", type="tertiary",
                  on_click=_go, args=("Profiles",), kwargs={"profile_id": profile_id})
        if customer:
            st.caption("/")
            st.button(customer["name"], key="crumb_customer", type="tertiary", on_click=_go,
                      args=("Profiles",), kwargs={"profile_id": profile_id, "customer_id": customer["id"]})
        if batch and customer:
            st.caption("/")
            st.button(f"{batch['id']} ({batch['version']})", key="crumb_batch", type="tertiary", on_click=_go,
                      args=("Profiles",), kwargs={"profile_id": profile_id, "customer_id": customer["id"], "batch_id": batch["id"]})
        if document:
            st.caption(f"/ {document['name']}")


def build_metric_trend_chart(
    trend_df: pd.DataFrame,
    version_change_points: list[dict[str, str]],
    metric_key: str,
    title: str,
) -> go.Figure:
    """Build a Plotly figure for metric trend over time with threshold bands.
    
    Creates a line chart with colored markers, threshold background bands, boundary
    dashed lines, and version change point annotations. Colors and bands use the
    same threshold logic as metric numbers (via metric_level()) to ensure consistency.
    
    Decision: Background bands are asymmetric for "lower" metrics (good at bottom)
    because the visual metaphor matches the threshold direction. Neutral connector
    lines join points without implying intermediate health (raw line never changes color).
    
    :param trend_df: DataFrame with columns "day" (date), metric_key (float values).
    :param version_change_points: List of dicts with "effective_day" (date), "version" (str)
                                 marking significant model/data changes.
    :param metric_key: Metric name to look up thresholds and apply coloring.
    :param title: Chart title and axis label.
    :return: Plotly Figure with dark theme, 280px height, metric-specific layout.
    """
    rule = METRIC_THRESHOLDS[metric_key]
    values = trend_df[metric_key].tolist()
    levels = [metric_level(metric_key, value) for value in values]
    fig = go.Figure()
    # Background bands and point colors use precisely the same boundaries as
    # metric numbers. A neutral connector avoids implying health between samples.
    if rule["direction"] == "higher":
        bands = [(0, rule["warn"], "bad"), (rule["warn"], rule["good"], "warn"), (rule["good"], 1, "good")]
    else:
        bands = [(0, rule["good"], "good"), (rule["good"], rule["warn"], "warn"), (rule["warn"], 1, "bad")]
    for low, high, level in bands:
        fig.add_hrect(y0=low, y1=high, fillcolor=METRIC_COLORS[level], opacity=.07, line_width=0, layer="below")
    for boundary in (rule["warn"], rule["good"]):
        fig.add_hline(y=boundary, line_dash="dot", line_color=METRIC_COLORS["neutral"], opacity=.5)
    fig.add_trace(
        go.Scatter(
            x=trend_df["day"],
            y=trend_df[metric_key],
            mode="lines+markers",
            name=title,
            line={"color": METRIC_COLORS["neutral"], "width": 2},
            marker={"size": 8, "color": [METRIC_COLORS[level] for level in levels]},
            customdata=levels,
            hovertemplate="Day: %{x|%Y-%m-%d}<br>Score: %{y:.0%}<br>Status: %{customdata}<extra></extra>",
            showlegend=False,
        )
    )

    for point in version_change_points:
        change_day = pd.to_datetime(point["effective_day"])
        fig.add_vline(x=change_day, line_dash="dash", line_color="#9aa3b2", line_width=1)
        fig.add_annotation(
            x=change_day,
            y=1.01,
            yref="paper",
            text=f"{point['version']}",
            showarrow=False,
            font={"size": 10, "color": "#9aa3b2"},
        )

    fig.update_layout(
        title=title,
        template="plotly_dark",
        hovermode="x unified",
        margin={"l": 30, "r": 15, "t": 45, "b": 40},
        plot_bgcolor="#1d2128",
        paper_bgcolor="#1d2128",
        font={"color": "#e8eaee", "family": "system-ui, -apple-system, Segoe UI, sans-serif"},
        hoverlabel={"bgcolor": "#1d2128", "bordercolor": "#2c323c", "font": {"color": "#e8eaee"}},
        height=280,
    )
    fig.update_xaxes(title="Date", showgrid=True, gridcolor="#2c323c", tickfont={"color": "#9aa3b2"})
    fig.update_yaxes(title="Score", tickformat=".0%", range=[0.0, 1.0], showgrid=True, gridcolor="#2c323c", tickfont={"color": "#9aa3b2"})
    return fig


def render_metric_trend_chart(trend_df: pd.DataFrame, version_change_points: list[dict[str, str]],
                              metric_key: str, title: str) -> None:
    """Render a metric trend chart to Streamlit and display its threshold hint.
    
    Wraps build_metric_trend_chart() with Streamlit rendering and a caption explaining
    the metric's thresholds. Uses theme=None to preserve fixed Plotly dark colors.
    
    :param trend_df: DataFrame with "day" and metric_key columns.
    :param version_change_points: List of version change point dicts with "effective_day" and "version".
    :param metric_key: Metric name for building chart and fetching thresholds.
    :param title: Chart title and axis label.
    :return: None (renders chart and caption to Streamlit app).
    """
    # Do not let Streamlit replace the fixed chart palette with the viewer theme.
    st.plotly_chart(build_metric_trend_chart(trend_df, version_change_points, metric_key, title), width="stretch", theme=None)
    st.caption(metric_hint(metric_key))


def batch_customer_names(batch: dict[str, Any], documents: list[dict[str, Any]],
                         customer_names: dict[str, str]) -> str:
    """Describe every customer represented in a batch rather than one owner.

    :param batch: Batch whose customer names should be displayed.
    :param documents: Available document records, optionally language-filtered.
    :param customer_names: Customer IDs mapped to display names.
    :return: Sorted customer names, raw IDs for unknown customers, or an em dash.
    """
    return ", ".join(sorted(customer_names.get(cid, cid)
                            for cid in navigation.batch_customer_ids(batch, documents))) or "—"


def render_document_details(document: dict[str, Any], batch: dict[str, Any],
                            traces: list[dict[str, Any]], selected_lang: str, *, key: str) -> None:
    """Render shared document diagnostics and drillable retrieval traces.

    :param document: Selected document with quality metrics and retrieval count.
    :param batch: Parent batch used to identify matching traces.
    :param traces: Trace records containing batch and document references.
    :param selected_lang: Global language filter applied to retrieval traces.
    :param key: Calling view's component namespace to prevent widget collisions.
    :return: None; renders document details and links to the Traces tab.
    """
    st.markdown(f"#### {document['name']}")
    d1, d2, d3 = st.columns(3)
    with d1:
        render_metric("Chunk score", "chunk_score", document["chunk_score"])
    with d2:
        render_metric("Embedding score", "embedding_score", document["embedding_score"])
    with d3:
        render_metric(f"Hit rate · {document['retrievals']} retrievals", "hit_rate", document["hit_rate"])
    st.markdown("<div class='muted'>Chunk diagnostics (mock): avg tokens "
                + cell_markup(metric_cell("tokens", 412)) + ", orphan chunks "
                + cell_markup(metric_cell("orphan_rate", .03)) + ", tables split across chunks "
                + cell_markup(metric_cell("split_tables", 2)) + ", duplicate chunks "
                + cell_markup(metric_cell("duplicate_rate", .01)) + ".</div>", unsafe_allow_html=True)
    hits = [t for t in traces if t["batch"] == batch["id"] and t["document"] == document["id"]
            and matches_language(t["lang"], selected_lang)]
    st.markdown("#### Recent retrieval traces for selected document")
    st.caption("Production trace links only; these judge scores do not contribute to golden evaluation scores.")
    if hits:
        click_table(
            ["Trace", "Query", "Chunk", "Faithfulness", "Version", "Cost"],
            [{"id": t["id"], "cells": [t["id"], t["query"], t["chunk"], metric_cell("faithfulness", t["faithfulness"]),
              t["version"], metric_cell("trace_cost", t["cost"])]} for t in hits],
            key=f"{key}_document_traces_{document['id']}_{selected_lang}", label="Document retrieval traces",
            on_action=lambda action: _go("Traces", trace_id=action["id"]),
        )
        st.caption("Click a retrieval row to open its trace tree.")
    else:
        st.info("No recent traces for this document and language.")


def render_batch_documents(batch: dict[str, Any], documents: list[dict[str, Any]],
                            customers: list[dict[str, Any]], *, key: str,
                            on_action: Callable[[dict[str, Any]], None]) -> None:
    """Render drillable document rows with per-document customer ownership.

    :param batch: Parent batch providing legacy customer and version defaults.
    :param documents: Documents already scoped to this batch and language filter.
    :param customers: Customer records used to display names instead of IDs.
    :param key: Unique component key for the calling view and current batch.
    :param on_action: Callback receiving the selected document's row action.
    :return: None; renders the document table or an empty-state message.
    """
    if not documents:
        st.info("No documents match this batch and language.")
        return
    customer_names = {c["id"]: c["name"] for c in customers}
    rows = []
    for document in documents:
        # Document ownership overrides the legacy single-owner batch field.
        customer_id = navigation.document_customer_id(document, batch)
        rows.append({"id": document["id"], "cells": [
            batch["id"], document["name"], customer_names.get(customer_id, customer_id or "—"),
            document.get("version", batch["version"]), document["lang"],
            metric_cell("count", document["pages"]), metric_cell("count", document["chunks"]),
            metric_cell("chunk_score", document["chunk_score"]),
            metric_cell("embedding_score", document["embedding_score"]),
            metric_cell("count", document["retrievals"]), metric_cell("hit_rate", document["hit_rate"]),
        ]})
    click_table(
        ["Batch", "Document", "Customer", "Version", "Language", "Pages", "Chunks", "Chunk score",
         "Embedding score", "Retrievals", "Hit rate"],
        rows, key=key, label="Batch documents", on_action=on_action,
    )
    st.caption("Click a document row to see diagnostics and retrievals.")


def render_batches(selected_lang: str, batches: list[dict[str, Any]],
                   documents: list[dict[str, Any]], customers: list[dict[str, Any]],
                   traces: list[dict[str, Any]]) -> None:
    """Render the customer-independent Batches → Documents → Diagnostics drilldown.

    :param selected_lang: Global language filter for batches and their documents.
    :param batches: Batch summaries, not restricted to a selected customer/profile.
    :param documents: All documents, optionally carrying their own customer_id.
    :param customers: Customer records used to label mixed-customer batches.
    :param traces: Retrieval traces for the selected document's diagnostics.
    :return: None; renders batch summaries, documents, or document details.
    """
    st.caption("Inspect ingestion batches across customers. A batch can contain documents from multiple customers.")
    visible = sorted((b for b in batches if matches_language(b["lang"], selected_lang)), key=lambda b: b["hit_rate"])
    if not visible:
        st.warning("No batches match the selected language filter.")
        return
    visible_documents = [d for d in documents if matches_language(d["lang"], selected_lang)]
    customer_names = {c["id"]: c["name"] for c in customers}
    batch = next((b for b in visible if b["id"] == st.session_state.batches_batch_id), None)

    with st.container(horizontal=True, vertical_alignment="center"):
        st.button("All batches", key="batches_crumb_all", type="tertiary", on_click=_go, args=("Batches",))
        if batch:
            st.caption("/")
            st.button(f"{batch['id']} ({batch['version']})", key="batches_crumb_batch", type="tertiary",
                      on_click=_go, args=("Batches",), kwargs={"batch_id": batch["id"]})

    if batch is None:
        st.markdown("### Document Batches")
        rows = []
        for candidate in visible:
            batch_docs = [d for d in visible_documents if d["batch_id"] == candidate["id"]]
            rows.append({"id": candidate["id"], "cells": [
                candidate["id"], batch_customer_names(candidate, visible_documents, customer_names),
                candidate["version"], candidate["lang"], metric_cell("count", candidate["docs"]),
                metric_cell("count", sum(d["pages"] for d in batch_docs)),
                metric_cell("count", sum(d["chunks"] for d in batch_docs)),
                metric_cell("chunk_score", candidate["chunk_score"]),
                metric_cell("embedding_score", candidate["embedding_score"]),
                metric_cell("count", candidate["retrieval_traffic"]), metric_cell("hit_rate", candidate["hit_rate"]),
            ]})
        click_table(
            ["Batch", "Customers", "Version", "Language", "Documents", "Pages", "Chunks", "Chunk score",
             "Embedding score", "Retrievals", "Hit rate"],
            rows, key=f"all_batches_{selected_lang}", label="Document batches",
            on_action=lambda action: _go("Batches", batch_id=action["id"]),
        )
        # The demo contains sampled documents; do not imply their totals cover a
        # full batch or recompute the supplied batch-level evaluation scores.
        st.caption("Lowest hit rates first. Click a batch to inspect its documents. Pages/chunks total the available "
                   "documents matching the language filter; document counts, retrievals, and scores are batch summaries.")
        return

    batch_docs = [d for d in visible_documents if d["batch_id"] == batch["id"]]
    document = next((d for d in batch_docs if d["id"] == st.session_state.batches_document_id), None)
    st.caption(f"Customers: {batch_customer_names(batch, batch_docs, customer_names)}")
    if document:
        customer_id = navigation.document_customer_id(document, batch)
        st.caption(f"Document: {document['name']} · Customer: {customer_names.get(customer_id, customer_id or '—')} · "
                   f"Version: {document.get('version', batch['version'])} · Language: {document['lang']}")
        render_document_details(document, batch, traces, selected_lang, key="batches")
        return

    st.markdown(f"### Documents in {batch['id']} ({batch['version']})")
    for column, (label, metric, value) in zip(st.columns(4), [
        ("Chunk score", "chunk_score", batch["chunk_score"]),
        ("Embedding score", "embedding_score", batch["embedding_score"]),
        ("Retrieval hit rate", "hit_rate", batch["hit_rate"]),
        ("Retrieval traffic", "count", batch["retrieval_traffic"]),
    ]):
        with column:
            render_metric(label, metric, value)
    render_batch_documents(
        batch, batch_docs, customers, key=f"batch_documents_{batch['id']}_{selected_lang}",
        on_action=lambda action: _go("Batches", batch_id=batch["id"], document_id=action["id"]),
    )


def render_overview(
    selected_lang: str,
    overview: dict[str, Any],
    batches: list[dict[str, Any]],
    customers: list[dict[str, Any]],
    documents: list[dict[str, Any]],
) -> None:
    """Render the Overview tab showing global quality KPIs, trends, and lowest-performing batches.
    
    Displays:
    - Key performance indicators (knowledge_base_quality, retrieval_performance, generation_quality)
    - Operational metrics (thumbs-up rate, retry rate, latency, throughput, cost)
    - Version-aware trend charts with threshold bands and version markers
    - Failure attribution breakdown as stacked percentages
    - Table of lowest hit-rate batches with drilldown to Batches
    
    All metrics use METRIC_THRESHOLDS for consistent coloring. Language filter hides
    non-matching batches. Note: Overview scores are golden-evaluation only, not impacted
    by production sessions/traces.
    
    :param selected_lang: User-selected language filter ("All", "English", "German").
    :param overview: Dict with keys: kpis, ops_metrics, trend, version_change_points,
                    attribution.
    :param batches: Full list of batch records (filtered by language inside function).
    :param customers: Full list of customer records (for name lookup).
    :param documents: Document records used to resolve customers within each batch.
    :return: None (renders Overview content to Streamlit app).
    """
    st.caption("Metrics on the Overview tab come from golden datasets only. Production sessions/traces do not change these scores.")

    kpi_cols = st.columns(len(overview["kpis"]))
    for col, item in zip(kpi_cols, overview["kpis"]):
        score = cell_markup(metric_cell(item["key"], item["score"]))
        detail = ", ".join(f"{escape(m['label'])} {cell_markup(metric_cell(m['key'], m['value']))}"
                   for m in item["detail_metrics"])
        detail += f" {escape(item.get('detail_note', ''))}"
        with col:
            st.markdown(
                (
                    "<div class='card'>"
                    f"<h4>{item['title']}</h4>"
                    f"<div class='score'>{score}</div>"
                    f"<div class='muted'>{detail}</div>"
                    "</div>"
                ),
                unsafe_allow_html=True,
            )

    st.markdown("### Operational Metrics")
    desired_order = [
        "Thumbs-up rate",
        "Retry rate",
        "No-answer rate",
        "Latency p95",
        "Throughput",
        "Avg cost / trace",
    ]
    item_by_title = {item["title"]: item for item in overview["ops_metrics"]}
    ordered_items = [item_by_title[t] for t in desired_order if t in item_by_title]

    ops_html = "<div class='ops-grid'>"
    for item in ordered_items:
        detail = ", ".join(f"{escape(m['label'])} {cell_markup(metric_cell(m['key'], m['value']))}"
                           for m in item["detail_metrics"]) if "detail_metrics" in item else escape(item["detail"])
        ops_html += (
            "<div class='ops-item'>"
            f"<div class='label'>{item['title']}</div>"
            f"<div class='value'>{cell_markup(metric_cell(item['key'], item['numeric_value']))}</div>"
            f"<div class='detail'>{detail}</div>"
            "</div>"
        )
    ops_html += "</div>"
    st.markdown(ops_html, unsafe_allow_html=True)

    st.markdown("### Trend by Version")
    st.caption("Vertical dashed lines mark version changes. Horizontal dashed lines mark thresholds.")
    trend_df = pd.DataFrame(overview["trend"])
    trend_df["day"] = pd.to_datetime(trend_df["day"])
    chart_order = [
        ("generation_quality", "Generation quality"),
        ("retrieval_performance", "Retrieval performance"),
        ("knowledge_base_quality", "Knowledge base quality"),
    ]
    for metric_key, title in chart_order:
        render_metric_trend_chart(
            trend_df=trend_df,
            version_change_points=overview["version_change_points"],
            metric_key=metric_key,
            title=title,
        )

    st.markdown("#### Version Changes")
    st.caption("Each version change is a vertical dashed line in the trend charts above.")
    st.dataframe(
        pd.DataFrame(overview["version_change_points"]),
        width="stretch",
        hide_index=True,
    )

    st.markdown("### Failure Attribution by Stage")
    st.caption("Share of all failures attributed to each stage. This is NOT an absolute failure rate by stage. Neutral coloring is intentional.")
    for item in overview["attribution"]:
        st.markdown(f"{escape(item['stage'])} — {cell_markup(metric_cell('failure_share', item['percent'], str(item['percent']) + '%'))}", unsafe_allow_html=True)
        st.progress(item["percent"] / 100)

    visible = [b for b in batches if matches_language(b["lang"], selected_lang)]
    if not visible:
        st.warning("No batches match the selected language filter.")
        return
    customer_names = {c["id"]: c["name"] for c in customers}
    visible_documents = [d for d in documents if matches_language(d["lang"], selected_lang)]
    worst = sorted(visible, key=lambda b: b["hit_rate"])[:4]
    lookup = {b["id"]: b for b in worst}

    def open_batch(action: dict[str, Any]) -> None:
        """Open a low-hit-rate batch without imposing a customer selection.

        :param action: Table row action identifying a currently visible batch.
        :return: None; switches to the batch's document list in Batches.
        """
        batch = lookup[action["id"]]
        _go("Batches", batch_id=batch["id"])

    st.markdown("### Document Batches with Lowest Retrieval Hit Rates")
    click_table(
        ["Batch", "Version", "Customers", "Hit rate", "Chunk score", "Embedding score"],
        [{"id": b["id"], "cells": [b["id"], b["version"], batch_customer_names(b, visible_documents, customer_names),
          metric_cell("hit_rate", b["hit_rate"]), metric_cell("chunk_score", b["chunk_score"]), metric_cell("embedding_score", b["embedding_score"])]} for b in worst],
        key=f"overview_batches_{selected_lang}", label="Lowest retrieval hit rate batches", on_action=open_batch,
    )
    st.caption("Click a batch row to open its documents in Batches, across all customers.")


def render_profiles(
    selected_lang: str,
    profiles: list[dict[str, Any]],
    customers: list[dict[str, Any]],
    batches: list[dict[str, Any]],
    documents: list[dict[str, Any]],
    traces: list[dict[str, Any]],
) -> None:
    """Render the Profiles tab with hierarchy drilldown and golden-dataset metrics.
    
    Implements a 4-level drilldown:
    1. Profile selector → profile cards and metric snapshot
    2. Customers → table of customer records for selected profile
    3. Batches → table of processing versions for selected customer
    4. Documents → table of documents in selected batch with chunk diagnostics
    
    At document level, also shows recent production retrieval traces and links to Traces tab.
    Breadcrumb navigation allows jumping back to any parent level. Language filter hides
    non-matching batches, documents, and traces.
    
    Decision: Profile filter widget is kept separate from navigation state (setdefault)
    so cross-tab links can update the profile even if the widget was already mounted.
    
    :param selected_lang: User-selected language filter ("All", "English", "German").
    :param profiles: List of profile dicts with id, name, score, metrics, version_scores.
    :param customers: List of customer dicts with id, name, profile.
    :param batches: Full list of batch records (filtered by language inside).
    :param documents: Full list of document records (filtered by language inside).
    :param traces: Full list of trace records (filtered by language inside).
    :return: None (renders Profiles content to Streamlit app).
    """
    st.caption("Metrics on the Profiles tab come from golden datasets only. Production sessions/traces do not change these scores.")

    cards = st.columns(len(profiles))
    for col, profile in zip(cards, profiles):
        score = cell_markup(metric_cell("profile_score", profile["score"]))
        with col:
            st.markdown(
                (
                    "<div class='card'>"
                    f"<h4>Profile {profile['id']} Composite Score</h4>"
                    f"<div><b>{profile['name']}</b></div>"
                    f"<div class='score'>{score}</div>"
                    f"<div class='muted'>{profile['coverage_note']}</div>"
                    "</div>"
                ),
                unsafe_allow_html=True,
            )

    profile_map = {p["id"]: p for p in profiles}
    profile_options = [p["id"] for p in profiles]
    profile_id = st.session_state.selected_profile_id
    # Keep widget state separate from navigation state so a cross-tab link can
    # update the profile even when the previous profile's widget was mounted.
    st.session_state.profile_filter = profile_id
    st.selectbox("Filter to Profile", profile_options, key="profile_filter", on_change=_profile_changed)
    profile = profile_map[profile_id]

    vcol1, vcol2 = st.columns(2)
    with vcol1:
        st.markdown(f"#### Profile {profile_id} Metric Snapshot")
        click_table(["Metric", "Value"],
                [{"id": m["key"], "cells": [m["name"], metric_cell(m["key"], m["value"])]} for m in profile["metrics"]],
                key=f"profile_metrics_{profile_id}", label=f"Profile {profile_id} Metric snapshot")
    with vcol2:
        st.markdown(f"#### Composite Scores for Profile {profile_id} by Version")
        click_table(["Version", "Composite Score"],
                [{"id": v["version"], "cells": [v["version"], metric_cell("profile_score", v["score"])]} for v in profile["version_scores"]],
                key=f"profile_versions_{profile_id}", label=f"Composite Scores for Profile {profile_id} by Version")

    profile_batches = [b for b in batches if b["profile"] == profile_id and matches_language(b["lang"], selected_lang)]
    visible_documents = [d for d in documents if matches_language(d["lang"], selected_lang)]

    def customer_batch_records(customer_id: str) -> list[dict[str, Any]]:
        """Scope shared batch summaries to the selected customer's documents.

        :param customer_id: Customer whose batch metrics should be displayed.
        :return: Legacy batch summaries or customer-specific shared-batch summaries.
        """
        records = []
        for candidate in profile_batches:
            if customer_id not in navigation.batch_customer_ids(candidate, visible_documents):
                continue
            if len(navigation.batch_customer_ids(candidate, documents)) <= 1:
                # Preserve supplied evaluation summaries for existing single-owner
                # batches; sampled documents do not represent their full totals.
                records.append(candidate)
                continue
            scoped = [d for d in visible_documents if d["batch_id"] == candidate["id"]
                      and navigation.document_customer_id(d, candidate) == customer_id]
            if not scoped:
                # A batch-level language tag does not guarantee a sampled
                # document exists for this customer in the selected language.
                continue
            retrievals = sum(d["retrievals"] for d in scoped)
            # Shared-batch totals cannot be attributed in full to every customer.
            # Use that customer's available documents: mean quality scores and a
            # retrieval-weighted hit rate (unknown when there are no retrievals).
            records.append({**candidate, "docs": len(scoped), "retrieval_traffic": retrievals,
                            "chunk_score": sum(d["chunk_score"] for d in scoped) / len(scoped),
                            "embedding_score": sum(d["embedding_score"] for d in scoped) / len(scoped),
                            "hit_rate": (sum(d["hit_rate"] * d["retrievals"] for d in scoped) / retrievals
                                         if retrievals else None)})
        return records

    customer = next((c for c in customers if c["id"] == st.session_state.selected_customer_id), None)
    selected_batches = customer_batch_records(customer["id"]) if customer else []
    batch = next((b for b in selected_batches if b["id"] == st.session_state.selected_batch_id), None)
    document = next((d for d in documents if d["id"] == st.session_state.selected_document_id), None)
    _breadcrumbs(profile_id, customer, batch, document)

    def destination(**parts: Any) -> None:
        """Keep profile context when opening a customer, batch, or document.

        :param parts: Customer, batch, and document IDs for the destination.
        :return: None; updates the Profiles navigation selection.
        """
        _go("Profiles", profile_id=profile_id, **parts)

    if document and batch and customer:
        render_document_details(document, batch, traces, selected_lang, key="profiles")
        return

    if batch and customer:
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            render_metric("Chunk score", "chunk_score", batch["chunk_score"])
        with c2:
            render_metric("Embedding score", "embedding_score", batch["embedding_score"])
        with c3:
            render_metric("Retrieval hit rate", "hit_rate", batch["hit_rate"])
        with c4:
            render_metric("Retrieval traffic", "count", batch["retrieval_traffic"])
        # Profiles stays customer-scoped even when Batches exposes the entire
        # mixed-customer ingestion run; do not leak other customers' documents.
        batch_docs = [d for d in visible_documents if d["batch_id"] == batch["id"]
                      and navigation.document_customer_id(d, batch) == customer["id"]]
        st.markdown(f"#### Documents in {batch['id']} ({batch['version']})")
        render_batch_documents(
            batch, batch_docs, customers, key=f"documents_{batch['id']}_{selected_lang}",
            on_action=lambda action: destination(customer_id=customer["id"], batch_id=batch["id"], document_id=action["id"]),
        )
        return

    if customer:
        customer_batches = selected_batches
        st.markdown(f"#### Batches for {customer['name']}")
        st.caption("Each processing version is listed separately. Click a batch to see its documents.")
        st.caption("Shared-batch metrics cover this customer's available language-filtered documents; "
                   "single-customer batches retain the supplied evaluation summaries.")
        click_table(
            ["Batch", "Version", "Ingested", "Docs", "Chunk score", "Embedding score", "Hit rate", "Queries", "Language"],
            [{"id": b["id"], "cells": [b["id"], b["version"], b["ingested"], metric_cell("count", b["docs"]),
              metric_cell("chunk_score", b["chunk_score"]), metric_cell("embedding_score", b["embedding_score"]), metric_cell("hit_rate", b["hit_rate"]),
              metric_cell("count", b["retrieval_traffic"]), b["lang"]]} for b in customer_batches],
            key=f"batches_{customer['id']}_{selected_lang}", label="Customer batches",
            on_action=lambda action: destination(customer_id=customer["id"], batch_id=action["id"]),
        )
        return

    customer_rows = []
    for candidate in customers:
        if candidate["profile"] != profile_id:
            continue
        subset = customer_batch_records(candidate["id"])
        if not subset:
            continue
        hit_rates = [b["hit_rate"] for b in subset if b["hit_rate"] is not None]
        customer_rows.append({"id": candidate["id"], "cells": [
            candidate["name"], metric_cell("count", len(subset)),
            metric_cell("chunk_score", sum(b["chunk_score"] for b in subset) / len(subset)),
            metric_cell("embedding_score", sum(b["embedding_score"] for b in subset) / len(subset)),
            metric_cell("hit_rate", sum(hit_rates) / len(hit_rates) if hit_rates else None),
            metric_cell("count", sum(b["retrieval_traffic"] for b in subset)), ", ".join(sorted({b["version"] for b in subset})),
        ]})
    st.markdown(f"#### Customers in Profile {profile_id}")
    st.caption("Shared-batch metrics use each customer's available documents, not the entire batch's traffic.")
    if not customer_rows:
        st.info("No customers have data for this profile and language.")
        return
    click_table(
        ["Customer", "Batches", "Chunk score", "Embedding score", "Hit rate", "Queries", "Versions"],
        customer_rows, key=f"customers_{profile_id}_{selected_lang}", label="Profile customers",
        on_action=lambda action: destination(customer_id=action["id"]),
    )
    st.caption("Click a customer row to see its batches.")


def render_sessions(selected_lang: str, sessions: list[dict[str, Any]]) -> None:
    """Render the Sessions tab with chat history and session-level judge metrics.
    
    Displays production-run chat sessions with judge snapshot data (goal completion,
    sentiment, satisfaction, retries, cost). Includes a mock chat replay and natural
    language analysis interface. Sessions are currently mocked; future implementation
    will link sessions to traces via session IDs.
    
    Language filter hides non-matching sessions.
    
    Decision: This tab is marked experimental because session-level judges and stored
    chat data are not yet available in the golden-evaluation pipeline.
    
    :param selected_lang: User-selected language filter ("All", "English", "German").
    :param sessions: List of session dicts with id, customer, lang, messages, judge_snapshot.
    :return: None (renders Sessions content to Streamlit app).
    """
    st.caption("Metrics on the Sessions tab come from production-run interactions.")
    st.warning(
        "This tab assumes future capabilities that we do not yet have "
        "(session-level judges,stored chats, and session IDs linked to traces).",
        icon="⚠️"
    )

    filtered = [s for s in sessions if matches_language(s["lang"], selected_lang)]
    if not filtered:
        st.warning("No sessions match the selected language filter.")
        return

    labels = [f"{s['id']} | {s['customer']} | {s['lang']} | {s['version']}" for s in filtered]
    selected_label = st.selectbox("Session", labels)
    session = filtered[labels.index(selected_label)]

    st.markdown("#### Chat")
    for message in session["messages"]:
        st.markdown(
            (
                "<div class='chat-bubble'>"
                f"<b>{message['speaker']}:</b> {message['text']}"
                "</div>"
            ),
            unsafe_allow_html=True,
        )

    snap = session["judge_snapshot"]
    snapshot = [
        ("Version", session["version"]),
        ("Goal completion", category_cell(snap["goal_completion"])),
        ("Inferred satisfaction", metric_cell("satisfaction", snap["inferred_satisfaction"])),
        ("Sentiment", category_cell(snap["sentiment"])),
        ("Retries", metric_cell("session_retries", snap["retries"])),
        ("No-answers", metric_cell("session_no_answers", snap["no_answers"])),
        ("Thumbs", category_cell(snap["thumbs"])),
        ("Total cost", metric_cell("session_cost", snap["total_cost"])),
        ("Traces", metric_cell("count", snap["trace_count"])),
    ]

    left, right = st.columns([1, 1])
    with left:
        st.markdown("#### Session Metrics from LLM Judge")
        click_table(["Metric", "Value"], [{"id": name, "cells": [name, value]} for name, value in snapshot],
                key=f"session_metrics_{session['id']}", label="Session judge metrics")
    with right:
        st.markdown("#### Ask About this Session")
        _ = st.text_input("Question", value="Why was the user frustrated?")
        if st.button("Ask LLM"):
            st.success(session["analysis_answer"])


def decorate_trace(trace: dict[str, Any]) -> dict[str, Any]:
    """Add classified metric cells to all spans in a trace for display in the UI.
    
    Decision: Threshold logic never runs on the frontend. Instead, Python computes
    metric_cell dicts with level/text/hint and passes them to JavaScript. This keeps
    thresholds single-sourced in METRIC_THRESHOLDS and avoids frontend threshold drift.
    
    Root spans (parent_id=None) use \"latency_seconds\" and \"trace_cost\" budgets.
    Non-root spans use \"span_latency_seconds\" and \"span_cost\" budgets.
    
    :param trace: Trace dict with spans array and top-level faithfulness value.
    :return: Modified trace dict with each span having a \"display_metrics\" key containing
            decorated metric cells (duration, cost, self_cost, status, faithfulness).
            Original trace data is not mutated (new span dicts created).
    """
    spans = []
    for span in trace.get("spans", []):
        root = span["parent_id"] is None
        spans.append({**span, "display_metrics": {
            "duration": metric_cell("latency_seconds" if root else "span_latency_seconds", span["duration_ms"] / 1000,
                                    f"{span['duration_ms']} ms"),
            "cost": metric_cell("trace_cost" if root else "span_cost", span["cost"]),
            "self_cost": metric_cell("span_cost", span["self_cost"]),
            "status": category_cell(span["status"]),
            "faithfulness": metric_cell("faithfulness", span["attributes"].get("faithfulness")),
        }})
    return {**trace, "spans": spans, "faithfulness_metric": metric_cell("faithfulness", trace["faithfulness"])}


def render_traces(selected_lang: str, traces: list[dict[str, Any]], batches: list[dict[str, Any]]) -> None:
    """Render the Traces tab showing production-run retrieval traces with span trees.
    
    Displays:
    - Table of recent traces with query, profile, customer, version, cost, latency, feedback
    - Expandable trace rows showing full span trees with input/output/attributes
    - Span-level details when selecting a span (duration, cost, status, faithfulness)
    - Links from retrieval spans back to their source documents in Batches tab
    - Mock natural-language analysis interface for trace questions
    
    Trace data decorates spans with metric cells (via decorate_trace) before rendering.
    Language filter hides non-matching traces. Span selection and collapse state are
    maintained independently of trace selection (reset when changing traces).
    
    Decision: Trace total cost comes from root span cost. Span \"cost\" includes
    descendants; use \"self_cost\" to avoid double-counting.
    
    :param selected_lang: User-selected language filter ("All", "English", "German").
    :param traces: List of trace dicts with spans, cost, latency, feedback, batch/document/chunk.
    :param batches: List of batch dicts used to validate source-document destinations.
    :return: None (renders Traces content to Streamlit app).
    """
    st.caption("Metrics on the Traces tab come from golden datasets and production-run interactions.")
    filtered = [t for t in traces if matches_language(t["lang"], selected_lang)]
    if not filtered:
        st.warning("No traces match the selected language filter.")
        return

    lookup = {t["id"]: t for t in filtered}

    def trace_action(action: dict[str, Any]) -> None:
        trace = lookup[action["id"]]
        kind = action.get("kind")
        if kind == "row":
            _go("Traces", trace_id=None if st.session_state.selected_trace_id == trace["id"] else trace["id"])
        elif kind == "source":
            span = next((s for s in trace.get("spans", []) if s["id"] == action.get("span_id")), None)
            attributes = span.get("attributes", {}) if span else {}
            source_batch_id = attributes.get("batch_id", trace["batch"])
            source_document_id = attributes.get("document_id", trace["document"])
            batch = next((b for b in batches if b["id"] == source_batch_id), None)
            if batch:
                # Source documents need not share one customer with the batch.
                _go("Batches", batch_id=batch["id"], document_id=source_document_id)
        elif any(s["id"] == action.get("span_id") for s in trace.get("spans", [])):
            span_id = action["span_id"]
            if kind == "span":
                st.session_state.selected_span_id = None if st.session_state.selected_span_id == span_id else span_id
            elif kind == "branch":
                collapsed = set(st.session_state.collapsed_span_ids)
                if span_id in collapsed:
                    collapsed.remove(span_id)
                else:
                    collapsed.add(span_id)
                st.session_state.collapsed_span_ids = sorted(collapsed)

    st.markdown("#### Recent traces")
    click_table(
        ["Trace", "Query", "Profile", "Customer", "Version", "Batch / document / chunk", "Faithfulness", "Cost", "Latency", "Feedback"],
        [{"id": t["id"], "cells": [t["id"], t["query"], t["profile"], t["customer"], t["version"],
          f"{t['batch']} / {t['document']} / {t['chunk']}", metric_cell("faithfulness", t["faithfulness"]), metric_cell("trace_cost", t["cost"]),
          metric_cell("latency_seconds", float(t["latency"].removesuffix("s"))), category_cell(t["feedback"])],
          "trace": decorate_trace(t), "expanded": t["id"] == st.session_state.selected_trace_id,
          "selected_span_id": st.session_state.selected_span_id,
          "collapsed_span_ids": st.session_state.collapsed_span_ids} for t in filtered],
        key=f"traces_{selected_lang}", label="Recent traces", on_action=trace_action,
    )
    selected_trace = lookup.get(st.session_state.selected_trace_id)

    st.markdown("#### Analyze a Trace")
    _ = st.text_input("Question", value="What went wrong?")
    if st.button("Ask LLM", disabled=selected_trace is None) and selected_trace:
        st.success(selected_trace["analysis_answer"])
    if not selected_trace:
        st.caption("Select a trace row before asking a question")


def main() -> None:
    """Initialize and run the Streamlit dashboard application.
    
    Execution flow:
    1. Set Streamlit page config (title, wide layout)
    2. Apply custom CSS dark theme and metric colors
    3. Resolve data source configuration from environment variables
    4. Load dashboard data (DashboardData) from configured adapter (JSON/API/S3/MLflow)
    5. Initialize navigation state with profile IDs
    6. Render header, language filter, and metric legend
    7. Render five tabs: Overview, Profiles, Batches, Sessions, Traces
    8. Each tab lazy-renders only when opened (tab.open check)
    
    Error handling: If data loading fails, display error message and stop.
    Adapter config determines which data source is used (see resolve_adapter_config()).
    
    :return: None (runs Streamlit app indefinitely until server stops).
    """
    st.set_page_config(page_title="MyAgent Quality Dashboard", layout="wide")
    apply_style()

    adapter_config = resolve_adapter_config()
    try:
        data = load_dashboard_data(tuple(sorted(adapter_config.items())), str(DATA_DIR))
    except Exception as exc:
        st.error("Failed to load dashboard data from configured source.")
        st.exception(exc)
        st.stop()

    overview = data.overview
    profiles = data.profiles
    customers = data.customers
    batches = data.batches
    documents = data.documents
    sessions = data.sessions
    traces = data.traces

    _init_navigation_state(profiles)

    st.markdown(f"<div class='draft-banner'>DRAFT with fake data. Layout and interactions are the proposal, numbers are placeholders.</div>", unsafe_allow_html=True)
    header_col, filter_col = st.columns([5, 2])
    with header_col:
        st.title("MyAgent Quality")
        st.caption("Pipeline (producer) and Agent (consumer), last 7 days")
    with filter_col:
        with st.container(border=True):
            st.markdown("<div class='filter-title'>Language Filter</div>", unsafe_allow_html=True)
            selected_lang = st.selectbox("Language", ["All", "English", "German"], index=0, label_visibility="collapsed")

    navigation.validate(st.session_state, customers, batches, documents, traces, selected_lang)
    tab_overview, tab_profiles, tab_batches, tab_sessions, tab_traces = st.tabs(
        ["Overview", "Profiles", "Batches", "Sessions", "Traces"], key="active_tab", on_change="rerun",
    )

    if tab_overview.open:
        with tab_overview:
            render_overview(selected_lang, overview, batches, customers, documents)
    if tab_profiles.open:
        with tab_profiles:
            render_profiles(selected_lang, profiles, customers, batches, documents, traces)
    if tab_batches.open:
        with tab_batches:
            render_batches(selected_lang, batches, documents, customers, traces)
    if tab_sessions.open:
        with tab_sessions:
            render_sessions(selected_lang, sessions)
    if tab_traces.open:
        with tab_traces:
            render_traces(selected_lang, traces, batches)


if __name__ == "__main__":
    main()
