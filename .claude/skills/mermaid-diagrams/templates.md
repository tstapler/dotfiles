# Mermaid Diagram Templates

Four production-ready templates. Copy, adapt labels/nodes, done.

---

## Template A: Architecture Flowchart (LR, dark palette)

```mermaid
%%{init: {'theme': 'base', 'themeVariables': {
  'primaryColor': '#1E293B',
  'primaryTextColor': '#F1F5F9',
  'primaryBorderColor': '#334155',
  'lineColor': '#64748B',
  'edgeLabelBackground': '#F8FAFC',
  'clusterBkg': '#F1F5F9',
  'clusterBorder': '#CBD5E1',
  'fontFamily': 'ui-sans-serif, system-ui',
  'fontSize': '14px'
}}}%%
flowchart LR
  classDef client  fill:#3B82F6,stroke:#1E40AF,color:#fff,stroke-width:2px
  classDef infra   fill:#1E293B,stroke:#475569,color:#94A3B8,stroke-width:1px
  classDef service fill:#0F172A,stroke:#334155,color:#E2E8F0,stroke-width:1px
  classDef store   fill:#064E3B,stroke:#065F46,color:#6EE7B7,stroke-width:1px

  C([Browser]):::client
  CDN[Cloudflare CDN]:::infra
  GW[API Gateway]:::infra
  A[Auth Service]:::service
  W[Workers]:::service
  DB[(Postgres)]:::store
  RD[(Redis)]:::store

  C --> CDN --> GW
  GW --> A
  GW --> W
  W --> DB
  W --> RD
```

---

## Template B: API Sequence Diagram

```mermaid
%%{init: {'theme': 'base', 'themeVariables': {
  'actorBkg': '#1E293B',
  'actorBorder': '#475569',
  'actorTextColor': '#F1F5F9',
  'signalColor': '#64748B',
  'noteBkgColor': '#FEF3C7',
  'noteTextColor': '#92400E',
  'activationBkgColor': '#3B82F6',
  'fontFamily': 'ui-sans-serif, system-ui',
  'fontSize': '14px'
}}}%%
sequenceDiagram
  autonumber
  actor U as User
  participant C as Client
  participant G as API Gateway
  participant A as Auth Service
  participant S as Service

  U->>+C: Submit form
  C->>+G: POST /api/resource
  G->>+A: Validate token
  A-->>-G: 200 OK {claims}
  G->>+S: Forward + claims
  S-->>-G: 201 Created {id}
  G-->>-C: 201 Created
  C-->>-U: Success feedback

  Note over S: Async: emit event<br/>to message queue
```

---

## Template C: State Machine

```mermaid
%%{init: {'theme': 'base', 'themeVariables': {
  'primaryColor': '#312E81',
  'primaryTextColor': '#E0E7FF',
  'primaryBorderColor': '#4338CA',
  'lineColor': '#818CF8',
  'edgeLabelBackground': '#EEF2FF',
  'fontFamily': 'ui-sans-serif, system-ui',
  'fontSize': '13px'
}}}%%
stateDiagram-v2
  [*] --> Idle

  state "Processing" as Processing {
    [*] --> Validating
    Validating --> Executing : valid
    Validating --> [*] : invalid / emit error
    Executing --> [*] : complete
  }

  Idle --> Processing : job submitted
  Processing --> Idle : success
  Processing --> Failed : timeout / exception

  state Failed {
    [*] --> Retrying
    Retrying --> [*] : max retries exceeded
  }

  Failed --> Idle : reset
  Failed --> [*] : abandoned
```

---

## Template D: ER / Database Schema

```mermaid
%%{init: {'theme': 'base', 'themeVariables': {
  'primaryColor': '#0F4C81',
  'primaryTextColor': '#fff',
  'primaryBorderColor': '#1a6abf',
  'lineColor': '#4A90D9',
  'edgeLabelBackground': '#EBF4FF',
  'fontFamily': 'ui-monospace, monospace',
  'fontSize': '13px'
}}}%%
erDiagram
  USER {
    uuid   id         PK
    string email      UK
    string name
    ts     created_at
  }
  SUBSCRIPTION {
    uuid   id         PK
    uuid   user_id    FK
    string plan
    ts     expires_at
  }
  POST {
    uuid   id         PK
    uuid   author_id  FK
    string title
    text   body
    ts     published_at
  }
  TAG {
    uuid   id   PK
    string name UK
  }
  POST_TAG {
    uuid post_id FK
    uuid tag_id  FK
  }

  USER         ||--o{ SUBSCRIPTION : has
  USER         ||--o{ POST         : writes
  POST         }o--o{ TAG          : via
  POST_TAG     }|--|| POST         : joins
  POST_TAG     }|--|| TAG          : joins
```

---

## Node Shape Reference

| Shape | Syntax | Use For |
|---|---|---|
| Rectangle | `A[Label]` | Default / process step |
| Rounded rect | `A(Label)` | Start / end / soft step |
| Stadium | `A([Label])` | Terminal / endpoint |
| Subroutine | `A[[Label]]` | Called function / module |
| Cylinder | `A[(Label)]` | Database / storage |
| Circle | `A((Label))` | Event / junction |
| Diamond | `A{Label}` | Decision / condition |
| Hexagon | `A{{Label}}` | Preparation step |
| Parallelogram | `A[/Label/]` | Input / output |
| Trapezoid | `A[/Label\]` | Manual input |

## ER Relationship Reference

| Syntax | Meaning |
|---|---|
| `\|\|--\|\|` | Exactly one — exactly one |
| `\|\|--o{` | Exactly one — zero or more |
| `}o--o{` | Zero or more — zero or more |
| `\|{--\|\|` | One or more — exactly one |
