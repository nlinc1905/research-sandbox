# MyAgent Quality Dashboard

A demo dashboard for evaluating retrieval-augmented generation (RAG) and chat-with-documents agent systems across multiple use cases. The dashboard ingests quality metrics from a data pipeline that processes document batches, extracts retrieval traces, and evaluates session outcomes.

## Overview

**Purpose**: Monitor and troubleshoot agent quality across multiple deployment profiles, customer cohorts, and document batches. Drill into individual traces to inspect retrieval quality, generation faithfulness, and span-level costs and latency. Visualize trends across versions and compare golden-dataset evaluation scores with production session feedback.

**Key features**:
- **Multi-profile evaluation**: Compare agent quality across different deployment variants (e.g., RAG vs. extraction vs. table digitization).
- **Hierarchy drilldown**: Profile → Customer → Batch → Document → Retrieval traces → Span trees.
- **Batch investigation**: Inspect a batch across all its customers, independently of the Profiles drilldown.
- **Metric coloring**: Semantic green/amber/red status for quality scores, latency, costs, and error rates.
- **Language filtering**: Filter all data by language (English, German, or both).
- **Pluggable data sources**: Switch between local JSON, HTTP API, S3, or MLflow artifacts without UI changes.
- **Mock data included**: Fully functional demo with fictional data and agent outputs.

## Getting started

### Quick start (local JSON data)

```bash
cd streamlit_app
pip install -r requirements.txt
streamlit run app.py
```

