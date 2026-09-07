# golang.org/x/sync Toolkit, sourcegraph/conc, and sync.Once

| Package | Use for |
|---|---|
| `errgroup` | Parallel work with first-error cancellation propagation |
| `semaphore` | Bounding concurrency (N-at-a-time worker limits) |
| `singleflight` | Collapsing duplicate concurrent calls (cache stampede prevention) |

## errgroup

```go
eg, ctx := errgroup.WithContext(ctx)
for _, item := range items {
    eg.Go(func() error { return process(ctx, item) })
}
if err := eg.Wait(); err != nil { return err }
```

**Panic pitfall**: a panic inside an `eg.Go` goroutine crashes the process — `errgroup` does not recover it. If callers are third-party code or the work is otherwise panic-prone, use `sourcegraph/conc` instead (below).

## sourcegraph/conc — Panic-Safe Goroutine Pools

`errgroup` propagates errors but not panics; `conc` propagates both — a panic in any spawned goroutine is caught, repropagated on `Wait()` with the original stack trace, and no longer takes the whole process down.

```go
import "github.com/sourcegraph/conc/pool"

p := pool.New().WithMaxGoroutines(10).WithErrors().WithContext(ctx)
for _, item := range items {
    item := item
    p.Go(func(ctx context.Context) error { return process(ctx, item) })
}
if err := p.Wait(); err != nil { return err } // also re-panics here if a goroutine panicked
```

Reach for `conc` instead of `errgroup` when: goroutines call code you don't fully trust not to panic, you want bounded concurrency (`WithMaxGoroutines`) without a separate `semaphore`, or you need `conc/iter.Map`/`ForEach` for a simple parallel-map-over-slice instead of hand-rolling the errgroup loop. Stick with plain `errgroup` for simple, already-panic-safe internal code — it's stdlib-adjacent and one less dependency.

## singleflight — Request Coalescing

```go
import "golang.org/x/sync/singleflight"

type Service struct {
    cache sync.Map
    group singleflight.Group
}

func (s *Service) getOrFetch(key string) (string, error) {
    if v, ok := s.cache.Load(key); ok {
        return v.(string), nil
    }
    v, err, _ := s.group.Do(key, func() (any, error) {
        result, err := expensiveFetch(key)
        if err == nil {
            s.cache.Store(key, result)
        }
        return result, err
    })
    if err != nil {
        return "", err
    }
    return v.(string), nil
}
```

**Panic propagation (production critical)**: If the executing goroutine panics, the panic is propagated to ALL waiting goroutines for that key. Wrap the inner function with `recover` if panics are possible.

**Cache invalidation**: Call `group.Forget(key)` to allow the next call for that key to re-execute.

**At extreme scale**: `singleflight.Group` uses a single global mutex over the key map. Under very high goroutine concurrency, consider `github.com/tarndt/shardedsingleflight`.

## sync.Once

```go
var (
    instance *Service
    once     sync.Once
)

func GetService() *Service {
    once.Do(func() { instance = &Service{...} })
    return instance
}
```
