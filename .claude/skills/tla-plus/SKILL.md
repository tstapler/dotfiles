---
name: tla-plus
description: Write, review, or model-check TLA+/PlusCal specs for distributed systems — leader election, consensus (Raft-style), message passing, network partitions/reordering/loss, crash-restart, clocks, CAS/optimistic-concurrency fields. Use whenever the user asks to model a protocol formally, write a TLA+ spec, run TLC, interpret a TLC counterexample, or asks "does this design have a race/lost-update/split-brain bug" for a distributed or concurrent system. Also use before trusting a spec's "no error found" result, or when reviewing someone else's .tla file.
---

# TLA+ for distributed systems

TLA+ specs earn their keep on exactly one class of bug: the one that only shows up on a specific
interleaving of concurrent/asynchronous events (a message arriving late, two writers racing, a
crash between two steps assumed atomic together). A unit test picks one ordering and asserts on
it; TLC (the model checker) explores *every* ordering the model allows, up to a size bound, and
reports the first one that breaks a stated property. If the task isn't shaped like that — no
concurrency, no partial failure, no asynchrony — a spec is overkill; say so rather than modeling it
anyway.

## Mental model, in one pass

A spec has three ingredients:
- **VARIABLES** — the state you're tracking (a counter, a message queue, `crashed[n]`, `leader`).
- **Actions** — atomic, guarded transitions (`Send`, `Receive`, `Crash`, `Vote`). Each is a
  predicate over unprimed (current) and primed (next) state; every variable not explicitly changed
  must be listed under `UNCHANGED`, or the action implicitly forbids any other value for it.
- **Invariants / properties** — what must hold in *every* reachable state (safety), or eventually
  (liveness, which needs fairness — see below).

TLC generates every state reachable from `Init` by every legal action sequence, bounded by the
constants in the `.cfg`, and checks each property in every one. "No error has been found" means
the property held in every state TLC could reach *under those specific constants and constraints*
— it is bounded evidence, not a universal proof. Say so explicitly when reporting results; don't
let "TLC verified it" imply more than it does. (Genuinely unbounded guarantees are what TLAPS, the
TLA+ Proof System, is for — a much larger investment, rarely worth it outside safety-critical
infrastructure.)

## Modeling idioms for distributed systems

Model the network as **global shared state that only certain actions can touch**, not as literal
sockets/RPCs — that's the actual substrate TLA+ specs use, and it's usually the right level of
abstraction. The most common beginner error is **illegal knowledge**: a guard that reads state no
real process could observe atomically (checking another node's private variable directly instead
of via a message it actually received). That silently makes the model *stronger* than reality and
hides real bugs — every guard should depend only on state the modeled process could actually know.

**Asynchronous message passing** — represent in-flight messages as a set (unordered — this is what
forces the protocol to handle reordering instead of assuming FIFO) or, when order matters, a
per-channel sequence:
```tla
Send(m)    == msgs' = msgs \union {m}
Receive(m) == /\ m \in msgs
              /\ msgs' = msgs \ {m}        \* remove on receive: no duplication
```
- **Duplication (at-least-once)**: don't remove `m` from `msgs` on receive, or requeue it after
  processing — either way the same message can be delivered again.
- **Loss (at-most-once)**: on receive, nondeterministically branch between the normal case and one
  that advances past the message without applying it.
- **Reordering**: automatic if `msgs` is a set rather than a sequence — don't reach for a sequence
  unless FIFO is actually a real property of the transport being modeled.
- **Pub/sub fan-out**: a function `queues == [r \in Readers |-> <<>>]`, delivered via
  `queues := [r \in Readers |-> Append(queues[r], d)]`.

**Network partitions**: a reachability/connectivity predicate gating which `Send`/`Receive` pairs
are enabled between which nodes — not a first-class "Partition" object. Model it as a constraint on
existing actions, the same way you'd model a firewall rule.

**Crash / restart** (the canonical idiom — confirmed against Raft reference specs):
```tla
Crash(n)   == /\ ~crashed[n]
              /\ crashed' = [crashed EXCEPT ![n] = TRUE]
              /\ UNCHANGED durableVars           \* durable state survives a crash
              /\ volatileVars' = [volatileVars EXCEPT ![n] = ResetValue]

Restart(n) == /\ crashed[n]
              /\ crashed' = [crashed EXCEPT ![n] = FALSE]
              /\ UNCHANGED durableVars
```
Gate every other per-node action with `~crashed[n]`. Split your variables into durable vs. volatile
up front — that split is what makes `Crash`/`Restart` a one-line `UNCHANGED` instead of a bespoke
mess per action. (A *permanent* crash needs no explicit variable — TLA+'s stuttering already allows
a process to take no visible step forever — but a temporary one that can later resume needs
`crashed[n]` explicitly.)

