---
title: Identify Unlinked Concepts
description: Scan text to find technical terms, concepts, and topics mentioned in plain text that should be wiki-linked or have their own zettels
arguments:
  - name: scope
    description: Which files to scan (today|week|month|journals|pages|file:<path>|all)
    required: false
    default: today
  - name: action
    description: What to do with findings (report|link|create-high|create-all|interactive)
    required: false
    default: report
  - name: min_priority
    description: Minimum priority level to process (high|medium|low)
    required: false
    default: medium
  - name: min_occurrences
    description: Minimum times a term must appear to be considered (1-10)
    required: false
    default: 2
---

# Identify Unlinked Concepts

Transform plain text mentions of technical terms, concepts, technologies, and topics into properly linked zettels, systematically enhancing your knowledge graph connectivity.

---

## Critical Problem This Solves

**Current Gap**: When writing journal entries and notes, users often mention important concepts in plain text without creating wiki links:

```markdown
- Today I learned about Kubernetes network policies and how they differ from AWS security groups
- Reading about CRDT conflict resolution and vector clocks
- Implemented rate limiting using token bucket algorithm
```

**Problems with unlinked concepts**:
- Important terms (`Kubernetes`, `network policies`, `AWS security groups`, `CRDT`, `vector clocks`, `token bucket algorithm`) are mentioned but not linked
- These concepts likely deserve their own comprehensive zettels
- Knowledge graph remains disconnected and less navigable
- Difficult to discover related content and build understanding
- Manual link creation is tedious and error-prone

**What This Command Provides**:
1. **Automatic detection** of technical terms, technologies, products, and concepts
2. **Priority scoring** to identify which terms are most important
3. **Intelligent filtering** to avoid false positives (common words, proper names)
4. **Automated linking** to convert plain text to `[[Wiki Links]]`
5. **Zettel creation** by delegating to `/knowledge/synthesize-knowledge`
6. **Context preservation** to maintain original text meaning and formatting

---

## Core Workflow Overview

```
Phase 1: Text Scanning and Extraction
├─ Scan specified files (journals, pages, specific files)
├─ Extract potential concepts using detection strategies
├─ Filter already wiki-linked text
└─ Build candidate list

Phase 2: Concept Validation and Categorization
├─ Check if pages exist for each concept
├─ Check if concept is already linked elsewhere
├─ Categorize by type (technology, concept, algorithm, etc.)
├─ Score importance (high/medium/low)
└─ Apply min_priority and min_occurrences filters

Phase 3: User Review and Selection
├─ Generate organized report by priority
├─ Show contexts where concepts appear
├─ Recommend actions (create zettel, add links, etc.)
└─ Get user confirmation (if interactive mode)

Phase 4: Automated Processing
├─ Add wiki links to source files (if action: link)
├─ Create zettels via synthesize-knowledge (if action: create-*)
├─ Update references across files
└─ Track results

Phase 5: Verification and Reporting
├─ Count links added vs failed
├─ List zettels created
├─ Report errors or ambiguities
└─ Suggest follow-up actions
```

---

## Phase 1: Text Scanning and Extraction

### Objective
Discover potential concepts mentioned in plain text that could be wiki-linked or become zettels.

### Step 1.1: Determine Scan Scope

Based on `scope` argument:

**`today` (default)**: Today's journal entry
```
File: /storage/emulated/0/personal-wiki/logseq/journals/YYYY_MM_DD.md
Where YYYY_MM_DD is today's date
```

**`week`**: Last 7 days of journal entries
```
Files: /storage/emulated/0/personal-wiki/logseq/journals/YYYY_MM_DD.md
For the past 7 days
```

**`month`**: Last 30 days of journal entries
```
Files: /storage/emulated/0/personal-wiki/logseq/journals/YYYY_MM_DD.md
For the past 30 days
```

**`journals`**: All journal entries
```
Pattern: /storage/emulated/0/personal-wiki/logseq/journals/*.md
```

**`pages`**: All pages
```
Pattern: /storage/emulated/0/personal-wiki/logseq/pages/*.md
```

**`file:<path>`**: Specific file
```
File: Provided absolute path
```

**`all`**: Everything (journals + pages)
```
Pattern: /storage/emulated/0/personal-wiki/logseq/**/*.md
```

### Step 1.2: Extract Potential Concepts

For each file in scope, apply multiple detection strategies:

**Strategy 1: Capitalized Multi-Word Terms**

Pattern: `([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)`

Examples:
- "Kubernetes Network Policies"
- "AWS Security Groups"
- "Conflict Free Replicated Data Types"

**Strategy 2: Technical Suffix Terms**

Pattern: `\w+(algorithm|protocol|pattern|system|framework|library|tool|service|platform|architecture|methodology|technique|approach)s?\b`

Examples:
- "token bucket algorithm"
- "consensus protocol"
- "circuit breaker pattern"
- "microservices architecture"

**Strategy 3: Cloud Services and Products**

Pattern: `(AWS|Azure|GCP|Google Cloud|Amazon)\s+[A-Z]\w+(?:\s+[A-Z]\w+)*`

Examples:
- "AWS Lambda"
- "Azure Functions"
- "Google Cloud Run"

**Strategy 4: Acronyms**

Pattern: `\b[A-Z]{2,}(?:/[A-Z0-9]+)?\b`

Examples:
- "CRDT"
- "REST"
- "GraphQL"
- "HTTP/2"
- "OAuth2"

**Strategy 5: Code References in Backticks**

Pattern: `` `([A-Z]\w+(?:\.[A-Z]\w+)*)` ``

Examples:
- `` `Service.Method` ``
- `` `ClassName` ``
- `` `Interface` ``

**Strategy 6: Quoted Concepts**

Pattern: `"([a-z][a-z\s]{2,49})"`

Examples:
- "eventual consistency"
- "CAP theorem"
- "domain-driven design"

**Strategy 7: Known Technology Names**

Maintain list of common technologies/products:
```
Common Technologies:
- Kubernetes, Docker, PostgreSQL, MySQL, MongoDB
- React, Vue, Angular, Svelte
- Terraform, Ansible, Chef, Puppet
- Kafka, RabbitMQ, Redis
- Prometheus, Grafana, Jaeger
- Jenkins, CircleCI, GitHub Actions
...
```

Pattern: Case-insensitive match against known list

### Step 1.3: Filter and Clean

**Exclude already wiki-linked text**:
```python
# Remove any text inside [[...]]
text = re.sub(r'\[\[([^\]]+)\]\]', '', text)
# Now extract concepts from remaining text
```

**Exclude common words**:
```python
stop_words = {
    "The", "This", "That", "These", "Those",
    "January", "February", ..., "December",
    "Monday", "Tuesday", ..., "Sunday",
    "Today", "Yesterday", "Tomorrow",
    # ... comprehensive stop word list
}

if candidate in stop_words:
    continue  # Skip
```

**Exclude proper names**:
```python
# Use common name patterns
name_patterns = [
    r'^[A-Z][a-z]+ [A-Z][a-z]+$',  # John Smith
    r'^Dr\. ',  # Dr. Name
    r'^Prof\. ',  # Prof. Name
]

if matches_name_pattern(candidate):
    continue  # Skip
```

**Normalize term**:
```python
# Remove extra whitespace
term = ' '.join(term.split())

# Handle possessives
term = term.rstrip("'s")

# Store original case but normalize for comparison
normalized = term.lower()
```

### Step 1.4: Build Candidate List

Create structured list of potential concepts:

