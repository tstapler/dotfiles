# Lock Contention

## What you see in the profile
- `AbstractQueuedSynchronizer.acquire` / `LockSupport.park` prominent in lock profile
- `jfrconv --lock` shows a specific lock dominating wait time
- Throughput drops sharply as thread count increases

## Replace `synchronized` with `ReentrantLock` for try-lock / interruptible patterns
```kotlin
// ❌ synchronized — no timeout, no interruptibility
@Synchronized
fun update(value: Int) { state = compute(value) }

// ✅ ReentrantLock with timeout — caller can give up
private val lock = ReentrantLock()

fun update(value: Int): Boolean {
    if (!lock.tryLock(100, TimeUnit.MILLISECONDS)) return false
    return try { state = compute(value); true }
    finally { lock.unlock() }
}
```

## StampedLock for read-heavy shared state
```kotlin
private val lock = StampedLock()
private var cachedValue = 0

// Optimistic read — no lock acquired, no contention
fun read(): Int {
    val stamp = lock.tryOptimisticRead()
    val value = cachedValue
    if (lock.validate(stamp)) return value          // fast path: no write occurred
    val readStamp = lock.readLock()                 // fallback: full read lock
    return try { cachedValue } finally { lock.unlockRead(readStamp) }
}

fun write(v: Int) {
    val stamp = lock.writeLock()
    try { cachedValue = v } finally { lock.unlockWrite(stamp) }
}
```

## Lock striping — reduce contention on shared maps
```kotlin
// ❌ One lock for all keys — every thread serializes
class Cache<K, V> {
    @Synchronized fun get(key: K): V? = map[key]
}

// ✅ 16 independent locks — ~16x less contention
class StripedCache<K, V>(stripes: Int = 16) {
    private val locks = Array(stripes) { ReentrantLock() }
    private val maps  = Array(stripes) { HashMap<K, V>() }
    private fun idx(key: K) = key.hashCode().and(0x7FFFFFFF) % stripes

    fun get(key: K): V? {
        val i = idx(key); locks[i].lock()
        return try { maps[i][key] } finally { locks[i].unlock() }
    }
    fun put(key: K, value: V) {
        val i = idx(key); locks[i].lock()
        try { maps[i][key] = value } finally { locks[i].unlock() }
    }
}
```

## Replace synchronized shared state with coroutine actor
For Kotlin code where multiple coroutines update shared state:
```kotlin
// ❌ Mutex around every state access
private val mutex = Mutex()
private var count = 0
suspend fun increment() = mutex.withLock { count++ }

// ✅ Actor owns the state — no shared mutable state, no locks
sealed interface CounterMsg
data object Increment : CounterMsg
class GetValue(val reply: CompletableDeferred<Int>) : CounterMsg

class Counter(scope: CoroutineScope) {
    private val channel = scope.actor<CounterMsg> {
        var count = 0
        for (msg in channel) when (msg) {
            Increment -> count++
            is GetValue -> msg.reply.complete(count)
        }
    }
    suspend fun increment() = channel.send(Increment)
    suspend fun value(): Int = CompletableDeferred<Int>().also { channel.send(GetValue(it)) }.await()
}
```

## Virtual thread + synchronized (JDK version matters)
```kotlin
// JDK 21–23: synchronized around blocking I/O pins the carrier thread
// → Replace with ReentrantLock if using virtual threads

// JDK 24+: synchronized is fixed (JEP 491) — pinning removed
// → No change needed
```
