# Naming Patterns Catalogue

Purpose: build candidate lists from structured research, not model recall. Each pattern gives a definition, examples, strengths, risks, and a concrete way to mine it. Hand survivors to the vetting step in SKILL.md.

## Pattern index (stable IDs for the brief step in SKILL.md)

Reference patterns by ID in themes and finalist records (e.g. "theme: minor Greek deities of measure = P1"). IDs 3.x are the **additional patterns** found beyond the seed list.

| ID | Pattern | ID | Pattern |
|---|---|---|---|
| P1 (2.1) | Mythology / pantheon | P11 (2.11) | Animals / plants / taxonomy |
| P2 (2.2) | Literary / fiction | P12 (2.12) | Science / units / physics |
| P3 (2.3) | Historical figures / artifacts | P13 (2.13) | CLI-friendly short names |
| P4 (2.4) | Descriptive (what it does) | P14 (2.14) | Misspelling / affix coinage |
| P5 (2.5) | Metaphor / trade-tool | P15 (2.15) | Compound words |
| P6 (2.6) | Pun / portmanteau / wordplay | P16 (2.16) | Reversed |
| P7 (2.7) | Acronym / backronym | P17 (2.17) | Numerals / leetspeak |
| P8 (2.8) | Foreign-language words | P18 (2.18) | People initials |
| P9 (2.9) | Domain jargon | P19 (2.19) | Inside jokes |
| P10 (2.10) | Geography / landmarks | | |
| A1 (3.1) | Numeronym | A6 (3.6) | Release-name schemes |
| A2 (3.2) | Recursive acronym | A7 (3.7) | Evocative trait word |
| A3 (3.3) | Operation-derived name | A8 (3.8) | Experiential name |
| A4 (3.4) | Codename lineage / rename | A9 (3.9) | Short-to-type gem/material word |
| A5 (3.5) | Sound-symbolism engineering | A10 (3.10) | Founder / eponym |

"Descriptive but distinctive" theme (SKILL.md round 1): use P4 seeds transformed by P14/P6/P8 (e.g. the function word in Latin or Welsh) so the name hints at function without being generic.

Mining rule for every pattern below: each raw term must be recorded with its source URL; target >= 30 terms per theme; prefer minor or obscure entries; in the second agent round pass the already-seen list and exclude it.

Evidence labels: **V** = supported by a source fetched this session (URL cited); **K** = well-known fact from model knowledge, not re-verified this session (re-check before relying on it); **U** = unverified or conflicting sources.

## Sources used

| Ref | Source | Used for |
|---|---|---|
| S1 | Trademark spectrum overviews: https://www.inta.org/?p=909 , https://fingerpaint.com/news-and-insights/the-trademark-spectrum-of-distinctiveness-when-it-comes-to-brand-naming , https://gleanmark.com/insights/the-spectrum-of-distinctiveness-how-strong-is-your-mark | Generic/descriptive/suggestive/arbitrary/fanciful ladder (law-firm and marketing pages; governing standard is Abercrombie, 2d Cir. 1976, and USPTO TMEP 1209.01) |
| S2 | Igor naming guide: https://www.igorinternational.com/process/brand-naming-expert.php , https://igorinternational.com/press/the-brand-namer.php | Functional / invented / experiential / evocative taxonomy; metaphor under evocative |
| S3 | Watkins, *Hello, My Name Is Awesome*: https://eatmywords.com/book/ , https://www.shortform.com/best-books/book/hello-my-name-is-awesome-book-reviews-alexandra-watkins | SMILE / SCRATCH tests |
| S4 | Lexicon Branding: https://laughingsquid.com/lexicon-branding-product-naming/ , https://www.lexiconbranding.com/myths-that-stop-remarkable-names/ , https://businesswire.com/news/home/20110322005181/en/Lexicon%e2%80%99s-Latest-Brand-Naming-Study-Results-Spelling | Sound symbolism, semantics/structure/sound |
| S5 | Startup naming trend pieces: https://techcrunch.com/2017/05/20/the-bizarre-naming-trends-that-modern-startups-follow/ , https://news.crunchbase.com/startups/startup-naming-trends-2020/ , https://thenextweb.com/news/whats-startups-name-trend-misspelled-words-ly-wont-go-away | Compound, portmanteau, misspelling, evocative-word trends |
| S6 | Kubernetes naming: https://www.geekwire.com/2016/ever-come-kooky-kubernetes-name-heptio/ | Greek word + codename story |
| S7 | Datamuse API docs: https://www.datamuse.com/api/ | Word-mining API |
| S8 | CLI naming guide: https://cli-guide.readthedocs.io/en/latest/design/naming.html , https://smallstep.com/blog/the-poetics-of-cli-command-names/ | Short-vs-mnemonic tradeoff |
| S9 | Numeronyms: https://en.wikipedia.org/wiki/Numeronym | i18n / k8s / a11y |
| S10 | Recursive acronyms: https://en.wikipedia.org/wiki/Recursive_acronym | GNU, PHP, WINE... |
| S11 | Unix command origins: https://robots.thoughtbot.com/how-grep-got-its-name , https://kb.iu.edu/d/abnd | grep, awk |
| S12 | Release-name schemes: https://wiki.ubuntu.com/DevelopmentCodeNames , https://wikipedia.com/wiki/Debian_6 | Ubuntu, Debian |
| S13 | Mozilla/Firefox history: https://thehistoryoftheweb.com/many-faces-names-mozilla/ , https://www.wikipedia.org/wiki/Mozilla | Codename-to-product, forced renames |
| S14 | Language-name origins: https://dev.to/scottydocs/how-programming-languages-got-their-names-207e , https://www.codecademy.com/resources/blog/how-programming-languages-got-their-names-explained | Ruby, Python, Go |
| S15 | Wikipedia deity lists: https://en.wikipedia.org/wiki/List_of_deities_by_classification , https://en.wikipedia.org/wiki/Lists_of_deities ; Wiktionary: https://en.wiktionary.org/wiki/Category:Roman_deities | Mythology mining |

