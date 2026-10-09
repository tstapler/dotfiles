# Configuration Composition

Use explicit ordered layers:

```text
typed defaults
→ core conf.d fragments sorted lexically
→ admitted integration fragments sorted by integration ID then filename
→ restricted scalar environment overlay
→ typed, audited runtime overrides
```

Never rely on filesystem enumeration order. State the merge operation for every field:

| Value | Rule |
|---|---|
| scalar | replace |
| map | explicit deep merge or replace |
| list | explicit replace, append, or keyed merge |
| secret | references only; never merge plaintext |

Integration declarations require a stable explicit ID, kind, declared capabilities, non-secret endpoint identity, version compatibility, and secret references. Do not derive durable IDs from array position.

Runtime overrides are a distinct, final layer. Validate schema and authorization, bind each to scope/actor/reason/expiry, write atomically, and expose provenance through an effective-config view. Preserve last known-good effective configuration if a new fragment or override fails validation.

For arrays of integration records, assign one fragment as owner unless keyed merge semantics are deliberately implemented; generic file layering cannot safely infer element identity or deletion rules.
