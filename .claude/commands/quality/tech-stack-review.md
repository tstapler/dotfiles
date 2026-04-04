---
description: High-level architecture review evaluating directional correctness, documentation
  quality, and FBG tech stack alignment
prompt: "# Tech Stack and Direction Review: ${1:-.}\n\nPerform a high-level architecture\
  \ review focusing on three key questions:\n\n1. **Are we heading in the right direction\
  \ architecturally?**\n2. **Do we have the right documentation and diagrams?**\n\
  3. **Are we using the right technologies aligned with FBG standards?**\n\n## Scope\n\
  \nReview scope: `${1:-.}` (defaults to entire project)\n\n---\n\n## FBG Supported\
  \ Tech Stack Standards\n\nThe FBG (Fanatics Betting & Gaming) supported technology\
  \ stack includes:\n\n### **Infrastructure and Platform**\n- **Cloud Provider**:\
  \ AWS (Amazon Web Services)\n- **Container Orchestration**: Amazon EKS (Elastic\
  \ Kubernetes Service)\n- **Service Mesh**: Istio (if applicable)\n- **Infrastructure\
  \ as Code**: Terraform, CloudFormation\n\n### **Application Stack**\n- **Primary\
  \ Language**: Java (Java 17+)\n- **Application Framework**: Spring Boot 3.x\n  -\
  \ Spring Web / WebFlux (for reactive)\n  - Spring Data JPA\n  - Spring Security\n\
  \  - Spring Cloud (for microservices patterns)\n- **Build Tools**: Gradle (preferred)\
  \ or Maven\n\n### **Data Storage**\n- **Relational Database**: Amazon RDS PostgreSQL\n\
  - **Caching**: Amazon ElastiCache for Redis\n- **Message Streaming**: Apache Kafka\
  \ (MSK - Managed Streaming for Kafka)\n\n### **Observability**\n- **Metrics and\
  \ Monitoring**: Datadog\n- **Logging**: Datadog Logs\n- **Tracing**: Datadog APM\n\
  - **Alerting**: Datadog Monitors\n\n### **CI/CD and Development**\n- **Version Control**:\
  \ GitHub\n- **CI/CD**: GitHub Actions\n- **Container Registry**: Amazon ECR\n- **Secrets\
  \ Management**: AWS Secrets Manager\n- **Configuration**: AWS Systems Manager Parameter\
  \ Store\n\n---\n\n## Phase 1: Directional Correctness Review\n\n### Architecture\
  \ Direction Assessment\n\n**Evaluate the following architectural aspects:**\n\n\
  1. **Microservices vs Monolith**\n   - [ ] Is the service boundary appropriate for\
  \ the domain?\n   - [ ] Are services at the right granularity (not too fine, not\
  \ too coarse)?\n   - [ ] Is there a clear bounded context for each service?\n  \
  \ - [ ] Are inter-service dependencies minimal and well-defined?\n   - **Questions\
  \ to Answer**:\n     - Should this be a microservice or part of a larger service?\n\
  \     - Are we creating a distributed monolith?\n     - Do service boundaries align\
  \ with business domains?\n\n2. **Data Architecture**\n   - [ ] Is data ownership\
  \ clear (database per service pattern)?\n   - [ ] Are we avoiding distributed transactions\
  \ where possible?\n   - [ ] Is caching strategy appropriate for access patterns?\n\
  \   - [ ] Is event-driven architecture used where appropriate?\n   - **Questions\
  \ to Answer**:\n     - Should services share a database or own their data?\n   \
  \  - Are we using Kafka events for inter-service communication correctly?\n    \
  \ - Is our caching strategy (Redis) aligned with read/write patterns?\n\n3. **Scalability\
  \ and Performance**\n   - [ ] Can the application scale horizontally?\n   - [ ]\
  \ Are there obvious bottlenecks in the design?\n   - [ ] Is database design optimized\
  \ for expected load?\n   - [ ] Are caching strategies preventing database overload?\n\
  \   - **Questions to Answer**:\n     - Will this architecture handle expected scale\
  \ (users, transactions, data volume)?\n     - Are we using reactive patterns (WebFlux)\
  \ where high concurrency is needed?\n     - Is connection pooling (HikariCP, PGBouncer)\
  \ configured correctly?\n\n4. **Reliability and Resilience**\n   - [ ] Are circuit\
  \ breakers implemented for external dependencies?\n   - [ ] Is retry logic appropriate\
  \ and idempotent?\n   - [ ] Are timeouts configured at all integration points?\n\
  \   - [ ] Is graceful degradation possible?\n   - **Questions to Answer**:\n   \
  \  - What happens when dependencies fail?\n     - Are we implementing resilience\
  \ patterns (Resilience4j)?\n     - Is chaos engineering considered in design?\n\n\
  5. **Security Architecture**\n   - [ ] Is authentication and authorization handled\
  \ correctly?\n   - [ ] Are secrets managed properly (AWS Secrets Manager)?\n   -\
  \ [ ] Is data encrypted at rest and in transit?\n   - [ ] Are API gateways and service\
  \ meshes securing inter-service communication?\n   - **Questions to Answer**:\n\
  \     - How are we handling authentication (JWT, OAuth)?\n     - Are we following\
  \ least-privilege principles?\n     - Is PII/sensitive data protected?\n\n### Directional\
  \ Red Flags\n\n**Watch for these anti-patterns:**\n\n- ❌ **Over-Engineering**: Building\
  \ for scale before it's needed\n- ❌ **Under-Engineering**: Ignoring known scale/reliability\
  \ requirements\n- ❌ **Technology Proliferation**: Adding technologies outside FBG\
  \ standards without justification\n- ❌ **Distributed Monolith**: Microservices that\
  \ are tightly coupled\n- ❌ **Data Sprawl**: No clear data ownership or strategy\n\
  - ❌ **Synchronous Coupling**: Microservices making blocking calls to many other\
  \ services\n- ❌ **Missing Observability**: No instrumentation for debugging production\
  \ issues\n\n---\n\n## Phase 2: Documentation and Diagram Assessment\n\n### Required\
  \ Documentation Checklist\n\n**Architecture Documentation**:\n- [ ] **System Context\
  \ Diagram**: Shows system boundaries and external integrations\n  - Format: C4 Level\
  \ 1 (Context)\n  - Shows: Users, external systems, boundaries\n  - Missing or outdated:\
  \ [yes/no]\n\n- [ ] **Container Diagram**: Shows high-level technology choices\n\
  \  - Format: C4 Level 2 (Container)\n  - Shows: Applications, databases, message\
  \ queues, caches\n  - Missing or outdated: [yes/no]\n\n- [ ] **Component Diagram**:\
  \ Shows internal structure of key services\n  - Format: C4 Level 3 (Component)\n\
  \  - Shows: Controllers, services, repositories, domain models\n  - Missing or outdated:\
  \ [yes/no]\n\n- [ ] **Data Flow Diagrams**: Shows how data moves through the system\n\
  \  - Shows: API calls, events, data persistence\n  - Missing or outdated: [yes/no]\n\
  \n- [ ] **Deployment Diagram**: Shows infrastructure and runtime environment\n \
  \ - Shows: EKS clusters, RDS instances, ElastiCache, Kafka clusters\n  - Includes:\
  \ Regions, availability zones, network topology\n  - Missing or outdated: [yes/no]\n\
  \n**Technical Documentation**:\n- [ ] **Architecture Decision Records (ADRs)**\n\
  \  - Template: MADR or similar\n  - Coverage: Major technology and pattern choices\n\
  \  - Up-to-date: [yes/no]\n\n- [ ] **API Documentation**\n  - Format: OpenAPI/Swagger\
  \ specs\n  - Coverage: All REST endpoints\n  - Automated generation: [yes/no]\n\n\
  - [ ] **Database Schema Documentation**\n  - ERD diagrams for key entities\n  -\
  \ Migration strategy documented\n  - Index strategy documented\n\n- [ ] **Kafka\
  \ Topic Documentation**\n  - Topic inventory\n  - Event schemas (Avro/JSON Schema)\n\
  \  - Producer/consumer mappings\n\n- [ ] **Runbooks and Operations Guides**\n  -\
  \ Deployment procedures\n  - Rollback procedures\n  - Common troubleshooting scenarios\n\
  \  - On-call playbooks\n\n- [ ] **README Files**\n  - Project overview\n  - Local\
  \ development setup\n  - Build and test instructions\n  - Deployment instructions\n\
  \n### Documentation Quality Assessment\n\n**For each documentation artifact, evaluate:**\n\
  \n1. **Accuracy**: Is documentation current with the code?\n2. **Completeness**:\
  \ Does it cover all critical aspects?\n3. **Clarity**: Is it understandable by the\
  \ target audience?\n4. **Maintainability**: Is it easy to keep up-to-date?\n5. **Discoverability**:\
  \ Can developers find it when needed?\n\n**Identify Documentation Gaps**:\n- Critical\
  \ gaps: [list missing docs that block understanding/operations]\n- Important gaps:\
  \ [list missing docs that cause friction]\n- Nice-to-have gaps: [list docs that\
  \ would help but aren't critical]\n\n### Diagram Tooling Recommendations\n\n**Preferred\
  \ Tools**:\n- **Architecture Diagrams**: PlantUML, Mermaid, Draw.io, Lucidchart\n\
  - **C4 Diagrams**: Structurizr, PlantUML with C4 extension\n- **Data Models**: DBeaver,\
  \ ERD tools, dbdiagram.io\n- **Sequence Diagrams**: PlantUML, Mermaid (in docs)\n\
  \n**Diagram-as-Code Benefits**:\n- Version controlled alongside code\n- Can be reviewed\
  \ in pull requests\n- Automated diagram generation possible\n\n---\n\n## Phase 3:\
  \ Technology Stack Alignment\n\n### Technology Compliance Assessment\n\n**Evaluate\
  \ current technology choices against FBG standards:**\n\n#### Infrastructure and\
  \ Platform\n| Component | FBG Standard | Current Usage | Aligned? | Notes/Justification\
  \ |\n|-----------|-------------|---------------|----------|---------------------|\n\
  | Cloud Provider | AWS | [Auto-detect] | [Yes/No] | [Reason if No] |\n| Container\
  \ Orchestration | EKS | [Auto-detect] | [Yes/No] | [Reason if No] |\n| IaC | Terraform/CFN\
  \ | [Auto-detect] | [Yes/No] | [Reason if No] |\n\n#### Application Stack\n| Component\
  \ | FBG Standard | Current Usage | Aligned? | Notes/Justification |\n|-----------|-------------|---------------|----------|---------------------|\n\
  | Language | Java 17+ | [Auto-detect from pom.xml/build.gradle] | [Yes/No] | [Reason\
  \ if No] |\n| Framework | Spring Boot 3.x | [Auto-detect] | [Yes/No] | [Reason if\
  \ No] |\n| Build Tool | Gradle/Maven | [Auto-detect] | [Yes/No] | [Reason if No]\
  \ |\n\n#### Data Storage\n| Component | FBG Standard | Current Usage | Aligned?\
  \ | Notes/Justification |\n|-----------|-------------|---------------|----------|---------------------|\n\
  | RDBMS | PostgreSQL (RDS) | [Auto-detect from config] | [Yes/No] | [Reason if No]\
  \ |\n| Cache | Redis (ElastiCache) | [Auto-detect from config] | [Yes/No] | [Reason\
  \ if No] |\n| Streaming | Kafka (MSK) | [Auto-detect from config] | [Yes/No] | [Reason\
  \ if No] |\n\n#### Observability\n| Component | FBG Standard | Current Usage | Aligned?\
  \ | Notes/Justification |\n|-----------|-------------|---------------|----------|---------------------|\n\
  | APM/Monitoring | Datadog | [Auto-detect from dependencies] | [Yes/No] | [Reason\
  \ if No] |\n\n### Non-Standard Technology Review\n\n**For any technology not in\
  \ the FBG stack:**\n\n1. **Technology**: [Name of non-standard tech]\n   - **Purpose**:\
  \ [What problem does it solve?]\n   - **Justification**: [Why is FBG standard not\
  \ suitable?]\n   - **Alternatives Considered**: [List FBG-compliant alternatives\
  \ evaluated]\n   - **Risk Assessment**: [Operational risk, support concerns, skills\
  \ gap]\n   - **Recommendation**: [Keep, Replace with FBG standard, Propose as new\
  \ FBG standard]\n\n2. **Technology**: [Name of non-standard tech]\n   - [Repeat\
  \ analysis]\n\n### Technology Debt Identification\n\n**Identify outdated or problematic\
  \ technology choices:**\n\n- **Legacy Versions**: Libraries or frameworks that are\
  \ outdated\n  - Java < 17\n  - Spring Boot < 3.x\n  - Postgres < 13\n\n- **Deprecated\
  \ Technologies**: Using technologies scheduled for retirement\n  - [List any deprecated\
  \ tech in use]\n\n- **Security Vulnerabilities**: Known CVEs in dependencies\n \
  \ - Run `mvn dependency-check:check` or `gradle dependencyCheckAnalyze`\n  - List\
  \ critical/high severity vulnerabilities\n\n---\n\n## Phase 4: Comprehensive Review\
  \ Report\n\n### Executive Summary\n\nGenerate a concise executive summary answering\
  \ the three key questions:\n\n#### 1. Are we heading in the right direction architecturally?\n\
  \n**Overall Direction**: [On Track / Needs Adjustment / Significant Concerns]\n\n\
  **Key Strengths**:\n- [List 2-3 positive directional choices]\n\n**Key Concerns**:\n\
  - [List 2-3 directional issues requiring attention]\n\n**Directional Recommendation**:\n\
  - [Overall guidance: Continue current path / Make specific adjustments / Consider\
  \ pivot]\n\n#### 2. Do we have the right documentation and diagrams?\n\n**Documentation\
  \ Coverage**: [Excellent / Good / Adequate / Insufficient]\n\n**What We Have**:\n\
  - [List existing, up-to-date documentation]\n\n**What We're Missing**:\n- **Critical**:\
  \ [List missing docs blocking effective development/operations]\n- **Important**:\
  \ [List missing docs causing friction]\n\n**Documentation Recommendation**:\n- [Prioritized\
  \ list of documentation to create/update]\n\n#### 3. Are we using the right technologies?\n\
  \n**Tech Stack Alignment**: [Fully Aligned / Mostly Aligned / Partially Aligned\
  \ / Non-Compliant]\n\n**Compliant Technologies**:\n- [List FBG-standard technologies\
  \ in use]\n\n**Non-Compliant Technologies**:\n- [List non-standard tech with justification\
  \ assessment]\n\n**Technology Recommendation**:\n- [List tech to replace, migrate,\
  \ or formally justify]\n\n### Detailed Findings\n\n**Architecture Direction**:\n\
  1. [Finding 1 with severity: Critical/High/Medium/Low]\n   - **Current State**:\
  \ [Description]\n   - **Concern**: [Why this is an issue]\n   - **Recommendation**:\
  \ [Specific action to take]\n   - **Impact**: [Effort and risk of change]\n\n2.\
  \ [Finding 2...]\n\n**Documentation Gaps**:\n1. [Gap 1 with severity]\n   - **Missing**:\
  \ [What documentation is absent]\n   - **Impact**: [How this affects team]\n   -\
  \ **Recommendation**: [What to create]\n   - **Effort**: [Estimated effort to create]\n\
  \n2. [Gap 2...]\n\n**Technology Alignment**:\n1. [Technology Issue 1 with severity]\n\
  \   - **Technology**: [Name]\n   - **Standard**: [FBG standard]\n   - **Gap**: [Deviation\
  \ description]\n   - **Recommendation**: [Replace / Justify / Migrate]\n   - **Migration\
  \ Path**: [If replacement needed]\n\n2. [Technology Issue 2...]\n\n### Prioritized\
  \ Action Plan\n\n**Immediate Actions (This Sprint)**:\n1. [ ] [P0 item - critical\
  \ directional or tech issue]\n2. [ ] [P0 item - critical documentation gap]\n\n\
  **Short Term (Next 2-4 Weeks)**:\n1. [ ] [P1 item - important directional adjustment]\n\
  2. [ ] [P1 item - key documentation creation]\n3. [ ] [P1 item - high-priority tech\
  \ stack alignment]\n\n**Medium Term (1-3 Months)**:\n1. [ ] [P2 item - architectural\
  \ improvement]\n2. [ ] [P2 item - documentation completion]\n3. [ ] [P2 item - technology\
  \ migration]\n\n**Long Term (3-6 Months)**:\n1. [ ] [P3 item - nice-to-have improvements]\n\
  2. [ ] [P3 item - comprehensive documentation]\n\n### Decision Points Requiring\
  \ Input\n\n**Key Decisions Needing Resolution**:\n\n1. **Decision**: [Description\
  \ of architectural decision needed]\n   - **Options**: [List 2-3 options]\n   -\
  \ **Recommendation**: [Preferred option with rationale]\n   - **Trade-offs**: [Analysis\
  \ of each option]\n   - **Stakeholders**: [Who should be involved in decision]\n\
  \n2. **Decision**: [Next decision...]\n\n---\n\n## Phase 5: Execution Guidance\n\
  \n### Using Agents for Improvements\n\n**For Detailed Architecture Analysis**: Use\
  \ existing `/quality:architecture-review` command\n```bash\n# After this high-level\
  \ review identifies issues, use the detailed review\n/quality:architecture-review\
  \ src/main/java/com/example/\n```\n\n**For Generating ADRs**: Create ADRs for key\
  \ decisions identified\n```markdown\n# Example ADR template\n# ADR-XXX: [Decision\
  \ Title]\n\n## Status\n[Proposed | Accepted | Deprecated | Superseded]\n\n## Context\n\
  [Describe the issue and the forces at play]\n\n## Decision\n[Describe the decision\
  \ and its rationale]\n\n## Consequences\n[Positive and negative outcomes]\n\n##\
  \ Alternatives Considered\n[List alternatives and why they weren't chosen]\n```\n\
  \n**For Creating Diagrams**: Use diagram-as-code tools\n```plantuml\n# Example C4\
  \ Container Diagram\n@startuml\n!include https://raw.githubusercontent.com/plantuml-stdlib/C4-PlantUML/master/C4_Container.puml\n\
  \nPerson(user, \"User\", \"A user of the system\")\nSystem_Boundary(c1, \"System\
  \ Name\") {\n    Container(web, \"Web Application\", \"Spring Boot\", \"Delivers\
  \ content\")\n    ContainerDb(db, \"Database\", \"PostgreSQL\", \"Stores data\"\
  )\n    Container(cache, \"Cache\", \"Redis\", \"Caches frequently accessed data\"\
  )\n}\n@enduml\n```\n\n### Tech Stack Migration Strategies\n\n**For Java Version\
  \ Upgrades**:\n1. Update build tool configuration (pom.xml/build.gradle)\n2. Update\
  \ language level in IDE and compiler\n3. Run tests and fix compilation errors\n\
  4. Update CI/CD pipelines\n5. Update container base images\n\n**For Spring Boot\
  \ Upgrades**:\n1. Check Spring Boot 3.x migration guide\n2. Update javax.* to jakarta.*\
  \ namespace\n3. Update dependencies to compatible versions\n4. Test thoroughly (breaking\
  \ changes are common)\n\n**For Database Migrations**:\n1. Document current database\
  \ usage patterns\n2. Plan migration strategy (dual-write, event streaming, etc.)\n\
  3. Test performance and compatibility\n4. Plan rollback strategy\n5. Execute phased\
  \ migration\n\n---\n\n## Review Execution\n\n### Step 1: Automated Discovery\n-\
  \ Use Grep/Read to detect technologies from config files\n- Map dependencies from\
  \ pom.xml/build.gradle\n- Identify infrastructure from Terraform/CloudFormation\n\
  - Find documentation files\n\n### Step 2: Directional Analysis\n- Evaluate architecture\
  \ against scale/reliability requirements\n- Assess microservices boundaries and\
  \ coupling\n- Review data architecture and event flows\n- Identify directional red\
  \ flags\n\n### Step 3: Documentation Audit\n- Inventory existing documentation\n\
  - Assess quality and currency\n- Identify critical gaps\n- Recommend diagram-as-code\
  \ approaches\n\n### Step 4: Tech Stack Compliance\n- Compare detected technologies\
  \ against FBG standards\n- Evaluate justifications for non-standard tech\n- Identify\
  \ migration paths for non-compliant tech\n- Assess security and operational risks\n\
  \n### Step 5: Report and Recommendations\n- Generate comprehensive report\n- Prioritize\
  \ findings by impact and effort\n- Provide concrete action plan\n- Identify key\
  \ decision points\n\n---\n\n## Success Criteria\n\n- ✅ Clear answer to \"Are we\
  \ heading in the right direction?\"\n- ✅ Complete documentation gap analysis with\
  \ priorities\n- ✅ Full tech stack compliance assessment\n- ✅ Prioritized action\
  \ plan (P0, P1, P2, P3)\n- ✅ Identified key decisions requiring stakeholder input\n\
  - ✅ Concrete migration plans for non-compliant technologies\n\n---\n\n## Usage Examples\n\
  \n```bash\n# Review entire project\n/quality:tech-stack-review\n\n# Review specific\
  \ service\n/quality:tech-stack-review services/payment-service\n\n# Review with\
  \ focus on documentation\n/quality:tech-stack-review --focus=documentation\n\n#\
  \ Review with focus on tech compliance\n/quality:tech-stack-review --focus=tech-stack\n\
  ```\n\n---\n\n## Related Commands\n\n- `/quality:architecture-review` - Detailed\
  \ code-level architecture analysis (SOLID, Clean Architecture, DDD)\n- `/code:implement`\
  \ - Implement features following FBG standards\n- `/plan:feature` - Plan features\
  \ with architecture considerations\n\n---\n\n**Remember**: This is a high-level\
  \ strategic review focused on direction, documentation, and tech stack alignment.\
  \ For detailed code-level analysis, use `/quality:architecture-review`. The goal\
  \ is to ensure the team is building the right thing, the right way, with the right\
  \ tools.\n"
