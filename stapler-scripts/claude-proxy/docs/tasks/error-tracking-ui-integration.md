# Error Tracking UI Integration

**Status**: Planning Complete | **Created**: 2026-04-16

---

## Epic Overview

### User Value

Enable proxy operators to view, search, and troubleshoot recurring errors through an integrated dashboard UI with deep linking from macOS notifications directly to specific error details.

**Problem Solved**: Currently, error notifications appear in macOS but require manual log searching to find details. Errors are difficult to track, triage, or analyze for patterns.

### Success Metrics

- **Usability**: User can navigate from notification to error detail in <5 seconds
- **Visibility**: All error types visible in dashboard with occurrence counts
- **Searchability**: Filter errors by provider, type, date range in <2 seconds
- **Reliability**: Deep links work 100% of the time (no broken fragment routes)

### Scope

**Included**:
- Backend API endpoints for error list and detail
- Frontend error list view with filtering/search
- Frontend error detail view with occurrence timeline
- URL fragment routing for deep linking
- Notification enhancements with fingerprint

**Excluded**:
- Real-time WebSocket updates (use polling like existing dashboard)
- Error occurrence pagination (MVP shows last 100)
- CSV export functionality (future enhancement)
- External notification services (Slack, PagerDuty)

### Constraints

- **Technology**: Vanilla JavaScript only (no React, Vue, Angular)
- **Database**: SQLite (no migration to PostgreSQL)
- **Notifications**: macOS `osascript` (terminal-notifier optional)
- **Pattern**: Single-file dashboard HTML embedded in FastAPI response
- **Authentication**: Same Bearer token as existing dashboard

---

## Architecture Decisions

### ADR-001: URL Fragment Routing

**Decision**: Use URL fragment routing (`#error/<fingerprint>`) with vanilla JavaScript.

**Rationale**:
- No server-side routing changes needed
- Notifications link directly: `http://localhost:47000/dashboard#error/abc123`
- Browser handles fragment navigation automatically
- Maintains existing single-file dashboard pattern
- No external dependencies

**Consequences**:
- Cannot use SSR for error detail views
- Browser back/forward require careful `popstate` handling
- SEO not applicable (internal tool)

### ADR-002: API Endpoint Design

**Decision**: Add RESTful endpoints `/api/errors` (list) and `/api/errors/{fingerprint}` (detail).

**Rationale**:
- Matches existing `/metrics` pattern
- Leverages existing ErrorTracker methods
- Separate concerns: list (summary) vs detail (with occurrences)
- No authentication needed (same security model)

**Implementation**:
```python
GET /api/errors?provider=bedrock&since=2026-04-15&limit=100
GET /api/errors/{fingerprint}
```

### ADR-003: Notification Deep Linking

**Decision**: Include short fingerprint in notification message, support `terminal-notifier` for clickable URLs (optional).

**Rationale**:
- Native `osascript` doesn't support clickable URLs
- Short fingerprint (8 chars) allows manual navigation
- `terminal-notifier` provides better UX when installed (brew install)
- Graceful fallback to `osascript` when not available

**Limitation**: macOS notifications don't support clickable URLs natively.

### ADR-004: UI Component Structure

**Decision**: Single-page app with two views: dashboard (default) and error-detail (overlay).

**Views**:
1. **Dashboard View**: Existing metrics + enhanced error list
2. **Error Detail View**: Full error summary + occurrence timeline

**State Management**:
```javascript
let currentView = 'dashboard' | 'error-detail';
let currentFingerprint = null;
```

### ADR-005: Filtering Strategy

**Decision**: Client-side filtering initially, server-side as future enhancement.

**Rationale**:
- Simple implementation (no server-side query changes)
- Works well for <1000 errors (typical load)
- Can upgrade to server-side filtering if performance degrades

**Filters**:
- Provider dropdown (anthropic, bedrock, all)
- Error type dropdown (ValidationException, etc.)
- Date range buttons (24h, 7d, 30d, all)
- Search box (error message text)

---

## Story Breakdown

### Story 5: Backend API Endpoints [4-5 hours]

**User Value**: Expose error tracking data via REST API for dashboard consumption.

**Acceptance Criteria**:
- ✅ `/api/errors` returns list of error types with counts
- ✅ `/api/errors?provider=bedrock` filters by provider
- ✅ `/api/errors/{fingerprint}` returns error detail + occurrences
- ✅ API returns 404 for invalid fingerprints
- ✅ Response schemas match ErrorTracker data structures

#### Task 5.1: Add `/api/errors` list endpoint [1-2h]