**Leader election / consensus (Raft-style)**: model one action per protocol message type
(`RequestVote`, `AppendEntries`, ...), each an atomic guarded transition; keep persistent state
(log, currentTerm, votedFor) separate from volatile/derived state precisely so `Crash` can
`UNCHANGED` the former. Compress "timer fires, then send RequestVote" into a single action rather
than modeling a timer separately, and let a server vote for itself directly instead of round-
tripping a self-addressed message — both cut state-space bloat without losing the property you're
checking. Reference specs worth reading before writing your own:
[ongardie/raft.tla](https://github.com/ongardie/raft.tla),
[heidihoward/leaderelection-tlaplus](https://github.com/heidihoward/leaderelection-tlaplus).

**Logical/vector clocks**: a scalar Lamport clock generalizes to a length-N vector. `Send`
increments the sender's own entry and stamps the message with the result; `Receive` takes the
pairwise max of the local vector and the incoming timestamp, then increments the receiver's own
entry so the new clock strictly dominates both priors. The same construction gives you version
vectors for replica/causality tracking (N = replica count instead of process count).

## Structuring the spec

- **CONSTANTS vs VARIABLES**: constants are the fixed parameters of a *class* of systems (node set,
  `MaxState`, a mode enum like `WriterMode`); variables are what actually evolves. Document
  non-obvious constants with an `ASSUME` clause.
- **Abstraction is the art of knowing what to discard.** Default to omission — add a component
  (a failure mode, a piece of state) only when leaving it out demonstrably breaks the specific
  question you're asking. A model built to check "does CAS prevent lost updates" doesn't need a
  faithful Cassandra storage-engine model; it needs a value and a version number.
- **Specify declaratively, not imperatively.** If a spec starts mirroring the real code's control
  flow, loops, and helper functions, you're simulating code, not specifying a system — state what
  must hold, not the steps that achieve it. This is also an argument for plain TLA+ over PlusCal in
  places: PlusCal's sequential-looking syntax nudges toward implementation-shaped thinking even
  when the real system isn't sequential.
- **Trim every variable.** If a value can be derived from other state, derive it in the invariant or
  a `LET`, don't store it — extra variables both enlarge the state space and can hide bugs by
  letting inconsistent combinations arise that a derived value couldn't represent.
- **Atomicity granularity should match the real system's, not be maximally coarse.** Get a coarse
  version passing first, then split one big action into the smaller steps the real system actually
  takes, and re-check. Coarse-grained actions can hide races that would manifest as separate steps
  for real.
- **Group related UNCHANGED variables into a tuple** (`workerState == <<queue, online>>`) once the
  variable count grows — repeating a long `UNCHANGED <<a,b,c,d,...>>` in every action is itself a
  bug magnet (easy to forget one when adding a variable later).

**Common mistakes, roughly in order of how often they bite:**
1. **Under-constraining**: forgetting to forbid a transition that can't happen for real, so TLC
   explores a physically-impossible trace and "finds" a bug that isn't real (or misses a real
   invariant violation behind a spurious one). More common than over-constraining for newcomers.
2. **Over-constraining via illegal knowledge** (see above) — hides real bugs instead of manufacturing
   fake ones, which makes it more dangerous even though it's rarer.
3. **Trivial/end-state-only "invariants"** — a property that's vacuously always true, or that only
   encodes a desired final state rather than something checkable at every reachable state. Ask of
   every invariant: "would this be false if the protocol were subtly broken?"
4. **While-loops in PlusCal for pure computation** — creates one new state per iteration for
   something that could be a single-step whole-structure update. Prefer set/function comprehensions.
5. **A spec that's "safe" by never making progress** — deadlocking or stalling forever passes every
   safety invariant trivially. Safety alone never rules this out; only a liveness check does.

## Invariants vs. liveness, and fairness

- Write `TypeOK` first, before any correctness invariant. TLA+ is untyped, so `TypeOK` is your type
  system and doubles as documentation of the data model. Run it before deeper invariants — same
  reason you'd run a compiler before debugging logic.
- A safety invariant (`Inv == ...`) must hold in every reachable state. A liveness property
  (`<>P`, "eventually P") needs **fairness** to be non-trivial, because without it TLC is always
  allowed to just never take the action that would make P true.
  - `WF_vars(A)` (weak fairness): if `A` becomes *continuously* enabled, it must eventually fire.
  - `SF_vars(A)` (strong fairness): if `A` is *repeatedly* (not necessarily continuously) enabled,
    it must eventually fire. Strictly stronger than WF.
  - Lamport's own rule: use `SF` only when you've confirmed `WF` genuinely isn't enough — a
    liveness result proved under `SF` claims the real implementation must provide the *harder*
    guarantee, which may not be true of the actual system.
  - Liveness checking is much slower than safety checking and incompatible with symmetry-set
    reduction — keep a separate, smaller-constant config for liveness rather than folding it into
    the main safety config.
- Don't skip liveness just because it's more expensive: a spec that only checks safety can pass
  while quietly deadlocking or looping forever, which is its own class of real bug (unavailability),
  just not the one safety invariants catch.

## Model-checking practice

- **Size for tractability deliberately, not by trial and error**: bound constants
  (`MaxState`, node-set size) to the smallest values that still exercise the mechanism you're
  checking; use `SYMMETRY Permutations(Set)` in the `.cfg` for interchangeable processes (but note
  symmetry reduction and liveness checking don't mix); use a `CONSTRAINT` to cap unbounded growth
  (in-flight message count, retry count) rather than letting the state space blow up. Reducing the
  *number* of states matters far more than speeding up per-state computation.
- **Check a small model first, scale up once the spec is stable.** Iterate fast on a cheap config;
  only invest in a larger, slower config once you're not finding new bugs on the small one.
- **Re-run at a larger bound before trusting a result.** A clean run at `MaxState = 2` might be an
  artifact of a state space too small to exercise the real interleavings — bump the bound (e.g. to
  4) and confirm the same invariants hold/fail the same way over the larger space. Cheap insurance:
  TLC runs are usually seconds, and a result that changes under a bigger bound was never solid.
- **Read TLC's per-action coverage stats.** An action reporting zero invocations across the whole
  run is a hard signal — either dead code in the spec or a guard that's accidentally unsatisfiable
  (often the "illegal knowledge" / over-constraining mistake above, caught mechanically).
- **Sabotage test before trusting a passing invariant.** Deliberately break the property being
  checked — remove the mutual-exclusion guard, flip a CAS check to always succeed — and confirm the
  invariant *does* fail. If it doesn't, either the invariant is too weak or the model never
  exercises the path you think it does. "Always be suspicious of success" is the operative rule
  here.
- **Read a counterexample as a reproduction recipe, not a statistic.** TLC reports the minimal
  (shortest) action sequence that breaks the property — a concrete `State 1 -> State 2 -> ...`
  trace naming which action fired and what changed at each step. That's the thing worth quoting
  back in a design doc, not just "TLC found a violation."

## Connecting the model back to real code

A spec that isn't traceable to the real system's actual operations is disconnected fiction — a
correct-sounding story that proves nothing about production. Ground every action in a citation to
the real code it's supposed to represent (file:line, function name) wherever the point is to say
something about an actual system rather than to explore a protocol abstractly. When the real
implementation changes, re-check the citations, not just the .tla file — a spec drifts silently
otherwise. For systems where this matters enough to invest further, conformance checking (capture
real execution traces, translate them into the spec's vocabulary, and verify the spec actually
permits every real trace) is the concrete practice for keeping the two from diverging — see
MongoDB's public writeup, linked below.

**Trace validation, concretely** — the mechanics behind "check the spec against real traces," per
[Cirstea, Kuppe, Loillier & Merz, "Validating Traces of Distributed Programs Against TLA+
Specifications"](https://arxiv.org/abs/2404.16075) (their reference implementation instruments
Java; the technique itself is language-agnostic):
- Frame it as *constrained model checking*, not refinement checking: given the spec's behaviors
  `S` and the trace-compatible behaviors `T` (any variable the trace didn't record is left free),
  success means `S ∩ T ≠ ∅`, deliberately weaker than requiring `T ⊆ S` — full refinement would
  reject an otherwise-valid trace whenever an unrecorded variable's non-deterministically-filled
  value doesn't happen to match what really occurred.
- Instrument only *changes* to spec variables at chosen linearization points (message send/receive,
  lock acquire/release, a commit to stable storage) — not full state snapshots. Those points are
  what "atomic transition" has to mean for the trace to correspond to spec actions at all.
- Drive TLC against the trace with a companion spec, not the original directly: for each spec
  action `A`, define `IsA == IsEvent("A") /\ A` (existentially quantify over `A`'s parameters if
  the trace didn't record them), combine into one `TraceNext`, and check the invariant
  **`[](l < Len(Trace))`** — not liveness (`<>(l >= Len(Trace))` fails on any legitimately-incomplete
  prefix) and not deadlock checking (a trace can legitimately dead-end mid-recording). A clean
  invariant run alone doesn't mean the whole trace matched — check the separate postcondition
  `TraceAccepted == TLCGet("stats").diameter - 1 = Len(Trace)` afterward.
- **Grain-of-atomicity mismatches are the dominant failure mode, ahead of actual logic bugs**: an
  implementation step finer or coarser than the spec's actions (a retried message that shouldn't
  re-fire an already-completed spec action; two spec actions folded into one real step). Fix by
  modeling the fold explicitly with TLC's action composition (`A \cdot B`) or by adjusting what gets
  logged — document the mismatch in the spec rather than silently working around it.
- **Trace precision is a real trade-off, not "more is always better."** Logging only variable names
  or only event names (never both) can blow the constrained state space up to infeasible; a
  well-chosen partial trace (e.g., events plus their arguments, when those determine every
  variable's value uniquely) can be nearly as cheap as full logging. Under-instrumentation's real
  risk isn't just inefficiency — it's a **false pass**: TLC can fill an unrecorded variable with a
  value that never actually occurred, silently accepting a trace that shouldn't have validated.
- Adopted in production CI by etcd (Go) and Microsoft's Confidential Consortium Framework (C++);
  CCF's adoption specifically surfaced safety violations its existing test suite had missed.

## Pre-trust checklist

Before reporting a TLA+ result as evidence for a design decision, confirm:

1. `TypeOK` passes, and was written before the deeper invariants.
2. Coverage is non-trivial — no action reports zero invocations; overall coverage isn't
   suspiciously low.
3. The sabotage test passed — breaking the property on purpose actually breaks the invariant.
4. Every invariant is reachable-state-wide, not a tautology or an end-condition in disguise.
5. Liveness/progress was checked too, not just safety — with its own (smaller) config.
6. Fairness assumptions are stated and are the *minimum* strength needed (`WF` unless `SF` is
   demonstrably required).
7. Bounds/constants are justified and re-checked at a larger value, not just "small enough to
   finish quickly."
8. The result's scope is stated honestly — "no error found under these constants," not
   "proven correct."
9. Every action that matters for the real-system conclusion cites the actual code it models.
10. Explicitly note what's out of scope (failure modes not modeled, reordering not represented,
    reconfiguration not covered) rather than letting silence imply completeness.

## References

- Leslie Lamport — [Safety, Liveness, and Fairness](https://lamport.azurewebsites.net/tla/safety-liveness.pdf); [Model Checking TLA+ Specifications](https://lamport.azurewebsites.net/pubs/yuanyu-model-checking.pdf)
- Newcombe et al. (AWS) — [Use of Formal Methods at Amazon Web Services](https://lamport.azurewebsites.net/tla/formal-methods-amazon.pdf)
- Marc Brooker & Ankush Desai (AWS, 2025) — [Systems Correctness Practices at AWS](https://queue.acm.org/detail.cfm?id=3712057); Brooker's [Getting into formal specification](https://brooker.co.za/blog/2022/07/29/getting-into-tla.html) and [Formal Methods Only Solve Half My Problems](https://brooker.co.za/blog/2022/06/02/formal.html)
- Hillel Wayne — [Designing Distributed Systems with TLA+](https://www.hillelwayne.com/talks/distributed-systems-tlaplus/); [Modeling Message Queues in TLA+](https://www.hillelwayne.com/post/tla-messages/)
- Murat Demirbas — [TLA+ mental models](https://muratbuffalo.blogspot.com/2026/03/tla-mental-models.html); [TLA+ modeling tips](http://muratbuffalo.blogspot.com/2025/12/tla-modeling-tips.html); [Logical/Vector clocks in TLA+/PlusCal](http://muratbuffalo.blogspot.com/2018/01/logical-clocks-and-vector-clocks.html)
- [learntla.com — General Tips](https://learntla.com/topics/tips.html) and [Optimizing Model Checking](https://learntla.com/topics/optimization.html)
- [tlaplus/Examples](https://github.com/tlaplus/Examples) — reference specs and per-spec `manifest.json` metadata convention
- [ongardie/raft.tla](https://github.com/ongardie/raft.tla), [Vanlightly/raft-tlaplus](https://github.com/Vanlightly/raft-tlaplus), [heidihoward/leaderelection-tlaplus](https://github.com/heidihoward/leaderelection-tlaplus)
- [TLA+ Wiki — coverage statistics](https://docs.tlapl.us/using:coverage)
- MongoDB Engineering — [Conformance Checking at MongoDB](https://www.mongodb.com/company/blog/engineering/conformance-checking-at-mongodb-testing-our-code-matches-our-tla-specs)
- Cirstea, Kuppe, Loillier & Merz — [Validating Traces of Distributed Programs Against TLA+ Specifications](https://arxiv.org/abs/2404.16075)
- [Surfing Complexity — TLA+ is hard to learn](https://surfingcomplexity.blog/2018/12/24/tla-is-hard-to-learn/)