---

# Tech Stack and Direction Review: ${1:-.}

Perform a high-level architecture review focusing on three key questions:

1. **Are we heading in the right direction architecturally?**
2. **Do we have the right documentation and diagrams?**
3. **Are we using the right technologies aligned with FBG standards?**

## Scope

Review scope: `${1:-.}` (defaults to entire project)

---

## FBG Supported Tech Stack Standards

The FBG (Fanatics Betting & Gaming) supported technology stack includes:

### **Infrastructure and Platform**
- **Cloud Provider**: AWS (Amazon Web Services)
- **Container Orchestration**: Amazon EKS (Elastic Kubernetes Service)
- **Service Mesh**: Istio (if applicable)
- **Infrastructure as Code**: Terraform, CloudFormation

### **Application Stack**
- **Primary Language**: Java (Java 17+)
- **Application Framework**: Spring Boot 3.x
  - Spring Web / WebFlux (for reactive)
  - Spring Data JPA
  - Spring Security
  - Spring Cloud (for microservices patterns)
- **Build Tools**: Gradle (preferred) or Maven

### **Data Storage**
- **Relational Database**: Amazon RDS PostgreSQL
- **Caching**: Amazon ElastiCache for Redis
- **Message Streaming**: Apache Kafka (MSK - Managed Streaming for Kafka)

