---
title: Schema Review
description: Comprehensive PostgreSQL schema analysis to identify optimization opportunities
---

# Database Schema Review and Optimization Analysis

This command uses the `postgres-optimizer` and `project-coordinator` agents to perform a comprehensive database schema review.

## Agent Delegation

### Phase 1: Schema Analysis with postgres-optimizer

```
@task postgres-optimizer

Perform comprehensive PostgreSQL schema analysis for the engineering-score-cards project.

**Database Connection** (from docker-compose.yml):
- Host: localhost:5432
- Database: scorecardsdb
- User: scorecardsuser
- Password: scorecardspass

**Analysis Tasks**:

1. **Discovery & Inventory**:
   - List all tables with sizes, row counts, and index information
   - Identify unused indexes (idx_scan = 0)
   - Find missing indexes on foreign keys
   - Analyze table bloat and dead tuple percentages
   - Gather cardinality statistics for all tables

2. **Per-Table Optimization Analysis**:
   - Review normalization appropriateness for access patterns
   - Identify unused or redundant indexes
   - Recommend missing indexes based on query patterns
   - Evaluate partitioning opportunities for large tables
   - Assess column type efficiency
   - Check for partial index or covering index opportunities
   - Verify VACUUM effectiveness

3. **Query Performance Review**:
   - Identify slow queries from pg_stat_statements
   - Run EXPLAIN ANALYZE on top queries
   - Check for cardinality estimation errors
   - Verify optimal index usage
   - Evaluate join strategies
   - Identify sequential scans that should be index scans

4. **Anti-Pattern Detection**:
   - N+1 query patterns
   - Missing composite indexes
   - Over-indexing (redundant indexes)
   - Under-indexing (missing FK indexes)
   - Inappropriate data types
   - Lack of partitioning on time-series data

5. **Data Lifecycle Review**:
   - Assess partitioning needs for growing tables
   - Review archival/cleanup strategies
   - Verify VACUUM effectiveness for write patterns
   - Recommend TTL strategies where appropriate

**Deliverables**:
- Database inventory report with statistics
- Per-table optimization recommendations (P0-P3 priority)
- Unused index report with removal recommendations
- Missing index report with implementation SQL
- Query performance analysis with optimization suggestions
- Expected performance impact estimates
- Implementation complexity assessment
```

### Phase 2: Task Organization with project-coordinator

After the postgres-optimizer agent completes its analysis:

```
@task project-coordinator

Organize database optimization findings into actionable ATOMIC tasks.

**Context**:
Completed comprehensive schema review identifying [N] optimization opportunities across indexes, normalization, partitioning, and query performance.

**Input from postgres-optimizer**:
[Paste the findings summary with priorities]

**Constraints**:
- Zero-downtime migrations preferred
- Must maintain read consistency during changes
- Backup before any DDL changes
- Each task should be 1-4 hours of focused work
- Use `CREATE INDEX CONCURRENTLY` for production

**Request**:
1. Create `docs/tasks/database-optimization.md` using AIC framework
2. Break down optimizations into atomic tasks (1-4 hours each):
   - Specific tables/indexes to modify
   - Clear success criteria
   - Testing requirements
   - Rollback plans
3. Identify task dependencies (e.g., must create index before dropping old one)
4. Recommend next action to start with (prioritize high-impact quick wins)
5. Provide progress tracking structure

**Output**: Structured task document with Epic → Story → Task breakdown, dependency visualization, and clear next action recommendation.
```

## Safety Reminders

- ⚠️ Always backup before DDL changes
- ⚠️ Test migrations on staging first
- ⚠️ Use `CREATE INDEX CONCURRENTLY` for zero-downtime
- ⚠️ Monitor query performance after changes
- ⚠️ Have rollback plans for all schema changes
- ⚠️ Consider resetting pg_stat_statements after baseline measurements

## Usage

```bash
# Run complete schema review
/db:review
```

The command will automatically invoke both agents in sequence, producing a comprehensive analysis and actionable task breakdown.
