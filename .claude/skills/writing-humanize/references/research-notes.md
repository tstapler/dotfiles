# AI Detection Research Notes

## How GPTZero Works

GPTZero and similar detectors use two primary statistical signals derived from language model probability distributions.

### Perplexity

**Definition**: The average negative log-likelihood of the next token given the context. Lower perplexity = the model found each word predictable.

**Why AI scores low**: Language models generate text by selecting high-probability tokens. The output is by construction less surprising than human word choices, which are shaped by personal vocabulary, regional dialect, emotional state, and idiosyncratic associations.

**What raises perplexity (makes text more human)**:
- Uncommon but precise word choices ("the ventilation duct" not "the air system")
- Personal vocabulary that doesn't appear in generic training corpora
- Field-specific jargon used correctly in unexpected contexts
- Syntactic constructions that deviate from default SVO patterns

**What destroys perplexity (AI tell)**:
- High-frequency filler: moreover, furthermore, robust, pivotal
- Default transition logic: "First... Second... Finally..."
- Safe hedging: "it might be worth considering"
- Generic category terms instead of specific nouns

### Burstiness

**Definition**: The variance in sentence-length distribution. Measured as the coefficient of variation (standard deviation / mean) of sentence lengths.

**Why AI scores flat**: Sampling at moderate temperature produces consistent output length because the model is optimizing for coherent continuity, not rhythmic contrast. The result is a flat distribution: sentences cluster within a narrow length band.

**Human writing is bursty**: Writers alternate register naturally. A short observation. Then a sentence that builds context across multiple clauses, introducing sub-arguments, qualifying the main claim, and resolving in a way that would be impossible to compress. Then another short sentence.

**Measuring burstiness**:
```
sentence_lengths = [len(s.split()) for s in sentences]
mean = sum(sentence_lengths) / len(sentence_lengths)
std_dev = (sum((x - mean)**2 for x in sentence_lengths) / len(sentence_lengths)) ** 0.5
cv = std_dev / mean  # target: cv > 0.5 for human-like text
```

A CV below 0.3 is a strong AI signal. Human prose typically runs 0.45–0.75.

**Longest/shortest ratio rule of thumb**: Human writing tends to have a longest/shortest sentence ratio of at least 3:1. AI flat-zones often produce 1.5:1–2:1.

## The Flagged Vocabulary Research

The Tier 1 word list derives from corpus comparison studies contrasting AI-generated text (primarily GPT-3.5/4 and Claude) against human baseline corpora (academic papers, journalism, personal essays). Key findings:

- "Delve" appears at 269× baseline rate in AI text — the single highest ratio documented
- "Tapestry" appears at 180× baseline
- "Realm" and "multifaceted" cluster together, suggesting they co-occur in AI training patterns
- The cluster of words (pivotal, seamless, robust, nuanced) appears disproportionately in AI text regardless of the prompt — they're default quality signals the model has learned to assert

**Why these words specifically**: They are high-status generic modifiers with broad applicability. A language model rewarded for producing "good-sounding" text learns that asserting quality (robust, cutting-edge, nuanced) reads as sophisticated. Human writers, by contrast, show quality rather than asserting it.

## Structural Signatures — Why They Emerge

### Uniform Paragraph Length

Training data for instruction-following models is heavily weighted toward well-structured expository writing. Paragraphs of 3–5 sentences are the modal form in that training set. The model defaults to the mode.

Human writing varies because paragraph breaks are driven by thought transitions, not sentence count. Writers break paragraphs:
- After a pithy observation they want to let breathe
- When the subject shifts mid-flow
- For rhetorical emphasis (a one-sentence paragraph)
- Because the previous paragraph ran long and the writer felt it

### Formulaic Openers and Closers

"In today's rapidly evolving landscape..." is the AI equivalent of a five-paragraph-essay opener. The model learned this template from academic and journalistic writing, where context-setting is conventional.

Human writers skip the setup when they have something to say. They start in medias res, with a specific scene, a claim, a contradiction, a question that already knows its answer.

The symmetric formulaic closer ("In conclusion, it is clear that...") mirrors this: the model has learned to summarize what it said rather than end on something new.

**Fix**: End on an image, a call, a question, or a position. Never summarize what you just said.

### Present Participial Clause Overuse

"Leveraging our expertise, we...", "Building on this foundation, the team...", "Recognizing the challenges ahead..."

This construction is technically correct and stylistically flat. It appears in AI text because it's a safe way to attach a modifier to a clause. Human writers use it occasionally but not as a default opener for sequential paragraphs.

## Authenticity Signals — What Detectors Can't Easily Measure (But Readers Can)

### The Anecdote Problem

AI describes categories of experience. Humans recall specific instances. The difference:

**AI**: "I have extensive experience collaborating with cross-functional teams to deliver complex projects under deadline."

**Human**: "The week before our launch, the infrastructure team and I were debugging a race condition in production at 2am. I'd been wrong about the root cause twice. On the third pass, we found it."

Both claim "cross-functional collaboration under deadline." Only one is credible.

### Hedging as a Failure Mode

AI systems are trained to avoid false statements, which produces defensive hedging. Humans hedge too, but selectively — to mark genuine uncertainty or to soften criticism.

Dense hedging reads as either:
1. The author isn't confident enough to commit
2. The author is a language model that's been trained not to assert falsehoods

Neither is good in a cover letter or personal essay.

**The commitment test**: For each hedged sentence, ask: if this claim turned out to be false, would that be a meaningful failure? If yes, hedge is appropriate. If no (the hedge is just social smoothing), cut it.

### Positivity Bias

Studies on large-scale AI text generation find that outputs trend measurably more positive than human writing matched for topic. This is a training artifact: human feedback rewards helpful, encouraging responses, which shifts the distribution toward positive framing.

In a cover letter or personal statement, consistent positivity without tension or failure reads as manufactured. Admitting one thing that went wrong, one position that lost, or one belief that changed makes the surrounding positivity credible.

### Em Dash Overuse — The Claude Specific Signal

Claude (the model used to generate this document) has a statistically elevated em dash usage rate compared to GPT-4 and human writers. The pattern: using em dash where a comma or period would serve equally well.

Correct em dash usage:
- Genuine interruption: "I was about to submit — the server went down."
- Parenthetical aside with internal commas: "The three founders — Alice, Bo, and Priya — all left within six months."
- Strong appositive: "The one tool that mattered — version control — was the one nobody was using."

Em dash overuse: "The solution was straightforward — we simply rewrote the parser." (comma works)

## Detection Evasion vs. Authentic Writing

This skill targets authentic writing improvement, not detection evasion. The distinction matters:

**Evasion** approaches (not what this skill does): Adding deliberate misspellings, injecting random uncommon words, using adversarial text that confuses classifiers.

**Authenticity** approach (what this skill does): Replacing generic with specific, flat with varied, hedged with committed, abstract with named. The resulting text is better writing by any human editorial standard, regardless of whether any classifier sees it.

A well-humanized document should pass a human editor's read as credible and specific, not merely pass a statistical test.

## Limitations

- No automated tool reliably detects AI text with <5% false positive rate on short documents
- Detectors vary significantly by tool, version, and input length
- The signals above are probabilistic: any individual signal in isolation is not conclusive
- Domain-specific writing (legal, medical, technical) has its own baseline distributions
- This skill cannot guarantee a document will "pass" any specific detector — it improves writing quality in ways that correlate with reduced detection probability