### **Observability**
- **Metrics and Monitoring**: Datadog
- **Logging**: Datadog Logs
- **Tracing**: Datadog APM
- **Alerting**: Datadog Monitors

### **CI/CD and Development**
- **Version Control**: GitHub
- **CI/CD**: GitHub Actions
- **Container Registry**: Amazon ECR
- **Secrets Management**: AWS Secrets Manager
- **Configuration**: AWS Systems Manager Parameter Store

---

## Phase 1: Directional Correctness Review

### Architecture Direction Assessment

**Evaluate the following architectural aspects:**

1. **Microservices vs Monolith**
   - [ ] Is the service boundary appropriate for the domain?
   - [ ] Are services at the right granularity (not too fine, not too coarse)?
   - [ ] Is there a clear bounded context for each service?
   - [ ] Are inter-service dependencies minimal and well-defined?
   - **Questions to Answer**:
     - Should this be a microservice or part of a larger service?
     - Are we creating a distributed monolith?
     - Do service boundaries align with business domains?

2. **Data Architecture**
   - [ ] Is data ownership clear (database per service pattern)?
   - [ ] Are we avoiding distributed transactions where possible?
   - [ ] Is caching strategy appropriate for access patterns?
   - [ ] Is event-driven architecture used where appropriate?
   - **Questions to Answer**:
     - Should services share a database or own their data?
     - Are we using Kafka events for inter-service communication correctly?
     - Is our caching strategy (Redis) aligned with read/write patterns?

