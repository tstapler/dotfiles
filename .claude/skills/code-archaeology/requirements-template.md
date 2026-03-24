# Code Archaeology Analysis: {PROJECT_NAME}

**Analyzed**: {DATE}
**Source**: {REPO_URL_OR_ARCHIVE_PATH}
**Working directory**: {TEMP_DIR_PATH}

---

## 1. Executive Summary

{2-3 sentences: what this system does, who it serves, and its primary value proposition. Derived from README + code reading.}

## 2. Tech Stack

| Layer | Technology | Evidence |
|-------|-----------|----------|
| Language | {e.g., Java 17} | {file:line or config reference} |
| Framework | {e.g., Spring Boot 3.2} | {build file reference} |
| Database | {e.g., PostgreSQL 15} | {config/migration reference} |
| Cache | {e.g., Redis 7} | {config reference} |
| Message Broker | {e.g., Kafka 3.x} | {config reference} |
| Build System | {e.g., Gradle 8.x} | {wrapper/config reference} |
| CI/CD | {e.g., GitHub Actions} | {workflow file reference} |
| Deployment | {e.g., Kubernetes + Helm} | {k8s/helm file reference} |
| Monitoring | {e.g., Prometheus + Grafana} | {config reference} |

## 3. Domain Model

### Entities

| Entity | Key Fields | Relationships | Source |
|--------|-----------|---------------|--------|
| {EntityName} | {field1, field2, ...} | {has-many X, belongs-to Y} | {file path} |

### Entity Relationship Summary

```
{ASCII or text-based relationship diagram}
{Example: User 1--* Order *--* Product}
```

## 4. API / Interface Contracts

### REST Endpoints

| Method | Path | Purpose | Auth | Source |
|--------|------|---------|------|--------|
| {GET} | {/api/resource} | {Description} | {Yes/No} | {file:line} |

### Events / Messages

| Event | Direction | Channel/Topic | Payload | Source |
|-------|-----------|---------------|---------|--------|
| {EventName} | {Produce/Consume} | {topic-name} | {key fields} | {file:line} |

### Scheduled Jobs

| Job | Schedule | Purpose | Source |
|-----|----------|---------|--------|
| {JobName} | {cron expression} | {Description} | {file:line} |

## 5. Functional Requirements (Derived)

{Number each requirement. Reference the code artifact it was derived from.}

| ID | Requirement | Source Artifact | Confidence |
|----|------------|-----------------|------------|
| FR-01 | The system SHALL {action} when {condition} | {file:line or endpoint} | {High/Medium/Low} |
| FR-02 | ... | ... | ... |

## 6. Non-Functional Requirements (Derived)

| ID | Category | Requirement | Evidence | Confidence |
|----|----------|------------|----------|------------|
| NFR-01 | Performance | {e.g., DB connection pool sized for 20 concurrent connections} | {config file:value} | {High/Medium/Low} |
| NFR-02 | Reliability | {e.g., Retries configured with exponential backoff, max 3 attempts} | {config/code reference} | ... |
| NFR-03 | Security | {e.g., All API endpoints require JWT authentication} | {middleware/filter reference} | ... |
| NFR-04 | Scalability | {e.g., Stateless design enables horizontal scaling} | {architectural evidence} | ... |
| NFR-05 | Observability | {e.g., Structured logging with correlation IDs} | {logging config reference} | ... |

## 7. Architectural Patterns

| Pattern | Evidence | Assessment |
|---------|----------|------------|
| {e.g., Layered Architecture} | {Controller -> Service -> Repository separation} | {Well-implemented / Partially / Leaky} |
| {e.g., Event-Driven} | {Kafka consumers in X, producers in Y} | ... |

## 8. Notable Design Choices

{For each choice, explain what they chose, what alternatives existed, and why they likely chose this approach.}

### 8.1 {Choice Title}
- **Decision**: {What they chose}
- **Alternatives**: {What else they could have done}
- **Likely rationale**: {Why this choice makes sense given the context}
- **Evidence**: {File references}

## 9. Problems to Solve / Technical Debt

{Ranked by adoption impact: Blocking > Significant > Minor}

### Blocking (Must fix before adoption)

| # | Problem | Location | Impact | Suggested Fix |
|---|---------|----------|--------|---------------|
| 1 | {Description} | {file:line} | {Why it blocks} | {Brief fix approach} |

### Significant (Should fix early)

| # | Problem | Location | Impact | Suggested Fix |
|---|---------|----------|--------|---------------|
| 1 | {Description} | {file:line} | {Risk if ignored} | {Brief fix approach} |

### Minor (Fix when convenient)

| # | Problem | Location | Impact | Suggested Fix |
|---|---------|----------|--------|---------------|
| 1 | {Description} | {file:line} | {Quality concern} | {Brief fix approach} |

## 10. Adoption Considerations

### Prerequisites
- {What you need to understand before using this code}
- {External services / accounts required}
- {Infrastructure requirements}

### Estimated Complexity
- **Codebase size**: {files, lines of code estimate}
- **External dependencies**: {count of runtime deps}
- **External service integrations**: {list of APIs/services called}
- **Data migration needs**: {schema complexity}

### Recommended Next Steps
1. {Most important thing to do first}
2. {Second priority}
3. {Third priority}

---

**Cleanup reminder**: Analysis working directory at `{TEMP_DIR_PATH}` can be removed:
```bash
rm -rf {TEMP_DIR_PATH}
```
