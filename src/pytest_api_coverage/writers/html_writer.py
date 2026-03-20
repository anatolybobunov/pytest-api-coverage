"""HTML report writer."""

from __future__ import annotations

import os
import shutil
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from jinja2 import Environment

CSS_STYLES = """
        :root {
            --color-success: #22c55e;
            --color-danger: #ef4444;
            --color-warning: #f59e0b;
            --color-bg: #f8fafc;
            --color-border: #e2e8f0;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: #1e293b;
            background: var(--color-bg);
            margin: 0;
            padding: 20px;
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 8px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            padding: 24px;
        }

        h1 {
            margin: 0 0 24px;
            font-size: 24px;
            font-weight: 600;
        }

        h2 {
            margin: 32px 0 16px;
            font-size: 18px;
            font-weight: 600;
            color: #334155;
            border-bottom: 2px solid var(--color-border);
            padding-bottom: 8px;
        }

        h2.origin-header {
            font-family: monospace;
            font-size: 16px;
            background: var(--color-bg);
            padding: 12px;
            border-radius: 4px;
            margin-top: 24px;
        }

        .summary {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 16px;
            margin-bottom: 32px;
        }

        .summary-card {
            background: var(--color-bg);
            border-radius: 8px;
            padding: 16px;
            text-align: center;
        }

        .summary-card .value {
            font-size: 32px;
            font-weight: 700;
            color: #0f172a;
        }

        .summary-card .label {
            font-size: 14px;
            color: #64748b;
            margin-top: 4px;
        }

        .coverage-bar {
            height: 8px;
            background: var(--color-border);
            border-radius: 4px;
            overflow: hidden;
            margin: 16px 0;
        }

        .coverage-bar .fill {
            height: 100%;
            background: var(--color-success);
            transition: width 0.3s ease;
        }

        .coverage-bar.low .fill { background: var(--color-danger); }
        .coverage-bar.medium .fill { background: var(--color-warning); }

        table {
            width: 100%;
            border-collapse: collapse;
            font-size: 14px;
            border: 1px solid #cbd5e1;
        }

        th, td {
            padding: 12px;
            text-align: left;
            border: 1px solid #cbd5e1;
        }

        th {
            background: var(--color-bg);
            font-weight: 600;
            color: #475569;
            border-bottom: 2px solid #94a3b8;
        }

        tr:hover td {
            background: #f1f5f9;
        }

        .badge {
            display: inline-block;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: 500;
        }

        /* C8: Three coverage states with colors */
        .badge-success { background: #dcfce7; color: #166534; }      /* Green: hit_count > 1 */
        .badge-warning { background: #e9ecef; color: #495057; }      /* Gray: hit_count == 1 */
        .badge-danger { background: #fee2e2; color: #991b1b; }       /* Red: not covered */

        /* Row background colors based on endpoint coverage status */
        tr.covered { background-color: #d4edda; }
        tr.partial-covered { background-color: #fff3cd; }
        tr.not-covered { background-color: #f8d7da; }
        tr.covered:hover td { background-color: #c3e6cb; }
        tr.partial-covered:hover td { background-color: #ffeeba; }
        tr.not-covered:hover td { background-color: #f5c6cb; }

        .badge-partial { background: #fff3cd; color: #856404; }

        /* Filter bar */
        .filter-bar {
            display: flex;
            gap: 8px;
            margin-bottom: 12px;
            flex-wrap: wrap;
        }

        .filter-btn {
            padding: 6px 14px;
            border-radius: 6px;
            border: 1px solid transparent;
            cursor: pointer;
            font-size: 13px;
            font-weight: 500;
            transition: opacity 0.15s;
        }

        .filter-btn:not(.active) {
            opacity: 0.4;
        }

        .filter-btn.filter-covered { background: #d4edda; color: #155724; border-color: #c3e6cb; }
        .filter-btn.filter-partial { background: #fff3cd; color: #856404; border-color: #ffeeba; }
        .filter-btn.filter-not-covered { background: #f8d7da; color: #721c24; border-color: #f5c6cb; }

        .method {
            font-weight: 600;
            font-family: monospace;
        }

        .method-get { color: #059669; }
        .method-post { color: #2563eb; }
        .method-put { color: #d97706; }
        .method-delete { color: #dc2626; }
        .method-patch { color: #7c3aed; }

        .path {
            font-family: monospace;
            color: #475569;
        }

        .response-codes {
            display: flex;
            gap: 4px;
            flex-wrap: wrap;
        }

        .response-code {
            font-family: monospace;
            font-size: 12px;
            padding: 2px 6px;
            border-radius: 4px;
            background: #e2e8f0;
        }

        .response-code.success { background: #dcfce7; }
        .response-code.redirect { background: #fef3c7; }
        .response-code.client-error { background: #fee2e2; }
        .response-code.server-error { background: #fecaca; }

        .footer {
            margin-top: 24px;
            padding-top: 16px;
            border-top: 1px solid var(--color-border);
            font-size: 12px;
            color: #94a3b8;
            text-align: center;
        }

        .origin-section {
            margin-bottom: 32px;
            border: 1px solid var(--color-border);
            border-radius: 8px;
            padding: 16px;
        }

        .origin-summary {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 12px;
            margin-bottom: 16px;
        }

        .origin-summary .summary-card {
            padding: 12px;
        }

        .origin-summary .summary-card .value {
            font-size: 24px;
        }

        /* Sortable headers */
        th.sortable {
            cursor: pointer;
            user-select: none;
            position: relative;
            padding-right: 24px;
        }

        th.sortable:hover {
            background: #e2e8f0;
        }

        th.sortable::after {
            content: '⇅';
            position: absolute;
            right: 8px;
            color: #94a3b8;
            font-size: 12px;
        }

        th.sortable.asc::after {
            content: '↑';
            color: #475569;
        }

        th.sortable.desc::after {
            content: '↓';
            color: #475569;
        }
"""