3. **Scalability and Performance**
   - [ ] Can the application scale horizontally?
   - [ ] Are there obvious bottlenecks in the design?
   - [ ] Is database design optimized for expected load?
   - [ ] Are caching strategies preventing database overload?
   - **Questions to Answer**:
     - Will this architecture handle expected scale (users, transactions, data volume)?
     - Are we using reactive patterns (WebFlux) where high concurrency is needed?
     - Is connection pooling (HikariCP, PGBouncer) configured correctly?

4. **Reliability and Resilience**
   - [ ] Are circuit breakers implemented for external dependencies?
   - [ ] Is retry logic appropriate and idempotent?
   - [ ] Are timeouts configured at all integration points?
   - [ ] Is graceful degradation possible?
   - **Questions to Answer**:
     - What happens when dependencies fail?
     - Are we implementing resilience patterns (Resilience4j)?
     - Is chaos engineering considered in design?

5. **Security Architecture**
   - [ ] Is authentication and authorization handled correctly?
   - [ ] Are secrets managed properly (AWS Secrets Manager)?
   - [ ] Is data encrypted at rest and in transit?
   - [ ] Are API gateways and service meshes securing inter-service communication?
   - **Questions to Answer**:
     - How are we handling authentication (JWT, OAuth)?
     - Are we following least-privilege principles?
     - Is PII/sensitive data protected?

