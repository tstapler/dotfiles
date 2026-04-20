# Error Patterns Reference

Technology-specific error signatures and investigation patterns.

## Java/Kotlin/JVM

### Common Error Types

| Error | Root Cause Pattern | Wiki Search | External Search |
|-------|-------------------|-------------|-----------------|
| `NullPointerException` | Uninitialized object, missing dependency injection | `[Service] null` OR `NPE` | `java NullPointerException [context]` |
| `OutOfMemoryError: Java heap space` | Memory leak, undersized heap | `OOM heap [service]` | `java heap space tuning` |
| `OutOfMemoryError: Metaspace` | Too many classes loaded, classloader leak | `metaspace [service]` | `java metaspace leak` |
| `StackOverflowError` | Infinite recursion | `stackoverflow [method]` | `java recursion depth` |
| `ClassNotFoundException` | Missing dependency, classpath issue | `ClassNotFound [class]` | `[framework] ClassNotFoundException` |
| `NoSuchMethodError` | Version mismatch, incompatible JAR | `NoSuchMethod [method]` | `java version conflict [library]` |
| `ConcurrentModificationException` | Modifying collection during iteration | `ConcurrentModification` | `java thread-safe collection` |

### Spring Boot Patterns

| Error | Root Cause | Investigation |
|-------|-----------|---------------|
| `BeanCreationException` | Circular dependency, missing bean | Search: `circular dependency` OR `@Bean [name]` |
| `NoUniqueBeanDefinitionException` | Multiple beans of same type | Search: `@Qualifier` OR `@Primary` |
| `ApplicationContextException` | Configuration error | Search: `@Configuration [service]` |

### Stack Trace Extraction

```
Key frames to search (ignore framework internals):
- First frame in your package: com.company.service.MyClass.method
- Last frame before exception: Often contains the actual bug
- "Caused by" chain: Each level may reveal different issues
```

## Python

### Common Error Types

| Error | Root Cause Pattern | Wiki Search | External Search |
|-------|-------------------|-------------|-----------------|
| `TypeError: 'NoneType'` | Null/None handling | `None type [function]` | `python NoneType error` |
| `ImportError/ModuleNotFoundError` | Missing package, path issue | `import [module]` | `python install [package]` |
| `AttributeError` | Wrong type, missing attribute | `AttributeError [class]` | `python [class] attributes` |
| `KeyError` | Missing dictionary key | `KeyError [key]` | `python dict get default` |
| `RecursionError` | Infinite recursion | `RecursionError` | `python recursion limit` |
| `MemoryError` | Large data, memory leak | `MemoryError` | `python memory profiling` |

### Async/Await Patterns

| Error | Root Cause | Investigation |
|-------|-----------|---------------|
| `RuntimeError: Event loop closed` | Improper async cleanup | Search: `asyncio event loop` |
| `RuntimeError: no running event loop` | Mixing sync/async | Search: `asyncio.run` OR `await` |
| `TimeoutError` in async | Slow I/O, deadlock | Search: `asyncio timeout` |

## Kubernetes/Container

### Pod Status Errors

| Status | Root Cause | Wiki Search | External Search |
|--------|-----------|-------------|-----------------|
| `OOMKilled` | Container memory limit exceeded | `OOMKilled [service]` | `kubernetes memory limits` |
| `CrashLoopBackOff` | Application crash on startup | `CrashLoopBackOff [service]` | `kubernetes crashloop debug` |
| `ImagePullBackOff` | Image not found, auth issue | `ImagePull [image]` | `kubernetes image pull secret` |
| `Pending` | Resource constraints, node selector | `Pending [service]` | `kubernetes pod pending` |
| `ContainerCreating` stuck | Volume mount, init container | `ContainerCreating` | `kubernetes volume mount` |

### Event Patterns

```bash
# Search wiki for k8s events
Grep pattern="Warning.*FailedScheduling|Warning.*FailedMount" path="logseq/"
Grep pattern="Back-off.*restarting" path="logseq/"
```

### Resource Issues

| Symptom | Root Cause | Investigation |
|---------|-----------|---------------|
| Evicted pods | Node pressure | Search: `eviction [node]` OR `disk pressure` |
| Slow scheduling | Resource fragmentation | Search: `scheduling [cluster]` |
| Network timeouts | CNI issues, DNS | Search: `CoreDNS` OR `calico` OR `network policy` |