**Objective**: Create API endpoint to list all error types with summary data.

**Files**:
- `main.py` (+30 lines)

**Implementation**:
```python
@app.get("/api/errors")
async def list_errors(
    provider: Optional[str] = None,
    since: Optional[str] = None,
    limit: int = 100
):
    errors = error_tracker.search_errors(provider, since, limit)
    return JSONResponse({"errors": errors})
```

**Testing**:
- `curl http://localhost:47000/api/errors` → all errors
- `curl http://localhost:47000/api/errors?provider=bedrock` → filtered
- `curl http://localhost:47000/api/errors?limit=10` → limited

**Validation**: Response includes fingerprint, provider, error_type, count, first_seen, last_seen

#### Task 5.2: Add `/api/errors/{fingerprint}` detail endpoint [1-2h]

**Objective**: Create API endpoint to retrieve error detail with occurrences.

**Files**:
- `main.py` (+40 lines)

**Implementation**:
```python
@app.get("/api/errors/{fingerprint}")
async def get_error_detail(fingerprint: str):
    error = error_tracker.get_error_by_fingerprint(fingerprint)
    if not error:
        raise HTTPException(404, "Error not found")

    occurrences = error_tracker.get_error_occurrences(fingerprint, limit=100)
    return JSONResponse({"error": error, "occurrences": occurrences})
```

**Testing**:
- Generate error, capture fingerprint
- `curl http://localhost:47000/api/errors/<fingerprint>` → error + occurrences
- `curl http://localhost:47000/api/errors/invalid` → 404

**Validation**: Response includes error summary + list of occurrences (timestamp, request_id, model, context)

#### Task 5.3: Add helper method for occurrences [1h]

**Objective**: Refactor occurrence retrieval into ErrorTracker helper method.

**Files**:
- `error_tracker.py` (+25 lines)

**Implementation**:
```python
def get_error_occurrences(self, fingerprint: str, limit: int = 100) -> List[Dict[str, Any]]:
    """Retrieve error occurrences for a given fingerprint."""
    conn = sqlite3.connect(self.db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM error_occurrences
        WHERE fingerprint = ?
        ORDER BY timestamp DESC
        LIMIT ?
    """, (fingerprint, limit))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]
```

**Testing**:
- Record 5 errors with same fingerprint
- Call method, verify 5 occurrences returned
- Test limit=2, verify only 2 returned

**Validation**: Returns list of dicts with keys: id, fingerprint, timestamp, request_id, model, context

---

### Story 6: Frontend Error List View [4-6 hours]

**User Value**: View all error types in dashboard with filtering and search capabilities.

**Acceptance Criteria**:
- ✅ Dashboard shows "All Error Types" section with full list
- ✅ Filter by provider (anthropic, bedrock, all)
- ✅ Filter by error type (ValidationException, etc.)
- ✅ Filter by date range (24h, 7d, 30d, all)
- ✅ Search by error message text (case-insensitive)
- ✅ "View Details" link navigates to `#error/<fingerprint>`

#### Task 6.1: Add error list section to dashboard [2-3h]

**Objective**: Replace "Recent Errors" table with full error list view with filters.

**Files**:
- `main.py` (DASHBOARD_HTML section, +150 lines)

**Implementation**:
- Replace "Recent Errors" table with "All Error Types" section
- Add filter controls: provider dropdown, error type dropdown, date range buttons
- Fetch `/api/errors` on page load, store in `allErrors` array
- Render error list table: Error Type, Provider, Message, First Seen, Last Seen, Count
- Add "View Details" link in each row (`#error/<fingerprint>`)
- Apply client-side filtering when controls change

**Testing**:
- Generate 5 different error types
- Reload dashboard, verify all 5 errors appear
- Filter by provider=bedrock, verify anthropic errors hidden
- Click "View Details", verify URL changes

**Validation**: Error list shows all types with correct counts, filters work, links navigate

#### Task 6.2: Implement client-side filtering logic [1-2h]

**Objective**: Filter error list by provider, error type, and date range.

**Files**:
- `main.py` (DASHBOARD_HTML JavaScript, +80 lines)

**Implementation**:
```javascript
let allErrors = [];  // Fetched from /api/errors
let filters = { provider: 'all', errorType: 'all', dateRange: 'all' };

function applyFilters() {
    const filtered = allErrors.filter(err => {
        if (filters.provider !== 'all' && err.provider !== filters.provider) return false;
        if (filters.errorType !== 'all' && err.error_type !== filters.errorType) return false;
        if (filters.dateRange !== 'all') {
            const cutoff = getDateCutoff(filters.dateRange);
            if (new Date(err.last_seen) < cutoff) return false;
        }
        return true;
    });
    renderErrorList(filtered);
}
```