### Directional Red Flags

**Watch for these anti-patterns:**

- ❌ **Over-Engineering**: Building for scale before it's needed
- ❌ **Under-Engineering**: Ignoring known scale/reliability requirements
- ❌ **Technology Proliferation**: Adding technologies outside FBG standards without justification
- ❌ **Distributed Monolith**: Microservices that are tightly coupled
- ❌ **Data Sprawl**: No clear data ownership or strategy
- ❌ **Synchronous Coupling**: Microservices making blocking calls to many other services
- ❌ **Missing Observability**: No instrumentation for debugging production issues

---

## Phase 2: Documentation and Diagram Assessment

### Required Documentation Checklist

**Architecture Documentation**:
- [ ] **System Context Diagram**: Shows system boundaries and external integrations
  - Format: C4 Level 1 (Context)
  - Shows: Users, external systems, boundaries
  - Missing or outdated: [yes/no]

- [ ] **Container Diagram**: Shows high-level technology choices
  - Format: C4 Level 2 (Container)
  - Shows: Applications, databases, message queues, caches
  - Missing or outdated: [yes/no]

- [ ] **Component Diagram**: Shows internal structure of key services
  - Format: C4 Level 3 (Component)
  - Shows: Controllers, services, repositories, domain models
  - Missing or outdated: [yes/no]