ENDPOINTS_TABLE_TEMPLATE = """
        <div class="filter-bar">
            <button class="filter-btn filter-covered active" data-filter="covered">
                Covered (<span class="count-covered">0</span>)
            </button>
            <button class="filter-btn filter-partial active" data-filter="partial-covered">
                Partial (<span class="count-partial">0</span>)
            </button>
            <button class="filter-btn filter-not-covered active" data-filter="not-covered">
                Not Covered (<span class="count-not-covered">0</span>)
            </button>
        </div>
        <table class="sortable-table">
            <thead>
                <tr>
                    <th class="sortable" data-sort="path">Path</th>
                    <th class="sortable" data-sort="hit_count">Hit Count</th>
                    <th>Method</th>
                    <th>Method Count</th>
                    <th>Response Codes</th>
                    <th class="sortable" data-sort="status">Status</th>
                </tr>
            </thead>
            <tbody>
                {% for path_data in endpoints %}
                {% set path_class = 'covered' if path_data.all_methods_covered else ('partial-covered' if path_data.is_covered else 'not-covered') %}
                {% set path_status = 2 if path_data.all_methods_covered else (1 if path_data.is_covered else 0) %}
                {% for method in path_data.methods %}
                {% set is_first = loop.first %}
                <tr class="{{ path_class }}" data-path="{{ path_data.path }}" data-hit-count="{{ path_data.hit_count }}" data-path-status="{{ path_status }}" data-group-size="{{ path_data.methods|length }}" data-is-first="{{ 'true' if is_first else 'false' }}">
                    {% if is_first %}
                    <td rowspan="{{ path_data.methods|length }}" class="path">{{ path_data.path }}</td>
                    <td rowspan="{{ path_data.methods|length }}">{{ path_data.hit_count }}</td>
                    {% endif %}
                    <td><span class="method method-{{ method.method|lower }}">{{ method.method }}</span></td>
                    <td>{{ method.hit_count }}</td>
                    <td>
                        <div class="response-codes">
                            {% for code, count in method.response_codes.items()|sort %}
                            {% set code_class = 'success' if code < 300 else ('redirect' if code < 400 else ('client-error' if code < 500 else 'server-error')) %}
                            <span class="response-code {{ code_class }}">{{ code }} ({{ count }})</span>
                            {% endfor %}
                        </div>
                    </td>
                    <td>
                        {% if method.hit_count > 1 %}
                        <span class="badge badge-success">Covered</span>
                        {% elif method.hit_count == 1 %}
                        <span class="badge badge-warning">Once</span>
                        {% else %}
                        <span class="badge badge-danger">Not Covered</span>
                        {% endif %}
                    </td>
                </tr>
                {% endfor %}
                {% endfor %}
            </tbody>
        </table>
"""

