# Rung 7: Lock-Free Queues and Ring Buffers

Only reach here after profiling shows a genuine MPMC queue is the bottleneck. Never start at this rung — lock-free data structures fix a narrow problem and are easy to misapply.

## Workiva/go-datastructures (preferred)

Bounded MPMC ring buffer with blocking semantics and `Dispose()` for clean shutdown:

```go
import "github.com/Workiva/go-datastructures/queue"

rb := queue.NewRingBuffer(1024) // capacity must be power of 2
rb.Put(item)   // blocks if full
rb.Get()       // blocks if empty
rb.Dispose()   // unblocks all waiters — call on shutdown
```

## golang-design/lockfree

Unbounded lock-free queue/stack. No `Dispose()` — own your shutdown coordination:

```go
import "github.com/golang-design/lockfree"

q := lockfree.NewQueue()
q.Enqueue(item)
v := q.Dequeue() // nil if empty
```

## What lock-free structures do NOT fix

A lock-free queue passes items between producers and consumers. It is **not** a substitute for a mutex guarding mutable struct fields. If many goroutines read/write fields on a shared object, the fix is copy-on-write (see [Atomics and Copy-on-Write](atomics-and-copy-on-write.md)) or `RWMutex` (see [Mutexes and Concurrent Maps](mutexes-and-concurrent-maps.md)) — not a lock-free queue.
