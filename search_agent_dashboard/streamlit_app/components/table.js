export default function(component) {
    const {parentElement, data, setTriggerValue} = component;
    const root = parentElement.querySelector('.table-root');
    for (const [level, color] of Object.entries(data.colors)) {
        root.style.setProperty(`--metric-${level}`, color);
    }
    const abort = new AbortController();
    const listen = (element, type, fn) => element.addEventListener(type, fn, {signal: abort.signal});
    // All dataset strings use textContent, never innerHTML, including model output.
    const node = (tag, text, className) => {
        const element = document.createElement(tag);
        if (text !== undefined && text !== null) element.textContent = String(text);
        if (className) element.className = className;
        return element;
    };
    const fire = (row, kind = 'row', extra = {}) => {
        setTriggerValue('action', {kind, id: row.id, ...extra});
    };
    const activate = (element, fn) => {
        element.tabIndex = 0;
        listen(element, 'click', fn);
        listen(element, 'keydown', event => {
            if (event.target === element && ['Enter', ' '].includes(event.key)) {
                event.preventDefault();
                fn(event);
            }
        });
    };
    const appendValue = (cell, value) => {
        if (value && typeof value === 'object' && 'level' in value) {
            // Python supplies the semantic level and palette from app.py.
            const level = ['good', 'warn', 'bad', 'neutral'].includes(value.level) ? value.level : 'neutral';
            const metric = node('span', value.text, `pill ${level}`);
            metric.title = value.hint;
            metric.dataset.metric = value.metric;
            metric.dataset.level = level;
            cell.append(metric);
        } else {
            cell.textContent = String(value ?? '—');
        }
    };
    const sourceButton = (row) => {
        const button = node('button', 'Open source document →', 'source-link');
        button.type = 'button';
        listen(button, 'click', () => fire(row, 'source'));
        return button;
    };
    const renderSpans = (row, container) => {
        const trace = row.trace;
        const spans = trace.spans ?? [];
        const byParent = new Map();
        const ids = new Set(spans.map(span => span.id));
        for (const span of spans) {
            const parent = ids.has(span.parent_id) ? span.parent_id : null;
            if (!byParent.has(parent)) byParent.set(parent, []);
            byParent.get(parent).push(span);
        }
        const collapsed = new Set(row.collapsed_span_ids ?? []);
        const visited = new Set();
        const renderBranch = (parent, depth) => {
            for (const span of byParent.get(parent) ?? []) {
                if (visited.has(span.id)) continue;
                visited.add(span.id);
                const children = byParent.get(span.id) ?? [];
                const selected = row.selected_span_id === span.id;
                const line = node('div', null, `span-row${selected ? ' selected' : ''}`);
                line.dataset.spanId = span.id;
                line.setAttribute('role', 'button');
                line.setAttribute('aria-label', `Show details for ${span.name}`);
                line.setAttribute('aria-expanded', String(selected));
                line.style.paddingLeft = `${depth * 22 + 8}px`;
                if (children.length) {
                    const disclosure = node('button', collapsed.has(span.id) ? '▸' : '▾', 'disclosure');
                    disclosure.type = 'button';
                    disclosure.setAttribute('aria-label', `${collapsed.has(span.id) ? 'Expand' : 'Collapse'} ${span.name}`);
                    disclosure.setAttribute('aria-expanded', String(!collapsed.has(span.id)));
                    listen(disclosure, 'click', event => {
                        event.stopPropagation();
                        fire(row, 'branch', {span_id: span.id});
                    });
                    line.append(disclosure);
                } else {
                    line.append(node('span', '·', 'leaf'));
                }
                line.append(node('code', span.name, 'span-name'));
                for (const key of ['duration', 'cost', 'status']) {
                    const cell = node('span', null, `span-${key}`);
                    appendValue(cell, span.display_metrics[key]);
                    line.append(cell);
                }
                activate(line, () => fire(row, 'span', {span_id: span.id}));
                container.append(line);
                if (selected) {
                    const detail = node('section', null, 'span-detail');
                    detail.setAttribute('aria-label', `Details for ${span.name}`);
                    detail.append(node('h4', span.name));
                    const summary = node('p', `Span: ${span.id} · Parent: ${span.parent_id ?? 'root'} · `);
                    appendValue(summary, span.display_metrics.duration);
                    summary.append(node('span', ' · Inclusive cost: '));
                    appendValue(summary, span.display_metrics.cost);
                    summary.append(node('span', ' · Self cost: '));
                    appendValue(summary, span.display_metrics.self_cost);
                    if (span.attributes?.faithfulness !== undefined) {
                        summary.append(node('span', ' · Faithfulness: '));
                        appendValue(summary, span.display_metrics.faithfulness);
                    }
                    detail.append(summary);
                    for (const [label, value] of [['Input', span.input], ['Output', span.output], ['Attributes', span.attributes]]) {
                        if (value === undefined) continue;
                        detail.append(node('h5', label));
                        detail.append(node('pre', typeof value === 'string' ? value : JSON.stringify(value, null, 2)));
                    }
                    if (span.attributes?.document_id) detail.append(sourceButton(row));
                    container.append(detail);
                }
                if (!collapsed.has(span.id)) renderBranch(span.id, depth + 1);
            }
        };
        renderBranch(null, 0);
        if (!spans.length) container.append(node('p', 'No span details are available for this trace.'));
        const judge = node('p', 'Judge: faithfulness ', 'muted');
        appendValue(judge, trace.faithfulness_metric);
        judge.append(node('span', ` · ${trace.version}`));
        container.append(judge);
        if (trace.mlflow_url) {
            try {
                const url = new URL(trace.mlflow_url);
                if (['http:', 'https:'].includes(url.protocol)) {
                    const link = node('a', 'Open full tree in MLflow ↗');
                    link.href = url.href;
                    link.target = '_blank';
                    link.rel = 'noopener noreferrer';
                    container.append(link);
                }
            } catch (_) { /* Do not render invalid or executable URLs. */ }
        }
    };

    const wrapper = node('div', null, 'table-scroll');
    const table = node('table');
    table.setAttribute('aria-label', data.label);
    const head = node('thead');
    const header = node('tr');
    for (const column of data.columns) header.append(node('th', column));
    head.append(header);
    table.append(head);
    const body = node('tbody');
    for (const row of data.rows) {
        const line = node('tr', null, `${data.interactive ? 'click-row' : 'metric-table-row'}${row.expanded ? ' selected' : ''}`);
        line.dataset.rowId = row.id;
        if (row.trace) line.setAttribute('aria-expanded', String(Boolean(row.expanded)));
        for (const [index, value] of row.cells.entries()) {
            const cell = node('td');
            if (index === 0 && row.trace) cell.append(node('span', row.expanded ? '▾ ' : '▸ ', 'row-disclosure'));
            const content = node('span');
            appendValue(content, value);
            cell.append(content);
            line.append(cell);
        }
        if (data.interactive) activate(line, () => fire(row));
        body.append(line);
        if (row.expanded && row.trace) {
            const detailRow = node('tr', null, 'trace-detail-row');
            const cell = node('td');
            cell.colSpan = data.columns.length;
            const panel = node('section', null, 'trace-tree');
            panel.setAttribute('aria-label', `Span tree for ${row.id}`);
            panel.append(node('h4', `Trace tree · ${row.id}`));
            panel.append(node('p', 'Click a span row for input/output details. Use the arrows to collapse or expand branches.', 'muted'));
            panel.append(node('p', 'Span costs include children; do not sum parent and child costs. All details are mock data.', 'muted'));
            renderSpans(row, panel);
            cell.append(panel);
            detailRow.append(cell);
            body.append(detailRow);
        }
    }
    table.append(body);
    wrapper.append(table);
    root.replaceChildren(wrapper);
    return () => abort.abort();
}