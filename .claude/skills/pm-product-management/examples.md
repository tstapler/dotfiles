# Product Management Examples

Worked examples showing completed artifacts. All examples use the personal-wiki/tools context for relevance.

## Example PRD: Todoist Bidirectional Sync

```markdown
# PRD: Todoist Bidirectional Sync (Push)

## Problem Statement

**Who**: Solo developer managing tasks across Todoist (mobile/quick capture) and local YAML files (deep planning)
**Problem**: Changes made to local task files (edits, completions, new tasks) are not pushed back to Todoist, creating divergent task states
**Frequency**: Every work session where tasks are modified locally
**Impact**: Tasks completed locally still show in Todoist; edits made locally are overwritten on next pull

## Jobs-to-be-Done

> When I edit or complete a task in my local YAML files, I want those changes to sync back to Todoist, so I can trust either system as my source of truth.

## Proposed Solution

Extend the V2 sync engine to detect locally modified tasks (via `is_locally_modified` flag) and push changes to Todoist via REST API. Conflict resolution uses last-write-wins with a manual review option for simultaneous edits.

## Success Metrics

| Metric | Current | Target | Measurement Method |
|--------|---------|--------|-------------------|
| Local edits reaching Todoist | 0% | 100% | Verify via API after sync |
| Sync conflicts requiring manual resolution | N/A | < 5% of syncs | Count conflict files |
| Round-trip sync time | N/A | < 30s for 100 tasks | CLI timing |

## Scope

### In Scope

- Push modified tasks (content, description, priority, labels, due date)
- Push task completions
- Push new tasks created locally
- Conflict detection for simultaneous edits
- Dry-run mode for previewing push

### Out of Scope

- Push project/section creation -- rationale: too complex for initial release, create in Todoist
- Real-time sync -- rationale: CLI-based workflow is batch-oriented
- Subtask reordering -- rationale: rarely modified locally

## Assumptions and Risks

| Assumption | Risk if Wrong | Mitigation |
|-----------|--------------|------------|
| Todoist API rate limits sufficient | Push fails for large batches | Implement backoff and batching |
| `last_modified_at` timestamps reliable | Silent data loss | Add checksum-based change detection |
| Users rarely edit same task in both places | Frequent conflicts | Add conflict review CLI command |

## Timeline

| Phase | Scope | Estimate |
|-------|-------|----------|
| MVP | Push modifications + completions | 3 days |
| V1 | + new tasks + conflict UI | 2 days |
| Future | Real-time watch mode | TBD |
```

## Example User Stories

```markdown
### TS-01: Push modified task to Todoist

**As a** developer using todoist-sync,
**I want** locally modified tasks to sync back to Todoist when I run `todoist-sync sync`,
**So that** my Todoist mobile app reflects changes I made in YAML files.

**Priority**: Must
**Estimate**: 4 hours
**Parent**: PRD: Todoist Bidirectional Sync

#### Acceptance Criteria

- [ ] **Given** a task with `is_locally_modified: true`, **When** I run `todoist-sync sync`, **Then** the task's content, priority, and due_date are updated in Todoist via API
- [ ] **Given** a successful push, **When** the API returns 200, **Then** `is_locally_modified` is set to `false` and `last_synced_at` is updated
- [ ] **Given** the API returns an error, **When** the push fails, **Then** the task remains marked as locally modified and the error is logged

#### Edge Cases

- [ ] Task deleted in Todoist since last pull: log warning, skip push, flag for user review
- [ ] API rate limit hit: back off exponentially, resume remaining tasks

---

### TS-02: Dry-run push preview

**As a** developer who is cautious about data sync,
**I want** to preview what would be pushed before actually pushing,
**So that** I can verify changes before they reach Todoist.

**Priority**: Should
**Estimate**: 2 hours
**Parent**: PRD: Todoist Bidirectional Sync

#### Acceptance Criteria

- [ ] **Given** locally modified tasks exist, **When** I run `todoist-sync sync --dry-run`, **Then** a table shows each task with: title, fields changed, old value, new value
- [ ] **Given** dry-run mode, **When** the command completes, **Then** no API calls are made and no local files are modified
```

## Example Roadmap

```markdown
# Roadmap: Todoist Sync

Last updated: 2026-03-26

## Vision

A single CLI that keeps Todoist and local task YAML files perfectly synchronized, enabling quick capture on mobile and deep planning in editor.

## Now (Committed)

### Outcome: Local changes reach Todoist reliably

| Item | Type | Status | Est. |
|------|------|--------|------|
| Push modified tasks | Build | Not started | 3 days |
| Push completions | Build | Not started | 1 day |
| Conflict detection | Build | Not started | 2 days |

**Key result**: 100% of local modifications appear in Todoist after sync

## Next (Planned)

### Outcome: New tasks can be created from either side

| Item | Type | Dependency | Est. |
|------|------|-----------|------|
| Create task locally, push to Todoist | Build | Push MVP | 2 days |
| Assign project/section during creation | Build | Push MVP | 1 day |

**Key result**: Full round-trip lifecycle without opening Todoist web

## Later (Exploring)

### Outcome: Sync is invisible -- happens without thinking

- File watcher for automatic sync on save
- Conflict resolution UI (TUI with Rich)
- Sync status dashboard

**Open questions**: Is real-time sync worth the complexity for a solo user?

## Parking Lot

- Todoist comments sync -- source: noticed during V2 migration
- Recurring task handling improvements -- source: bug report during testing
```

## Example RICE Scoring

```markdown
## Backlog Prioritization: Book Sync Features

| Feature | Reach | Impact | Confidence | Effort (days) | RICE Score |
|---------|-------|--------|-----------|--------------|------------|
| Hardcover API integration | 50 books | 2 | 80% | 3 | 26.7 |
| Reading progress tracking | 200 sessions/yr | 1 | 50% | 5 | 20.0 |
| Auto-recommend from reading history | 50 books | 2 | 50% | 4 | 12.5 |
| Export to Goodreads CSV | 10 exports/yr | 0.5 | 100% | 1 | 5.0 |

**Decision**: Hardcover API integration first (highest score, highest confidence).
Reading progress tracking needs research to raise confidence before committing.
```

## Example Trade-Off Analysis

```markdown
# Feature Scope: Conflict Resolution for Todoist Sync

**Parent**: PRD: Todoist Bidirectional Sync

## Options

### Option A: Last-Write-Wins (Automatic)

- **Description**: Compare timestamps; most recent edit wins silently
- **Pros**: Zero user intervention, simple implementation
- **Cons**: Silent data loss if both sides edited
- **Effort**: 0.5 days
- **Risk**: User loses a Todoist edit they made on mobile
- **Reversibility**: Two-way door (can add manual review later)

### Option B: Manual Review Queue

- **Description**: Conflicting tasks written to `conflicts/` directory for manual resolution
- **Pros**: No data loss, user controls outcome
- **Cons**: Blocks sync completion, adds friction
- **Effort**: 2 days
- **Risk**: Conflict queue grows and gets ignored
- **Reversibility**: Two-way door

## Recommendation

**Choice**: Option A with safety net
**Rationale**: Solo developer rarely edits same task in both places simultaneously.
Last-write-wins handles 95%+ of cases. Add a `--conflicts` flag that shows recent
auto-resolved conflicts so the user can spot-check.
**Trade-offs accepted**: Rare silent data loss for daily workflow simplicity.
```
