---
description: Comprehensive PostgreSQL schema analysis to identify optimization opportunities
prompt: "# Database Schema Review and Optimization Analysis\n\nThis command uses the\
  \ `postgres-optimizer` and `project-coordinator` agents to perform a comprehensive\
  \ database schema review.\n\n## Agent Delegation\n\n### Phase 1: Schema Analysis\
  \ with postgres-optimizer\n\n```\n@task postgres-optimizer\n\nPerform comprehensive\
  \ PostgreSQL schema analysis for the engineering-score-cards project.\n\n**Database\
  \ Connection** (from docker-compose.yml):\n- Host: localhost:5432\n- Database: scorecardsdb\n\
  - User: scorecardsuser\n- Password: scorecardspass\n\n**Analysis Tasks**:\n\n1.\
  \ **Discovery & Inventory**:\n   - List all tables with sizes, row counts, and index\
  \ information\n   - Identify unused indexes (idx_scan = 0)\n   - Find missing indexes\
  \ on foreign keys\n   - Analyze table bloat and dead tuple percentages\n   - Gather\
  \ cardinality statistics for all tables\n\n2. **Per-Table Optimization Analysis**:\n\
  \   - Review normalization appropriateness for access patterns\n   - Identify unused\
  \ or redundant indexes\n   - Recommend missing indexes based on query patterns\n\
  \   - Evaluate partitioning opportunities for large tables\n   - Assess column type\
  \ efficiency\n   - Check for partial index or covering index opportunities\n   -\
  \ Verify VACUUM effectiveness\n\n3. **Query Performance Review**:\n   - Identify\
  \ slow queries from pg_stat_statements\n   - Run EXPLAIN ANALYZE on top queries\n\
  \   - Check for cardinality estimation errors\n   - Verify optimal index usage\n\
  \   - Evaluate join strategies\n   - Identify sequential scans that should be index\
  \ scans\n\n4. **Anti-Pattern Detection**:\n   - N+1 query patterns\n   - Missing\
  \ composite indexes\n   - Over-indexing (redundant indexes)\n   - Under-indexing\
  \ (missing FK indexes)\n   - Inappropriate data types\n   - Lack of partitioning\
  \ on time-series data\n\n5. **Data Lifecycle Review**:\n   - Assess partitioning\
  \ needs for growing tables\n   - Review archival/cleanup strategies\n   - Verify\
  \ VACUUM effectiveness for write patterns\n   - Recommend TTL strategies where appropriate\n\
  \n**Deliverables**:\n- Database inventory report with statistics\n- Per-table optimization\
  \ recommendations (P0-P3 priority)\n- Unused index report with removal recommendations\n\
  - Missing index report with implementation SQL\n- Query performance analysis with\
  \ optimization suggestions\n- Expected performance impact estimates\n- Implementation\
  \ complexity assessment\n```\n\n### Phase 2: Task Organization with project-coordinator\n\
  \nAfter the postgres-optimizer agent completes its analysis:\n\n```\n@task project-coordinator\n\
  \nOrganize database optimization findings into actionable ATOMIC tasks.\n\n**Context**:\n\
  Completed comprehensive schema review identifying [N] optimization opportunities\
  \ across indexes, normalization, partitioning, and query performance.\n\n**Input\
  \ from postgres-optimizer**:\n[Paste the findings summary with priorities]\n\n**Constraints**:\n\
  - Zero-downtime migrations preferred\n- Must maintain read consistency during changes\n\
  - Backup before any DDL changes\n- Each task should be 1-4 hours of focused work\n\
  - Use `CREATE INDEX CONCURRENTLY` for production\n\n**Request**:\n1. Create `docs/tasks/database-optimization.md`\
  \ using Implementation Plan format\n2. Break down optimizations into atomic tasks\
  \ (1-4 hours each):\n   - Specific tables/indexes to modify\n   - Clear success\
  \ criteria\n   - Testing requirements\n   - Rollback plans\n3. Identify task dependencies\
  \ (e.g., must create index before dropping old one)\n4. Recommend next action to\
  \ start with (prioritize high-impact quick wins)\n5. Provide progress tracking structure\n\
  \n**Output**: Structured task document with Epic → Story → Task breakdown, dependency\
  \ visualization, and clear next action recommendation.\n```\n\n## Safety Reminders\n\
  \n- ⚠️ Always backup before DDL changes\n- ⚠️ Test migrations on staging first\n\
  - ⚠️ Use `CREATE INDEX CONCURRENTLY` for zero-downtime\n- ⚠️ Monitor query performance\
  \ after changes\n- ⚠️ Have rollback plans for all schema changes\n- ⚠️ Consider\
  \ resetting pg_stat_statements after baseline measurements\n\n## Usage\n\n```bash\n\
  # Run complete schema review\n/db:review\n```\n\nThe command will automatically\
  \ invoke both agents in sequence, producing a comprehensive analysis and actionable\
  \ task breakdown.\n"
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
1. Create `docs/tasks/database-optimization.md` using Implementation Plan format
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
