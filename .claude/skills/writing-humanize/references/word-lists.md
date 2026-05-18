# AI Vocabulary Reference — Flagged Terms and Safe Substitutions

## Tier 1 — Highest Overrepresentation (50–269× in AI vs. human text)

These words appear at rates so elevated that a single instance in a short document is a meaningful signal.

| Flagged Word | Typical AI Usage | Human Alternatives |
|-------------|-----------------|-------------------|
| delve | "delve into the topic" | explore, dig into, look at, examine, trace, unpack |
| realm | "in the realm of possibility" | world, domain, field, area — or restructure the sentence |
| nuanced | "a nuanced approach" | Name what the nuance actually is; cut the word |
| multifaceted | "a multifaceted problem" | Name the facets: "three separate issues" |
| tapestry | "a rich tapestry of..." | Cut; find the concrete noun being decorated |
| robust | "a robust solution" | specific, reliable, load-tested, battle-hardened — or name what it handles |
| pivotal | "a pivotal moment" | decisive, turning-point, the moment everything changed |
| seamless | "seamless integration" | frictionless, invisible, automatic, zero-config |
| leverage | "leverage our expertise" | use, apply, draw on, bring — "leverage" is almost always weaker |
| harness | "harness the power of" | use, capture, direct, apply |
| underscore | "this underscores the need for" | shows, proves, confirms, makes clear |
| testament | "a testament to their commitment" | evidence of, proof that, shows their commitment |
| cutting-edge | "cutting-edge technology" | Name the actual technology; cut the modifier |
| intricate | "intricate details" | complex, layered, involved — or name the specific complexity |

**Usage rule**: One Tier 1 hit in a short document (under 500 words) warrants a flag. Three hits in any document warrants a HIGH risk rating.

## Tier 2 — Structural Transition Overuse

These words are not inherently AI vocabulary, but their placement pattern (starting paragraph boundaries, appearing in runs) is a strong structural signal.

| Word | Signal Pattern | Fix |
|------|---------------|-----|
| moreover | Used to open 2+ consecutive paragraphs | Replace with a direct pivot sentence that earns the transition |
| furthermore | Used mid-paragraph to add a second point | Restructure as a new sentence or use a dash |
| additionally | Used as default paragraph bridge | Cut and re-order; let the logic speak |
| it is worth noting | Throat-clearing hedge before an important point | State the point directly; cut the throat-clear |
| notably | Overused to flag emphasis | Cut; let the sentence carry its own weight |
| importantly | Same as notably | Cut |

**Usage rule**: Flag any document where 3+ consecutive paragraphs open with one of these words, or where any single one appears 3+ times.

## Em Dash Overuse

AI models — including Claude — have a statistically measurable em dash overuse pattern specifically where a comma or period would be natural.

**Flag**: More than 1 em dash per 150 words on average, OR any sentence with 2 em dashes where neither creates genuinely parenthetical emphasis.

**Test**: For each em dash, ask: does this mark a genuine interruption, a parenthetical aside, or an appositive? If a comma or period works equally well, replace it.

## Hedging Density Threshold

Count per 300 words of the following hedge markers:

- might, could, arguably, perhaps, seemingly, potentially, it's important to note, one might argue, it can be said that, in many ways, in some sense

**Threshold**: More than 3 per 300 words signals AI hedging pattern.

**Fix**: For each hedge, make a binary choice — commit to the claim, or cut it. Occasional hedging is human. Pervasive hedging is not.

## Abstract Nominalization List

Nominalizations hide who did what. AI defaults to them. Flag these when a verb form exists:

| Nominalization | Preferred Form |
|---------------|---------------|
| implementation | implemented, we built, they shipped |
| utilization | use, used |
| optimization | sped up, reduced by X%, improved |
| facilitation | helped, enabled, made possible |
| collaboration | worked with, built together with |
| enhancement | improved, fixed, added |
| integration | connected, linked, embedded |
| transformation | changed, rebuilt, rewrote |
| initialization | started, launched, set up |
| configuration | set up, configured as, tuned |

**Flag rule**: More than 2 nominalizations per paragraph, or any nominalization hiding a named agent ("The implementation team" → "Sarah's team").

## Safe Vocabulary — What Human Writing Uses Instead

When replacing Tier 1 words, prefer:

- **Specificity over category**: "three engineers" not "the team"; "15% throughput gain" not "significant improvement"
- **Verbs over noun phrases**: "we shipped" not "the shipping was completed"
- **Concrete objects**: "the API key was hardcoded in production" not "a security vulnerability was identified"
- **Named people**: "Priya rewrote the parser" not "the parser was improved"
- **Specific times**: "in Q3 2023" not "recently"

## Register Notes

Substitutions must match the register of the source text:

- Academic/formal: prefer technical precision, not colloquial substitutes
- Cover letter/professional: prefer active, first-person, specific — not either extreme
- Blog/casual: contractions, sentence fragments for emphasis, rhetorical questions are human signals
- Technical documentation: precision and directness; avoid hedging entirely

Human technical writing is often blunter than AI writing. "This breaks if X" not "It is worth noting that X may cause issues."