Not verified: Marina Zhukova naming material (search returned nothing relevant; skip citing). Igor treating founder names as its own category (not confirmed; the founder-name type appears in other blog lists). Exact SMILE "M" wording (Memorable vs Meaningful differs by source).

---

## Part 1. Classification frameworks (how to label a candidate)

| Framework | Categories | Use |
|---|---|---|
| Trademark spectrum (S1) | Generic, descriptive, suggestive, arbitrary, fanciful/coined | Legal strength. Aim for suggestive/arbitrary/fanciful. Descriptive needs secondary meaning; generic is unprotectable. V |
| Igor (S2) | Functional, invented, experiential, evocative (metaphor sits under evocative) | Strategy lens. V |
| Lexicon (S4) | Semantics + structure + sound symbolism | Sound-level scoring. V (firm's own account, not independently tested) |
| Watkins SMILE / SCRATCH (S3) | SMILE = Suggestive, Memorable (or Meaningful), Imagery, Legs, Emotional. SCRATCH = Spelling-challenged, Copycat, Restrictive, Annoying, Tame, Curse of knowledge, Hard to pronounce | Evaluation checklist (see Part 4). V |

Note from S1: coined names can still become generic (Aspirin, Thermos, escalator). Suggestive names are the usual legal/marketing sweet spot but the suggestive/descriptive line is unpredictable.

---

## Part 2. Seed patterns

### 2.1 Mythology / pantheon
- **Definition:** Deity, hero, monster, place, or epithet from any tradition.
- **Examples:** Kubernetes (Greek *kubernetes*, steersman; V, S6); Nike (Greek goddess of victory; V, S2); Hermes, Atlas, Apollo (K, heavily used); Firebird/Phoenix as Firefox codenames (V, S13).
- **Strengths:** Built-in story, gravitas, short words, easy tool metaphors.
- **Risks:** Major figures are saturated (Hermes, Atlas, Apollo, Athena, Thor, Odin, Zeus, Loki, Titan). Expect GitHub/npm/PyPI/crates collisions and trademark classes 9/42 conflicts. Check cultural-sensitivity for living religions (Hindu, Yoruba, Native/First Nations deities).
- **How to mine:**
  - Wikipedia https://en.wikipedia.org/wiki/List_of_deities_by_classification (by function: smiths, messengers, craftsmen, boundaries, weather) and https://en.wikipedia.org/wiki/Lists_of_deities (by culture). V
  - Wiktionary categories, e.g. https://en.wiktionary.org/wiki/Category:Roman_deities (sub-categories exist per language). V
  - Theoi.com (Greek, includes minor daimones, nymphs, epithets), Perseus Digital Library (Greek/Latin texts, Smith's dictionary), Wikipedia "Norse/Egyptian/Hindu/Yoruba/Japanese (kami)/Celtic/Slavic/Mesopotamian/Polynesian mythology" and their "List of ..." pages. K
  - Search queries: `minor Greek gods of <function>`, `epithets of <deity>`, `<culture> deity of <tool/function>`, `god of boundaries/measurement/threshold/crossroads/forge`.
  - Prefer: minor figures, epithets, attendants, objects (a god's tool or animal), and rarely used cultures. Skip anything that returns more than a page of GitHub hits for the bare word.

### 2.2 Literary / fiction
- **Definition:** Characters, places, artifacts, and invented words from books, film, games.
- **Examples:** Debian release names from Toy Story characters (V, S12); Kubernetes' "Seven of Nine" Star Trek codename (V, S6); Mozilla from Mosaic + Godzilla (V, S13, attribution details secondary).
- **Strengths:** Community in-joke value, rich name pools.
- **Risks:** Copyrighted/trademarked IP (Disney, Tolkien Enterprises are aggressive); the name signals fandom, not function.
- **How to mine:** Wikipedia "List of minor characters in X"; Project Gutenberg public-domain works (pre-1929 US): extract proper nouns and rare nouns; Wikisource; public-domain epics (Beowulf, Kalevala, Mabinogion). Prefer public domain.

### 2.3 Historical figures / artifacts
- **Definition:** Scientists, engineers, explorers, ships, instruments, inscriptions.
- **Examples:** Tesla, Babbage, Lovelace (K); Rosetta (K); Mercurial/Nautilus (K). Verify a name's current use before proposing.
- **Strengths:** Credible, storytellable, often a tool/instrument that matches function (astrolabe, sextant, orrery).
- **Risks:** Person names carry publicity-rights and trademark issues; living persons are out. Overused famous inventors.
- **How to mine:** Wikipedia "List of scientific instruments", "List of navigation instruments", "Category:Ships of <era>"; Wikipedia "List of Rosetta-like artifacts"; Science Museum Group / Smithsonian collection search; query `obscure <century> instrument for measuring <thing>`.

### 2.4 Descriptive (what it does)
- **Definition:** The name states function (Igor "functional", S2; trademark "descriptive", S1).
- **Examples:** `sed` ("stream editor", V, S11 via Red Hat); `grep` (g/re/p operation; V, S11); PowerShell (K); "Mailchimp" is NOT descriptive.
- **Strengths:** Instantly understood; good for CLI.
- **Risks:** Weakest trademark protection; collides with generic terms; terrible searchability ("go", "rust"); needs secondary meaning (S1).
- **How to mine:** Datamuse `ml=<function>` and `rel_syn=`; verb lists from the feature set; shorten via truncation/contraction (see 2.14). Treat as a seed for transformation, not a final name.

### 2.5 Metaphor / trade-tool
- **Definition:** A physical tool, craft term, or process whose action mirrors the product (Igor files metaphor under evocative, S2).
- **Examples:** Kubernetes (helmsman; V, S6); Amazon (river/scale; V, S2); plumb line, kiln, loom, anvil, bellows (concept examples; check each for collisions).
- **Strengths:** Intuitive mental model, ready-made vocabulary for subcommands.
- **Risks:** Common nouns are crowded (Anvil, Forge, Loom are all taken in software, K); trademark conflicts in the common-word space.
- **How to mine:** Trade glossaries (Wikipedia "Glossary of <trade>": carpentry, masonry, shipbuilding, weaving, blacksmithing, surveying, printing/typesetting, brewing, bookbinding, falconry, heraldry); Wiktionary category `English terms of <trade>` / "Category:en:Tools". Query: `glossary of <trade> terms`, `<trade> tool that <verb the product does>`.

### 2.6 Pun / portmanteau / wordplay
- **Definition:** Blends or puns on two words or a word and a domain term.
- **Examples:** Pinterest, Codecademy (V as portmanteau examples, S5); Mozilla (Mosaic+Godzilla; V, S13); Wine "Wine Is Not an Emulator" (V, S10).
- **Strengths:** Distinctive, often registrable (suggestive/fanciful).
- **Risks:** Harder to say aloud and to search; may seem dated; trademark examiners treat blends as coined, fine, but near-matches to existing marks can still conflict. Explaining the joke is a cost (S5).
- **How to mine:** Datamuse `sp=` wildcards (e.g. `sp=*grid*`) and `sl=` for sound-alikes; take two Datamuse `ml=` lists (function and metaphor) and overlap letter sequences programmatically (suffix of A = prefix of B, length >= 2).

### 2.7 Acronym / backronym
- **Definition:** Letters stand for words; backronym picks the word first, then invents the expansion.
- **Examples:** GNU, PHP, YAML (V as acronyms/joke acronyms, S10); LAME (V, S10).
- **Strengths:** Short, nerd cred.
- **Risks:** Most 3-4 letter combos are taken; hard to search; "meaningless" letters read as corporate.
- **How to mine:** Generate a word from 2.x patterns, then backronym; query `pronounceable acronym generator`; check the resulting 3-5 letter string against registries.

### 2.8 Foreign-language words
- **Definition:** Words from Latin, Greek, Japanese, Welsh, Hawaiian, Old English, Sanskrit, Old Norse, Finnish, Gaelic, etc. Igor lists "non-English names not widely known" with invented names (S2).
- **Examples:** Kubernetes (Greek; V, S6); Gentoo (K, not verified); Hermes (Greek, K, saturated).
- **Strengths:** Large untapped vocabulary; short evocative words; meaning layer.
- **Risks:** Negative or vulgar meaning in other languages (check at least Spanish, Portuguese, French, German, Russian, Mandarin/Japanese, Arabic, Hindi); cultural appropriation concerns for sacred words (Hawaiian, Maori, Native languages); diacritics break typing and URLs.
- **How to mine:**
  - Wiktionary: `https://en.wiktionary.org/wiki/Category:<Language>_lemmas`, `Category:Latin_terms_with_usage_examples`, `Appendix:Basic_English_words`... K
  - Etymonline https://www.etymonline.com (root words, Proto-Indo-European).
  - Datamuse has English only; for translation use Wiktionary "Translations" tables for a seed English word (e.g. `thread` -> 50 languages).
  - Wikipedia "List of Latin phrases", "List of English words of <language> origin"; Old English: Bosworth-Toller (bosworthtoller.com); Hawaiian: wehewehe.org; Welsh: geiriadur.ac.uk; Sanskrit: sanskrit-lexicon.uni-koeln.de.
  - Query: `<english concept> in <language> etymology`.

### 2.9 Domain jargon
- **Definition:** Insider terms from the product's field (surveying, audio, cartography, finance, LiDAR, etc.).
- **Examples:** grep, sed, awk from Unix text-processing jargon (V, S11); Kubernetes from nautical jargon (V, S6); Docker/container (K).
- **Strengths:** Instant resonance with the target users; avoids generic marketing words.
- **Risks:** Insider-only; jargon often already used by competitors in the same domain (direct conflict).
- **How to mine:** Domain glossaries (Wikipedia "Glossary of ...", standards bodies like ISO/OGC, ASPRS for LiDAR), textbook indices, Datamuse `rel_trg=<domain term>`, `topics=<domain>` parameter. Review the competitors' docs for what is already used.

### 2.10 Geography / landmarks
- **Definition:** Places, rivers, mountains, streets, ships' ports, geological terms.
- **Examples:** Gran Paradiso (Firefox 3.0 codename, a real mountain; V, S13); Amazon (V, S2); Ubuntu "Hardy Heron" is not geography (ignore).
- **Strengths:** Concrete imagery; many obscure names; local meaning for community.
- **Risks:** Place-name trademarks are weak and often geographically descriptive (S1 logic); political/cultural baggage; location confusions in search.
- **How to mine:** Wikipedia "List of mountain passes/fjords/lighthouses/islands of <region>"; GeoNames (geonames.org dumps) filter by feature code and population < N so names are rare; USGS GNIS; OpenStreetMap place nodes.

### 2.11 Animals / plants / taxonomy
- **Definition:** Common or Latin names; taxonomic ranks; genus names.
- **Examples:** Python's logo and Firefox (red panda; V, S13); pandas, Jaguar (K).
- **Strengths:** Mascot-friendly, strong imagery, memorable.
- **Risks:** Hugely overused (Fox, Falcon, Raven, Orca, Hawk, Lynx); mascot copyright; Latin binomials are hard to spell.
- **How to mine:** Wikipedia "List of <class> by common name"; Wikispecies; GBIF species API (api.gbif.org/v1/species/search?q=); iNaturalist taxa; pick rare families/genera and archaic common names; glossaries of botanical Latin (Wikipedia "Glossary of botanical terms").

### 2.12 Science / units / physics terms
- **Definition:** Named units, constants, phenomena, math objects.
- **Examples:** Pentium (Greek penta + -ium; V as case study, S4); Tesla, Kelvin (K).
- **Strengths:** Technical credibility; many short words.
- **Risks:** Unit symbols are generic; famous terms are claimed (Quark, Tensor, Photon).
- **How to mine:** Wikipedia "List of physical constants/ eponymous laws/ unit symbols"; Wikipedia "List of Greek/Latin roots in English"; IUPAC element names; Wikipedia "Glossary of <field>"; Datamuse `rel_trg=<concept>`.

### 2.13 CLI-friendly short names
- **Definition:** Names optimized for the keyboard and shell.
- **Evidence:** CLI guides frame naming as a tradeoff between mnemonic meaning and short, easy-to-type names (V, S8). A commonly cited rule of thumb is <= 8 characters (V as a stated heuristic only, from a vendor blog; not a standard). Ruby's creator rejected "diamond"/"sapphire" as too long to type (V, S14, secondary).
- **Examples:** grep, sed, awk (V, S11); fd, rg, jq, bat (K).
- **Strengths:** Daily ergonomics; becomes a verb.
- **Risks:** Collides with existing binaries on PATH and Homebrew/apt packages; heavy search noise.
- **How to mine / test:** 3-5 letter strings; alternate hands on QWERTY; no shift or special characters; check `command -v <name>`, `brew search <name>`, `apt-cache search ^<name>$`, `pacman -Ss ^<name>$`; avoid existing Unix command names (list in `/usr/bin` of each target OS).

### 2.14 Misspelling / dropped vowel / affix coinage
- **Definition:** Altered spellings (Flickr), suffixes -ify, -ly, -ium, -io, -ix, -ex.
- **Examples:** Pentium (-ium; V, S4); misspelling and -ly trends documented in S5 (V); Spotify, Bitly (K).
- **Strengths:** Available domains; reads as coined (strongest trademark class, S1).
- **Risks:** Hard to say aloud and spell on first hearing; Lexicon's study is titled "Spelling Matters" (S4, V as a title; read for results); SCRATCH "Spelling-challenged" (S3); looks dated; voice assistants mis-transcribe.
- **How to mine:** Take 2.4/2.8 seeds, apply a rule set programmatically; filter with a spell-by-ear test (say it to a voice transcriber or ask a sub-agent to transcribe a spoken form).

### 2.15 Compound words
- **Definition:** Two real words fused (GrubHub, Fitbit; V, S5).
- **Strengths:** Fast to create, meaning visible, rhyming compounds stick (S5).
- **Risks:** Ubiquitous, so collisions; can be confusing; often descriptive/weak (S1).
- **How to mine:** Cross two Datamuse lists (`ml=<function>` x `ml=<metaphor>`); test with `sp=` for real-word split; reject when either half is a generic term.

### 2.16 Reversed / spelled backwards
- **Definition:** Reverse a word (Nissan-style; K).
- **Examples:** "Stressed" -> "Desserts" is the standard illustration (K); no verified dev-tool example found. Treat as low-yield.
- **Risks:** Often unpronounceable; flagged by SCRATCH hard-to-pronounce (S3).
- **How to mine:** Script reversal of word lists; keep only results that match Datamuse `sp=` real words or pass a pronounceability heuristic (vowel ratio, no triple consonants).

### 2.17 Numerals / leetspeak
- **Definition:** Digits substituted for letters or standing for words (see also numeronym in 3.1).
- **Examples:** k8s, i18n, a11y (V, S9).
- **Risks:** Hard to speak; trademark strength low if only a stylization; search engines may normalize.
- **How to mine:** Generate from candidate words >= 8 letters (numeronym), then check that the numeronym is not an existing community abbreviation.

### 2.18 Initials of people
- **Definition:** Names derived from the founders' initials or surnames.
- **Examples:** awk (Aho, Weinberger, Kernighan; V, S11); Tiffany & Co as founder name (V as an example of a founder-name type, from a blog list cited in the Igor search).
- **Strengths:** Credit, unique string, humble tone.
- **Risks:** Meaningless to users; requires a joke or story; surname trademarks need consent.
- **How to mine:** Permute team initials; check anagrams with an anagram solver; rare surnames from the project's contributor list.

### 2.19 Inside jokes
- **Definition:** Names with a private story.
- **Examples:** Kubernetes' "Project Seven" lineage and Heptio (V, S6); Python from Monty Python (V, S14).
- **Strengths:** Authentic voice and community identity.
- **Risks:** Excludes newcomers; the joke can age or offend; check that the joke source's IP is not defended.
- **How to mine:** Existing repo commit messages, issue titles, README; the project's origin story; review with a skeptic agent for "would an outsider be put off".

---

## Part 3. Additional patterns found (beyond the seed list)

| # | Pattern | Definition | Verified examples | Risk | How to mine |
|---|---|---|---|---|---|
| 3.1 | **Numeronym** | First letter + count + last letter | k8s, i18n, a11y (V, S9); the convention is traced to DEC in the 1980s (V, S9, one main source) | Works as an alias, rarely as a primary name | Script over words >= 8 letters |
| 3.2 | **Recursive acronym** | Expansion contains the acronym | GNU, WINE, PHP (V, S10) | Dated nerd-humor; "PHP" expansion changed over time; sources disagree on origins (U on details) | Pick a name, write "X is not Y"/"X: X ..." and test it |
| 3.3 | **Operation-derived name** | Name is a compressed command or action | grep from ed's `g/re/p` (V, S11) | Works only if the operation is known to the audience | List the tool's main operation in its predecessor's syntax |
| 3.4 | **Codename-to-product / rename lineage** | Internal project name kept or adapted (and forced renames) | Mozilla, Phoenix to Firebird to Firefox; Firebird dropped because a DB project already had it (V, S13, secondary) | The lesson: collision found late costs a rename; vet before announcing | Pull history of renamed projects (Wikipedia "Firefox early version history") as a failure checklist; keep a "codename -> vetted name" step |
| 3.5 | **Sound-symbolism engineering** | Choose phonemes for feel: plosives (b, t, k) read as hard/reliable, sonorants (n, l, m) as soft, "v" as energy (V, S4, firm's claims) | BlackBerry (chosen over Strawberry for the b-sound; V, S4), Dasani (spa-like sound; V, S4) | Claims come from the namer's own marketing, untested independently | Score candidates by phoneme classes; generate names with a target phoneme profile via Datamuse `sp=` patterns |
| 3.6 | **Release-name schemes** | A fixed theme and rule that generate names over time | Ubuntu adjective+animal same letter (V, S12); Debian Toy Story characters (V, S12); Android desserts through v9 (V, droidwiki via search) | Good for sub-names (versions, plugins), not main brand | Pick a theme with a deep pool (e.g. minor mythology) and use it for the family of names, not only the top project |
| 3.7 | **Evocative trait word** | Real word naming a desirable state or trait | Mighty, Cured, Elate (V as examples cited, S5/Crunchbase) | Crowded in startup space; vague | Datamuse `ml=<benefit>`; thesaurus.com for valued synonyms |
| 3.8 | **Experiential name** | Names the user's experience or feeling rather than the object (Igor category, S2) | Examples not extracted from sources (U); K candidates only | Sourcing weak here | Interview the "job to be done" and list verbs/feelings; Datamuse `rel_trg=` on the feeling |
| 3.9 | **Chosen-for-short-to-type gem/material word** | Real short noun picked partly because longer synonyms are annoying | Ruby (V, S14 secondary) | Common words are crowded; "Ruby" now trademark-search-noisy | Wiktionary/WordNet hyponyms of a category (gems, metals, knots), filtered to <= 6 letters |
| 3.10 | **Founder / eponym name** | Named after a founder | Tiffany & Co (V as an example, blog list); awk uses authors (V, S11) | Not neutral for an OSS project; legal ownership | Only when contributors agree |

---

## Part 4. Evaluation criteria

Score each candidate pass/fail first, then rank. SMILE/SCRATCH (S3) is the backbone; trademark spectrum (S1) sets legal strength.

| Criterion | Test | Tool/method |
|---|---|---|
| Pronounceable | Two syllables ideal; no ambiguous clusters; one obvious pronunciation | Say it aloud; ask a sub-agent to transcribe it back from phonetic respelling |
| Spellable | Heard once, typed correctly (SCRATCH "spelling-challenged") | Voice-assistant check (S3 mentions Siri) |
| CLI-typeable | <= ~8 chars (heuristic, S8), lowercase ASCII, no shift/hyphen, hands alternate | Typing check; `command -v`, `brew search`, `apt-cache`, `pacman -Ss` |
| Searchable | Top web results are not another product; not a common English word (Go/Rust problem) | Search `"<name>" <category>`, `"<name>" github`, plus bare name |
| Short | 4-8 letters preferred | Count |
| Distinct from copycats | Not a variant of a known tool (SCRATCH "copycat") | Registry search |
| No negative meaning elsewhere | Check main target languages and slang | Wiktionary entry in each language, Urban Dictionary, `<name> meaning in <language>` |
| Tone | Not restrictive (ties to one feature), not tame (bland) | Human review |
| Legal strength | Suggestive/arbitrary/fanciful beats descriptive (S1) | Tag each candidate |
| Handles available | GitHub org/repo, npm, PyPI, crates.io, Homebrew, domain (.com/.dev/.io), social handles | Delegated to pm-name-vetting SKILL.md |
| Mascot/IP safe | No third-party IP | Skip fiction sources unless public domain |

Hard rejects: exact existing dev-tool in same category; unpronounceable; offensive meaning; major trademark in classes 9/42/35 (check USPTO TESS replacement search at https://tmsearch.uspto.gov and EUIPO TMview, K).

---

## Part 5. Multi-round expansion protocol

Maps onto SKILL.md's Generation Protocol (rounds 1-5). Goal: >= 150 raw terms (>= 30 per theme, each with source URL), <= 20 finalists handed to vetting.

1. **Seed themes (round 1: brief).** From the product brief extract: core function verbs, user's job, metaphor domains (physical tool, craft, navigation), tone words, and constraints (CLI? length? audience). Write 5-8 themes, each tagged with a pattern ID from the index; include at least one pun/portmanteau (P6) theme and one descriptive-but-distinctive (P4 transformed) theme, plus a rare mythology source, a trade glossary, a foreign language, and a science/geo source. Prefer themes the model would not pick unprompted.
2. **Mine word lists (round 2).** For each theme fetch a real list (Wikipedia list page, Wiktionary category, Theoi, GeoNames, GBIF). Save to scratch files; extract raw tokens. Do not generate from memory. Record the source URL per list.
3. **Expand and cross-pollinate (round 3).** Per theme spawn a sub-agent (parallel) with the theme's list and instructions:
   - Datamuse expansions: `https://api.datamuse.com/words?ml=<concept>&max=100`, `rel_trg=<word>` (statistically associated words), `sl=<word>` (sound-alikes), `sp=<pattern>` (wildcards like `b?t`, `*zzle*`), `rel_syn=`, `topics=` (V, S7, parameter descriptions from secondary docs; confirm against the official page).
   - Thesaurus sites (thesaurus.com, Moby thesaurus, WordNet via wordnet-online or NLTK) for synonyms and hyponyms; Wiktionary translations for foreign forms; etymonline for roots.
   - Return only tokens that carry a source and a one-line meaning.
   - Run a second agent round per theme with the seen-terms list passed in and excluded.
   - **Cross-pollinate.** Combine patterns: mythology x tool metaphor (e.g. a smith-deity's epithet, or a god of boundaries for a validator); foreign word x trade jargon (Welsh/Old English word for a craft tool); geography x function (a pass/ford for a pipeline); taxonomy x measurement. Apply affix/portmanteau rules (2.14, 2.6) to the best seeds. Name the pattern used per candidate.
4. **Filter (round 4).** Script: length, ASCII, pronounceability heuristic, not on PATH of target OSes, not in top-N English words (avoid Go/Rust search problem), dedupe near-matches (edit distance <= 1). Discard descriptive-only and generic. Then apply Part 4 criteria plus a quick foreign-meaning and SCRATCH pass. Keep <= 20 finalists, each with pattern ID and source URL recorded.
5. **Hand-off (round 5).** Emit a table: name, pattern ID, source URL, meaning, trademark-spectrum class, SMILE/SCRATCH notes. Pass to the Search Protocol in SKILL.md (GitHub, registries, web, domains). Preserve rejected-name reasons so later runs avoid them.

Diversity rule: no single pattern may supply more than ~30% of the final shortlist; at least two shortlist names should come from sources the model would not have suggested unprompted.

Failure lesson (S13): Firebird was adopted and then dropped for a collision with an existing open-source database. Vet before announcing, and keep a fallback ranking.
