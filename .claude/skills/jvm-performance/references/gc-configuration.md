# GC Configuration

When allocation reduction is not enough, tune the GC. Run `jfrconv --gc` (or check `jstat -gcutil`) to confirm GC is the problem before touching flags.

## GC selection

| Workload | GC | Minimum flags |
|---|---|---|
| General server app | G1GC (default JDK 9+) | `-Xms=Xmx -XX:MaxGCPauseMillis=200` |
| Latency-sensitive (< 1ms pauses) | ZGC | `-XX:+UseZGC` (JDK 23+ gen by default) |
| Max throughput, pauses acceptable | Parallel GC | `-XX:+UseParallelGC` |
| Batch / single-core container | Serial GC | `-XX:+UseSerialGC` |

## G1GC production baseline
```bash
-XX:+UseG1GC
-Xms4g -Xmx4g                     # fix heap — eliminate resize pauses
-XX:MaxGCPauseMillis=200          # target (not guaranteed)
-XX:G1HeapRegionSize=16m          # increase if > 50% of regions are "humongous"
-XX:G1NewSizePercent=20
-XX:G1MaxNewSizePercent=40
-Xlog:gc*:file=gc.log:time,uptime # always log
```

## ZGC production baseline (JDK 21+)
```bash
-XX:+UseZGC                        # generational by default JDK 23+; add -XX:+ZGenerational on JDK 21
-Xms4g -Xmx4g
-XX:SoftMaxHeapSize=3500m          # leave headroom for concurrent marking
-Xlog:gc*:file=gc.log:time,uptime
```

## Common GC symptoms and fixes

| GC log symptom | Cause | Fix |
|---|---|---|
| Frequent young GCs | High allocation rate | Profile alloc hotspots; apply allocation/GC patterns |
| G1 "humongous allocation" | Object > 50% region size | Increase `-XX:G1HeapRegionSize` or reduce object |
| `Concurrent Mode Failure` | GC falling behind allocation | Increase heap; reduce allocation rate |
| `CodeCache is full` | JIT cache exhausted | `-XX:ReservedCodeCacheSize=512m` |
| Metaspace OOM | Class loader leak / many dynamic classes | `-XX:MaxMetaspaceSize=512m`; fix leak |
| Full GC on startup only | Small initial heap forces resize | Set `-Xms` == `-Xmx` |