```python
candidates = {
    "Kubernetes": {
        "original_term": "Kubernetes",
        "normalized": "kubernetes",
        "detection_method": "capitalized_term",
        "occurrences": [
            {
                "file": "2025_12_14.md",
                "line_number": 23,
                "context": "Investigated Kubernetes network policies for multi-tenant isolation"
            },
            {
                "file": "2025_12_13.md",
                "line_number": 45,
                "context": "Setting up Kubernetes cluster with kubeadm"
            }
        ],
        "total_occurrences": 2,
        "files": ["2025_12_14.md", "2025_12_13.md"]
    },
    "network policies": {
        "original_term": "network policies",
        "normalized": "network policies",
        "detection_method": "technical_suffix",
        "occurrences": [...],
        "total_occurrences": 3,
        "files": ["2025_12_14.md"]
    }
}
```

### Success Criteria - Phase 1

- ✅ All files in scope read successfully
- ✅ All detection strategies applied
- ✅ Already-linked text properly excluded
- ✅ Stop words and proper names filtered out
- ✅ Candidate list built with full occurrence metadata
- ✅ Original context preserved for each occurrence
- ✅ Precision target: >80% of candidates are legitimate concepts
- ✅ Recall target: >70% of technical terms detected

### Example Extraction Output

```
📊 Text Scanning Complete

**Scan Scope**: Today (2025_12_14.md)
**Lines Processed**: 247
**Already Linked Terms**: 18 (excluded)

**Potential Concepts Detected**: 12

**Detection Methods Applied**:
- Capitalized terms: 5 candidates
- Technical suffixes: 4 candidates
- Acronyms: 2 candidates
- Quoted concepts: 1 candidate

**Top Candidates by Occurrence**:
1. "Kubernetes" - 5 occurrences
2. "network policies" - 3 occurrences
3. "AWS Security Groups" - 2 occurrences
4. "CRDT" - 2 occurrences
5. "token bucket algorithm" - 1 occurrence
...

**Next**: Validating candidates and categorizing...
```

---

## Phase 2: Concept Validation and Categorization

### Objective
Determine which candidates already have pages, categorize by type, and assign priority scores.

### Step 2.1: Check Page Existence

For each candidate:

```python
def check_page_status(term):
    # Try exact match
    exact_path = f"/storage/emulated/0/personal-wiki/logseq/pages/{term}.md"
    if os.path.exists(exact_path):
        return "EXISTS", exact_path

    # Try title case
    title_case = term.title()
    title_path = f"/storage/emulated/0/personal-wiki/logseq/pages/{title_case}.md"
    if os.path.exists(title_path):
        return "EXISTS", title_path

    # Try variations (singular/plural)
    singular = singularize(term)
    plural = pluralize(term)

    for variant in [singular, plural]:
        variant_path = f"/storage/emulated/0/personal-wiki/logseq/pages/{variant}.md"
        if os.path.exists(variant_path):
            return "EXISTS_VARIANT", variant_path

    return "MISSING", None
```

**Page Status**:
- `EXISTS`: Exact match found
- `EXISTS_VARIANT`: Similar page found (singular/plural)
- `MISSING`: No page exists

### Step 2.2: Check If Already Linked

Search if term appears as wiki link elsewhere:

```python
def check_if_linked(term):
    # Search for [[Term]] or [[term]] in all files
    pattern = f"\\[\\[{re.escape(term)}\\]\\]"

    # Run grep across wiki
    result = grep(pattern, case_insensitive=True)

    if result.count > 0:
        return "ALREADY_LINKED", result.count
    else:
        return "NEVER_LINKED", 0
```

**Link Status**:
- `ALREADY_LINKED`: Term appears as `[[Term]]` in some files
- `NEVER_LINKED`: Term never appears as wiki link

### Step 2.3: Categorize by Type

Classify each concept into category:

```python
def categorize_concept(term, context):
    # Technology/Product
    tech_patterns = [
        r'(Kubernetes|Docker|PostgreSQL|Redis|Kafka|...)',
        r'(AWS|Azure|GCP) \w+',
    ]
    if matches_any(term, tech_patterns):
        return "Technology/Product"

    # Concept/Theory
    concept_keywords = ['theorem', 'principle', 'law', 'model', 'consistency']
    if any(kw in term.lower() for kw in concept_keywords):
        return "Concept/Theory"

    # Algorithm/Pattern
    algo_keywords = ['algorithm', 'pattern', 'approach', 'technique']
    if any(kw in term.lower() for kw in algo_keywords):
        return "Algorithm/Pattern"

    # Tool/Framework
    tool_keywords = ['framework', 'library', 'tool', 'utility']
    if any(kw in term.lower() for kw in tool_keywords):
        return "Tool/Framework"

    # Protocol/Standard
    protocol_keywords = ['protocol', 'standard', 'specification', 'RFC']
    if any(kw in term.lower() for kw in protocol_keywords):
        return "Protocol/Standard"

    # Check context for hints
    if re.search(r'(implement|using|with|via) ' + re.escape(term), context):
        return "Tool/Framework"

    # Default
    return "General Concept"
```

**Categories**:
- Technology/Product (Kubernetes, PostgreSQL, React)
- Concept/Theory (CAP theorem, eventual consistency)
- Algorithm/Pattern (token bucket, circuit breaker)
- Tool/Framework (OpenRewrite, Terraform)
- Protocol/Standard (HTTP/2, OAuth2)
- General Concept (catch-all)

### Step 2.4: Score Importance

Calculate priority score:

```python
def calculate_priority(candidate):
    score = 0

    # Factor 1: Occurrence Count (primary signal)
    occurrences = candidate["total_occurrences"]
    if occurrences >= 5:
        score += 100  # Very high priority
    elif occurrences >= 3:
        score += 75   # High priority
    elif occurrences == 2:
        score += 40   # Medium priority
    else:
        score += 10   # Low priority

    # Factor 2: Number of Files
    file_count = len(candidate["files"])
    if file_count >= 3:
        score += 30   # Cross-file usage
    elif file_count == 2:
        score += 15

    # Factor 3: Capitalization (proper nouns more likely important)
    term = candidate["original_term"]
    if term[0].isupper():
        score += 10

    # Factor 4: Context Signals
    contexts = [occ["context"] for occ in candidate["occurrences"]]

    # Technical context indicators
    tech_indicators = ['implement', 'using', 'configure', 'deploy', 'install']
    if any(indicator in ' '.join(contexts).lower() for indicator in tech_indicators):
        score += 15

    # Importance markers
    if any('important' in ctx.lower() for ctx in contexts):
        score += 20
    if any('research' in ctx.lower() for ctx in contexts):
        score += 10

    # Factor 5: Category
    category = candidate["category"]
    if category == "Technology/Product":
        score += 10  # Technologies often deserve zettels
    elif category == "Algorithm/Pattern":
        score += 10  # Algorithms worth documenting

    # Factor 6: Already Exists?
    if candidate["page_status"] == "EXISTS":
        score -= 50  # Lower priority if page exists (just need links)

    # Factor 7: Detection Method Confidence
    method = candidate["detection_method"]
    if method == "capitalized_term":
        score += 5   # High confidence
    elif method == "technical_suffix":
        score += 5   # High confidence
    elif method == "acronym":
        score += 3   # Medium confidence

    return score

# Assign priority level
if score >= 100:
    priority = "HIGH"
elif score >= 50:
    priority = "MEDIUM"
else:
    priority = "LOW"
```

**Priority Levels**:
- **HIGH** (score ≥ 100): 3+ occurrences OR important context markers
- **MEDIUM** (score 50-99): 2 occurrences OR significant context
- **LOW** (score < 50): Single occurrence or weak signals

### Step 2.5: Apply Filters

Filter candidates based on arguments:

```python
# Apply min_occurrences filter
candidates = [c for c in candidates if c["total_occurrences"] >= min_occurrences]

# Apply min_priority filter
priority_thresholds = {
    "high": 100,
    "medium": 50,
    "low": 0
}
threshold = priority_thresholds[min_priority]
candidates = [c for c in candidates if c["priority_score"] >= threshold]

# Sort by priority score (descending)
candidates.sort(key=lambda c: c["priority_score"], reverse=True)
```