**Testing**:
- Generate errors with different providers and types
- Apply each filter, verify correct errors shown
- Combine filters, verify intersection works

**Validation**: Filters reduce error list correctly, "No errors" message when all excluded

#### Task 6.3: Add search box for error message text [1h]

**Objective**: Enable full-text search of error messages.

**Files**:
- `main.py` (DASHBOARD_HTML section, +40 lines)

**Implementation**:
- Add text input: "Search error messages"
- On input change, filter by message substring (case-insensitive)
- Combine with existing filters

**Testing**:
- Search for "context_management", verify error appears
- Search for "invalid", verify no results
- Combine search + provider filter

**Validation**: Search filters by message content, case-insensitive, combines with filters

---

### Story 7: Frontend Error Detail View [4-7 hours]

**User Value**: View detailed error information with occurrence timeline via deep link.

**Acceptance Criteria**:
- ✅ Navigate to `#error/<fingerprint>` shows error detail view
- ✅ Detail view shows error summary (type, provider, message, counts)
- ✅ Detail view shows occurrence timeline (timestamp, request_id, model)
- ✅ "Back to Dashboard" button returns to dashboard view
- ✅ Browser back/forward buttons work correctly
- ✅ Auto-refresh pauses while viewing detail

#### Task 7.1: Implement URL fragment routing [1-2h]

**Objective**: Enable client-side routing via URL fragments.

**Files**:
- `main.py` (DASHBOARD_HTML JavaScript, +60 lines)

**Implementation**:
```javascript
let currentView = 'dashboard';
let currentFingerprint = null;

window.addEventListener('hashchange', handleRoute);
window.addEventListener('popstate', handleRoute);
window.addEventListener('load', handleRoute);

function handleRoute() {
    const hash = window.location.hash;
    if (hash.startsWith('#error/')) {
        showErrorDetail(hash.slice(7));
    } else {
        showDashboard();
    }
}

function showDashboard() {
    currentView = 'dashboard';
    document.getElementById('dashboard-view').style.display = 'block';
    document.getElementById('error-detail-view').style.display = 'none';
    startAutoRefresh();
}

function showErrorDetail(fingerprint) {
    currentView = 'error-detail';
    document.getElementById('dashboard-view').style.display = 'none';
    document.getElementById('error-detail-view').style.display = 'block';
    stopAutoRefresh();
    fetchAndRenderErrorDetail(fingerprint);
}
```

**Testing**:
- Navigate to `#error/abc123`, verify detail view shown
- Click browser back, verify dashboard shown
- Navigate to dashboard, verify URL is `#`

**Validation**: URL routing works, back/forward work, auto-refresh pauses in detail view

#### Task 7.2: Create error detail view HTML/CSS [2-3h]

**Objective**: Design and implement error detail view UI.

**Files**:
- `main.py` (DASHBOARD_HTML section, +200 lines)

**Implementation**:
- Add `<div id="error-detail-view">` container (hidden by default)
- Header: Back button, error type, provider badge, fingerprint
- Summary: Error message, first seen, last seen, count
- Occurrences timeline: Table with timestamp, request_id, model, context
- Loading state: Spinner while fetching
- Error state: "Error not found" message