SORT_SCRIPT = """
    <script>
    (function() {
        // Helper: collect row groups from a tbody
        function getGroups(tbody) {
            const rows = Array.from(tbody.querySelectorAll('tr'));
            const groups = [];
            let currentGroup = [];
            rows.forEach(function(row) {
                if (row.dataset.isFirst === 'true') {
                    if (currentGroup.length > 0) groups.push(currentGroup);
                    currentGroup = [row];
                } else {
                    currentGroup.push(row);
                }
            });
            if (currentGroup.length > 0) groups.push(currentGroup);
            return groups;
        }

        // Initialize filter bars
        document.querySelectorAll('.filter-bar').forEach(function(bar) {
            const table = bar.nextElementSibling;
            if (!table || !table.classList.contains('sortable-table')) return;
            const tbody = table.querySelector('tbody');

            // Count endpoints by path-status for this table
            const counts = {covered: 0, 'partial-covered': 0, 'not-covered': 0};
            getGroups(tbody).forEach(function(group) {
                const status = parseInt(group[0].dataset.pathStatus, 10);
                if (status === 2) counts['covered']++;
                else if (status === 1) counts['partial-covered']++;
                else counts['not-covered']++;
            });

            bar.querySelector('.count-covered').textContent = counts['covered'];
            bar.querySelector('.count-partial').textContent = counts['partial-covered'];
            bar.querySelector('.count-not-covered').textContent = counts['not-covered'];

            // Filter button click handlers
            bar.querySelectorAll('.filter-btn').forEach(function(btn) {
                btn.addEventListener('click', function() {
                    this.classList.toggle('active');
                    const activeFilters = new Set(
                        Array.from(bar.querySelectorAll('.filter-btn.active'))
                            .map(b => b.dataset.filter)
                    );
                    getGroups(tbody).forEach(function(group) {
                        const status = parseInt(group[0].dataset.pathStatus, 10);
                        const cls = status === 2 ? 'covered' : (status === 1 ? 'partial-covered' : 'not-covered');
                        const visible = activeFilters.has(cls);
                        group.forEach(function(row) {
                            row.style.display = visible ? '' : 'none';
                        });
                    });
                });
            });
        });

        // Sortable tables
        document.querySelectorAll('.sortable-table').forEach(function(table) {
            const headers = table.querySelectorAll('th.sortable');

            headers.forEach(function(header) {
                header.addEventListener('click', function() {
                    const sortKey = this.dataset.sort;
                    const tbody = table.querySelector('tbody');
                    const isAsc = this.classList.contains('asc');

                    // Clear other headers
                    headers.forEach(h => h.classList.remove('asc', 'desc'));
                    this.classList.add(isAsc ? 'desc' : 'asc');

                    const groups = getGroups(tbody);

                    // Sort groups
                    groups.sort(function(a, b) {
                        const rowA = a[0];
                        const rowB = b[0];
                        let valA, valB;

                        if (sortKey === 'path') {
                            valA = rowA.dataset.path.toLowerCase();
                            valB = rowB.dataset.path.toLowerCase();
                            return isAsc ? valB.localeCompare(valA) : valA.localeCompare(valB);
                        } else if (sortKey === 'hit_count') {
                            valA = parseInt(rowA.dataset.hitCount, 10);
                            valB = parseInt(rowB.dataset.hitCount, 10);
                        } else if (sortKey === 'status') {
                            valA = parseInt(rowA.dataset.pathStatus, 10);
                            valB = parseInt(rowB.dataset.pathStatus, 10);
                        }

                        const diff = valA - valB;
                        return isAsc ? -diff : diff;
                    });

                    // Rebuild tbody
                    tbody.innerHTML = '';
                    groups.forEach(function(group) {
                        group.forEach(function(row) {
                            tbody.appendChild(row);
                        });
                    });
                });
            });
        });
    })();
    </script>
"""

HTML_TEMPLATE = (
    """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>API Coverage Report</title>
    <style>"""
    + CSS_STYLES
    + """
    </style>
</head>
<body>
    <div class="container">
        <h1>API Coverage Report</h1>
        {% if swagger_source %}
        <p style="color: #64748b; font-family: monospace; margin-bottom: 24px; word-break: break-all;">
            <strong>Swagger:</strong> {{ swagger_source }}
        </p>
        {% endif %}

        <div class="summary">
            <div class="summary-card">
                <div class="value">{{ "%.1f"|format(summary.coverage_percentage) }}%</div>
                <div class="label">Coverage</div>
            </div>
            <div class="summary-card">
                <div class="value">{{ summary.covered_endpoints }}/{{ summary.total_endpoints }}</div>
                <div class="label">Endpoints Covered</div>
            </div>
            <div class="summary-card">
                <div class="value">{{ summary.total_requests }}</div>
                <div class="label">Total Requests</div>
            </div>
        </div>

        {% set bar_class = 'low' if summary.coverage_percentage < 50 else ('medium' if summary.coverage_percentage < 80 else '') %}
        <div class="coverage-bar {{ bar_class }}">
            <div class="fill" style="width: {{ summary.coverage_percentage }}%"></div>
        </div>

        """
    + ENDPOINTS_TABLE_TEMPLATE
    + """

        <div class="footer">
            Generated on {{ generated_at }} by pytest-api-coverage
        </div>
    </div>
    """
    + SORT_SCRIPT
    + """
</body>
</html>"""
)