- [ ] **Data Flow Diagrams**: Shows how data moves through the system
  - Shows: API calls, events, data persistence
  - Missing or outdated: [yes/no]

- [ ] **Deployment Diagram**: Shows infrastructure and runtime environment
  - Shows: EKS clusters, RDS instances, ElastiCache, Kafka clusters
  - Includes: Regions, availability zones, network topology
  - Missing or outdated: [yes/no]

**Technical Documentation**:
- [ ] **Architecture Decision Records (ADRs)**
  - Template: MADR or similar
  - Coverage: Major technology and pattern choices
  - Up-to-date: [yes/no]

- [ ] **API Documentation**
  - Format: OpenAPI/Swagger specs
  - Coverage: All REST endpoints
  - Automated generation: [yes/no]

- [ ] **Database Schema Documentation**
  - ERD diagrams for key entities
  - Migration strategy documented
  - Index strategy documented

- [ ] **Kafka Topic Documentation**
  - Topic inventory
  - Event schemas (Avro/JSON Schema)
  - Producer/consumer mappings

- [ ] **Runbooks and Operations Guides**
  - Deployment procedures
  - Rollback procedures
  - Common troubleshooting scenarios
  - On-call playbooks

- [ ] **README Files**
  - Project overview
  - Local development setup
  - Build and test instructions
  - Deployment instructions

### Documentation Quality Assessment

**For each documentation artifact, evaluate:**

1. **Accuracy**: Is documentation current with the code?
2. **Completeness**: Does it cover all critical aspects?
3. **Clarity**: Is it understandable by the target audience?
4. **Maintainability**: Is it easy to keep up-to-date?
5. **Discoverability**: Can developers find it when needed?