**CSS**:
- Match dashboard dark theme (#0a0a0a, #1a1a1a)
- Back button: Left arrow + "Back to Dashboard"
- Provider badge: Colored like existing error type badges
- Timeline: Reverse chronological, alternating rows

**Testing**:
- Navigate to error detail, verify correct styling
- Navigate to invalid fingerprint, verify "Error not found"

**Validation**: Detail view matches dashboard theme, all components render correctly

#### Task 7.3: Fetch and render error detail data [1-2h]

**Objective**: Fetch error detail from API and populate UI.

**Files**:
- `main.py` (DASHBOARD_HTML JavaScript, +100 lines)

**Implementation**:
```javascript
async function fetchAndRenderErrorDetail(fingerprint) {
    showLoadingState();

    try {
        const response = await fetch(`/api/errors/${fingerprint}`);
        if (!response.ok) {
            showErrorState(response.status === 404 ? 'Error not found' : 'Failed to load');
            return;
        }

        const data = await response.json();
        renderErrorDetailView(data.error, data.occurrences);
    } catch (err) {
        showErrorState('Network error');
    }
}

function renderErrorDetailView(error, occurrences) {
    // Populate error summary
    document.getElementById('detail-error-type').textContent = error.error_type;
    // ... populate all fields

    // Render occurrences timeline
    const tbody = document.getElementById('occurrences-body');
    tbody.innerHTML = occurrences.map(occ => `<tr>
        <td>${new Date(occ.timestamp).toLocaleString()}</td>
        <td>${occ.request_id || '—'}</td>
        <td>${occ.model || '—'}</td>
    </tr>`).join('');
}
```

**Testing**:
- Generate error with 3 occurrences
- Navigate to detail, verify count=3
- Verify occurrences table shows 3 rows with timestamps

**Validation**: Detail view populates correctly, occurrences in reverse chronological order

---

### Story 8: Notification Deep Linking Enhancement [3-4 hours]

**User Value**: Click notification to navigate directly to error detail in dashboard.

**Acceptance Criteria**:
- ✅ Notification includes short fingerprint (8 chars) for manual lookup
- ✅ (Optional) Notification clickable via terminal-notifier

#### Task 8.1: Update notification to include fingerprint [30min]

**Objective**: Include short fingerprint in notification message for manual navigation.

**Files**:
- `error_tracker.py` (+5 lines)

**Implementation**:
```python
def send_desktop_notification(self, fingerprint: str, signature: Dict[str, str]) -> None:
    title = f"New Error: {signature['provider']}"
    message = f"{signature['error_type']}: {signature['message'][:80]}\n(ID: {fingerprint[:8]})"

    subprocess.run(
        ['osascript', '-e', f'display notification "{message}" with title "{title}"'],
        timeout=2, capture_output=True, text=True
    )
```

**Testing**:
- Trigger new error, verify notification shows fingerprint
- Copy fingerprint, navigate to `#error/<fingerprint>`

**Validation**: Notification shows 8-char fingerprint, manual navigation works

#### Task 8.2: Add terminal-notifier support (optional) [2-3h]

**Objective**: Enable clickable notifications when terminal-notifier installed.

**Files**:
- `error_tracker.py` (+40 lines)

**Implementation**:
```python
def send_desktop_notification(self, fingerprint: str, signature: Dict[str, str]) -> None:
    title = f"New Error: {signature['provider']}"
    message = f"{signature['error_type']}: {signature['message'][:100]}"
    url = f"http://localhost:47000/dashboard#error/{fingerprint}"

    # Try terminal-notifier first
    try:
        result = subprocess.run(
            ['terminal-notifier', '-title', title, '-message', message,
             '-open', url, '-group', 'claude-proxy-errors'],
            timeout=2, capture_output=True
        )
        if result.returncode == 0:
            return
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass  # Fallback to osascript

    # Fallback: osascript
    subprocess.run(['osascript', '-e', f'display notification "{message}" with title "{title}"'])
```

**Installation**: `brew install terminal-notifier`

**Testing**:
- Install terminal-notifier, trigger error, click notification
- Verify browser opens to error detail
- Uninstall terminal-notifier, verify fallback works

**Validation**: Clickable when installed, graceful fallback to osascript

---

### Story 9: CLI Query Commands [2-3 hours]

**User Value**: Query error tracking data from command line for scripting and automation.

**Acceptance Criteria**:
- ✅ `claude-proxy-errors list` shows all error types
- ✅ `claude-proxy-errors list --provider bedrock` filters by provider
- ✅ `claude-proxy-errors show <fingerprint>` shows error detail with occurrences
- ✅ `claude-proxy-errors stats` shows summary statistics (total errors, by provider, by type)
- ✅ Commands output formatted tables (use Rich library)

#### Task 9.1: Create CLI entry point script [1h]

**Objective**: Create command-line interface for error tracking queries.

**Files**:
- `cli_errors.py` (new file, +150 lines)
- `requirements.txt` (+1 line: `rich`)

**Implementation**:
```python
#!/usr/bin/env python3
"""CLI for querying error tracking database."""
import argparse
import sys
from pathlib import Path
from rich.console import Console
from rich.table import Table
from error_tracker import ErrorTracker

def main():
    parser = argparse.ArgumentParser(description='Query claude-proxy error tracking')
    subparsers = parser.add_subparsers(dest='command', help='Command')

    # List command
    list_parser = subparsers.add_parser('list', help='List all error types')
    list_parser.add_argument('--provider', help='Filter by provider')
    list_parser.add_argument('--limit', type=int, default=100, help='Max results')

    # Show command
    show_parser = subparsers.add_parser('show', help='Show error detail')
    show_parser.add_argument('fingerprint', help='Error fingerprint')

    # Stats command
    subparsers.add_parser('stats', help='Show summary statistics')

    args = parser.parse_args()

    tracker = ErrorTracker()
    console = Console()

    if args.command == 'list':
        list_errors(tracker, console, args.provider, args.limit)
    elif args.command == 'show':
        show_error(tracker, console, args.fingerprint)
    elif args.command == 'stats':
        show_stats(tracker, console)
    else:
        parser.print_help()

if __name__ == '__main__':
    main()
```

**Testing**:
- `python cli_errors.py list` → shows all errors
- `python cli_errors.py list --provider bedrock` → filtered
- `python cli_errors.py show <fingerprint>` → error detail
- `python cli_errors.py stats` → statistics

**Validation**: CLI script runs, all subcommands work, Rich tables format correctly

#### Task 9.2: Implement list command with Rich formatting [1h]

**Objective**: Display error list as formatted table.

**Files**:
- `cli_errors.py` (+50 lines)

**Implementation**:
```python
def list_errors(tracker, console, provider=None, limit=100):
    """Display error types as formatted table."""
    errors = tracker.search_errors(provider=provider, limit=limit)

    if not errors:
        console.print("[yellow]No errors found[/yellow]")
        return

    table = Table(title=f"Error Types ({len(errors)} total)")
    table.add_column("Fingerprint", style="cyan", no_wrap=True)
    table.add_column("Provider", style="magenta")
    table.add_column("Error Type", style="red")
    table.add_column("Message", style="white")
    table.add_column("Count", justify="right", style="green")
    table.add_column("Last Seen", style="dim")

    for err in errors:
        table.add_row(
            err['fingerprint'][:8],
            err['provider'],
            err['error_type'],
            err['message'][:50] + '...' if len(err['message']) > 50 else err['message'],
            str(err['count']),
            err['last_seen'][:10]  # Date only
        )

    console.print(table)
```

**Testing**:
- Generate 5 different errors
- Run `python cli_errors.py list`
- Verify Rich table with 5 rows
- Verify columns: fingerprint (8 chars), provider, error_type, message (truncated), count, last_seen

**Validation**: Table formatted correctly, colors applied, data accurate

#### Task 9.3: Implement show command with occurrence details [1h]

**Objective**: Display error detail with occurrence timeline.

**Files**:
- `cli_errors.py` (+80 lines)

**Implementation**:
```python
def show_error(tracker, console, fingerprint):
    """Display error detail with occurrences."""
    error = tracker.get_error_by_fingerprint(fingerprint)

    if not error:
        console.print(f"[red]Error not found: {fingerprint}[/red]")
        sys.exit(1)

    # Error summary
    console.print(f"\n[bold cyan]Error Details[/bold cyan]")
    console.print(f"Fingerprint: {error['fingerprint']}")
    console.print(f"Provider: {error['provider']}")
    console.print(f"Operation: {error['operation']}")
    console.print(f"Error Type: [red]{error['error_type']}[/red]")
    console.print(f"Message: {error['message']}")
    console.print(f"First Seen: {error['first_seen']}")
    console.print(f"Last Seen: {error['last_seen']}")
    console.print(f"Occurrence Count: [green]{error['count']}[/green]")

    # Occurrences table
    occurrences = tracker.get_error_occurrences(fingerprint, limit=50)

    if occurrences:
        console.print(f"\n[bold cyan]Recent Occurrences ({len(occurrences)} shown)[/bold cyan]")
        table = Table()
        table.add_column("Timestamp", style="dim")
        table.add_column("Request ID", style="cyan")
        table.add_column("Model", style="magenta")

        for occ in occurrences:
            table.add_row(
                occ['timestamp'],
                occ.get('request_id', '—'),
                occ.get('model', '—')
            )

        console.print(table)
```

**Testing**:
- Generate error with 3 occurrences
- Capture fingerprint
- Run `python cli_errors.py show <fingerprint>`
- Verify error summary + occurrences table

**Validation**: Error detail displays correctly, occurrences table shows all data

---

### Story 10: Export Functionality [2-3 hours]

**User Value**: Export error data to CSV for analysis in spreadsheet tools or external systems.

**Acceptance Criteria**:
- ✅ `claude-proxy-errors export --format csv` exports error list to CSV
- ✅ `claude-proxy-errors export <fingerprint> --format csv` exports occurrences to CSV
- ✅ CSV includes all relevant fields (fingerprint, provider, error_type, message, count, timestamps)
- ✅ Output to stdout (pipe-able) or file via `--output` flag
- ✅ JSON export format also supported

#### Task 10.1: Add export command to CLI [1h]

**Objective**: Add export subcommand with format options.

**Files**:
- `cli_errors.py` (+100 lines)

**Implementation**:
```python
# In main()
export_parser = subparsers.add_parser('export', help='Export error data')
export_parser.add_argument('fingerprint', nargs='?', help='Export specific error occurrences')
export_parser.add_argument('--format', choices=['csv', 'json'], default='csv', help='Output format')
export_parser.add_argument('--output', '-o', help='Output file (default: stdout)')
export_parser.add_argument('--provider', help='Filter by provider')
export_parser.add_argument('--limit', type=int, default=1000, help='Max records')

# Handler
elif args.command == 'export':
    export_errors(tracker, args.fingerprint, args.format, args.output, args.provider, args.limit)
```

**Testing**:
- `python cli_errors.py export --format csv` → CSV to stdout
- `python cli_errors.py export --output errors.csv` → CSV to file
- `python cli_errors.py export <fingerprint> --format json` → JSON occurrences

**Validation**: Export command accepts all flags, validates format/output

#### Task 10.2: Implement CSV export logic [1-2h]

**Objective**: Export error data to CSV format.

**Files**:
- `cli_errors.py` (+80 lines)

**Implementation**:
```python
import csv
import json
from io import StringIO

def export_errors(tracker, fingerprint, format, output_file, provider, limit):
    """Export error data to CSV or JSON."""
    if fingerprint:
        # Export occurrences for specific error
        error = tracker.get_error_by_fingerprint(fingerprint)
        if not error:
            print(f"Error not found: {fingerprint}", file=sys.stderr)
            sys.exit(1)

        occurrences = tracker.get_error_occurrences(fingerprint, limit=limit)
        data = occurrences
        fieldnames = ['id', 'fingerprint', 'timestamp', 'request_id', 'model', 'full_message']
    else:
        # Export error types list
        errors = tracker.search_errors(provider=provider, limit=limit)
        data = errors
        fieldnames = ['fingerprint', 'provider', 'operation', 'error_type', 'message',
                      'first_seen', 'last_seen', 'count']

    if format == 'csv':
        output = StringIO() if output_file is None else open(output_file, 'w', newline='')
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)

        if output_file is None:
            print(output.getvalue())
        else:
            output.close()
            print(f"Exported {len(data)} records to {output_file}", file=sys.stderr)

    elif format == 'json':
        output = sys.stdout if output_file is None else open(output_file, 'w')
        json.dump(data, output, indent=2)
        if output_file:
            output.close()
            print(f"Exported {len(data)} records to {output_file}", file=sys.stderr)
```

**Testing**:
- Generate 10 errors
- `python cli_errors.py export --format csv > errors.csv`
- Open errors.csv, verify all fields present
- `python cli_errors.py export <fingerprint> --format json > occurrences.json`
- Verify JSON structure correct

**Validation**: CSV/JSON output valid, all fields included, pipe-able to stdout

#### Task 10.3: Add stats command for summary statistics [30min]

**Objective**: Display aggregate statistics about error types.

**Files**:
- `cli_errors.py` (+50 lines)

**Implementation**:
```python
def show_stats(tracker, console):
    """Display summary statistics."""
    errors = tracker.search_errors(limit=10000)  # Get all

    if not errors:
        console.print("[yellow]No errors found[/yellow]")
        return

    # Aggregate stats
    total_errors = len(errors)
    total_occurrences = sum(e['count'] for e in errors)
    by_provider = {}
    by_type = {}

    for err in errors:
        provider = err['provider']
        error_type = err['error_type']

        by_provider[provider] = by_provider.get(provider, 0) + err['count']
        by_type[error_type] = by_type.get(error_type, 0) + err['count']

    # Display summary
    console.print(f"\n[bold cyan]Error Tracking Statistics[/bold cyan]")
    console.print(f"Total Error Types: {total_errors}")
    console.print(f"Total Occurrences: {total_occurrences}")

    # By provider table
    table = Table(title="Occurrences by Provider")
    table.add_column("Provider", style="magenta")
    table.add_column("Count", justify="right", style="green")
    for provider, count in sorted(by_provider.items(), key=lambda x: x[1], reverse=True):
        table.add_row(provider, str(count))
    console.print(table)

    # By error type table
    table = Table(title="Top 10 Error Types")
    table.add_column("Error Type", style="red")
    table.add_column("Count", justify="right", style="green")
    for error_type, count in sorted(by_type.items(), key=lambda x: x[1], reverse=True)[:10]:
        table.add_row(error_type, str(count))
    console.print(table)
```

**Testing**:
- Generate errors: 5 bedrock ValidationException, 3 anthropic RateLimitError
- Run `python cli_errors.py stats`
- Verify totals correct
- Verify by-provider table shows bedrock=5, anthropic=3
- Verify by-type table shows ValidationException=5, RateLimitError=3

**Validation**: Statistics accurate, tables formatted correctly, top 10 error types shown

---

## Known Issues

### Bug-001: Race Condition in Error Occurrence Count [SEVERITY: Low]

**Description**: High-concurrency error logging may cause incorrect occurrence counts.

**Mitigation**: Already mitigated via SQLite WAL mode + atomic `UPDATE ... SET count = count + 1`

**Prevention**: Add concurrency test (10 threads, 10 errors each, verify count=100)

### Bug-002: URL Fragment Deep Link Breaks Auto-Refresh [SEVERITY: Medium]

**Description**: Dashboard auto-refresh continues while viewing error detail.

**Mitigation**:
```javascript
function loadMetrics() {
    if (currentView !== 'dashboard') return;  // Skip when viewing detail
    // ... refresh logic
}
```

**Prevention**: Pause auto-refresh when `currentView !== 'dashboard'`

### Bug-003: Notification Fingerprint Truncation [SEVERITY: Low]

**Description**: Long error_type may truncate meaningful message content.

**Mitigation**: Include fingerprint in subtitle, truncate message to 80 chars

### Bug-004: Browser Back Button State Desync [SEVERITY: Medium]

**Description**: Browser back button may not trigger view updates.

**Mitigation**: Use both `hashchange` and `popstate` event listeners

### Bug-005: Invalid Fingerprint in URL Fragment [SEVERITY: Low]

**Description**: User may manually edit URL to invalid fingerprint.

**Mitigation**: Show "Error not found" message with "Back to Dashboard" button

### Bug-006: SQLite Database Lock Contention [SEVERITY: Medium]

**Description**: High-concurrency API queries + error logging may cause SQLITE_BUSY errors.

**Mitigation**: WAL mode enabled, consider retry logic with exponential backoff if contention detected

---

## Dependency Visualization

```
Story 5 (Backend API):
  5.1 [/api/errors] → 5.2 [/api/errors/{fp}] → 5.3 [Helper method]
  ↓
Story 6 (Error List):
  6.1 [Error list UI] → 6.2 [Filtering] → 6.3 [Search]
  ↓
Story 7 (Error Detail):
  7.1 [URL routing] → 7.2 [Detail HTML] → 7.3 [Fetch logic]
  ↓
Story 8 (Notifications):
  8.1 [Fingerprint in notification] → 8.2 [terminal-notifier (optional)]

Story 9 (CLI Commands) [Independent]:
  9.1 [CLI entry point] → 9.2 [List command] → 9.3 [Show command]

Story 10 (Export) [Depends on Story 9]:
  10.1 [Export command] → 10.2 [CSV export] → 10.3 [Stats command]
```

**Critical Path (Web UI)**:
1. 5.1 → 6.1 (API before UI)
2. 6.1 → 7.1 (List before detail routing)
3. 7.1 → 7.2 (Routing before detail UI)
4. 5.2 → 7.3 (API before detail fetch)

**Independent Paths**:
- Stories 9-10 (CLI) can be implemented in parallel with Stories 5-8 (Web UI)
- Both use ErrorTracker directly (no API dependency)

---

## Integration Checkpoints

### Checkpoint 1: After Story 5 (Backend API)

**Verify**:
- `/api/errors` returns error list with correct schema
- `/api/errors/{fingerprint}` returns error detail + occurrences
- API returns 404 for invalid fingerprints
- ErrorTracker.get_error_occurrences helper works correctly

**Test**:
```bash
curl http://localhost:47000/api/errors
curl http://localhost:47000/api/errors?provider=bedrock
curl http://localhost:47000/api/errors/<valid-fingerprint>
curl http://localhost:47000/api/errors/invalid  # Should return 404
```

### Checkpoint 2: After Story 6 (Error List View)

**Verify**:
- Dashboard shows full error list (not just recent 4)
- Filters work: provider, error type, date range
- Search box filters by message text
- "View Details" link changes URL to `#error/<fingerprint>`
- Filters combine correctly (intersection)

**Test**:
- Generate 5 different error types via proxy
- Reload dashboard, verify all 5 shown
- Apply each filter, verify correct subset shown
- Search for error message substring, verify filtering
- Click "View Details", verify URL change

### Checkpoint 3: After Story 7 (Error Detail View)

**Verify**:
- Navigate to `#error/<fingerprint>` shows detail view
- Detail view shows error summary + occurrence timeline
- "Back to Dashboard" button returns to dashboard
- Browser back/forward work correctly
- Auto-refresh pauses while viewing detail
- Invalid fingerprint shows "Error not found"

**Test**:
- Generate error, copy fingerprint from logs
- Navigate to `http://localhost:47000/dashboard#error/<fingerprint>`
- Verify detail view renders correctly
- Click "Back to Dashboard", verify dashboard restored
- Click browser back button, verify navigation works
- Navigate to `#error/invalid`, verify error state shown

### Checkpoint 4: After Story 8 (Final)

**Verify**:
- Notification includes short fingerprint (8 chars)
- (If terminal-notifier installed) Notification clickable
- Clicking notification opens browser to error detail
- Fallback to osascript works when terminal-notifier not installed

**Test**:
- Trigger new error, check notification
- Copy fingerprint from notification
- Navigate to dashboard with fingerprint in URL
- Verify error detail loads
- (If installed) Click notification, verify browser opens to detail

### Checkpoint 5: After Story 9 (CLI Commands)

**Verify**:
- CLI script `cli_errors.py` runs successfully
- `python cli_errors.py list` shows all error types in Rich table
- `python cli_errors.py list --provider bedrock` filters correctly
- `python cli_errors.py show <fingerprint>` displays error detail + occurrences
- `python cli_errors.py stats` shows summary statistics with tables
- Rich formatting applies (colors, tables)

**Test**:
- Generate 5 different errors
- Run `python cli_errors.py list` → verify 5 errors shown
- Run `python cli_errors.py show <fingerprint>` → verify detail + occurrences
- Run `python cli_errors.py stats` → verify counts by provider and type
- Verify Rich tables formatted correctly (colors, alignment)

### Checkpoint 6: After Story 10 (Export Functionality)

**Verify**:
- `python cli_errors.py export --format csv` outputs valid CSV to stdout
- `python cli_errors.py export --output errors.csv` writes to file
- `python cli_errors.py export <fingerprint> --format json` exports occurrences
- CSV includes all fields: fingerprint, provider, error_type, message, count, timestamps
- JSON structure validates correctly
- Export pipe-able: `python cli_errors.py export | head -10` works

**Test**:
- Generate 10 errors
- Export to CSV: `python cli_errors.py export --format csv > errors.csv`
- Open CSV in spreadsheet, verify all columns present
- Export to file: `python cli_errors.py export --output errors.csv`
- Verify file contains header + 10 data rows
- Export occurrences: `python cli_errors.py export <fingerprint> --format json > occ.json`
- Verify JSON structure: `{"id": ..., "fingerprint": ..., "timestamp": ...}`
- Pipe test: `python cli_errors.py export | wc -l` → should show line count

---

## Success Criteria

- ✅ All 17 atomic tasks completed and validated
- ✅ All acceptance criteria met for Stories 5-10
- ✅ Integration tests pass (error list, detail, filtering)
- ✅ End-to-end flow works: error → notification → deep link → detail view
- ✅ Browser back/forward navigation works correctly
- ✅ Auto-refresh pauses when viewing error detail
- ✅ CLI commands work: list, show, stats, export
- ✅ CSV/JSON export validates correctly
- ✅ All 6 known issues documented with mitigation strategies
- ✅ Documentation complete and accurate

---

## Timeline & Effort

| Story | Tasks | Estimated Time |
|-------|-------|----------------|
| Story 5: Backend API | 3 tasks | 4-5 hours |
| Story 6: Error List View | 3 tasks | 4-6 hours |
| Story 7: Error Detail View | 3 tasks | 4-7 hours |
| Story 8: Notifications | 2 tasks | 3-4 hours (1 optional) |
| Story 9: CLI Commands | 3 tasks | 2-3 hours |
| Story 10: Export Functionality | 3 tasks | 2-3 hours |
| **Total** | **17 tasks** | **19-28 hours (3-4 days)** |

**Critical Path Duration**: 12-16 hours for web UI (Stories 5-8), CLI optional (Stories 9-10)

---

## Next Steps

1. Review this implementation plan
2. Open fresh session (per MDD workflow)
3. Run `/code:implement` to begin Story 5 (Backend API)
4. After each story, run integration checkpoint tests
5. Final validation: end-to-end deep link flow

**Agent ID**: af0a120 (resume with this ID if needed)
