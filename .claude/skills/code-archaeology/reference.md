# Code Archaeology Reference Guide

## Tech Stack Detection

### Language Detection by Marker Files

| Marker File | Language/Platform | Build System |
|-------------|------------------|--------------|
| `package.json` | JavaScript/TypeScript | npm/yarn/pnpm |
| `tsconfig.json` | TypeScript | tsc |
| `pom.xml` | Java/Kotlin | Maven |
| `build.gradle` / `build.gradle.kts` | Java/Kotlin | Gradle |
| `go.mod` | Go | go modules |
| `Cargo.toml` | Rust | cargo |
| `requirements.txt` / `pyproject.toml` / `setup.py` | Python | pip/poetry/uv |
| `Gemfile` | Ruby | bundler |
| `mix.exs` | Elixir | mix |
| `*.csproj` / `*.sln` | C#/.NET | dotnet/MSBuild |
| `composer.json` | PHP | composer |
| `Makefile` | C/C++ (often) | make |
| `CMakeLists.txt` | C/C++ | cmake |
| `build.zig` | Zig | zig build |
| `pubspec.yaml` | Dart/Flutter | pub |
| `Package.swift` | Swift | SwiftPM |

### Framework Detection

| Signal | Framework |
|--------|-----------|
| `@SpringBootApplication` annotation | Spring Boot (Java) |
| `django.conf.settings` import | Django (Python) |
| `flask` in requirements | Flask (Python) |
| `fastapi` in requirements | FastAPI (Python) |
| `express` in package.json | Express.js (Node) |
| `next` in package.json | Next.js (React) |
| `nuxt` in package.json | Nuxt.js (Vue) |
| `rails` in Gemfile | Ruby on Rails |
| `phoenix` in mix.exs | Phoenix (Elixir) |
| `gin-gonic/gin` in go.mod | Gin (Go) |
| `actix-web` in Cargo.toml | Actix (Rust) |
| `axum` in Cargo.toml | Axum (Rust) |
| `ASP.NET` in csproj | ASP.NET (C#) |
| `laravel` in composer.json | Laravel (PHP) |

### Infrastructure Detection

| Signal | Infrastructure |
|--------|---------------|
| `Dockerfile` | Docker containerization |
| `docker-compose.yml` | Docker Compose orchestration |
| `k8s/` or `kubernetes/` dir | Kubernetes deployment |
| `helm/` dir or `Chart.yaml` | Helm charts |
| `terraform/` or `*.tf` files | Terraform IaC |
| `pulumi/` or `Pulumi.yaml` | Pulumi IaC |
| `.github/workflows/` | GitHub Actions CI/CD |
| `.gitlab-ci.yml` | GitLab CI |
| `Jenkinsfile` | Jenkins CI |
| `.circleci/config.yml` | CircleCI |
| `serverless.yml` | Serverless Framework |
| `cdk.json` | AWS CDK |
| `sam-template.yaml` | AWS SAM |

## Reverse Engineering Patterns by Language

### Java/Kotlin (Spring Boot)

**Entry points:**
```
# Application bootstrap
Grep: @SpringBootApplication
Grep: public static void main

# REST controllers
Grep: @RestController
Grep: @Controller
Grep: @RequestMapping|@GetMapping|@PostMapping|@PutMapping|@DeleteMapping

# Scheduled jobs
Grep: @Scheduled
Grep: @EnableScheduling
```

**Domain model:**
```
# JPA entities
Grep: @Entity
Grep: @Table

# Database migrations
Glob: **/db/migration/*.sql
Glob: **/flyway/*.sql
Glob: **/liquibase/*.xml

# DTOs and value objects
Grep: record.*\(  (Java records)
Grep: data class  (Kotlin data classes)
```

**Data flow:**
```
# Service layer
Grep: @Service
Grep: @Transactional

# Repository layer
Grep: @Repository
Grep: extends JpaRepository|extends CrudRepository

# External API clients
Grep: @FeignClient
Grep: RestTemplate|WebClient
Grep: HttpClient
```

**Configuration:**
```
# Application config
Read: src/main/resources/application.yml
Read: src/main/resources/application.properties

# Security config
Grep: extends WebSecurityConfigurerAdapter|@EnableWebSecurity
Grep: SecurityFilterChain
```

### Python (Django/FastAPI/Flask)

**Entry points:**
```
# Django
Read: manage.py
Read: */urls.py
Read: */wsgi.py or */asgi.py

# FastAPI
Grep: FastAPI()
Grep: app = FastAPI
Grep: @app.get|@app.post|@router.get|@router.post

# Flask
Grep: Flask(__name__)
Grep: @app.route
```

**Domain model:**
```
# Django ORM
Grep: class.*models.Model
Glob: **/migrations/*.py

# SQLAlchemy
Grep: class.*Base.*:
Grep: Column\(
Glob: **/alembic/versions/*.py

# Pydantic
Grep: class.*BaseModel
Grep: class.*BaseSchema
```

### Go

**Entry points:**
```
Read: cmd/*/main.go  (conventional entry points)
Read: main.go

# HTTP handlers
Grep: http.HandleFunc|http.Handle
Grep: func.*http.Handler
Grep: r.GET|r.POST  (gin)
Grep: e.GET|e.POST  (echo)
```

**Domain model:**
```
# Struct definitions
Grep: type.*struct
Grep: json:\"  (JSON-serializable structs)

# Database
Grep: gorm.Model
Grep: sqlx
Glob: **/migrations/*.sql
```

### TypeScript/JavaScript (Node.js)

**Entry points:**
```
# Check package.json "main" and "scripts.start"
Read: package.json

# Express
Grep: express\(\)
Grep: app.listen
Grep: router.get|router.post

# NestJS
Grep: @Controller
Grep: @Module
Grep: NestFactory.create
```

**Domain model:**
```
# TypeORM/Prisma
Read: prisma/schema.prisma
Grep: @Entity
Grep: @Column

# Mongoose
Grep: mongoose.Schema
Grep: mongoose.model

# Sequelize
Grep: sequelize.define
Glob: **/migrations/*.js
```

## Data Flow Tracing Strategy

### Top-Down Approach (Recommended)

1. **Start at HTTP/event entry point** (controller, handler, consumer)
2. **Follow the call chain** through service/business logic layer
3. **Identify side effects**: DB writes, cache updates, event emissions, external API calls
4. **Map the response path** back to the caller

### Reading Order for Maximum Understanding

1. **README.md** - Author's intent and context
2. **package manifest** - Dependencies reveal capabilities (e.g., `kafka-node` = event-driven)
3. **Entry points** - Where does execution begin?
4. **Route/handler definitions** - What does the system expose?
5. **Domain models** - What nouns does the system operate on?
6. **Service layer** - What business logic transforms data?
7. **Repository/data layer** - How is data persisted and retrieved?
8. **Configuration** - What are the operational parameters?
9. **Tests** - What behaviors are explicitly verified?
10. **Infrastructure** - How is it deployed and operated?

## Architectural Pattern Identification

### Monolith Signals
- Single deployable artifact (one Dockerfile, one build output)
- Shared database (one connection string)
- In-process method calls between domains
- Single `src/` directory with all code

### Microservices Signals
- Multiple Dockerfiles or services in docker-compose
- Service-to-service HTTP/gRPC calls
- Multiple databases (different connection strings per service)
- API gateway configuration
- Service mesh config (Istio, Linkerd)

### Modular Monolith Signals
- Single deployment but clear module boundaries
- Internal module APIs (interfaces/contracts between modules)
- Module-scoped database schemas
- Gradle/Maven multi-module with dependency restrictions

### Event-Driven Signals
- Kafka/RabbitMQ/SQS consumer setup
- Event/message classes or schemas
- Async processing, outbox patterns
- Saga/choreography patterns
- Dead letter queue configuration

### CQRS Signals
- Separate read/write models
- Projection/materialized view builders
- Event store or event log
- Separate query and command handlers

### DDD Signals
- Bounded context directories (e.g., `ordering/`, `shipping/`, `billing/`)
- Aggregate root classes
- Value object implementations (immutable, equality by value)
- Domain event classes
- Repository interfaces per aggregate

## Security Posture Assessment

### Authentication Patterns to Look For
| Pattern | Signal |
|---------|--------|
| JWT | `jsonwebtoken`, `jwt` dependencies; token validation middleware |
| OAuth2/OIDC | `oauth2`, `openid-connect` deps; authorization code flow |
| API Keys | Header extraction middleware; `X-API-Key` references |
| Session-based | Session store config (Redis sessions); cookie settings |
| mTLS | Certificate loading; TLS client config |

### Authorization Patterns
| Pattern | Signal |
|---------|--------|
| RBAC | Role definitions, role checking middleware, `@PreAuthorize` |
| ABAC | Policy engine integration, attribute-based checks |
| ACL | Permission tables, ownership checks per resource |
| None | No auth middleware on routes (vulnerability) |

### Common Security Gaps
- Routes without authentication middleware
- SQL string concatenation (injection risk)
- Unsanitized user input in templates (XSS risk)
- Hardcoded secrets in source code
- Missing CORS configuration
- No rate limiting on sensitive endpoints
- Debug/admin endpoints exposed without auth

## Dependency Risk Assessment

### Red Flags in Dependencies
- Deprecated packages (check for archived repos, "DEPRECATED" in README)
- Known vulnerability patterns (e.g., old versions of common libs)
- Excessive dependency count (supply chain risk)
- Vendored/forked dependencies with local patches
- Pinned to very old versions with no updates
- Dependencies pulling in native code (portability risk)

### Dependency Categories to Catalog
1. **Runtime**: Required to run the application
2. **Build-time**: Required to build but not ship
3. **Dev-only**: Test frameworks, linters, formatters
4. **Infrastructure**: Deployment, monitoring, logging
5. **External services**: SDK clients for APIs (AWS, Stripe, etc.)

## Output Quality Checklist

Before finalizing the analysis document, verify:

- [ ] Executive summary captures what the system does in 2-3 sentences
- [ ] Every tech stack item has a source file reference
- [ ] Domain model lists all entities with their key fields
- [ ] API contracts include method, path, and purpose
- [ ] Functional requirements use "System SHALL" format
- [ ] Non-functional requirements cite specific config values
- [ ] Architectural patterns are named and evidenced
- [ ] Design choices explain the "why" (inferred)
- [ ] Problems are ranked by adoption impact
- [ ] No findings reference executed code (read-only analysis)