Open [http://localhost:8501](http://localhost:8501) in your browser.

### Running tests

From the `streamlit_app` directory:

```bash
# Run all tests (navigation, metrics, adapter configuration)
python -m pytest tests/ -v

# Or use unittest directly
python -m unittest discover -s tests -v

# Run a specific test file
python -m unittest tests.test_navigation -v
python -m unittest tests.test_metric_colors -v
python -m unittest tests.test_data_adapter -v
```

### Validating JavaScript

```bash
# Check table component syntax
node --input-type=module --check components/table.js
```

## File and folder structure

```
search_agent_dashboard/
├── README.MD                           # This file
├── databricks_app_scaffold/            # Databricks App config scaffold (entry command + env conventions)
│   ├── app.yaml.example                # Example app config with Streamlit entry command and env keys
│   └── .env.example                    # Environment variable convention template
├── streamlit_app/                      # Main application root
│   ├── app.py                          # Streamlit app entry point; defines all UI logic
│   ├── click_tables.py                 # Wrapper for custom HTML table component
│   ├── data_adapter.py                 # Data source abstraction layer
│   ├── navigation.py                   # Session state and drilldown logic
│   ├── styles.css                      # Custom dark theme and card styling
│   ├── requirements.txt                # Python dependencies (Streamlit 1.67+, pandas, plotly)
│   ├── .streamlit/
│   │   └── config.toml                 # Streamlit theme config; ensures dark palette in both modes
│   ├── components/                     # Custom Streamlit component for clickable tables
│   │   ├── table.js                    # Table rendering and row/span click handling (no checkboxes)
│   │   └── table.css                   # Table styling (dark theme, semantic score colors)
│   ├── data/                           # Mock datasets (or replaced by adapter)
│   │   ├── overview.json               # Global KPIs, operational metrics, version trends
│   │   ├── profiles.json               # Agent deployment profiles with metric snapshots
│   │   ├── customers.json              # Customer/account cohorts and their profiles
│   │   ├── batches.json                # Document processing batches (version-aware)
│   │   ├── documents.json              # Individual documents with chunk/embedding scores
│   │   ├── sessions.json               # Chat sessions with judge snapshots and feedback
│   │   └── traces.json                 # Retrieval traces with nested span trees
│   └── tests/                          # Unit and integration tests
│       ├── test_navigation.py          # Navigation state transitions and validation
│       ├── test_metric_colors.py       # Metric threshold definitions and coloring
│       └── test_data_adapter.py        # Data source adapter routing and config
```

### Key file descriptions

#### `app.py`

Main Streamlit application. Contains:

- **Metric configuration**: METRIC_THRESHOLDS dict defining green/amber/red boundaries for all metrics (chunk score, faithfulness, latency, cost, etc.).
- **Rendering functions**: `render_overview()`, `render_profiles()`, `render_batches()`, `render_sessions()`, `render_traces()`. Profiles and Batches share document tables and diagnostics.
- **Data loading**: Single cached `load_dashboard_data()` call that adapts between JSON/API/S3/MLflow sources without UI changes.
- **Semantic coloring**: Helper functions `metric_cell()`, `category_cell()`, `metric_level()` that apply consistent coloring to cards, tables, and charts.
- **Chart rendering**: `build_metric_trend_chart()` with threshold-aware background bands and point colors.

#### `data_adapter.py`

Abstraction layer for pluggable data sources. Includes:

- **DashboardData**: Frozen dataclass with all dashboard datasets (overview, profiles, customers, batches, documents, sessions, traces).
- **Adapters**:
  - `JsonFileAdapter`: Reads local JSON files (default).
  - `ApiAdapter`: Reads `{base_url}/{dataset}.json` over HTTP with optional bearer token.
  - `S3Adapter`: Reads S3 objects with optional region and prefix.
  - `MlflowArtifactAdapter`: Downloads MLflow artifacts and reads local JSON.
- **Factory**: `create_adapter(config, default_path)` routes by source type; `resolve_adapter_config()` reads environment variables.

#### `navigation.py`

Session state and data validation. Implements:

- **State initialization**: `initialize(state, profile_ids)` sets up default selections.
- **Navigation**: `navigate(state, tab, ...)` updates active tab and drilldown selections (profile → customer → batch → document).
- **Validation**: `validate(state, customers, batches, documents, traces, language)` clears stale selections when language filter hides data.
- **Span state**: Manages `selected_span_id` and `collapsed_span_ids` independently of traces.

#### `click_tables.py`

Wrapper around a custom Streamlit component (JavaScript + CSS) for HTML-style interactive tables. Features:

- **No checkboxes**: Click anywhere on a row to trigger navigation (breadcrumb, drilldown, trace expand).
- **Span trees**: Display trace trees with collapsible branches and selectable spans.
- **Semantic coloring**: Renders score cells with green/amber/red pills and tooltips.
- **Stable IDs**: Uses record IDs (not row indices) for navigation and selection.

#### `components/table.js`

Client-side rendering and interaction:

- **Row activation**: Click or keyboard (Enter/Space) to fire actions.
- **Span trees**: Renders nested spans with disclosure arrows, duration, cost, and status.
- **Metric display**: Applies Python-supplied semantic level (good/warn/bad/neutral) to cells.
- **Source links**: Retrieval spans can link back to their source document in Batches.

#### `components/table.css`

Dark theme styles (colors injected by app.py via CSS custom properties):

- Semantic color classes: `.good`, `.warn`, `.bad`, `.neutral`.
- Span tree layout: Grid with disclosure, name, duration, cost, status columns.
- Table scroll container and cell padding.

#### `styles.css`

Main application styling:

- **Color palette**: Fixed dark theme (no light mode override).
- **Cards**: Metric cards with borders and semantic score coloring.
- **Progress bars**: Neutral gray fill (context only, no directional health).
- **Tabs**: Muted inactive, accent blue active.
- **Widgets**: Streamlit selectbox, input, buttons inherit dark palette.

#### `.streamlit/config.toml`

Streamlit configuration file (must be in hidden `.streamlit` directory):

- **Theme**: Sets `[theme.light]` and `[theme.dark]` to identical colors (dark palette regardless of mode).
- **Plotly**: Uses `theme=None` to preserve muted chart colors.
- **Layout**: Wide mode by default.
- **Required version**: Streamlit 1.67 or newer for theme configuration and custom component API.

#### `data/*.json` (Mock datasets)

Each file represents a database view or pipeline output:

- **overview.json**: Global KPIs (knowledge_base_quality, retrieval_performance, generation_quality), operational metrics (latency, throughput, cost), trends by version, failure attribution.
- **profiles.json**: Agent profiles with golden-dataset evaluation scores and version progression.
- **customers.json**: Customer/account records linked to profiles.
- **batches.json**: Version-aware document batch summaries. The current mock records retain their legacy single-customer ownership; the Batches view does not require that restriction.
- **documents.json**: Individual documents with chunk score, embedding score, hit rate, retrieval count. An optional `customer_id` overrides legacy batch ownership; an optional `version` overrides the batch version. No mixed-customer examples are included yet.
- **sessions.json**: Production chat sessions with judge snapshots (goal completion, sentiment, cost, trace count).
- **traces.json**: Retrieval traces with nested spans; each span includes input, output, timing, cost, attributes (e.g., retrieved chunk ID, faithfulness).

All data is mock. JSON schema is documented by tests and can be extended without UI changes.

#### `tests/`

Unit and integration tests:

- **test_navigation.py**: Validates state transitions, breadcrumb behavior, language filter edge cases.
- **test_metric_colors.py**: Verifies metric thresholds, coloring consistency between cards and charts, invalid value handling.
- **test_data_adapter.py**: Tests adapter routing, config resolution, JSON loading.

## App layout

- `streamlit_app/app.py`: Streamlit UI and interactions.
- `streamlit_app/data_adapter.py`: Source adapter layer (JSON, API, S3, MLflow).
- `streamlit_app/styles.css`: Custom styling using the original HTML's dark palette.
- `streamlit_app/.streamlit/config.toml`: Matching native Streamlit widget/table themes.
- `streamlit_app/data/*.json`: Mock data contract for dashboard content.
- `streamlit_app/requirements.txt`: Python dependencies.

The app intentionally separates UI from data so each JSON source can be replaced over time with real systems (MLflow, S3-derived tables, pipeline API, Unity Catalog views).

## Data source adapter

UI rendering in `app.py` reads one stable `DashboardData` shape from
`data_adapter.py`. To switch data backends, change configuration only; no UI
logic changes are required.

### Supported sources

- `json` (default): reads local `data/*.json` files.
- `api`: reads `{base_url}/{dataset}.json` over HTTP.
- `s3`: reads `{prefix}/{dataset}.json` from S3.
- `mlflow`: reads artifacts directory containing `{dataset}.json` files.

### Configure via environment variables

Common:

- `MyAgent_DATA_SOURCE=json|api|s3|mlflow`

JSON:

- `MyAgent_JSON_DIR=/absolute/path/to/data`

API:

- `MyAgent_API_BASE_URL=https://host/path`
- `MyAgent_API_TOKEN=...` (optional bearer token)
- `MyAgent_API_TIMEOUT_SECONDS=10` (optional)

S3:

- `MyAgent_S3_BUCKET=my-bucket`
- `MyAgent_S3_PREFIX=optional/prefix`
- `MyAgent_S3_REGION=us-east-1` (optional)

MLflow:

- `MyAgent_MLFLOW_ARTIFACT_PATH=runs:/<run_id>/artifacts/<path>`
- `MyAgent_MLFLOW_TRACKING_URI=...` (optional)

Optional dependencies for non-JSON sources are only needed when you select
those sources:

- S3 source: `boto3`
- MLflow source: `mlflow`

## Appearance

The dashboard always uses the original HTML's **dark** palette: charcoal page,
slightly lighter cards, off-white text, muted gray labels, blue accents, and an
amber draft banner/dashed notes. Both Streamlit theme modes use the same colors,
and charts retain their muted series colors. Switching the browser/OS or
Streamlit light/dark setting does not change this palette.

Start Streamlit from the `streamlit_app` directory so it loads `.streamlit/config.toml`. Include that hidden directory when deploying to Databricks Apps. After adding or changing the native theme configuration, stop/restart the Streamlit server and refresh the browser. Streamlit 1.67 or newer is required by the theme configuration and is included in the requirements.

**Theme enforcement**: Both `[theme.light]` and `[theme.dark]` in `config.toml` are set to identical dark colors. This ensures the dashboard always renders in dark mode, regardless of user browser or OS preference.

## Deployment

### Databricks Apps

Use the `streamlit_app` directory as the app source.

Suggested entrypoint: `streamlit run app.py --server.port $PORT --server.address 0.0.0.0`

If your Databricks App template supports `requirements.txt`, keep it as-is; otherwise install dependencies as part of your app build step.

#### Scaffold files included

The repo includes a Databricks App scaffold with an entry command and env conventions:

- `databricks_app_scaffold/app.yaml.example`
- `databricks_app_scaffold/.env.example`

Use it as a starting point:

1. Copy `databricks_app_scaffold/app.yaml.example` into your Databricks App config file.
2. Keep the command aligned with this dashboard entry command:
  `streamlit run streamlit_app/app.py --server.port=$PORT --server.address=0.0.0.0`
3. Set `MyAgent_DATA_SOURCE` and only the companion variables for that source.
4. Store secret values (for example API tokens) in Databricks secret references rather than plaintext.

### Environment configuration

Switch data sources by setting environment variables before launch:

```bash
# Local JSON (default)
export MyAgent_DATA_SOURCE=json
export MyAgent_JSON_DIR=/path/to/data
streamlit run app.py

# HTTP API
export MyAgent_DATA_SOURCE=api
export MyAgent_API_BASE_URL=https://api.example.com/data
export MyAgent_API_TOKEN=secret_token  # optional
export MyAgent_API_TIMEOUT_SECONDS=10  # optional
streamlit run app.py

# S3
export MyAgent_DATA_SOURCE=s3
export MyAgent_S3_BUCKET=my-bucket
export MyAgent_S3_PREFIX=dashboards/prod  # optional
export MyAgent_S3_REGION=us-east-1  # optional
streamlit run app.py

# MLflow artifacts
export MyAgent_DATA_SOURCE=mlflow
export MyAgent_MLFLOW_ARTIFACT_PATH=runs:/run123/artifacts/data
export MyAgent_MLFLOW_TRACKING_URI=https://mlflow.example.com  # optional
streamlit run app.py
```

## Included views

- Overview: global quality, ops metrics, version-aware trend, attribution, low-performing batches.
- Profiles: hierarchy drilldown `profile -> customer -> batch -> document`, with version-specific metrics.
- Batches: customer-independent batch list, ordered by lowest retrieval hit rate, with customer names and version, language, document/page/chunk counts, quality scores, and retrievals. Click a batch for its documents, then a document for shared diagnostics and trace links. Page/chunk totals cover the available language-filtered document records; other batch totals/scores come from the supplied summaries.
- Sessions: experimental tab with mocked chat/session-level judge snapshot and natural-language analysis response.
- Traces: clickable trace rows (with total cost), inline expandable span trees,
  MLflow links, and mocked natural-language analysis responses.

### Click-based drilldowns

Interactive tables are ordinary HTML tables rendered through Streamlit's built-in
component API. There is no checkbox/select column and no additional grid dependency.
Click anywhere on a row, or focus it and press Enter/Space:

- Overview batch row → Batches, at that batch's documents across customers.
- Profile customer → batches → documents → document diagnostics.
- Batches row → all documents in that batch → document diagnostics; customer ownership is shown per document.
- Breadcrumb links → the corresponding parent level.
- Document retrieval row → Traces, with the matching trace expanded.
- Trace row → expand/collapse its tree directly below the row.
- Span row → input, output, attributes, timing, and cost details.
- Span arrow → expand/collapse its child spans.
- Retrieval span's source link → the corresponding document in Batches.

Batches keeps its selection separate from Profiles, so investigating a batch does
not replace the profile/customer drilldown. Both views respect the global language
filter. Profiles restricts document rows to the selected customer; Batches does not.
For shared batches, Profiles derives customer-specific summaries from the available
language-filtered documents (mean chunk/embedding scores, retrieval-weighted hit
rate, and customer-only document/retrieval totals) rather than counting the entire
batch for each customer. Single-customer batches retain their supplied summaries.
Customer names are resolved from each document's optional `customer_id`, falling
back to the batch's legacy `customer_id` only when the document field is absent.
Unknown ownership is shown as an em dash rather than guessed. Existing sample data
is unchanged and still contains only single-customer batches.

Mock spans are structured records in `data/traces.json`, with `id`, `parent_id`,
`name`, `duration_ms`, `cost`, `self_cost`, `status`, `input`, `output`, and
`attributes`. Span `cost` includes descendants; sum `self_cost` (not inclusive
parent/child costs) to reproduce the trace total. All span details are fictional.

The component's JavaScript/CSS assets are in `streamlit_app/components`; include
them with the app source when deploying. Data strings are rendered as text, not
executable HTML. Navigation uses stable record IDs rather than displayed row indices.

Regression tests are in `streamlit_app/tests/test_navigation.py` and use the
standard-library unittest runner (discover tests from the app directory).

## Data pipeline and use cases

The dashboard is designed to ingest outputs from a data pipeline that processes multiple RAG and agent use cases:

1. **RAG knowledge retrieval**: Query documents with semantic search; evaluate precision, recall, faithfulness.
2. **Structured extraction**: Extract fields from documents; measure field-level accuracy and schema validity.
3. **Table and form digitization**: Convert tables/forms to structured data; track cell accuracy and structural integrity.
4. **Session feedback**: Collect chat outcomes, user ratings, and retry/no-answer signals.

For each use case:

- **Golden evaluation** is run on a fixed test set (profiles store versioned scores).
- **Production traces** are logged and sampled for inspection (traces tab shows recent examples).
- **Version tracking** allows comparison across model updates (charts mark version change dates).
- **Multi-language support** tracks performance separately (English/German toggle filters data).

### Data generation

Replace mock JSON with real pipeline outputs:

1. Export overview, profiles, customers, batches, documents, sessions, traces as JSON.
2. Upload to S3 (`MyAgent_DATA_SOURCE=s3`) or serve via API (`MyAgent_DATA_SOURCE=api`).
3. Or store as MLflow artifacts and use `MyAgent_DATA_SOURCE=mlflow`.
4. Restart the app; no code changes required.

## Global filter

Language filter options: `All`, `English`, `German`, applied across all tabs. Filters hide non-matching batches, documents, traces, and sessions; breadcrumb navigation and drilldowns respect the filter.
