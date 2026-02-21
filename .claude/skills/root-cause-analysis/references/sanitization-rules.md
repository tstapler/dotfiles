# Sanitization Rules for External Search

Rules for removing sensitive information before web searches.

## Critical: Always Sanitize Before Web Search

External searches (Brave Search, Google, Stack Overflow) should NEVER contain:
- Credentials (API keys, tokens, passwords)
- Internal infrastructure details
- Customer/user identifiers
- Proprietary code patterns

## Sanitization Patterns

### Credentials and Secrets

| Pattern | Example | Sanitize To |
|---------|---------|-------------|
| API Keys | `sk-abc123...`, `AKIA...` | `[API_KEY]` |
| Bearer Tokens | `Authorization: Bearer eyJ...` | `[AUTH_TOKEN]` |
| Passwords | `password=mysecret123` | `[PASSWORD]` |
| Connection Strings | `postgresql://user:pass@host/db` | `postgresql connection string` |
| AWS Secrets | `aws_secret_access_key=...` | `[AWS_SECRET]` |
| Private Keys | `-----BEGIN RSA PRIVATE KEY-----` | `[PRIVATE_KEY]` |

### Infrastructure Details

| Pattern | Example | Sanitize To |
|---------|---------|-------------|
| Internal Hostnames | `db.internal.company.com` | `[internal hostname]` |
| Private IPs | `10.0.1.45`, `192.168.x.x` | `[internal IP]` |
| AWS Account IDs | `arn:aws:iam::123456789012:...` | `AWS IAM ARN` |
| K8s Namespaces | `fbg-prod-1`, `fbg-dev-1c` | `[k8s namespace]` |
| Internal URLs | `https://internal.company.com/api/v1` | `[internal API endpoint]` |
| Database Names | `prod_users_db`, `customers_rds` | `[database]` |

### Customer/User Data

| Pattern | Example | Sanitize To |
|---------|---------|-------------|
| User IDs | `user_id: 12345678` | `[user_id]` |
| Email Addresses | `john.doe@customer.com` | `[email]` |
| Account Numbers | `account: ACC-123456` | `[account_id]` |
| Transaction IDs | `txn_abc123def456` | `[transaction_id]` |
| Session IDs | `session: sess_xyz789` | `[session_id]` |

### Proprietary Code

| Pattern | Example | Sanitize To |
|---------|---------|-------------|
| Internal Package Names | `com.company.internal.service` | `[internal package]` |
| Custom Class Names | `FBGUserAuthenticator` | `custom authenticator class` |
| Internal Method Names | `reconcileBetSettlements()` | `reconciliation method` |
| Business Logic | `calculateOddsWithVig()` | `odds calculation` |

## Regex Patterns for Detection

### Credential Detection

```regex
# AWS Keys
AKIA[0-9A-Z]{16}
aws_secret_access_key\s*=\s*\S+

# Generic API Keys
['"](sk|pk|api|key|token|secret|password|auth)[_-]?[a-zA-Z0-9]{16,}['"]

# Bearer Tokens
Bearer\s+[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+

# Connection Strings
(postgres|mysql|mongodb|redis)://[^@]+@[^\s]+
```

### Infrastructure Detection

```regex
# Internal Hostnames
[a-z0-9-]+\.(internal|corp|local|private)\.[a-z]+

# Private IPs
(10\.\d{1,3}\.\d{1,3}\.\d{1,3}|172\.(1[6-9]|2[0-9]|3[01])\.\d{1,3}\.\d{1,3}|192\.168\.\d{1,3}\.\d{1,3})

# AWS ARNs
arn:aws:[a-z0-9-]+:[a-z0-9-]*:\d{12}:
```

### PII Detection

```regex
# Email
[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}

# Phone (US)
\+?1?[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}

# SSN
\d{3}-\d{2}-\d{4}
```

## Sanitization Process

### Step 1: Identify Sensitive Elements

Scan the error message or search query for:
1. Known credential patterns
2. Internal infrastructure references
3. Customer identifiers
4. Proprietary terminology

### Step 2: Replace with Generic Terms

```
Before: "ConnectionRefused to db.internal.company.com:5432 user prod_app"
After:  "PostgreSQL ConnectionRefused [internal hostname]:5432"

Before: "NullPointerException at com.company.auth.FBGUserAuth.validate()"
After:  "Java NullPointerException in authentication validation"

Before: "Failed to authenticate user_id: 12345678 with token eyJ..."
After:  "Authentication failure for user"
```

### Step 3: Verify Before Searching

Checklist before external search:
- [ ] No API keys or tokens
- [ ] No internal hostnames or IPs
- [ ] No customer identifiers
- [ ] No proprietary class/method names
- [ ] No database or table names
- [ ] Generic technology terms used

## Safe Search Patterns

### Technology + Error Type

```
Safe: "Java NullPointerException validation"
Safe: "PostgreSQL connection refused timeout"
Safe: "Kubernetes OOMKilled container"
Safe: "Spring Boot BeanCreationException circular"
```

### Library + Version + Issue

```
Safe: "Flyway 11.20 executeInTransaction false"
Safe: "Spring Boot 3.2 actuator health check"
Safe: "PostgreSQL 15 deadlock detection"
```

### Generic Problem Descriptions

```
Safe: "database connection pool exhaustion"
Safe: "kubernetes pod memory limits"
Safe: "java heap space tuning"
Safe: "async/await deadlock python"
```

## Examples: Before and After

### Example 1: Database Error

**Original:**
```
FATAL: too many connections for role "prod_app_user"
  at connection pool to db-prod-rds.us-east-2.rds.amazonaws.com:5432/users_prod
```

**Sanitized for search:**
```
PostgreSQL "too many connections for role" connection pool RDS
```

### Example 2: Authentication Error

**Original:**
```
AuthenticationException: Failed to validate token eyJhbGciOiJSUzI1NiIs...
  for user_id 98765432 against https://auth.internal.company.com/oauth2/token
```

**Sanitized for search:**
```
JWT authentication validation failed OAuth2
```

### Example 3: Kubernetes Error

**Original:**
```
Warning FailedScheduling pod/ats-sportsbook-api-7b8f9c-abc12 in fbg-prod-1
  0/50 nodes available: 25 Insufficient memory, 25 node(s) had taint
  node.kubernetes.io/disk-pressure
```

**Sanitized for search:**
```
Kubernetes FailedScheduling "Insufficient memory" "disk-pressure" taint
```

## Categories: Never Search Externally

### Absolute No-Go

- Production credentials of any kind
- Customer PII (names, emails, addresses)
- Financial data (account numbers, transactions)
- Security vulnerabilities before patched
- Internal architecture diagrams or descriptions
- Compliance-sensitive information (PCI, HIPAA, SOC2)

### Conditional (Internal Review First)

- Performance metrics that reveal scale
- Error rates that indicate reliability issues
- Architecture patterns unique to organization
- Custom tooling implementations
