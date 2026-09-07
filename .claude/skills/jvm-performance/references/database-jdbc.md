# Database / JDBC

## What you see in the profile
- `DriverManager.getConnection` or `HikariPool.getConnection` in hot path → no pool / pool exhausted
- `PreparedStatement.execute` compiling SQL on every call → no statement cache
- N×M individual inserts for a batch operation → missing `executeBatch()`

## HikariCP minimum correct configuration
```kotlin
HikariConfig().apply {
    jdbcUrl = "jdbc:postgresql://host/db"
    // CPU * 2 + 1 for I/O-bound workloads (Hikari recommendation)
    maximumPoolSize = 2 * Runtime.getRuntime().availableProcessors() + 1
    minimumIdle = maximumPoolSize   // pre-warm all connections; no ramp-up delay
    connectionTimeout = 30_000
    maxLifetime = 1_800_000         // recycle before DB server drops the connection
    cachePrepStmts = true
    prepStmtCacheSize = 250
    prepStmtCacheSqlLimit = 2048
}
```

## Batch inserts — order-of-magnitude faster than row-by-row
```kotlin
// ❌ N round-trips
for (item in items) db.insert(item)

// ✅ 1 round-trip
connection.prepareStatement("INSERT INTO items (id, name) VALUES (?, ?)").use { stmt ->
    for (item in items) {
        stmt.setInt(1, item.id)
        stmt.setString(2, item.name)
        stmt.addBatch()
    }
    stmt.executeBatch()
}
```

## Read-only transaction hint
```kotlin
connection.isReadOnly = true  // skip undo log writes, may use read-replica
```
