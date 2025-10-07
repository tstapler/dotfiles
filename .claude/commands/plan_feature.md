---
title: Plan Feature
description: Comprehensive feature planning using established software engineering principles and methodologies
arguments: [feature_description]
---

# Feature Planning & Architecture Guide

I'll help you plan, design, and implement $ARGUMENTS by applying established software engineering principles, design patterns, and best practices from highly regarded literature and academic research. The approach will be tailored to your specific context and technology stack.

## Planning Process

### 1. **Requirements Gathering & Analysis Phase**
   - Apply requirements engineering techniques (IEEE 830, EARS notation)
   - Identify functional requirements using user stories (Agile/Scrum framework)
   - Define non-functional requirements (ISO/IEC 25010 quality model):
     - **Performance**: Response time, throughput, resource usage
     - **Scalability**: Load capacity, growth accommodation
     - **Security**: Authentication, authorization, data protection
     - **Reliability**: Availability, fault tolerance, recoverability
     - **Maintainability**: Code quality, modularity, testability
     - **Usability**: User experience, accessibility, learnability
     - **Portability**: Platform independence, compatibility
   - Create acceptance criteria and definition of done
   - Prioritize using MoSCoW method (Must, Should, Could, Won't)
   - Document assumptions, constraints, and dependencies

### 2. **Architecture & Design Phase**
   - **Select appropriate architectural patterns**:
     - Layered Architecture for separation of concerns
     - Hexagonal Architecture (Ports & Adapters) for testability
     - Microservices for distributed systems
     - Event-Driven Architecture for decoupling
     - CQRS for read/write optimization
     - Clean Architecture for maintainability

   - **Apply Domain-Driven Design (DDD) principles** (Eric Evans):
     - Strategic Design: Identify Bounded Contexts, create Context Maps
     - Tactical Design: Define Aggregates, Entities, Value Objects, Domain Events
     - Establish Ubiquitous Language with stakeholders

   - **Design system components using**:
     - GoF Design Patterns (Factory, Strategy, Observer, etc.)
     - Enterprise Application Patterns (Repository, Unit of Work, Service Layer)
     - Modern patterns (Circuit Breaker, API Gateway, Saga, BFF)

   - **Create architectural decision records (ADRs)** for key choices
   - Consider evolutionary architecture principles (Neal Ford)

### 3. **User Interface Design Phase**
   - **Apply UX design principles**:
     - User-centered design approach
     - Information architecture and navigation design
     - Interaction design patterns
     - Visual hierarchy and consistency
   - Follow accessibility standards (WCAG 2.1)
   - Implement responsive design principles
   - Consider design systems and component libraries
   - Use wireframing and prototyping for validation
   - Plan for error states, loading states, empty states

### 4. **Implementation Planning Phase**
   - **Break down into implementable tasks**:
     - Create user stories with acceptance criteria
     - Estimate effort and complexity
     - Identify dependencies and ordering
     - Plan incremental delivery (vertical slices)

   - **Define technical approach**:
     - Technology stack and frameworks
     - Data models and database schema
     - API contracts and integration points
     - Security implementation strategy
     - Error handling and logging approach

   - **Follow SOLID principles** (Robert C. Martin):
     - Single Responsibility Principle
     - Open-Closed Principle
     - Liskov Substitution Principle
     - Interface Segregation Principle
     - Dependency Inversion Principle

   - **Apply Clean Code practices**:
     - Meaningful names for clarity
     - Small, focused functions
     - DRY (Don't Repeat Yourself)
     - Purposeful comments and documentation
     - Error handling over error codes

### 5. **Quality Assurance Strategy**
   - **Implement testing strategy** (Test Pyramid - Mike Cohn):
     - Unit tests for individual components (TDD/BDD when appropriate)
     - Integration tests for component interactions
     - End-to-end tests for critical user journeys
     - Performance tests for non-functional requirements

   - **Apply testing patterns**:
     - Test Doubles (mocks, stubs, fakes)
     - Arrange-Act-Assert pattern
     - Given-When-Then for BDD

   - **Code quality measures**:
     - Code reviews using established checklists
     - Static analysis tools
     - Code coverage metrics
     - Complexity metrics (cyclomatic complexity)

   - **Validation approach**:
     - Functional requirements validation
     - Non-functional requirements validation
     - User acceptance testing
     - Security testing

## Non-Functional Concerns Addressed

### Performance
- Identify potential bottlenecks early
- Apply caching strategies (client-side, server-side, CDN)
- Consider asynchronous processing for long-running operations
- Plan database query optimization
- Profile and optimize based on metrics

### Security
- Follow OWASP Top 10 guidelines
- Implement authentication and authorization
- Apply principle of least privilege
- Validate inputs, encode outputs, parameterize queries
- Plan for secure data storage and transmission
- Consider rate limiting and DOS protection

### Scalability
- Design for horizontal scaling when appropriate
- Consider database scaling strategies (read replicas, sharding)
- Implement stateless services where possible
- Use load balancing effectively
- Plan caching and CDN usage
- Consider async/event-driven patterns for decoupling

### Maintainability
- Write self-documenting code
- Manage technical debt intentionally
- Keep complexity manageable (low coupling, high cohesion)
- Follow established conventions
- Create comprehensive documentation
- Plan for monitoring and observability

### Reliability
- Implement error handling and recovery
- Use circuit breakers and retry patterns with exponential backoff
- Plan for failure scenarios (chaos engineering principles)
- Implement health checks and monitoring
- Design for graceful degradation
- Plan alerting and incident response

### Observability
- Structured logging with appropriate levels
- Distributed tracing for microservices
- Metrics collection (RED or USE method)
- Dashboards and visualizations
- Alerting thresholds and escalation

## Deliverables & Artifacts

Based on project needs, create:
- **Architecture diagrams** (C4 model, UML, sequence diagrams)
- **API specifications** (OpenAPI/Swagger)
- **Database schemas** and ER diagrams
- **User stories** with acceptance criteria
- **Technical design documents**
- **Implementation roadmap** with milestones
- **Testing strategy** and test plans
- **Architecture Decision Records** (ADRs)

## Academic and Industry References

### Requirements & Planning
- "Software Requirements" (Karl Wiegers)
- "User Story Mapping" (Jeff Patton)
- "Agile Estimating and Planning" (Mike Cohn)
- IEEE 830 Standard for Software Requirements Specifications
- ISO/IEC 25010 Software Quality Model

### Architecture & Design
- "Clean Architecture" (Robert C. Martin)
- "Domain-Driven Design" (Eric Evans)
- "Implementing Domain-Driven Design" (Vaughn Vernon)
- "Software Architecture in Practice" (Bass, Clements, Kazman)
- "Building Evolutionary Architectures" (Ford, Parsons, Kua)
- "Patterns of Enterprise Application Architecture" (Martin Fowler)
- "Microservices Patterns" (Chris Richardson)
- C4 Model for Software Architecture (Simon Brown)

### Implementation
- "Clean Code" (Robert C. Martin)
- "Code Complete" (Steve McConnell)
- "The Pragmatic Programmer" (Hunt & Thomas)
- "Design Patterns: Elements of Reusable Object-Oriented Software" (Gang of Four)
- "Refactoring: Improving the Design of Existing Code" (Martin Fowler)
- "A Philosophy of Software Design" (John Ousterhout)
- "Working Effectively with Legacy Code" (Michael Feathers)

### Quality & Testing
- "Test-Driven Development by Example" (Kent Beck)
- "Growing Object-Oriented Software, Guided by Tests" (Freeman & Pryce)
- "The Art of Unit Testing" (Roy Osherove)
- "Release It!" (Michael Nygard)

### UX & Design
- "Don't Make Me Think" (Steve Krug)
- "The Design of Everyday Things" (Don Norman)
- "About Face: The Essentials of Interaction Design" (Cooper, Reimann, Cronin)

### Standards & Guidelines
- ISO/IEC 25010 (Software Quality Model)
- WCAG 2.1 (Web Accessibility Guidelines)
- OWASP Top 10 (Security)
- Twelve-Factor App Methodology

## Workflow

I'll guide you through this process systematically:

1. **Understand the feature**: Clarify requirements and context
2. **Analyze implications**: Consider technical and business impacts
3. **Design solution**: Apply appropriate patterns and principles
4. **Plan implementation**: Break down into actionable tasks
5. **Define quality measures**: Establish testing and validation approach
6. **Document decisions**: Create necessary artifacts and ADRs

Let's begin planning **$ARGUMENTS**. I'll help you build a robust, maintainable solution that meets functional and non-functional requirements while following established engineering principles and best practices.