## PostgreSQL/Database

### Common Errors

| Error | Root Cause | Wiki Search | External Search |
|-------|-----------|-------------|-----------------|
| `FATAL: too many connections` | Connection pool exhaustion | `connection pool [service]` | `pgbouncer configuration` |
| `deadlock detected` | Concurrent transactions | `deadlock [table]` | `postgresql deadlock` |
| `could not serialize access` | Serialization failure | `serialization [table]` | `postgresql isolation level` |
| `canceling statement due to lock timeout` | Long-held locks | `lock timeout` | `postgresql lock monitoring` |
| `out of shared memory` | Too many locks | `shared memory` | `postgresql max_locks` |
| `SQLSTATE 42P01` | Missing table | `[table] not found` | `postgresql create table` |

### Lock Investigation

```bash
# Search for lock-related issues
Grep pattern="deadlock|lock timeout|waiting.*lock" path="logseq/" -i
Grep pattern="pg_locks|pg_stat_activity" path="logseq/"
```

### Connection Issues

```bash
# Search for connection problems
Grep pattern="connection refused|too many connections" path="logseq/" -i
Grep pattern="PGBouncer|connection pool" path="logseq/"
```

## AWS/Cloud

### Common Errors

| Error | Root Cause | Wiki Search | External Search |
|-------|-----------|-------------|-----------------|
| `AccessDeniedException` | IAM permissions | `IAM [service]` OR `permission denied` | `aws iam policy [service]` |
| `ThrottlingException` | Rate limit exceeded | `throttling [service]` | `aws [service] rate limit` |
| `ResourceNotFoundException` | Resource deleted or wrong region | `[resource] not found` | `aws [resource] [region]` |
| `ValidationException` | Invalid input | `validation [api]` | `aws [api] parameters` |

### Service-Specific

| Service | Common Issue | Investigation |
|---------|-------------|---------------|
| Lambda | Timeout, memory | Search: `Lambda timeout` OR `Lambda memory` |
| EKS | Node scaling, IAM | Search: `EKS [cluster]` OR `IRSA` |
| RDS | Connection, storage | Search: `RDS [instance]` OR `storage full` |
| S3 | Access, encryption | Search: `S3 bucket policy` OR `S3 encryption` |

## HTTP/API Errors

### Status Code Investigation

| Code | Meaning | Wiki Search | External Search |
|------|---------|-------------|-----------------|
| 400 | Bad Request | `400 [endpoint]` | `[api] request format` |
| 401 | Unauthorized | `401 auth [service]` | `[service] authentication` |
| 403 | Forbidden | `403 permission` | `[service] authorization` |
| 404 | Not Found | `404 [endpoint]` | `[api] endpoint` |
| 429 | Rate Limited | `429 rate limit` | `[api] rate limit` |
| 500 | Server Error | `500 [service]` | `[service] internal error` |
| 502 | Bad Gateway | `502 gateway` | `nginx bad gateway` |
| 503 | Unavailable | `503 [service]` | `[service] availability` |
| 504 | Timeout | `504 timeout` | `[service] timeout configuration` |

## Error Signature Extraction Examples

### Java Stack Trace
```
java.lang.NullPointerException: Cannot invoke "String.length()" because "str" is null
    at com.example.UserService.validateInput(UserService.java:42)
    at com.example.UserController.createUser(UserController.java:28)

Extract:
- Error: NullPointerException
- Location: UserService.validateInput:42
- Search: "NullPointerException validateInput" OR "UserService null"
```

### Python Traceback
```
Traceback (most recent call last):
  File "/app/service.py", line 45, in process_data
    result = data['missing_key']
KeyError: 'missing_key'

Extract:
- Error: KeyError
- Location: service.py:process_data:45
- Search: "KeyError missing_key" OR "process_data KeyError"
```

### Kubernetes Event
```
Warning  FailedScheduling  pod/my-service-abc123  0/3 nodes are available:
3 Insufficient memory. preemption: 0/3 nodes are available.

Extract:
- Error: FailedScheduling
- Cause: Insufficient memory
- Search: "FailedScheduling memory" OR "my-service resource"
```