### Success Criteria - Phase 2

- ✅ All candidates checked for existing pages
- ✅ All candidates categorized by type
- ✅ Priority scores calculated consistently
- ✅ Filters applied correctly (min_occurrences, min_priority)
- ✅ Results sorted by importance
- ✅ False positive rate < 20%
- ✅ High-priority items genuinely more important than low-priority

### Example Categorization Output

```
🎯 Concept Validation and Categorization

**Candidates Analyzed**: 12
**After Filtering** (min_occurrences: 2, min_priority: medium): 6

**High Priority** (score ≥ 100):

1. **Kubernetes** (Technology/Product) - Score: 125
   - Occurrences: 5 times across 3 files
   - Page status: MISSING
   - Link status: NEVER_LINKED
   - Context: Technical implementation ("setting up Kubernetes cluster")
   - Suggested action: Create zettel + add wiki links

2. **network policies** (Concept/Theory) - Score: 105
   - Occurrences: 3 times in 1 file
   - Page status: MISSING
   - Link status: NEVER_LINKED
   - Context: Technical deep-dive ("Kubernetes network policies for isolation")
   - Suggested action: Create zettel + add wiki links

**Medium Priority** (score 50-99):

3. **AWS Security Groups** (Technology/Product) - Score: 65
   - Occurrences: 2 times in 1 file
   - Page status: MISSING
   - Link status: NEVER_LINKED
   - Context: Comparison ("compared with AWS security groups")
   - Suggested action: Create zettel

4. **CRDT** (Concept/Theory) - Score: 60
   - Occurrences: 2 times across 2 files
   - Page status: EXISTS_VARIANT (found "Conflict-Free Replicated Data Types.md")
   - Link status: ALREADY_LINKED (4 instances elsewhere)
   - Suggested action: Add wiki links only (page exists)

5. **Calico** (Tool/Framework) - Score: 55
   - Occurrences: 2 times in 1 file
   - Page status: MISSING
   - Link status: NEVER_LINKED
   - Context: CNI plugin mention
   - Suggested action: Create zettel

6. **Cilium** (Tool/Framework) - Score: 55
   - Occurrences: 2 times in 1 file
   - Page status: MISSING
   - Link status: NEVER_LINKED
   - Context: CNI plugin mention
   - Suggested action: Create zettel

**Filtered Out** (below threshold): 6 concepts
- "token bucket algorithm" (1 occurrence)
- "label selectors" (1 occurrence)
...

**Next**: Generating user review report...
```

---

## Phase 3: User Review and Selection

### Objective
Present findings in organized format and determine which actions to take.

### Step 3.1: Generate Organized Report

Format report by priority level:

```markdown
## Unlinked Concepts Found

**Scan Scope**: [scope description]
**Files Scanned**: [count]
**Total Candidates**: [count]
**After Filtering**: [count] (min_occurrences: [N], min_priority: [level])

---

### High Priority ([count])

**[Term]** ([Category]) - Score: [score]
- **Occurrences**: [count] times across [file_count] files
- **Page status**: [MISSING|EXISTS|EXISTS_VARIANT]
- **Link status**: [NEVER_LINKED|ALREADY_LINKED]
- **Contexts**:
  - [File]: "[surrounding text...]"
  - [File]: "[surrounding text...]"
- **Suggested action**: [Create zettel + add links | Add links only | Review manually]

---

### Medium Priority ([count])

[Same format as High Priority]

---

### Low Priority ([count])

[Same format, possibly condensed]

---

### Summary

**Concepts by Action**:
- Create zettel + add links: [count] concepts
- Add links only (page exists): [count] concepts
- Review manually (ambiguous): [count] concepts

**Available Actions**:
1. `report` - You're viewing the report (no changes made)
2. `link` - Add wiki links to existing pages only
3. `create-high` - Create zettels for high-priority concepts
4. `create-all` - Create zettels for all concepts
5. `interactive` - Choose which concepts to process

**Next Steps**:
- Review findings above
- Re-run with desired action, e.g.:
  - `/knowledge/identify-unlinked-concepts today link`
  - `/knowledge/identify-unlinked-concepts today create-high`
  - `/knowledge/identify-unlinked-concepts today interactive`
```

### Step 3.2: Interactive Mode (if action: interactive)

Present choices and get user input:

```
📋 Interactive Concept Selection

Found [count] concepts that could be processed.

For each concept, choose action:
[L] Add wiki links only
[C] Create zettel + add wiki links
[S] Skip
[A] Accept all remaining with default action
[Q] Quit

---

1/6: **Kubernetes** (Technology/Product) - 5 occurrences
     Page: MISSING | Links: NEVER_LINKED
     Context: "setting up Kubernetes cluster"

     Suggested: Create zettel + add links

     Action [L/C/S/A/Q]: _
```

User inputs choices, command tracks selections.

### Step 3.3: Determine Actions Based on Mode

```python
if action == "report":
    # Just show report, make no changes
    return report

elif action == "link":
    # Add wiki links for concepts where page exists
    concepts_to_link = [c for c in candidates if c["page_status"].startswith("EXISTS")]

elif action == "create-high":
    # Create zettels for high-priority missing concepts
    concepts_to_create = [c for c in candidates
                         if c["priority"] == "HIGH" and c["page_status"] == "MISSING"]

elif action == "create-all":
    # Create zettels for all missing concepts
    concepts_to_create = [c for c in candidates if c["page_status"] == "MISSING"]

elif action == "interactive":
    # Use user-selected actions
    concepts_to_link = user_selections["link"]
    concepts_to_create = user_selections["create"]
```

### Success Criteria - Phase 3

- ✅ Report clearly organized by priority
- ✅ All relevant context shown for each concept
- ✅ Suggested actions appropriate for each concept
- ✅ Action options clearly explained
- ✅ Interactive mode (if used) presents clear choices
- ✅ User selections tracked accurately

---

## Phase 4: Automated Processing

### Objective
Execute selected actions: add wiki links and/or create zettels.

### Step 4.1: Add Wiki Links

For each concept selected for linking:

```python
def add_wiki_links(concept):
    term = concept["original_term"]
    occurrences = concept["occurrences"]

    # Determine proper page name
    if concept["page_status"] == "EXISTS":
        page_name = term
    elif concept["page_status"] == "EXISTS_VARIANT":
        page_name = concept["variant_name"]  # Use variant that exists
    else:
        # Capitalize properly for new page
        page_name = term.title() if term.islower() else term

    # For each occurrence, update the file
    for occurrence in occurrences:
        file_path = occurrence["file"]
        line_number = occurrence["line_number"]

        # Read file
        content = read_file(file_path)
        lines = content.split('\n')

        # Get line
        line = lines[line_number - 1]

        # Create wiki link, preserving case
        # Find the term in the line (case-insensitive)
        import re
        pattern = re.compile(re.escape(term), re.IGNORECASE)

        # Replace with wiki link
        def replace_with_link(match):
            original_text = match.group(0)
            # Preserve original case for display, use proper page name for link
            return f"[[{page_name}]]"

        # Only replace if not already in [[...]]
        # Split line by [[...]] sections
        parts = re.split(r'(\[\[.*?\]\])', line)
        new_parts = []
        for part in parts:
            if part.startswith('[['):
                # Already a wiki link, don't modify
                new_parts.append(part)
            else:
                # Plain text, apply replacement
                new_parts.append(pattern.sub(replace_with_link, part))

        new_line = ''.join(new_parts)

        # Update line
        lines[line_number - 1] = new_line

        # Write file
        new_content = '\n'.join(lines)
        write_file(file_path, new_content)

        # Track success
        concept["link_added_count"] += 1

    return concept["link_added_count"]
```