HTML_SPLIT_TEMPLATE = (
    """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>API Coverage Report (Split by Origin)</title>
    <style>"""
    + CSS_STYLES
    + """
    </style>
</head>
<body>
    <div class="container">
        <h1>API Coverage Report</h1>
        {% if swagger_source %}
        <p style="color: #64748b; font-family: monospace; margin-bottom: 16px; word-break: break-all;">
            <strong>Swagger:</strong> {{ swagger_source }}
        </p>
        {% endif %}
        <p style="color: #64748b; margin-bottom: 24px;">Split by Origin</p>

        <div class="summary">
            <div class="summary-card">
                <div class="value">{{ "%.1f"|format(combined_summary.coverage_percentage) }}%</div>
                <div class="label">Combined Coverage</div>
            </div>
            <div class="summary-card">
                <div class="value">{{ combined_summary.covered_endpoints }}/{{ combined_summary.total_endpoints }}</div>
                <div class="label">Endpoints Covered</div>
            </div>
            <div class="summary-card">
                <div class="value">{{ combined_summary.total_requests }}</div>
                <div class="label">Total Requests</div>
            </div>
            <div class="summary-card">
                <div class="value">{{ combined_summary.origins_count }}</div>
                <div class="label">Origins</div>
            </div>
        </div>

        {% set bar_class = 'low' if combined_summary.coverage_percentage < 50 else ('medium' if combined_summary.coverage_percentage < 80 else '') %}
        <div class="coverage-bar {{ bar_class }}">
            <div class="fill" style="width: {{ combined_summary.coverage_percentage }}%"></div>
        </div>

        {% for origin, origin_data in origins|dictsort %}
        <section class="origin-section">
            <h2 class="origin-header">{{ origin }}</h2>

            <div class="origin-summary">
                <div class="summary-card">
                    <div class="value">{{ "%.1f"|format(origin_data.summary.coverage_percentage) }}%</div>
                    <div class="label">Coverage</div>
                </div>
                <div class="summary-card">
                    <div class="value">{{ origin_data.summary.covered_endpoints }}/{{ origin_data.summary.total_endpoints }}</div>
                    <div class="label">Endpoints</div>
                </div>
                <div class="summary-card">
                    <div class="value">{{ origin_data.summary.total_requests }}</div>
                    <div class="label">Requests</div>
                </div>
            </div>

            {% set endpoints = origin_data.endpoints %}
            """
    + ENDPOINTS_TABLE_TEMPLATE
    + """
        </section>
        {% endfor %}

        <div class="footer">
            Generated on {{ generated_at }} by pytest-api-coverage
        </div>
    </div>
    """
    + SORT_SCRIPT
    + """
</body>
</html>"""
)


class HtmlWriter:
    """Writes coverage report as HTML file."""

    @classmethod
    def write(cls, report_data: dict[str, Any], output_path: str | Path) -> Path:
        """Write coverage report as HTML file.

        Args:
            report_data: Coverage report dictionary
            output_path: Destination file path

        Returns:
            Path to written file
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        html_content = cls._render(report_data)

        # Atomic write
        fd, temp_path = tempfile.mkstemp(
            suffix=".html",
            dir=output_path.parent,
        )

        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(html_content)
            shutil.move(temp_path, output_path)
        except Exception:
            Path(temp_path).unlink(missing_ok=True)
            raise

        return output_path

    @classmethod
    def write_string(cls, report_data: dict[str, Any]) -> str:
        """Serialize report data to HTML string.

        Args:
            report_data: Coverage report dictionary

        Returns:
            HTML string
        """
        return cls._render(report_data)

    @classmethod
    def _render(cls, report_data: dict[str, Any]) -> str:
        """Render report data to HTML string."""
        generated_at = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")

        env = Environment(autoescape=True)

        if report_data.get("split_by_origin"):
            template = env.from_string(HTML_SPLIT_TEMPLATE)
            return template.render(
                swagger_source=report_data.get("swagger_source", ""),
                combined_summary=report_data.get("combined_summary", {}),
                origins=report_data.get("origins", {}),
                generated_at=generated_at,
            )

        template = env.from_string(HTML_TEMPLATE)
        return template.render(
            swagger_source=report_data.get("swagger_source", ""),
            summary=report_data.get("summary", {}),
            endpoints=report_data.get("endpoints", []),
            generated_at=generated_at,
        )
