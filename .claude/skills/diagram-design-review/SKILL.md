---
name: diagram-design-review
description: Review an existing diagram (mermaid or otherwise) in a design doc for communication quality — legend, consistent shape/color notation, right abstraction level (C4 or equivalent), and readability once rendered (e.g. rasterized into a Google Doc). Use when asked to review, critique, or improve a diagram already in a doc. For diagram syntax/styling on a NEW diagram use mermaid-diagrams; for deciding whether a section of prose should become a diagram at all use design-doc-review:visuals.
---

# Diagram design review

Most diagram problems aren't syntax problems — the mermaid renders fine and is still hard to read.
This skill checks the things that make a diagram *communicate*, not just compile.

## Checklist

1. **Legend, if notation isn't self-evident.** Any diagram using more than 2 distinct shapes or more
   than 2 non-default colors needs a legend mapping each one to its meaning. "The reader can infer
   it" is not a legend. Exception: a single, universally-understood convention (e.g. a cylinder =
   datastore) doesn't need a legend entry on its own, but stop using that exception once a second
   shape/color joins it.

2. **Shape carries meaning, consistently.** Pick a shape-to-concept mapping once and hold it for the
   whole doc (ideally the whole doc set):
   - Rectangle: process / service / component
   - Cylinder: datastore
   - Hexagon: external system / third-party boundary
   - Rounded rectangle / stadium: event, message, or queue
   - Diamond: decision point (flowcharts only)
   A component that's sometimes a plain rectangle and sometimes a rounded one with no reason is a
   tell that shapes were chosen for layout, not meaning — fix that before anything else.

3. **Color carries meaning, not decoration.** Color should map to a dimension the reader needs (new
   vs. existing, this-team-owns vs. that-team-owns, sync vs. async) — never "this looked nice."
   If two colors don't map to anything, merge them. If the doc already has a status/ownership
   convention (e.g. this repo's Rollout tables), reuse those colors in diagrams instead of inventing
   new ones — consistency across the doc beats a diagram that's pretty in isolation.

4. **Ownership/trust boundary is explicit, not inferred from labels.** If the diagram spans more
   than one owner — services you run, a platform team's managed service, a third-party/cloud
   provider (AWS, etc.) — that boundary needs to be visible as a grouping (a subgraph/boundary box,
   per C4's system-boundary convention), not buried in each node's text. Don't reuse the
   existing/new fill color for this — ownership and build-status are independent dimensions, and
   collapsing them into one color forces the reader to guess which one they're looking at. A
   diagram with only one owner throughout doesn't need this at all.

5. **Right abstraction level for the audience — use C4 as the default framework.**
   [C4](https://c4model.com/) gives four zoom levels; pick the one matching what the reader needs to
   decide, not the one that happens to match what you drew first:
   - **Context**: this system + the other systems/people it talks to. For "why does this exist" /
     executive or cross-team audiences.
   - **Container**: the deployable/runnable pieces inside the system (services, DBs, queues) and how
     they talk. For "how is this built" / the working-group audience most design docs target.
   - **Component**: the internal modules of one container. Only include this if the review is
     evaluating that container's internal design, not the system as a whole.
   - **Code**: class/interface level. Almost never belongs in a design doc — this is what a detailed
     design doc's own code snippets are for.
   A diagram mixing levels (e.g. a Container-level box next to a Code-level class name) is confusing
   regardless of styling — split it into two diagrams at two levels instead of merging them.
   C4 is the default, not mandatory: a sequence diagram is still right for "what's the order of
   calls," and a state diagram is still right for "what states can this be in" — C4 governs the
   *system-structure* diagrams specifically, per `mermaid-diagrams`'s type-selection table.

6. **Caption ties the diagram to the claim it supports.** A diagram with no caption sentence forces
   the reader to reverse-engineer why it's there. One sentence, right above or below: what point in
   the prose this diagram is illustrating (see `design-doc-review:visuals` for when a diagram should
   exist at all; this step is about a diagram that already exists).

7. **Readability once rendered, not just in source.** If this diagram will be rasterized on publish
   (mermaid → static PNG on a Google Docs push, e.g. via docspan — see
   [docspan#134](https://github.com/tstapler/docspan/issues/134) for a concrete case of this going
   wrong), check for the failure modes that only show up after rendering, not in the mermaid source:
   - More than ~10-12 nodes flat in one diagram — text shrinks to fit, becomes illegible at normal
     doc zoom. Split into subgraphs or multiple diagrams instead.
   - Long edge labels on a wide flowchart — they either get clipped or force the whole diagram to
     scale down to fit the page width.
   - Don't assume centering/sizing happened correctly after a push — that's an infrastructure
     concern for the publishing tool, not something fixable by editing the diagram, but a diagram
     with fewer nodes and shorter labels degrades more gracefully when the renderer doesn't get it
     right.

## Output

Report findings against the checklist above, most-impactful first (legend/shape/color confusion
before rendering nitpicks). For each finding: what's wrong, why it costs the reader something
concrete (not "could be better"), and the specific fix. Apply fixes directly if asked to fix, not
just review.