**Identify Documentation Gaps**:
- Critical gaps: [list missing docs that block understanding/operations]
- Important gaps: [list missing docs that cause friction]
- Nice-to-have gaps: [list docs that would help but aren't critical]

### Diagram Tooling Recommendations

**Preferred Tools**:
- **Architecture Diagrams**: PlantUML, Mermaid, Draw.io, Lucidchart
- **C4 Diagrams**: Structurizr, PlantUML with C4 extension
- **Data Models**: DBeaver, ERD tools, dbdiagram.io
- **Sequence Diagrams**: PlantUML, Mermaid (in docs)

**Diagram-as-Code Benefits**:
- Version controlled alongside code
- Can be reviewed in pull requests
- Automated diagram generation possible

---

## Phase 3: Technology Stack Alignment

### Technology Compliance Assessment

**Evaluate current technology choices against FBG standards:**

#### Infrastructure and Platform
| Component | FBG Standard | Current Usage | Aligned? | Notes/Justification |
|-----------|-------------|---------------|----------|---------------------|
| Cloud Provider | AWS | [Auto-detect] | [Yes/No] | [Reason if No] |
| Container Orchestration | EKS | [Auto-detect] | [Yes/No] | [Reason if No] |
| IaC | Terraform/CFN | [Auto-detect] | [Yes/No] | [Reason if No] |

#### Application Stack
| Component | FBG Standard | Current Usage | Aligned? | Notes/Justification |
|-----------|-------------|---------------|----------|---------------------|
| Language | Java 17+ | [Auto-detect from pom.xml/build.gradle] | [Yes/No] | [Reason if No] |
| Framework | Spring Boot 3.x | [Auto-detect] | [Yes/No] | [Reason if No] |
| Build Tool | Gradle/Maven | [Auto-detect] | [Yes/No] | [Reason if No] |

#### Data Storage
| Component | FBG Standard | Current Usage | Aligned? | Notes/Justification |
|-----------|-------------|---------------|----------|---------------------|
| RDBMS | PostgreSQL (RDS) | [Auto-detect from config] | [Yes/No] | [Reason if No] |
| Cache | Redis (ElastiCache) | [Auto-detect from config] | [Yes/No] | [Reason if No] |
| Streaming | Kafka (MSK) | [Auto-detect from config] | [Yes/No] | [Reason if No] |

#### Observability
| Component | FBG Standard | Current Usage | Aligned? | Notes/Justification |
|-----------|-------------|---------------|----------|---------------------|
| APM/Monitoring | Datadog | [Auto-detect from dependencies] | [Yes/No] | [Reason if No] |

### Non-Standard Technology Review

**For any technology not in the FBG stack:**

1. **Technology**: [Name of non-standard tech]
   - **Purpose**: [What problem does it solve?]
   - **Justification**: [Why is FBG standard not suitable?]
   - **Alternatives Considered**: [List FBG-compliant alternatives evaluated]
   - **Risk Assessment**: [Operational risk, support concerns, skills gap]
   - **Recommendation**: [Keep, Replace with FBG standard, Propose as new FBG standard]

2. **Technology**: [Name of non-standard tech]
   - [Repeat analysis]

### Technology Debt Identification

**Identify outdated or problematic technology choices:**

- **Legacy Versions**: Libraries or frameworks that are outdated
  - Java < 17
  - Spring Boot < 3.x
  - Postgres < 13

- **Deprecated Technologies**: Using technologies scheduled for retirement
  - [List any deprecated tech in use]

- **Security Vulnerabilities**: Known CVEs in dependencies
  - Run `mvn dependency-check:check` or `gradle dependencyCheckAnalyze`
  - List critical/high severity vulnerabilities

---

## Phase 4: Comprehensive Review Report

### Executive Summary

Generate a concise executive summary answering the three key questions:

#### 1. Are we heading in the right direction architecturally?

**Overall Direction**: [On Track / Needs Adjustment / Significant Concerns]

**Key Strengths**:
- [List 2-3 positive directional choices]

**Key Concerns**:
- [List 2-3 directional issues requiring attention]

**Directional Recommendation**:
- [Overall guidance: Continue current path / Make specific adjustments / Consider pivot]

#### 2. Do we have the right documentation and diagrams?

**Documentation Coverage**: [Excellent / Good / Adequate / Insufficient]

**What We Have**:
- [List existing, up-to-date documentation]

**What We're Missing**:
- **Critical**: [List missing docs blocking effective development/operations]
- **Important**: [List missing docs causing friction]

**Documentation Recommendation**:
- [Prioritized list of documentation to create/update]

#### 3. Are we using the right technologies?

**Tech Stack Alignment**: [Fully Aligned / Mostly Aligned / Partially Aligned / Non-Compliant]

**Compliant Technologies**:
- [List FBG-standard technologies in use]

**Non-Compliant Technologies**:
- [List non-standard tech with justification assessment]

**Technology Recommendation**:
- [List tech to replace, migrate, or formally justify]

### Detailed Findings

**Architecture Direction**:
1. [Finding 1 with severity: Critical/High/Medium/Low]
   - **Current State**: [Description]
   - **Concern**: [Why this is an issue]
   - **Recommendation**: [Specific action to take]
   - **Impact**: [Effort and risk of change]

2. [Finding 2...]

**Documentation Gaps**:
1. [Gap 1 with severity]
   - **Missing**: [What documentation is absent]
   - **Impact**: [How this affects team]
   - **Recommendation**: [What to create]
   - **Effort**: [Estimated effort to create]

2. [Gap 2...]

**Technology Alignment**:
1. [Technology Issue 1 with severity]
   - **Technology**: [Name]
   - **Standard**: [FBG standard]
   - **Gap**: [Deviation description]
   - **Recommendation**: [Replace / Justify / Migrate]
   - **Migration Path**: [If replacement needed]

2. [Technology Issue 2...]

### Prioritized Action Plan

**Immediate Actions (This Sprint)**:
1. [ ] [P0 item - critical directional or tech issue]
2. [ ] [P0 item - critical documentation gap]

**Short Term (Next 2-4 Weeks)**:
1. [ ] [P1 item - important directional adjustment]
2. [ ] [P1 item - key documentation creation]
3. [ ] [P1 item - high-priority tech stack alignment]

**Medium Term (1-3 Months)**:
1. [ ] [P2 item - architectural improvement]
2. [ ] [P2 item - documentation completion]
3. [ ] [P2 item - technology migration]

**Long Term (3-6 Months)**:
1. [ ] [P3 item - nice-to-have improvements]
2. [ ] [P3 item - comprehensive documentation]

### Decision Points Requiring Input

**Key Decisions Needing Resolution**:

1. **Decision**: [Description of architectural decision needed]
   - **Options**: [List 2-3 options]
   - **Recommendation**: [Preferred option with rationale]
   - **Trade-offs**: [Analysis of each option]
   - **Stakeholders**: [Who should be involved in decision]

2. **Decision**: [Next decision...]

---

## Phase 5: Execution Guidance

### Using Agents for Improvements

**For Detailed Architecture Analysis**: Use existing `/quality:architecture-review` command
```bash
# After this high-level review identifies issues, use the detailed review
/quality:architecture-review src/main/java/com/example/
```

**For Generating ADRs**: Create ADRs for key decisions identified
```markdown
# Example ADR template
# ADR-XXX: [Decision Title]

## Status
[Proposed | Accepted | Deprecated | Superseded]

## Context
[Describe the issue and the forces at play]

## Decision
[Describe the decision and its rationale]

## Consequences
[Positive and negative outcomes]

## Alternatives Considered
[List alternatives and why they weren't chosen]
```

**For Creating Diagrams**: Use diagram-as-code tools
```plantuml
# Example C4 Container Diagram
@startuml
!include https://raw.githubusercontent.com/plantuml-stdlib/C4-PlantUML/master/C4_Container.puml

Person(user, "User", "A user of the system")
System_Boundary(c1, "System Name") {
    Container(web, "Web Application", "Spring Boot", "Delivers content")
    ContainerDb(db, "Database", "PostgreSQL", "Stores data")
    Container(cache, "Cache", "Redis", "Caches frequently accessed data")
}
@enduml
```

### Tech Stack Migration Strategies

**For Java Version Upgrades**:
1. Update build tool configuration (pom.xml/build.gradle)
2. Update language level in IDE and compiler
3. Run tests and fix compilation errors
4. Update CI/CD pipelines
5. Update container base images

**For Spring Boot Upgrades**:
1. Check Spring Boot 3.x migration guide
2. Update javax.* to jakarta.* namespace
3. Update dependencies to compatible versions
4. Test thoroughly (breaking changes are common)

**For Database Migrations**:
1. Document current database usage patterns
2. Plan migration strategy (dual-write, event streaming, etc.)
3. Test performance and compatibility
4. Plan rollback strategy
5. Execute phased migration

---

## Review Execution

### Step 1: Automated Discovery
- Use Grep/Read to detect technologies from config files
- Map dependencies from pom.xml/build.gradle
- Identify infrastructure from Terraform/CloudFormation
- Find documentation files

### Step 2: Directional Analysis
- Evaluate architecture against scale/reliability requirements
- Assess microservices boundaries and coupling
- Review data architecture and event flows
- Identify directional red flags

### Step 3: Documentation Audit
- Inventory existing documentation
- Assess quality and currency
- Identify critical gaps
- Recommend diagram-as-code approaches

### Step 4: Tech Stack Compliance
- Compare detected technologies against FBG standards
- Evaluate justifications for non-standard tech
- Identify migration paths for non-compliant tech
- Assess security and operational risks

### Step 5: Report and Recommendations
- Generate comprehensive report
- Prioritize findings by impact and effort
- Provide concrete action plan
- Identify key decision points

---

## Success Criteria

- ✅ Clear answer to "Are we heading in the right direction?"
- ✅ Complete documentation gap analysis with priorities
- ✅ Full tech stack compliance assessment
- ✅ Prioritized action plan (P0, P1, P2, P3)
- ✅ Identified key decisions requiring stakeholder input
- ✅ Concrete migration plans for non-compliant technologies

---

## Usage Examples

```bash
# Review entire project
/quality:tech-stack-review

# Review specific service
/quality:tech-stack-review services/payment-service

# Review with focus on documentation
/quality:tech-stack-review --focus=documentation

# Review with focus on tech compliance
/quality:tech-stack-review --focus=tech-stack
```

---

## Related Commands

- `/quality:architecture-review` - Detailed code-level architecture analysis (SOLID, Clean Architecture, DDD)
- `/code:implement` - Implement features following FBG standards
- `/plan:feature` - Plan features with architecture considerations

---

**Remember**: This is a high-level strategic review focused on direction, documentation, and tech stack alignment. For detailed code-level analysis, use `/quality:architecture-review`. The goal is to ensure the team is building the right thing, the right way, with the right tools.
