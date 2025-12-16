---
title: Anti-Pattern Detection
description: Scan PostgreSQL codebase and schema for anti-patterns using postgres-optimizer agent
arguments: [path]
---

# PostgreSQL Anti-Pattern Detection

This command uses the `postgres-optimizer` agent to systematically scan your PostgreSQL schema, migrations, and application code for common anti-patterns identified in the PostgreSQL community wiki "Don't Do This".

## Agent Delegation

```
@task postgres-optimizer

Scan the codebase for PostgreSQL anti-patterns following the comprehensive guide at https://wiki.postgresql.org/wiki/Don't_Do_This

**Scope**: ${1:-.}

**Analysis Categories**:

### 1. Text Storage Anti-Patterns
- ❌ CHAR(n) usage (should use TEXT or VARCHAR)
- ❌ VARCHAR without justification (TEXT is usually better)
- ❌ Using length constraints for validation (should use CHECK)

### 2. Data Type Anti-Patterns
- ❌ MONEY type (precision issues, use NUMERIC)
- ❌ SERIAL instead of IDENTITY
- ❌ Inappropriate type choices for domain

### 3. Date/Time Anti-Patterns
- ❌ TIMESTAMP WITHOUT TIME ZONE for events
- ❌ Storing UTC as local time
- ❌ Using TIMESTAMP for dates (should use DATE)
- ❌ Using CHAR/VARCHAR for timestamps
- ❌ BETWEEN for timestamp ranges (exclusive end)
- ❌ Now() in DEFAULT (should use CURRENT_TIMESTAMP)

### 4. SQL Construct Anti-Patterns
- ❌ NOT IN with nullable columns
- ❌ BETWEEN with timestamps (should use >= AND <)
- ❌ Upper case, quoted names without reason
- ❌ Unnecessary LIKE wildcards
- ❌ Rules instead of triggers
- ❌ Table inheritance for partitioning

### 5. Schema Design Anti-Patterns
- ❌ Rules/columns for business logic states
- ❌ EAV (Entity-Attribute-Value) patterns
- ❌ Splitting tables by time period manually
- ❌ Polymorphic associations without proper foreign keys

### 6. Index Anti-Patterns
- ❌ Missing indexes on foreign keys
- ❌ Redundant/overlapping indexes
- ❌ Indexes on small tables
- ❌ Wrong index type for query patterns
- ❌ Not using partial indexes appropriately

### 7. Query Anti-Patterns
- ❌ SELECT * in application queries
- ❌ N+1 query patterns
- ❌ Missing LIMIT on unbounded queries
- ❌ Cartesian products (missing JOIN conditions)
- ❌ Subqueries that should be JOINs

### 8. Security/Configuration Anti-Patterns
- ❌ SQL_ASCII encoding (should use UTF8)
- ❌ TRUST authentication over TCP/IP
- ❌ psql -W in scripts (password prompt)
- ❌ String concatenation for SQL (SQL injection risk)

**Search Locations**:
1. **Schema Definitions**: DDL files, migrations, schema.sql
2. **Application Code**: Query builders, ORM configurations, raw SQL
3. **Configuration**: postgresql.conf, pg_hba.conf, connection strings
4. **Database Inspection**: If connection details provided, inspect live schema

**Analysis Output**:

For each anti-pattern found:
1. **Location**: File:line or database object name
2. **Anti-Pattern**: Which specific pattern from the list
3. **Current Code**: The problematic code snippet
4. **Impact**: Performance/correctness/security risk (Critical/High/Medium/Low)
5. **Fix**: Specific recommended change
6. **Migration Path**: How to safely remediate (if schema change)

**Deliverables**:
- Summary count of anti-patterns by category and severity
- Detailed findings report with file locations
- Prioritized remediation plan (Critical → High → Medium → Low)
- Safe migration scripts for schema changes
- Estimated effort and risk for each fix

**Safety Notes**:
- Flag any findings that require production migration carefully
- Provide rollback plans for schema changes
- Consider backward compatibility for type changes
- Note any performance implications during migration
```

## Usage

```bash
# Scan current directory
/db:antipatterns

# Scan specific path
/db:antipatterns src/main/resources/db/migration

# Scan with database connection (add to command)
/db:antipatterns . --db-url postgresql://localhost:5432/mydb
```

## Reference

This command implements checks from the PostgreSQL community wiki:
https://wiki.postgresql.org/wiki/Don't_Do_This

## Integration with /db:review

This command complements `/db:review` by:
- `/db:review`: Comprehensive schema optimization analysis (cardinality, indexes, queries)
- `/db:antipatterns`: Focused anti-pattern detection in code and schema

Use both for complete database health assessment.