**Link Addition Rules**:
- ✅ Preserve original text capitalization where sensible
- ✅ Use proper page name in wiki link syntax
- ✅ Never create links inside existing `[[...]]` sections
- ✅ Handle singular/plural variations intelligently
- ✅ Maintain original markdown formatting
- ✅ Update all occurrences consistently

**Edge Cases**:
- **Term appears inside code block**: Skip (don't link code)
- **Term inside URL**: Skip (don't break URLs)
- **Term already partially linked**: Only link unlinked instances
- **Overlapping terms**: Prefer longer, more specific term

### Step 4.2: Create Zettels

For each concept selected for zettel creation:

```python
def create_zettel(concept):
    term = concept["original_term"]
    contexts = [occ["context"] for occ in concept["occurrences"]]
    category = concept["category"]

    # Build context summary for synthesis
    context_summary = f"""
    Context for [[{term}]]:

    Category: {category}
    Occurrences: {concept["total_occurrences"]} times across {len(concept["files"])} files

    Referenced in:
    """

    for file, context in zip(concept["files"], contexts):
        context_summary += f"\n{file}:\n  \"{context}\"\n"

    # Identify related concepts from same files
    related = concept.get("co_occurring_concepts", [])
    if related:
        context_summary += f"\nRelated concepts mentioned alongside:\n"
        for rel in related[:5]:  # Top 5
            context_summary += f"- [[{rel}]]\n"

    # Delegate to synthesize-knowledge
    invoke_command(
        "/knowledge/synthesize-knowledge",
        topic=term,
        additional_context=context_summary
    )

    # After synthesis completes, add wiki links
    if page_created_successfully(term):
        add_wiki_links(concept)
        return "SUCCESS"
    else:
        return "FAILED"
```

**Synthesis Instructions**:
```
/knowledge/synthesize-knowledge "{term}"

Additional context for synthesis:
- This topic was identified as unlinked concept in journal entries
- Category: {category}
- Mentioned {count} times across {file_count} files
- Related concepts: {related_list}
- Context: {context_summary}

Please create a comprehensive zettel (500+ words) covering:
1. What {term} is and core functionality
2. Key concepts and technical details
3. Use cases and applications
4. Comparison to alternatives (if applicable)
5. Related concepts: {related_concepts_as_links}

CRITICAL: Follow hub/spoke architecture:
- Create comprehensive topic page (500+ words)
- Add brief summary to daily hub (30-80 words with links)
- NO comprehensive content in daily hub
```

### Step 4.3: Track Processing Results

Maintain results for each concept:

```python
results = {
    "concepts_processed": [],
    "links_added": 0,
    "zettels_created": 0,
    "errors": []
}

for concept in selected_concepts:
    result = {
        "term": concept["original_term"],
        "action": concept["selected_action"],  # "link" or "create"
        "status": "SUCCESS" | "PARTIAL" | "FAILED",
        "links_added": 0,
        "zettel_created": False,
        "files_modified": [],
        "error": None
    }

    try:
        if concept["selected_action"] == "link":
            result["links_added"] = add_wiki_links(concept)
            result["status"] = "SUCCESS"

        elif concept["selected_action"] == "create":
            synthesis_result = create_zettel(concept)
            if synthesis_result == "SUCCESS":
                result["zettel_created"] = True
                result["links_added"] = concept["link_added_count"]
                result["status"] = "SUCCESS"
            else:
                result["status"] = "FAILED"
                result["error"] = "Zettel creation failed"

    except Exception as e:
        result["status"] = "FAILED"
        result["error"] = str(e)
        results["errors"].append(result)

    results["concepts_processed"].append(result)

    if result["status"] == "SUCCESS":
        results["links_added"] += result["links_added"]
        if result["zettel_created"]:
            results["zettels_created"] += 1
```

### Success Criteria - Phase 4

- ✅ Wiki links added safely without breaking markdown
- ✅ All occurrences of concept linked consistently
- ✅ Zettels created via synthesize-knowledge delegation
- ✅ Hub/spoke architecture maintained (brief summaries + comprehensive pages)
- ✅ Original text formatting preserved
- ✅ Errors handled gracefully without aborting workflow
- ✅ All changes tracked with file paths and counts

### Example Processing Output

```
🚀 Processing Concepts

**Action**: create-high
**Concepts Selected**: 2 (high priority)

---

**Concept 1/2: Kubernetes** (Technology/Product)

Creating comprehensive zettel...
✓ Delegated to /knowledge/synthesize-knowledge
✓ Research completed (4 sources found)
✓ Zettel created: Kubernetes.md (1,623 words)
✓ Daily hub updated: Knowledge Synthesis - 2025-12-14.md (65 words)

Adding wiki links...
✓ 2025_12_14.md: 3 links added
✓ 2025_12_13.md: 2 links added
✓ Total links: 5

Status: SUCCESS ✓

---

**Concept 2/2: network policies** (Concept/Theory)

Creating comprehensive zettel...
✓ Delegated to /knowledge/synthesize-knowledge
✓ Research completed (3 sources found)
✓ Zettel created: Network Policies.md (892 words)
✓ Daily hub updated: Knowledge Synthesis - 2025-12-14.md (58 words)

Adding wiki links...
✓ 2025_12_14.md: 3 links added
✓ Total links: 3

Status: SUCCESS ✓

---

✅ Processing Complete
- Concepts processed: 2/2
- Zettels created: 2
- Wiki links added: 8
- Files modified: 2
- Errors: 0
```

---

## Phase 5: Verification and Reporting

### Objective
Verify all changes were successful and provide comprehensive completion report.

### Step 5.1: Verify Link Additions

For each file modified:

```python
def verify_link_additions(results):
    verification = {
        "total_expected": 0,
        "total_verified": 0,
        "failed_links": []
    }

    for result in results["concepts_processed"]:
        if result["links_added"] == 0:
            continue

        term = result["term"]
        expected_links = result["links_added"]
        verification["total_expected"] += expected_links

        # Re-read files and count [[Term]] occurrences
        for file_path in result["files_modified"]:
            content = read_file(file_path)

            # Count wiki links to this term
            pattern = f"\\[\\[{re.escape(term)}\\]\\]"
            actual_count = len(re.findall(pattern, content, re.IGNORECASE))

            verification["total_verified"] += actual_count

            if actual_count != expected_links:
                verification["failed_links"].append({
                    "file": file_path,
                    "term": term,
                    "expected": expected_links,
                    "actual": actual_count
                })

    return verification
```

### Step 5.2: Verify Zettel Creation

For each zettel that should have been created:

```python
def verify_zettel_creation(results):
    verification = {
        "total_expected": results["zettels_created"],
        "total_verified": 0,
        "quality_issues": []
    }

    for result in results["concepts_processed"]:
        if not result["zettel_created"]:
            continue

        term = result["term"]
        page_path = f"/storage/emulated/0/personal-wiki/logseq/pages/{term}.md"

        # Check file exists
        if not os.path.exists(page_path):
            verification["quality_issues"].append({
                "term": term,
                "issue": "File not found",
                "severity": "ERROR"
            })
            continue

        # Check word count
        content = read_file(page_path)
        word_count = len(content.split())

        if word_count < 500:
            verification["quality_issues"].append({
                "term": term,
                "issue": f"Only {word_count} words (minimum 500)",
                "severity": "WARNING"
            })
        else:
            verification["total_verified"] += 1

        # Check for sources
        if "## Sources" not in content:
            verification["quality_issues"].append({
                "term": term,
                "issue": "Missing Sources section",
                "severity": "WARNING"
            })

    return verification
```

### Step 5.3: Generate Completion Report

Create comprehensive final report:

```markdown
## Unlinked Concepts Processing Complete

**Execution Summary**:
- Command: /knowledge/identify-unlinked-concepts [scope] [action] [min_priority] [min_occurrences]
- Scan Scope: [scope description]
- Action: [action]
- Execution Time: [timestamp]

---

### Discovery Phase

**Files Scanned**: [count]
**Candidates Detected**: [count]
**After Filtering**: [count] (min_occurrences: [N], min_priority: [level])

**Priority Breakdown**:
- High priority: [count] concepts
- Medium priority: [count] concepts
- Low priority: [count] concepts

---

### Processing Phase

**Concepts Processed**: [count]

**Successful**:
1. [[Kubernetes]] (Technology/Product)
   - Action: Created zettel + added links
   - Zettel: Kubernetes.md (1,623 words, 4 sources)
   - Links added: 5 across 2 files
   - Files modified: 2025_12_14.md, 2025_12_13.md

2. [[Network Policies]] (Concept/Theory)
   - Action: Created zettel + added links
   - Zettel: Network Policies.md (892 words, 3 sources)
   - Links added: 3 in 2025_12_14.md
   - Files modified: 2025_12_14.md

**Partial Success**: [count]
(None) OR
- [[Topic X]] - Links added but zettel creation failed

**Failed**: [count]
(None) OR
- [[Topic Y]] - Reason: [error message]

---

### Verification Phase

**Link Additions**:
- ✅ Expected links: [count]
- ✅ Verified links: [count]
- ✅ Success rate: [percentage]%

**Zettel Creation**:
- ✅ Expected zettels: [count]
- ✅ Created and verified: [count]
- ⚠️  Quality warnings: [count]

**Quality Issues** (if any):
- [[Term]] - Only [X] words (minimum 500 recommended)
- [[Term]] - Missing Sources section

---

### Impact Summary

**Before**:
- Unlinked concept mentions: [count] across [file_count] files
- Knowledge graph gaps: [count] missing pages
- Manual linking required: Yes

**After**:
- Wiki links added: [count]
- New zettels created: [count]
- Files modified: [count]
- Knowledge graph gaps resolved: [count]

**Knowledge Base Growth**:
- New content: [total_words] words
- New sources: [total_sources] references
- New connections: [total_links] wiki links

---

### Files Modified

**Journal Entries**: [count]
- /storage/emulated/0/personal-wiki/logseq/journals/2025_12_14.md (+8 links)
- /storage/emulated/0/personal-wiki/logseq/journals/2025_12_13.md (+2 links)

**Pages Created**: [count]
- /storage/emulated/0/personal-wiki/logseq/pages/Kubernetes.md (new)
- /storage/emulated/0/personal-wiki/logseq/pages/Network Policies.md (new)

**Daily Synthesis Updated**:
- /storage/emulated/0/personal-wiki/logseq/pages/Knowledge Synthesis - 2025-12-14.md

---

### Next Steps

**Recommended Actions**:
1. Review newly created zettels for accuracy and completeness
2. Add more sources to zettels with < 3 references
3. Expand related concepts mentioned in new zettels

**Remaining Unlinked Concepts** (not processed this run):

**Medium Priority** ([count]):
- [[AWS Security Groups]] - 2 occurrences in 2025_12_14.md
  - Action: /knowledge/identify-unlinked-concepts today create-all medium

**Low Priority** ([count]):
- [[token bucket algorithm]] - 1 occurrence
  - Consider: Add to "Needs Synthesis" for manual research

**Suggestions**:
- Run `/knowledge/validate-links` to verify all links resolve correctly
- Run `/knowledge/expand-missing-topics` to discover more missing concepts
- Continue daily practice of identifying and linking concepts
```

### Success Criteria - Phase 5

- ✅ All link additions verified by re-reading files
- ✅ All created zettels checked for existence and quality
- ✅ Quality issues identified and reported
- ✅ Comprehensive report generated with metrics
- ✅ Before/after comparison shows clear impact
- ✅ File paths documented for all changes
- ✅ Next steps provided for remaining work
- ✅ Success rate > 90% for link additions
- ✅ All created zettels meet minimum standards (or flagged)

---

## Edge Cases and Error Handling

### Edge Case 1: Ambiguous Terms

**Scenario**: "Lambda" could be AWS Lambda or lambda calculus.

**Detection**:
```python
ambiguous_terms = {
    "Lambda": ["AWS Lambda", "lambda calculus", "Lambda function"],
    "Delta": ["Delta encoding", "Delta Lake", "River delta"],
    "Stream": ["Java Stream", "Kafka Stream", "data stream"],
}

if normalized_term in ambiguous_terms:
    # Mark as ambiguous
    candidate["ambiguous"] = True
    candidate["possible_meanings"] = ambiguous_terms[normalized_term]
```

**Handling**:
```
⚠️  Ambiguous Term: "Lambda"

**Possible Meanings**:
1. AWS Lambda (serverless compute)
2. Lambda calculus (formal system)
3. Lambda function (programming)

**Contexts**:
- "deploying with Lambda functions" → likely AWS Lambda
- "functional programming with lambda" → likely lambda calculus

**Action Required**:
- Review contexts and specify which meaning to create
- Manual invocation: /knowledge/synthesize-knowledge "AWS Lambda"
```

**Resolution**:
- Flag in report with possible meanings
- Show contexts to help user decide
- Require manual clarification (don't auto-create)

---

### Edge Case 2: Acronym Expansions

**Scenario**: "K8s" is short for "Kubernetes".

**Detection**:
```python
acronym_expansions = {
    "K8s": "Kubernetes",
    "i18n": "internationalization",
    "a11y": "accessibility",
    "l10n": "localization",
}

if term in acronym_expansions:
    expanded = acronym_expansions[term]
    # Check if expanded form exists
```

**Handling**:
```
ℹ️  Acronym Detected: "K8s"

**Expanded Form**: Kubernetes
**Status**: Page exists (Kubernetes.md)

**Action**: Adding wiki links using expanded form [[Kubernetes]]
- Replacing "K8s" → "[[Kubernetes]]" (or "[[Kubernetes|K8s]]" to preserve display)
```

**Resolution**:
- Maintain mapping of common acronyms
- Link to expanded form page
- Consider using link aliases: `[[Kubernetes|K8s]]`

---

### Edge Case 3: Already Partially Linked

**Scenario**: "Kubernetes" mentioned 5 times, 2 already as `[[Kubernetes]]`.

**Detection**:
```python
total_mentions = 5
linked_mentions = 2  # Already as [[Kubernetes]]
unlinked_mentions = total_mentions - linked_mentions  # = 3

if unlinked_mentions > 0 and linked_mentions > 0:
    # Partially linked
    candidate["partially_linked"] = True
```

**Handling**:
```
ℹ️  Partially Linked: "Kubernetes"

**Status**:
- Total mentions: 5
- Already linked: 2
- Unlinked: 3

**Action**: Adding wiki links to 3 unlinked instances only
```

**Resolution**:
- Only add links to unlinked instances
- Report both counts clearly
- Verify final state has all instances linked

---

### Edge Case 4: Case Variations

**Scenario**: "kubernetes" (lowercase) and "Kubernetes" (capitalized).

**Detection**:
```python
# Group by normalized (lowercase) form
normalized_groups = {}
for candidate in candidates:
    norm = candidate["normalized"]
    if norm not in normalized_groups:
        normalized_groups[norm] = []
    normalized_groups[norm].append(candidate)

# Find groups with multiple case variations
for norm, group in normalized_groups.items():
    if len(group) > 1:
        # Case variations detected
```

**Handling**:
```
⚠️  Case Variations Detected: "Kubernetes"

**Variations Found**:
- "Kubernetes" (capitalized) - 3 occurrences
- "kubernetes" (lowercase) - 2 occurrences

**Action**: Using most common capitalization: "Kubernetes"
**Page**: Kubernetes.md

**Note**: All variations will link to [[Kubernetes]] page.
Logseq wiki links are case-sensitive - recommend standardizing capitalization.
```

**Resolution**:
- Use most common capitalization for page name
- Link all variations to same page
- Warn user about case sensitivity
- Suggest manual standardization

---

### Edge Case 5: Compound Concepts

**Scenario**: "AWS Lambda functions" - is it "AWS Lambda" or "Lambda Functions"?

**Detection**:
```python
# Detect overlapping/nested concepts
if "AWS Lambda" in candidates and "Lambda Functions" in candidates:
    # Check if they overlap in text
    if overlaps_in_context(candidates["AWS Lambda"], candidates["Lambda Functions"]):
        # Compound concept
```

**Handling**:
```
⚠️  Overlapping Concepts Detected

**Compound Phrase**: "AWS Lambda functions"

**Possible Interpretations**:
1. [[AWS Lambda]] (the service) + "functions" (generic term)
   - Link: "[[AWS Lambda]] functions"

2. [[Lambda Functions]] (specific programming concept)
   - Link: "[[Lambda Functions]]"

**Context**: "deploying with AWS Lambda functions"

**Recommendation**: Create [[AWS Lambda]] page (service)
Using "[[AWS Lambda]] functions" (service + generic term)
```

**Resolution**:
- Detect overlapping terms
- Choose longer, more specific term when appropriate
- Or split into multiple links: `[[AWS Lambda]] functions`
- Prioritize based on context

---

### Edge Case 6: Page Name Variations

**Scenario**: Should it be "Network Policy" (singular) or "Network Policies" (plural)?

**Detection**:
```python
def find_name_variations(term):
    variations = []

    # Check singular/plural
    singular = singularize(term)
    plural = pluralize(term)

    for variant in [singular, plural]:
        page_path = f"logseq/pages/{variant}.md"
        if os.path.exists(page_path):
            variations.append((variant, page_path))

    return variations
```

**Handling**:
```
ℹ️  Name Variation Found

**Detected Term**: "Network Policies" (plural)
**Existing Page**: Network Policy.md (singular)

**Action**: Linking to existing page [[Network Policy]]
All instances of "network policies" → [[Network Policy]]

**Note**: Logseq will display as "Network Policy" in links.
To preserve plural display, use alias: [[Network Policy|network policies]]
```

**Resolution**:
- Check both singular and plural forms
- Link to whichever exists
- Use link aliases if display text matters: `[[Network Policy|network policies]]`

---

### Edge Case 7: Term Inside Code Block

**Scenario**: "Kubernetes" mentioned in code block `kubectl get pods`.

**Detection**:
```python
def is_in_code_block(line, position):
    # Check if position is inside backticks
    before = line[:position]
    backtick_count = before.count('`')

    # If odd number of backticks before, we're inside code
    return backtick_count % 2 == 1

def is_in_fenced_code_block(lines, line_number):
    # Check if line is inside ``` ``` block
    fence_count = 0
    for i in range(line_number):
        if lines[i].strip().startswith('```'):
            fence_count += 1

    # If odd number of fences before, we're inside code block
    return fence_count % 2 == 1
```

**Handling**:
```
ℹ️  Skipping Code Block

**Line**: `kubectl get pods -n kubernetes-system`
**Reason**: "kubernetes" appears inside inline code backticks

**Action**: Skipping (not creating wiki link inside code)
```

**Resolution**:
- Detect inline code: `...`
- Detect fenced code blocks: ``` ... ```
- Skip any matches inside code
- Only link in prose text

---

### Edge Case 8: Term in URL

**Scenario**: "kubernetes" in URL `https://kubernetes.io/docs`.

**Detection**:
```python
def is_in_url(line, term_position):
    # Find all URLs in line
    url_pattern = r'https?://[^\s)]+'

    for match in re.finditer(url_pattern, line):
        url_start, url_end = match.span()
        if url_start <= term_position < url_end:
            return True

    return False
```

**Handling**:
```
ℹ️  Skipping URL

**Line**: "See https://kubernetes.io/docs for details"
**Reason**: "kubernetes" appears inside URL

**Action**: Skipping (not creating wiki link inside URL)
```

**Resolution**:
- Detect URLs in line
- Skip any matches inside URL text
- Maintain URL integrity

---

### Edge Case 9: Synthesis Fails

**Scenario**: `/knowledge/synthesize-knowledge` times out or fails.

**Detection**:
```python
try:
    result = invoke_command("/knowledge/synthesize-knowledge", topic=term)
    if result.status != "SUCCESS":
        raise Exception(f"Synthesis failed: {result.error}")
except Exception as e:
    # Synthesis failed
```

**Handling**:
```
❌ Zettel Creation Failed: [[Kubernetes]]

**Error**: Research timeout after 180 seconds

**Action**:
- Marked as FAILED
- Wiki links NOT added (page doesn't exist)
- Continue with remaining concepts

**Retry**:
Manual invocation: /knowledge/synthesize-knowledge "Kubernetes"
```

**Resolution**:
- Log error details
- Mark concept as FAILED
- Don't add wiki links (no page to link to)
- Continue with remaining concepts
- Provide retry instructions in final report

---

### Edge Case 10: No Concepts Found

**Scenario**: Scan completes but no concepts detected.

**Detection**:
```python
if len(candidates) == 0:
    # No concepts found
```

**Handling**:
```
✅ No Unlinked Concepts Found

**Scan Results**:
- Files scanned: 3
- Lines processed: 847
- Already linked terms: 42
- New concepts detected: 0

**Status**: Your knowledge graph is well-connected! ✓

All technical terms in the scanned content are already wiki-linked.

**Suggestions**:
- Continue daily practice of linking concepts as you write
- Run `/knowledge/validate-links` for comprehensive link health check
- Run `/knowledge/expand-missing-topics` to find missing topic pages
```

**Resolution**:
- Report success (well-connected knowledge graph)
- Provide positive feedback
- Suggest related commands

---

## Usage Examples

### Example 1: Daily Journal Review (Default)

**Scenario**: Review today's journal for unlinked concepts.

**Command**:
```
/knowledge/identify-unlinked-concepts
```

**Equivalent to**:
```
/knowledge/identify-unlinked-concepts today report medium 2
```

**Execution**:

1. **Discovery**:
   - Scanned: 2025_12_14.md (247 lines)
   - Detected: 12 potential concepts
   - After filtering (2+ occurrences, medium+ priority): 6 concepts

2. **Report Generated**:
   ```
   ## Unlinked Concepts Found

   **High Priority** (2):
   1. Kubernetes (Technology) - 5 occurrences
   2. network policies (Concept) - 3 occurrences

   **Medium Priority** (4):
   3. AWS Security Groups - 2 occurrences
   4. CRDT - 2 occurrences (page exists)
   5. Calico - 2 occurrences
   6. Cilium - 2 occurrences
   ```

3. **User Action**: Reviews report, decides to process high-priority items.

4. **Next Command**:
   ```
   /knowledge/identify-unlinked-concepts today create-high
   ```

---

### Example 2: Add Wiki Links Only

**Scenario**: Add wiki links for concepts where pages already exist.

**Command**:
```
/knowledge/identify-unlinked-concepts today link
```

**Execution**:

1. **Discovery**: Found 6 concepts

2. **Filtering**: Only process concepts where page exists
   - "CRDT" → found Conflict-Free Replicated Data Types.md
   - Others: MISSING (skip)

3. **Processing**:
   ```
   🔗 Adding Wiki Links

   **Concept: CRDT**
   - Page exists: Conflict-Free Replicated Data Types.md
   - Adding links to 2 occurrences

   ✓ 2025_12_14.md line 45: Added [[Conflict-Free Replicated Data Types]]
   ✓ 2025_12_13.md line 89: Added [[Conflict-Free Replicated Data Types]]

   Status: SUCCESS
   ```

4. **Report**:
   ```
   ## Wiki Links Added

   **Modified Files**: 2
   - 2025_12_14.md: +1 link
   - 2025_12_13.md: +1 link

   **Links to Existing Pages**: 2
   - [[Conflict-Free Replicated Data Types]] (2 instances)

   **Concepts Skipped** (no existing page): 5
   - Kubernetes, network policies, AWS Security Groups, Calico, Cilium

   **Next Steps**:
   Run `/knowledge/identify-unlinked-concepts today create-high` to create missing pages
   ```

---

### Example 3: Create Zettels for High-Priority

**Scenario**: Research and create zettels for most important unlinked concepts.

**Command**:
```
/knowledge/identify-unlinked-concepts today create-high high
```

**Execution**:

1. **Discovery**: Found 2 high-priority concepts

2. **Processing**:
   ```
   🚀 Creating Zettels (High Priority)

   **Concept 1/2: Kubernetes**

   ✓ Delegating to /knowledge/synthesize-knowledge...
   ✓ Research completed (4 sources)
   ✓ Zettel created: Kubernetes.md (1,623 words)
   ✓ Daily hub updated (65 words with links)
   ✓ Adding wiki links: 5 instances across 2 files

   **Concept 2/2: network policies**

   ✓ Delegating to /knowledge/synthesize-knowledge...
   ✓ Research completed (3 sources)
   ✓ Zettel created: Network Policies.md (892 words)
   ✓ Daily hub updated (58 words with links)
   ✓ Adding wiki links: 3 instances in 1 file
   ```

3. **Verification**:
   ```
   ✅ All Zettels Created Successfully

   **Created**: 2 zettels
   - Kubernetes.md (1,623 words, 4 sources) ✓
   - Network Policies.md (892 words, 3 sources) ✓

   **Wiki Links Added**: 8 total
   - 2025_12_14.md: +6 links
   - 2025_12_13.md: +2 links

   **Daily Synthesis Updated**:
   - Knowledge Synthesis - 2025-12-14.md (+2 sections)
   ```

---

### Example 4: Interactive Mode

**Scenario**: Review each concept and choose action manually.

**Command**:
```
/knowledge/identify-unlinked-concepts week interactive medium 1
```

**Execution**:

1. **Discovery**: Found 18 concepts from past week

2. **Interactive Prompt**:
   ```
   📋 Interactive Concept Selection

   Found 18 concepts. For each, choose action:
   [L] Add wiki links only
   [C] Create zettel + add links
   [S] Skip
   [A] Accept all remaining with default action
   [Q] Quit

   ---

   1/18: **Kubernetes** (Technology) - 8 occurrences across 4 files
         Page: MISSING | Links: NEVER_LINKED
         Context: "setting up Kubernetes cluster"
         Suggested: Create zettel + add links

         Action [L/C/S/A/Q]: C

   ✓ Marked for zettel creation

   ---

   2/18: **Docker** (Technology) - 6 occurrences across 3 files
         Page: EXISTS (Docker.md, 1,234 words)
         Links: NEVER_LINKED
         Suggested: Add wiki links only

         Action [L/C/S/A/Q]: L

   ✓ Marked for wiki linking

   ---

   3/18: **token bucket algorithm** (Algorithm) - 1 occurrence
         Page: MISSING | Links: NEVER_LINKED
         Suggested: Skip (low occurrence)

         Action [L/C/S/A/Q]: S

   ✓ Skipped

   ---

   [... continues for all 18 concepts ...]

   Summary:
   - Create zettel: 5 concepts
   - Add links only: 8 concepts
   - Skip: 5 concepts

   Proceed with selected actions? [Y/n]: Y
   ```

3. **Processing**: Executes selected actions

4. **Report**: Shows results for each concept

---

### Example 5: Weekly Comprehensive Scan

**Scenario**: Find all unlinked concepts from this week's journals.

**Command**:
```
/knowledge/identify-unlinked-concepts week create-all low 1
```

**Parameters**:
- Scope: Past 7 days
- Action: Create zettels for all missing concepts
- Min priority: low (include everything)
- Min occurrences: 1 (even single mentions)

**Execution**:

1. **Discovery**:
   - Scanned: 7 journal files
   - Detected: 45 potential concepts
   - After filtering (1+ occurrences, low+ priority): 45 concepts

2. **Categorization**:
   - High priority: 8 concepts
   - Medium priority: 15 concepts
   - Low priority: 22 concepts

3. **Processing**:
   - Create zettels: 27 (18 missing, 9 failed)
   - Add links only: 18 (existing pages)

4. **Results**:
   ```
   ## Weekly Comprehensive Scan Complete

   **Concepts Processed**: 45/45

   **Zettels Created**: 18
   **Zettels Failed**: 9 (research timeouts, low-quality sources)
   **Wiki Links Added**: 67 across 7 files

   **Impact**:
   - New content: 16,483 words
   - New sources: 72 references
   - Knowledge graph growth: 18 new nodes, 67 new connections

   **Failed Concepts** (review and retry):
   - [[Obscure Framework]] - No high-quality sources found
   - [[Niche Technology]] - Research timeout
   ... (7 more)
   ```

---

### Example 6: Specific File Scan

**Scenario**: Process concepts from specific synthesis page.

**Command**:
```
/knowledge/identify-unlinked-concepts file:/storage/emulated/0/personal-wiki/logseq/pages/Knowledge Synthesis - 2025-12-10.md report
```

**Execution**:

1. **Discovery**: Scanned single file

2. **Report**:
   ```
   ## Unlinked Concepts in Specific File

   **File**: Knowledge Synthesis - 2025-12-10.md

   **Found**: 8 concepts

   **High Priority** (0): None

   **Medium Priority** (2):
   - Docker Compose - 2 occurrences
   - Container Networking - 2 occurrences

   **Low Priority** (6):
   - Volume Mounts - 1 occurrence
   - Port Binding - 1 occurrence
   ... (4 more)

   **Recommendation**:
   Run `/knowledge/identify-unlinked-concepts file:/storage/emulated/0/personal-wiki/logseq/pages/Knowledge Synthesis - 2025-12-10.md create-all medium` to create medium+ priority zettels
   ```

---

## Integration Patterns

### Workflow 1: Daily Journal Writing + Linking

**Daily Practice**:
```bash
# 1. Write journal entry naturally (don't worry about links)
# Just write in plain text

# 2. After writing, identify unlinked concepts
/knowledge/identify-unlinked-concepts today report

# 3. Review findings, then add links to existing pages
/knowledge/identify-unlinked-concepts today link

# 4. Create zettels for important new concepts
/knowledge/identify-unlinked-concepts today create-high

# 5. Validate all links
/knowledge/validate-links
```

**Benefits**:
- Write naturally without interrupting flow
- Systematically link concepts after writing
- Build knowledge graph incrementally

---

### Workflow 2: Pre-Synthesis Discovery

**Before running synthesis**:
```bash
# 1. Identify concepts that need research
/knowledge/identify-unlinked-concepts week report high

# 2. Review high-priority concepts - these are important topics mentioned multiple times

# 3. Manually research and synthesize the most important ones
/knowledge/synthesize-knowledge "Important Concept from List"

# 4. After synthesis, link remaining mentions
/knowledge/identify-unlinked-concepts week link
```

**Benefits**:
- Discover what topics deserve deep research
- Prioritize synthesis efforts
- Ensure comprehensive coverage of important concepts

---

### Workflow 3: Weekly Knowledge Graph Maintenance

**Weekly Cleanup**:
```bash
# 1. Find all unlinked concepts from this week
/knowledge/identify-unlinked-concepts week report medium 2

# 2. Create zettels for high-priority items
/knowledge/identify-unlinked-concepts week create-high high

# 3. Add links for existing pages
/knowledge/identify-unlinked-concepts week link

# 4. Validate entire wiki
/knowledge/validate-links stats

# 5. Commit changes
git add .
git commit -m "Weekly knowledge graph linking - [date]"
```

**Benefits**:
- Regular maintenance keeps graph connected
- Prevents accumulation of unlinked mentions
- Systematic knowledge base growth

---

### Workflow 4: Post-Import Processing

**After importing notes from external sources**:
```bash
# 1. Import markdown files to journals/pages

# 2. Identify all unlinked concepts in imported content
/knowledge/identify-unlinked-concepts all report low 1

# 3. Link to existing pages first
/knowledge/identify-unlinked-concepts all link

# 4. Create zettels for frequently mentioned concepts
/knowledge/identify-unlinked-concepts all create-high medium

# 5. Review remaining low-priority concepts
# Manually decide which to research further
```

**Benefits**:
- Quickly integrate external content
- Discover important concepts in imported notes
- Connect imported content to existing knowledge

---

### Workflow 5: Automated Pre-Commit Hook

**Git Hook**: Check for unlinked high-priority concepts before commit.

```bash
#!/bin/bash
# .git/hooks/pre-commit

# Run identification in report mode
result=$(/knowledge/identify-unlinked-concepts today report high 3)

# Parse result for high-priority count
high_priority_count=$(echo "$result" | grep -c "High Priority")

if [ $high_priority_count -gt 0 ]; then
    echo "⚠️  Warning: High-priority unlinked concepts detected"
    echo ""
    echo "$result"
    echo ""
    echo "Recommendation: Run '/knowledge/identify-unlinked-concepts today create-high' before commit"
    echo ""
    echo "Continue anyway? [y/N]"
    read -r response

    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

exit 0
```

**Benefits**:
- Gentle reminder to link concepts
- Ensures consistent knowledge graph quality
- Can be bypassed when needed

---

## Quality Standards

### Detection Accuracy Standards

**MUST ACHIEVE**:
- ✅ Precision > 80% (80%+ of detected concepts are legitimate)
- ✅ Recall > 70% (70%+ of technical terms detected)
- ✅ False positive rate < 20%
- ✅ No common words misidentified as concepts
- ✅ No proper names misidentified as concepts
- ✅ Already-linked text properly excluded

**Detection Strategy Effectiveness**:
- Capitalized terms: 85%+ precision
- Technical suffixes: 80%+ precision
- Acronyms: 75%+ precision (some ambiguity expected)
- Cloud services: 90%+ precision
- Quoted concepts: 70%+ precision (more ambiguity)

---

### Categorization Accuracy Standards

**MUST ACHIEVE**:
- ✅ Category assignment > 85% accurate
- ✅ Priority scores correlate with actual importance
- ✅ High-priority concepts genuinely more important than low-priority
- ✅ Context signals properly weighted

**Category Distribution** (typical):
- Technology/Product: 30-40% of concepts
- Concept/Theory: 20-30%
- Algorithm/Pattern: 15-25%
- Tool/Framework: 15-20%
- Protocol/Standard: 5-10%
- General Concept: 5-10%

---

### Link Addition Safety Standards

**MUST ENSURE**:
- ✅ No broken markdown after link addition
- ✅ Original text meaning preserved
- ✅ No links created inside code blocks
- ✅ No links created inside URLs
- ✅ Proper wiki link syntax: `[[Page Name]]`
- ✅ All occurrences linked consistently
- ✅ File integrity maintained

**Validation**:
- Re-read all modified files
- Verify link count matches expected
- Check markdown renders correctly
- Ensure no formatting corruption

---

### Zettel Creation Delegation Standards

**MUST DELEGATE WITH**:
- ✅ Clear topic name
- ✅ Relevant context from occurrences
- ✅ Related concepts identified
- ✅ Category information
- ✅ Hub/spoke architecture instructions
- ✅ Minimum quality requirements (500+ words, 3+ sources)

**MUST VERIFY AFTER**:
- ✅ Zettel created and exists
- ✅ Meets minimum word count (500+)
- ✅ Has required sections
- ✅ Sources cited (3+)
- ✅ Daily hub updated appropriately (30-80 words)
- ✅ No comprehensive content in hub

---

### Reporting Transparency Standards

**MUST INCLUDE**:
- ✅ Scan scope and file counts
- ✅ Detection method breakdown
- ✅ Priority distribution
- ✅ Suggested actions for each concept
- ✅ Context excerpts for user review
- ✅ Before/after comparison
- ✅ Success and failure counts
- ✅ File paths for all changes
- ✅ Next steps and recommendations

---

## Command Invocation

**Format**: `/knowledge/identify-unlinked-concepts [scope] [action] [min_priority] [min_occurrences]`

**Arguments**:

1. **scope** (optional, default: `today`):
   - `today`: Today's journal entry
   - `week`: Last 7 days of journals
   - `month`: Last 30 days of journals
   - `journals`: All journal entries
   - `pages`: All pages
   - `file:<absolute_path>`: Specific file
   - `all`: Everything (journals + pages)

2. **action** (optional, default: `report`):
   - `report`: Show findings, make no changes
   - `link`: Add wiki links to existing pages only
   - `create-high`: Create zettels for high-priority concepts
   - `create-all`: Create zettels for all concepts
   - `interactive`: Ask user for each concept

3. **min_priority** (optional, default: `medium`):
   - `high`: Only concepts with score ≥ 100
   - `medium`: Concepts with score ≥ 50
   - `low`: All concepts (score ≥ 0)

4. **min_occurrences** (optional, default: `2`):
   - Integer 1-10
   - Minimum times term must appear to be considered
   - Lower = more sensitive, higher = more conservative

**Examples**:

```bash
# Default: Today's journal, report only, medium+ priority, 2+ occurrences
/knowledge/identify-unlinked-concepts

# Add links for existing pages in this week's journals
/knowledge/identify-unlinked-concepts week link

# Create zettels for high-priority concepts from today
/knowledge/identify-unlinked-concepts today create-high high

# Interactive mode for all journals, low priority, single occurrences
/knowledge/identify-unlinked-concepts journals interactive low 1

# Create all missing zettels from specific file
/knowledge/identify-unlinked-concepts file:/storage/emulated/0/personal-wiki/logseq/journals/2025_12_14.md create-all medium 2

# Report on pages directory, high priority only
/knowledge/identify-unlinked-concepts pages report high 3

# Everything, create all, including single mentions
/knowledge/identify-unlinked-concepts all create-all low 1
```

**Execution Mode**: Orchestration with delegation to `/knowledge/synthesize-knowledge`

**Expected Duration**:
- Report only: 10-30 seconds (scanning + analysis)
- Link additions: 1-2 minutes (file modifications)
- Create 1 zettel: 5-10 minutes (research + synthesis)
- Create 5 zettels: 25-50 minutes
- Create 10 zettels: 50-100 minutes

**Prerequisites**:
- `/knowledge/synthesize-knowledge` command available (for zettel creation)
- `/knowledge/validate-links` command available (for verification)
- Read access to logseq/journals and logseq/pages
- Write access to logseq/journals and logseq/pages (for link additions)
- Internet access (for zettel research via Brave Search)

**Success Criteria**:
- ✅ All concepts detected with >80% precision
- ✅ Priority scores accurately reflect importance
- ✅ Wiki links added safely without breaking markdown
- ✅ Zettels created meet quality standards (500+ words, 3+ sources)
- ✅ Hub/spoke architecture maintained
- ✅ Comprehensive report generated
- ✅ Clear next steps provided
- ✅ All changes tracked and verifiable
