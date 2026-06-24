---
description: Scan text to find technical terms, concepts, and topics mentioned in
  plain text that should be wiki-linked or have their own zettels
prompt: "# Identify Unlinked Concepts\n\nTransform plain text mentions of technical\
  \ terms, concepts, technologies, and topics into properly linked zettels, systematically\
  \ enhancing your knowledge graph connectivity.\n\n---\n\n## Critical Problem This\
  \ Solves\n\n**Current Gap**: When writing journal entries and notes, users often\
  \ mention important concepts in plain text without creating wiki links:\n\n```markdown\n\
  - Today I learned about Kubernetes network policies and how they differ from AWS\
  \ security groups\n- Reading about CRDT conflict resolution and vector clocks\n\
  - Implemented rate limiting using token bucket algorithm\n```\n\n**Problems with\
  \ unlinked concepts**:\n- Important terms (`Kubernetes`, `network policies`, `AWS\
  \ security groups`, `CRDT`, `vector clocks`, `token bucket algorithm`) are mentioned\
  \ but not linked\n- These concepts likely deserve their own comprehensive zettels\n\
  - Knowledge graph remains disconnected and less navigable\n- Difficult to discover\
  \ related content and build understanding\n- Manual link creation is tedious and\
  \ error-prone\n\n**What This Command Provides**:\n1. **Automatic detection** of\
  \ technical terms, technologies, products, and concepts\n2. **Priority scoring**\
  \ to identify which terms are most important\n3. **Intelligent filtering** to avoid\
  \ false positives (common words, proper names)\n4. **Automated linking** to convert\
  \ plain text to `[[Wiki Links]]`\n5. **Zettel creation** by delegating to `/knowledge/synthesize-knowledge`\n\
  6. **Context preservation** to maintain original text meaning and formatting\n\n\
  ---\n\n## Core Workflow Overview\n\n```\nPhase 1: Text Scanning and Extraction\n\
  ├─ Scan specified files (journals, pages, specific files)\n├─ Extract potential\
  \ concepts using detection strategies\n├─ Filter already wiki-linked text\n└─ Build\
  \ candidate list\n\nPhase 2: Concept Validation and Categorization\n├─ Check if\
  \ pages exist for each concept\n├─ Check if concept is already linked elsewhere\n\
  ├─ Categorize by type (technology, concept, algorithm, etc.)\n├─ Score importance\
  \ (high/medium/low)\n└─ Apply min_priority and min_occurrences filters\n\nPhase\
  \ 3: User Review and Selection\n├─ Generate organized report by priority\n├─ Show\
  \ contexts where concepts appear\n├─ Recommend actions (create zettel, add links,\
  \ etc.)\n└─ Get user confirmation (if interactive mode)\n\nPhase 4: Automated Processing\n\
  ├─ Add wiki links to source files (if action: link)\n├─ Create zettels via synthesize-knowledge\
  \ (if action: create-*)\n├─ Update references across files\n└─ Track results\n\n\
  Phase 5: Verification and Reporting\n├─ Count links added vs failed\n├─ List zettels\
  \ created\n├─ Report errors or ambiguities\n└─ Suggest follow-up actions\n```\n\n\
  ---\n\n## Phase 1: Text Scanning and Extraction\n\n### Objective\nDiscover potential\
  \ concepts mentioned in plain text that could be wiki-linked or become zettels.\n\
  \n### Step 1.1: Determine Scan Scope\n\nBased on `scope` argument:\n\n**`today`\
  \ (default)**: Today's journal entry\n```\nFile: /storage/emulated/0/personal-wiki/logseq/journals/YYYY_MM_DD.md\n\
  Where YYYY_MM_DD is today's date\n```\n\n**`week`**: Last 7 days of journal entries\n\
  ```\nFiles: /storage/emulated/0/personal-wiki/logseq/journals/YYYY_MM_DD.md\nFor\
  \ the past 7 days\n```\n\n**`month`**: Last 30 days of journal entries\n```\nFiles:\
  \ /storage/emulated/0/personal-wiki/logseq/journals/YYYY_MM_DD.md\nFor the past\
  \ 30 days\n```\n\n**`journals`**: All journal entries\n```\nPattern: /storage/emulated/0/personal-wiki/logseq/journals/*.md\n\
  ```\n\n**`pages`**: All pages\n```\nPattern: /storage/emulated/0/personal-wiki/logseq/pages/*.md\n\
  ```\n\n**`file:<path>`**: Specific file\n```\nFile: Provided absolute path\n```\n\
  \n**`all`**: Everything (journals + pages)\n```\nPattern: /storage/emulated/0/personal-wiki/logseq/**/*.md\n\
  ```\n\n### Step 1.2: Extract Potential Concepts\n\nFor each file in scope, apply\
  \ multiple detection strategies:\n\n**Strategy 1: Capitalized Multi-Word Terms**\n\
  \nPattern: `([A-Z][a-z]+(?:\\s+[A-Z][a-z]+)+)`\n\nExamples:\n- \"Kubernetes Network\
  \ Policies\"\n- \"AWS Security Groups\"\n- \"Conflict Free Replicated Data Types\"\
  \n\n**Strategy 2: Technical Suffix Terms**\n\nPattern: `\\w+(algorithm|protocol|pattern|system|framework|library|tool|service|platform|architecture|methodology|technique|approach)s?\\\
  b`\n\nExamples:\n- \"token bucket algorithm\"\n- \"consensus protocol\"\n- \"circuit\
  \ breaker pattern\"\n- \"microservices architecture\"\n\n**Strategy 3: Cloud Services\
  \ and Products**\n\nPattern: `(AWS|Azure|GCP|Google Cloud|Amazon)\\s+[A-Z]\\w+(?:\\\
  s+[A-Z]\\w+)*`\n\nExamples:\n- \"AWS Lambda\"\n- \"Azure Functions\"\n- \"Google\
  \ Cloud Run\"\n\n**Strategy 4: Acronyms**\n\nPattern: `\\b[A-Z]{2,}(?:/[A-Z0-9]+)?\\\
  b`\n\nExamples:\n- \"CRDT\"\n- \"REST\"\n- \"GraphQL\"\n- \"HTTP/2\"\n- \"OAuth2\"\
  \n\n**Strategy 5: Code References in Backticks**\n\nPattern: `` `([A-Z]\\w+(?:\\\
  .[A-Z]\\w+)*)` ``\n\nExamples:\n- `` `Service.Method` ``\n- `` `ClassName` ``\n\
  - `` `Interface` ``\n\n**Strategy 6: Quoted Concepts**\n\nPattern: `\"([a-z][a-z\\\
  s]{2,49})\"`\n\nExamples:\n- \"eventual consistency\"\n- \"CAP theorem\"\n- \"domain-driven\
  \ design\"\n\n**Strategy 7: Known Technology Names**\n\nMaintain list of common\
  \ technologies/products:\n```\nCommon Technologies:\n- Kubernetes, Docker, PostgreSQL,\
  \ MySQL, MongoDB\n- React, Vue, Angular, Svelte\n- Terraform, Ansible, Chef, Puppet\n\
  - Kafka, RabbitMQ, Redis\n- Prometheus, Grafana, Jaeger\n- Jenkins, CircleCI, GitHub\
  \ Actions\n...\n```\n\nPattern: Case-insensitive match against known list\n\n###\
  \ Step 1.3: Filter and Clean\n\n**Exclude already wiki-linked text**:\n```python\n\
  # Remove any text inside [[...]]\ntext = re.sub(r'\\[\\[([^\\]]+)\\]\\]', '', text)\n\
  # Now extract concepts from remaining text\n```\n\n**Exclude common words**:\n```python\n\
  stop_words = {\n    \"The\", \"This\", \"That\", \"These\", \"Those\",\n    \"January\"\
  , \"February\", ..., \"December\",\n    \"Monday\", \"Tuesday\", ..., \"Sunday\"\
  ,\n    \"Today\", \"Yesterday\", \"Tomorrow\",\n    # ... comprehensive stop word\
  \ list\n}\n\nif candidate in stop_words:\n    continue  # Skip\n```\n\n**Exclude\
  \ proper names**:\n```python\n# Use common name patterns\nname_patterns = [\n  \
  \  r'^[A-Z][a-z]+ [A-Z][a-z]+$',  # John Smith\n    r'^Dr\\. ',  # Dr. Name\n  \
  \  r'^Prof\\. ',  # Prof. Name\n]\n\nif matches_name_pattern(candidate):\n    continue\
  \  # Skip\n```\n\n**Normalize term**:\n```python\n# Remove extra whitespace\nterm\
  \ = ' '.join(term.split())\n\n# Handle possessives\nterm = term.rstrip(\"'s\")\n\
  \n# Store original case but normalize for comparison\nnormalized = term.lower()\n\
  ```\n\n### Step 1.4: Build Candidate List\n\nCreate structured list of potential\
  \ concepts:\n\n```python\ncandidates = {\n    \"Kubernetes\": {\n        \"original_term\"\
  : \"Kubernetes\",\n        \"normalized\": \"kubernetes\",\n        \"detection_method\"\
  : \"capitalized_term\",\n        \"occurrences\": [\n            {\n           \
  \     \"file\": \"2025_12_14.md\",\n                \"line_number\": 23,\n     \
  \           \"context\": \"Investigated Kubernetes network policies for multi-tenant\
  \ isolation\"\n            },\n            {\n                \"file\": \"2025_12_13.md\"\
  ,\n                \"line_number\": 45,\n                \"context\": \"Setting\
  \ up Kubernetes cluster with kubeadm\"\n            }\n        ],\n        \"total_occurrences\"\
  : 2,\n        \"files\": [\"2025_12_14.md\", \"2025_12_13.md\"]\n    },\n    \"\
  network policies\": {\n        \"original_term\": \"network policies\",\n      \
  \  \"normalized\": \"network policies\",\n        \"detection_method\": \"technical_suffix\"\
  ,\n        \"occurrences\": [...],\n        \"total_occurrences\": 3,\n        \"\
  files\": [\"2025_12_14.md\"]\n    }\n}\n```\n\n### Success Criteria - Phase 1\n\n\
  - ✅ All files in scope read successfully\n- ✅ All detection strategies applied\n\
  - ✅ Already-linked text properly excluded\n- ✅ Stop words and proper names filtered\
  \ out\n- ✅ Candidate list built with full occurrence metadata\n- ✅ Original context\
  \ preserved for each occurrence\n- ✅ Precision target: >80% of candidates are legitimate\
  \ concepts\n- ✅ Recall target: >70% of technical terms detected\n\n### Example Extraction\
  \ Output\n\n```\n\U0001F4CA Text Scanning Complete\n\n**Scan Scope**: Today (2025_12_14.md)\n\
  **Lines Processed**: 247\n**Already Linked Terms**: 18 (excluded)\n\n**Potential\
  \ Concepts Detected**: 12\n\n**Detection Methods Applied**:\n- Capitalized terms:\
  \ 5 candidates\n- Technical suffixes: 4 candidates\n- Acronyms: 2 candidates\n-\
  \ Quoted concepts: 1 candidate\n\n**Top Candidates by Occurrence**:\n1. \"Kubernetes\"\
  \ - 5 occurrences\n2. \"network policies\" - 3 occurrences\n3. \"AWS Security Groups\"\
  \ - 2 occurrences\n4. \"CRDT\" - 2 occurrences\n5. \"token bucket algorithm\" -\
  \ 1 occurrence\n...\n\n**Next**: Validating candidates and categorizing...\n```\n\
  \n---\n\n## Phase 2: Concept Validation and Categorization\n\n### Objective\nDetermine\
  \ which candidates already have pages, categorize by type, and assign priority scores.\n\
  \n### Step 2.1: Check Page Existence\n\nFor each candidate:\n\n```python\ndef check_page_status(term):\n\
  \    # Try exact match\n    exact_path = f\"/storage/emulated/0/personal-wiki/logseq/pages/{term}.md\"\
  \n    if os.path.exists(exact_path):\n        return \"EXISTS\", exact_path\n\n\
  \    # Try title case\n    title_case = term.title()\n    title_path = f\"/storage/emulated/0/personal-wiki/logseq/pages/{title_case}.md\"\
  \n    if os.path.exists(title_path):\n        return \"EXISTS\", title_path\n\n\
  \    # Try variations (singular/plural)\n    singular = singularize(term)\n    plural\
  \ = pluralize(term)\n\n    for variant in [singular, plural]:\n        variant_path\
  \ = f\"/storage/emulated/0/personal-wiki/logseq/pages/{variant}.md\"\n        if\
  \ os.path.exists(variant_path):\n            return \"EXISTS_VARIANT\", variant_path\n\
  \n    return \"MISSING\", None\n```\n\n**Page Status**:\n- `EXISTS`: Exact match\
  \ found\n- `EXISTS_VARIANT`: Similar page found (singular/plural)\n- `MISSING`:\
  \ No page exists\n\n### Step 2.2: Check If Already Linked\n\nSearch if term appears\
  \ as wiki link elsewhere:\n\n```python\ndef check_if_linked(term):\n    # Search\
  \ for [[Term]] or [[term]] in all files\n    pattern = f\"\\\\[\\\\[{re.escape(term)}\\\
  \\]\\\\]\"\n\n    # Run grep across wiki\n    result = grep(pattern, case_insensitive=True)\n\
  \n    if result.count > 0:\n        return \"ALREADY_LINKED\", result.count\n  \
  \  else:\n        return \"NEVER_LINKED\", 0\n```\n\n**Link Status**:\n- `ALREADY_LINKED`:\
  \ Term appears as `[[Term]]` in some files\n- `NEVER_LINKED`: Term never appears\
  \ as wiki link\n\n### Step 2.3: Categorize by Type\n\nClassify each concept into\
  \ category:\n\n```python\ndef categorize_concept(term, context):\n    # Technology/Product\n\
  \    tech_patterns = [\n        r'(Kubernetes|Docker|PostgreSQL|Redis|Kafka|...)',\n\
  \        r'(AWS|Azure|GCP) \\w+',\n    ]\n    if matches_any(term, tech_patterns):\n\
  \        return \"Technology/Product\"\n\n    # Concept/Theory\n    concept_keywords\
  \ = ['theorem', 'principle', 'law', 'model', 'consistency']\n    if any(kw in term.lower()\
  \ for kw in concept_keywords):\n        return \"Concept/Theory\"\n\n    # Algorithm/Pattern\n\
  \    algo_keywords = ['algorithm', 'pattern', 'approach', 'technique']\n    if any(kw\
  \ in term.lower() for kw in algo_keywords):\n        return \"Algorithm/Pattern\"\
  \n\n    # Tool/Framework\n    tool_keywords = ['framework', 'library', 'tool', 'utility']\n\
  \    if any(kw in term.lower() for kw in tool_keywords):\n        return \"Tool/Framework\"\
  \n\n    # Protocol/Standard\n    protocol_keywords = ['protocol', 'standard', 'specification',\
  \ 'RFC']\n    if any(kw in term.lower() for kw in protocol_keywords):\n        return\
  \ \"Protocol/Standard\"\n\n    # Check context for hints\n    if re.search(r'(implement|using|with|via)\
  \ ' + re.escape(term), context):\n        return \"Tool/Framework\"\n\n    # Default\n\
  \    return \"General Concept\"\n```\n\n**Categories**:\n- Technology/Product (Kubernetes,\
  \ PostgreSQL, React)\n- Concept/Theory (CAP theorem, eventual consistency)\n- Algorithm/Pattern\
  \ (token bucket, circuit breaker)\n- Tool/Framework (OpenRewrite, Terraform)\n-\
  \ Protocol/Standard (HTTP/2, OAuth2)\n- General Concept (catch-all)\n\n### Step\
  \ 2.4: Score Importance\n\nCalculate priority score:\n\n```python\ndef calculate_priority(candidate):\n\
  \    score = 0\n\n    # Factor 1: Occurrence Count (primary signal)\n    occurrences\
  \ = candidate[\"total_occurrences\"]\n    if occurrences >= 5:\n        score +=\
  \ 100  # Very high priority\n    elif occurrences >= 3:\n        score += 75   #\
  \ High priority\n    elif occurrences == 2:\n        score += 40   # Medium priority\n\
  \    else:\n        score += 10   # Low priority\n\n    # Factor 2: Number of Files\n\
  \    file_count = len(candidate[\"files\"])\n    if file_count >= 3:\n        score\
  \ += 30   # Cross-file usage\n    elif file_count == 2:\n        score += 15\n\n\
  \    # Factor 3: Capitalization (proper nouns more likely important)\n    term =\
  \ candidate[\"original_term\"]\n    if term[0].isupper():\n        score += 10\n\
  \n    # Factor 4: Context Signals\n    contexts = [occ[\"context\"] for occ in candidate[\"\
  occurrences\"]]\n\n    # Technical context indicators\n    tech_indicators = ['implement',\
  \ 'using', 'configure', 'deploy', 'install']\n    if any(indicator in ' '.join(contexts).lower()\
  \ for indicator in tech_indicators):\n        score += 15\n\n    # Importance markers\n\
  \    if any('important' in ctx.lower() for ctx in contexts):\n        score += 20\n\
  \    if any('research' in ctx.lower() for ctx in contexts):\n        score += 10\n\
  \n    # Factor 5: Category\n    category = candidate[\"category\"]\n    if category\
  \ == \"Technology/Product\":\n        score += 10  # Technologies often deserve\
  \ zettels\n    elif category == \"Algorithm/Pattern\":\n        score += 10  # Algorithms\
  \ worth documenting\n\n    # Factor 6: Already Exists?\n    if candidate[\"page_status\"\
  ] == \"EXISTS\":\n        score -= 50  # Lower priority if page exists (just need\
  \ links)\n\n    # Factor 7: Detection Method Confidence\n    method = candidate[\"\
  detection_method\"]\n    if method == \"capitalized_term\":\n        score += 5\
  \   # High confidence\n    elif method == \"technical_suffix\":\n        score +=\
  \ 5   # High confidence\n    elif method == \"acronym\":\n        score += 3   #\
  \ Medium confidence\n\n    return score\n\n# Assign priority level\nif score >=\
  \ 100:\n    priority = \"HIGH\"\nelif score >= 50:\n    priority = \"MEDIUM\"\n\
  else:\n    priority = \"LOW\"\n```\n\n**Priority Levels**:\n- **HIGH** (score ≥\
  \ 100): 3+ occurrences OR important context markers\n- **MEDIUM** (score 50-99):\
  \ 2 occurrences OR significant context\n- **LOW** (score < 50): Single occurrence\
  \ or weak signals\n\n### Step 2.5: Apply Filters\n\nFilter candidates based on arguments:\n\
  \n```python\n# Apply min_occurrences filter\ncandidates = [c for c in candidates\
  \ if c[\"total_occurrences\"] >= min_occurrences]\n\n# Apply min_priority filter\n\
  priority_thresholds = {\n    \"high\": 100,\n    \"medium\": 50,\n    \"low\": 0\n\
  }\nthreshold = priority_thresholds[min_priority]\ncandidates = [c for c in candidates\
  \ if c[\"priority_score\"] >= threshold]\n\n# Sort by priority score (descending)\n\
  candidates.sort(key=lambda c: c[\"priority_score\"], reverse=True)\n```\n\n### Success\
  \ Criteria - Phase 2\n\n- ✅ All candidates checked for existing pages\n- ✅ All candidates\
  \ categorized by type\n- ✅ Priority scores calculated consistently\n- ✅ Filters\
  \ applied correctly (min_occurrences, min_priority)\n- ✅ Results sorted by importance\n\
  - ✅ False positive rate < 20%\n- ✅ High-priority items genuinely more important\
  \ than low-priority\n\n### Example Categorization Output\n\n```\n\U0001F3AF Concept\
  \ Validation and Categorization\n\n**Candidates Analyzed**: 12\n**After Filtering**\
  \ (min_occurrences: 2, min_priority: medium): 6\n\n**High Priority** (score ≥ 100):\n\
  \n1. **Kubernetes** (Technology/Product) - Score: 125\n   - Occurrences: 5 times\
  \ across 3 files\n   - Page status: MISSING\n   - Link status: NEVER_LINKED\n  \
  \ - Context: Technical implementation (\"setting up Kubernetes cluster\")\n   -\
  \ Suggested action: Create zettel + add wiki links\n\n2. **network policies** (Concept/Theory)\
  \ - Score: 105\n   - Occurrences: 3 times in 1 file\n   - Page status: MISSING\n\
  \   - Link status: NEVER_LINKED\n   - Context: Technical deep-dive (\"Kubernetes\
  \ network policies for isolation\")\n   - Suggested action: Create zettel + add\
  \ wiki links\n\n**Medium Priority** (score 50-99):\n\n3. **AWS Security Groups**\
  \ (Technology/Product) - Score: 65\n   - Occurrences: 2 times in 1 file\n   - Page\
  \ status: MISSING\n   - Link status: NEVER_LINKED\n   - Context: Comparison (\"\
  compared with AWS security groups\")\n   - Suggested action: Create zettel\n\n4.\
  \ **CRDT** (Concept/Theory) - Score: 60\n   - Occurrences: 2 times across 2 files\n\
  \   - Page status: EXISTS_VARIANT (found \"Conflict-Free Replicated Data Types.md\"\
  )\n   - Link status: ALREADY_LINKED (4 instances elsewhere)\n   - Suggested action:\
  \ Add wiki links only (page exists)\n\n5. **Calico** (Tool/Framework) - Score: 55\n\
  \   - Occurrences: 2 times in 1 file\n   - Page status: MISSING\n   - Link status:\
  \ NEVER_LINKED\n   - Context: CNI plugin mention\n   - Suggested action: Create\
  \ zettel\n\n6. **Cilium** (Tool/Framework) - Score: 55\n   - Occurrences: 2 times\
  \ in 1 file\n   - Page status: MISSING\n   - Link status: NEVER_LINKED\n   - Context:\
  \ CNI plugin mention\n   - Suggested action: Create zettel\n\n**Filtered Out** (below\
  \ threshold): 6 concepts\n- \"token bucket algorithm\" (1 occurrence)\n- \"label\
  \ selectors\" (1 occurrence)\n...\n\n**Next**: Generating user review report...\n\
  ```\n\n---\n\n## Phase 3: User Review and Selection\n\n### Objective\nPresent findings\
  \ in organized format and determine which actions to take.\n\n### Step 3.1: Generate\
  \ Organized Report\n\nFormat report by priority level:\n\n```markdown\n## Unlinked\
  \ Concepts Found\n\n**Scan Scope**: [scope description]\n**Files Scanned**: [count]\n\
  **Total Candidates**: [count]\n**After Filtering**: [count] (min_occurrences: [N],\
  \ min_priority: [level])\n\n---\n\n### High Priority ([count])\n\n**[Term]** ([Category])\
  \ - Score: [score]\n- **Occurrences**: [count] times across [file_count] files\n\
  - **Page status**: [MISSING|EXISTS|EXISTS_VARIANT]\n- **Link status**: [NEVER_LINKED|ALREADY_LINKED]\n\
  - **Contexts**:\n  - [File]: \"[surrounding text...]\"\n  - [File]: \"[surrounding\
  \ text...]\"\n- **Suggested action**: [Create zettel + add links | Add links only\
  \ | Review manually]\n\n---\n\n### Medium Priority ([count])\n\n[Same format as\
  \ High Priority]\n\n---\n\n### Low Priority ([count])\n\n[Same format, possibly\
  \ condensed]\n\n---\n\n### Summary\n\n**Concepts by Action**:\n- Create zettel +\
  \ add links: [count] concepts\n- Add links only (page exists): [count] concepts\n\
  - Review manually (ambiguous): [count] concepts\n\n**Available Actions**:\n1. `report`\
  \ - You're viewing the report (no changes made)\n2. `link` - Add wiki links to existing\
  \ pages only\n3. `create-high` - Create zettels for high-priority concepts\n4. `create-all`\
  \ - Create zettels for all concepts\n5. `interactive` - Choose which concepts to\
  \ process\n\n**Next Steps**:\n- Review findings above\n- Re-run with desired action,\
  \ e.g.:\n  - `/knowledge/identify-unlinked-concepts today link`\n  - `/knowledge/identify-unlinked-concepts\
  \ today create-high`\n  - `/knowledge/identify-unlinked-concepts today interactive`\n\
  ```\n\n### Step 3.2: Interactive Mode (if action: interactive)\n\nPresent choices\
  \ and get user input:\n\n```\n\U0001F4CB Interactive Concept Selection\n\nFound\
  \ [count] concepts that could be processed.\n\nFor each concept, choose action:\n\
  [L] Add wiki links only\n[C] Create zettel + add wiki links\n[S] Skip\n[A] Accept\
  \ all remaining with default action\n[Q] Quit\n\n---\n\n1/6: **Kubernetes** (Technology/Product)\
  \ - 5 occurrences\n     Page: MISSING | Links: NEVER_LINKED\n     Context: \"setting\
  \ up Kubernetes cluster\"\n\n     Suggested: Create zettel + add links\n\n     Action\
  \ [L/C/S/A/Q]: _\n```\n\nUser inputs choices, command tracks selections.\n\n###\
  \ Step 3.3: Determine Actions Based on Mode\n\n```python\nif action == \"report\"\
  :\n    # Just show report, make no changes\n    return report\n\nelif action ==\
  \ \"link\":\n    # Add wiki links for concepts where page exists\n    concepts_to_link\
  \ = [c for c in candidates if c[\"page_status\"].startswith(\"EXISTS\")]\n\nelif\
  \ action == \"create-high\":\n    # Create zettels for high-priority missing concepts\n\
  \    concepts_to_create = [c for c in candidates\n                         if c[\"\
  priority\"] == \"HIGH\" and c[\"page_status\"] == \"MISSING\"]\n\nelif action ==\
  \ \"create-all\":\n    # Create zettels for all missing concepts\n    concepts_to_create\
  \ = [c for c in candidates if c[\"page_status\"] == \"MISSING\"]\n\nelif action\
  \ == \"interactive\":\n    # Use user-selected actions\n    concepts_to_link = user_selections[\"\
  link\"]\n    concepts_to_create = user_selections[\"create\"]\n```\n\n### Success\
  \ Criteria - Phase 3\n\n- ✅ Report clearly organized by priority\n- ✅ All relevant\
  \ context shown for each concept\n- ✅ Suggested actions appropriate for each concept\n\
  - ✅ Action options clearly explained\n- ✅ Interactive mode (if used) presents clear\
  \ choices\n- ✅ User selections tracked accurately\n\n---\n\n## Phase 4: Automated\
  \ Processing\n\n### Objective\nExecute selected actions: add wiki links and/or create\
  \ zettels.\n\n### Step 4.1: Add Wiki Links\n\nFor each concept selected for linking:\n\
  \n```python\ndef add_wiki_links(concept):\n    term = concept[\"original_term\"\
  ]\n    occurrences = concept[\"occurrences\"]\n\n    # Determine proper page name\n\
  \    if concept[\"page_status\"] == \"EXISTS\":\n        page_name = term\n    elif\
  \ concept[\"page_status\"] == \"EXISTS_VARIANT\":\n        page_name = concept[\"\
  variant_name\"]  # Use variant that exists\n    else:\n        # Capitalize properly\
  \ for new page\n        page_name = term.title() if term.islower() else term\n\n\
  \    # For each occurrence, update the file\n    for occurrence in occurrences:\n\
  \        file_path = occurrence[\"file\"]\n        line_number = occurrence[\"line_number\"\
  ]\n\n        # Read file\n        content = read_file(file_path)\n        lines\
  \ = content.split('\\n')\n\n        # Get line\n        line = lines[line_number\
  \ - 1]\n\n        # Create wiki link, preserving case\n        # Find the term in\
  \ the line (case-insensitive)\n        import re\n        pattern = re.compile(re.escape(term),\
  \ re.IGNORECASE)\n\n        # Replace with wiki link\n        def replace_with_link(match):\n\
  \            original_text = match.group(0)\n            # Preserve original case\
  \ for display, use proper page name for link\n            return f\"[[{page_name}]]\"\
  \n\n        # Only replace if not already in [[...]]\n        # Split line by [[...]]\
  \ sections\n        parts = re.split(r'(\\[\\[.*?\\]\\])', line)\n        new_parts\
  \ = []\n        for part in parts:\n            if part.startswith('[['):\n    \
  \            # Already a wiki link, don't modify\n                new_parts.append(part)\n\
  \            else:\n                # Plain text, apply replacement\n          \
  \      new_parts.append(pattern.sub(replace_with_link, part))\n\n        new_line\
  \ = ''.join(new_parts)\n\n        # Update line\n        lines[line_number - 1]\
  \ = new_line\n\n        # Write file\n        new_content = '\\n'.join(lines)\n\
  \        write_file(file_path, new_content)\n\n        # Track success\n       \
  \ concept[\"link_added_count\"] += 1\n\n    return concept[\"link_added_count\"\
  ]\n```\n\n**Link Addition Rules**:\n- ✅ Preserve original text capitalization where\
  \ sensible\n- ✅ Use proper page name in wiki link syntax\n- ✅ Never create links\
  \ inside existing `[[...]]` sections\n- ✅ Handle singular/plural variations intelligently\n\
  - ✅ Maintain original markdown formatting\n- ✅ Update all occurrences consistently\n\
  \n**Edge Cases**:\n- **Term appears inside code block**: Skip (don't link code)\n\
  - **Term inside URL**: Skip (don't break URLs)\n- **Term already partially linked**:\
  \ Only link unlinked instances\n- **Overlapping terms**: Prefer longer, more specific\
  \ term\n\n### Step 4.2: Create Zettels\n\nFor each concept selected for zettel creation:\n\
  \n```python\ndef create_zettel(concept):\n    term = concept[\"original_term\"]\n\
  \    contexts = [occ[\"context\"] for occ in concept[\"occurrences\"]]\n    category\
  \ = concept[\"category\"]\n\n    # Build context summary for synthesis\n    context_summary\
  \ = f\"\"\"\n    Context for [[{term}]]:\n\n    Category: {category}\n    Occurrences:\
  \ {concept[\"total_occurrences\"]} times across {len(concept[\"files\"])} files\n\
  \n    Referenced in:\n    \"\"\"\n\n    for file, context in zip(concept[\"files\"\
  ], contexts):\n        context_summary += f\"\\n{file}:\\n  \\\"{context}\\\"\\\
  n\"\n\n    # Identify related concepts from same files\n    related = concept.get(\"\
  co_occurring_concepts\", [])\n    if related:\n        context_summary += f\"\\\
  nRelated concepts mentioned alongside:\\n\"\n        for rel in related[:5]:  #\
  \ Top 5\n            context_summary += f\"- [[{rel}]]\\n\"\n\n    # Delegate to\
  \ synthesize-knowledge\n    invoke_command(\n        \"/knowledge/synthesize-knowledge\"\
  ,\n        topic=term,\n        additional_context=context_summary\n    )\n\n  \
  \  # After synthesis completes, add wiki links\n    if page_created_successfully(term):\n\
  \        add_wiki_links(concept)\n        return \"SUCCESS\"\n    else:\n      \
  \  return \"FAILED\"\n```\n\n**Synthesis Instructions**:\n```\n/knowledge/synthesize-knowledge\
  \ \"{term}\"\n\nAdditional context for synthesis:\n- This topic was identified as\
  \ unlinked concept in journal entries\n- Category: {category}\n- Mentioned {count}\
  \ times across {file_count} files\n- Related concepts: {related_list}\n- Context:\
  \ {context_summary}\n\nPlease create a comprehensive zettel (500+ words) covering:\n\
  1. What {term} is and core functionality\n2. Key concepts and technical details\n\
  3. Use cases and applications\n4. Comparison to alternatives (if applicable)\n5.\
  \ Related concepts: {related_concepts_as_links}\n\nCRITICAL: Follow hub/spoke architecture:\n\
  - Create comprehensive topic page (500+ words)\n- Add brief summary to daily hub\
  \ (30-80 words with links)\n- NO comprehensive content in daily hub\n```\n\n###\
  \ Step 4.3: Track Processing Results\n\nMaintain results for each concept:\n\n```python\n\
  results = {\n    \"concepts_processed\": [],\n    \"links_added\": 0,\n    \"zettels_created\"\
  : 0,\n    \"errors\": []\n}\n\nfor concept in selected_concepts:\n    result = {\n\
  \        \"term\": concept[\"original_term\"],\n        \"action\": concept[\"selected_action\"\
  ],  # \"link\" or \"create\"\n        \"status\": \"SUCCESS\" | \"PARTIAL\" | \"\
  FAILED\",\n        \"links_added\": 0,\n        \"zettel_created\": False,\n   \
  \     \"files_modified\": [],\n        \"error\": None\n    }\n\n    try:\n    \
  \    if concept[\"selected_action\"] == \"link\":\n            result[\"links_added\"\
  ] = add_wiki_links(concept)\n            result[\"status\"] = \"SUCCESS\"\n\n  \
  \      elif concept[\"selected_action\"] == \"create\":\n            synthesis_result\
  \ = create_zettel(concept)\n            if synthesis_result == \"SUCCESS\":\n  \
  \              result[\"zettel_created\"] = True\n                result[\"links_added\"\
  ] = concept[\"link_added_count\"]\n                result[\"status\"] = \"SUCCESS\"\
  \n            else:\n                result[\"status\"] = \"FAILED\"\n         \
  \       result[\"error\"] = \"Zettel creation failed\"\n\n    except Exception as\
  \ e:\n        result[\"status\"] = \"FAILED\"\n        result[\"error\"] = str(e)\n\
  \        results[\"errors\"].append(result)\n\n    results[\"concepts_processed\"\
  ].append(result)\n\n    if result[\"status\"] == \"SUCCESS\":\n        results[\"\
  links_added\"] += result[\"links_added\"]\n        if result[\"zettel_created\"\
  ]:\n            results[\"zettels_created\"] += 1\n```\n\n### Success Criteria -\
  \ Phase 4\n\n- ✅ Wiki links added safely without breaking markdown\n- ✅ All occurrences\
  \ of concept linked consistently\n- ✅ Zettels created via synthesize-knowledge delegation\n\
  - ✅ Hub/spoke architecture maintained (brief summaries + comprehensive pages)\n\
  - ✅ Original text formatting preserved\n- ✅ Errors handled gracefully without aborting\
  \ workflow\n- ✅ All changes tracked with file paths and counts\n\n### Example Processing\
  \ Output\n\n```\n\U0001F680 Processing Concepts\n\n**Action**: create-high\n**Concepts\
  \ Selected**: 2 (high priority)\n\n---\n\n**Concept 1/2: Kubernetes** (Technology/Product)\n\
  \nCreating comprehensive zettel...\n✓ Delegated to /knowledge/synthesize-knowledge\n\
  ✓ Research completed (4 sources found)\n✓ Zettel created: Kubernetes.md (1,623 words)\n\
  ✓ Daily hub updated: Knowledge Synthesis - 2025-12-14.md (65 words)\n\nAdding wiki\
  \ links...\n✓ 2025_12_14.md: 3 links added\n✓ 2025_12_13.md: 2 links added\n✓ Total\
  \ links: 5\n\nStatus: SUCCESS ✓\n\n---\n\n**Concept 2/2: network policies** (Concept/Theory)\n\
  \nCreating comprehensive zettel...\n✓ Delegated to /knowledge/synthesize-knowledge\n\
  ✓ Research completed (3 sources found)\n✓ Zettel created: Network Policies.md (892\
  \ words)\n✓ Daily hub updated: Knowledge Synthesis - 2025-12-14.md (58 words)\n\n\
  Adding wiki links...\n✓ 2025_12_14.md: 3 links added\n✓ Total links: 3\n\nStatus:\
  \ SUCCESS ✓\n\n---\n\n✅ Processing Complete\n- Concepts processed: 2/2\n- Zettels\
  \ created: 2\n- Wiki links added: 8\n- Files modified: 2\n- Errors: 0\n```\n\n---\n\
  \n## Phase 5: Verification and Reporting\n\n### Objective\nVerify all changes were\
  \ successful and provide comprehensive completion report.\n\n### Step 5.1: Verify\
  \ Link Additions\n\nFor each file modified:\n\n```python\ndef verify_link_additions(results):\n\
  \    verification = {\n        \"total_expected\": 0,\n        \"total_verified\"\
  : 0,\n        \"failed_links\": []\n    }\n\n    for result in results[\"concepts_processed\"\
  ]:\n        if result[\"links_added\"] == 0:\n            continue\n\n        term\
  \ = result[\"term\"]\n        expected_links = result[\"links_added\"]\n       \
  \ verification[\"total_expected\"] += expected_links\n\n        # Re-read files\
  \ and count [[Term]] occurrences\n        for file_path in result[\"files_modified\"\
  ]:\n            content = read_file(file_path)\n\n            # Count wiki links\
  \ to this term\n            pattern = f\"\\\\[\\\\[{re.escape(term)}\\\\]\\\\]\"\
  \n            actual_count = len(re.findall(pattern, content, re.IGNORECASE))\n\n\
  \            verification[\"total_verified\"] += actual_count\n\n            if\
  \ actual_count != expected_links:\n                verification[\"failed_links\"\
  ].append({\n                    \"file\": file_path,\n                    \"term\"\
  : term,\n                    \"expected\": expected_links,\n                   \
  \ \"actual\": actual_count\n                })\n\n    return verification\n```\n\
  \n### Step 5.2: Verify Zettel Creation\n\nFor each zettel that should have been\
  \ created:\n\n```python\ndef verify_zettel_creation(results):\n    verification\
  \ = {\n        \"total_expected\": results[\"zettels_created\"],\n        \"total_verified\"\
  : 0,\n        \"quality_issues\": []\n    }\n\n    for result in results[\"concepts_processed\"\
  ]:\n        if not result[\"zettel_created\"]:\n            continue\n\n       \
  \ term = result[\"term\"]\n        page_path = f\"/storage/emulated/0/personal-wiki/logseq/pages/{term}.md\"\
  \n\n        # Check file exists\n        if not os.path.exists(page_path):\n   \
  \         verification[\"quality_issues\"].append({\n                \"term\": term,\n\
  \                \"issue\": \"File not found\",\n                \"severity\": \"\
  ERROR\"\n            })\n            continue\n\n        # Check word count\n  \
  \      content = read_file(page_path)\n        word_count = len(content.split())\n\
  \n        if word_count < 500:\n            verification[\"quality_issues\"].append({\n\
  \                \"term\": term,\n                \"issue\": f\"Only {word_count}\
  \ words (minimum 500)\",\n                \"severity\": \"WARNING\"\n          \
  \  })\n        else:\n            verification[\"total_verified\"] += 1\n\n    \
  \    # Check for sources\n        if \"## Sources\" not in content:\n          \
  \  verification[\"quality_issues\"].append({\n                \"term\": term,\n\
  \                \"issue\": \"Missing Sources section\",\n                \"severity\"\
  : \"WARNING\"\n            })\n\n    return verification\n```\n\n### Step 5.3: Generate\
  \ Completion Report\n\nCreate comprehensive final report:\n\n```markdown\n## Unlinked\
  \ Concepts Processing Complete\n\n**Execution Summary**:\n- Command: /knowledge/identify-unlinked-concepts\
  \ [scope] [action] [min_priority] [min_occurrences]\n- Scan Scope: [scope description]\n\
  - Action: [action]\n- Execution Time: [timestamp]\n\n---\n\n### Discovery Phase\n\
  \n**Files Scanned**: [count]\n**Candidates Detected**: [count]\n**After Filtering**:\
  \ [count] (min_occurrences: [N], min_priority: [level])\n\n**Priority Breakdown**:\n\
  - High priority: [count] concepts\n- Medium priority: [count] concepts\n- Low priority:\
  \ [count] concepts\n\n---\n\n### Processing Phase\n\n**Concepts Processed**: [count]\n\
  \n**Successful**:\n1. [[Kubernetes]] (Technology/Product)\n   - Action: Created\
  \ zettel + added links\n   - Zettel: Kubernetes.md (1,623 words, 4 sources)\n  \
  \ - Links added: 5 across 2 files\n   - Files modified: 2025_12_14.md, 2025_12_13.md\n\
  \n2. [[Network Policies]] (Concept/Theory)\n   - Action: Created zettel + added\
  \ links\n   - Zettel: Network Policies.md (892 words, 3 sources)\n   - Links added:\
  \ 3 in 2025_12_14.md\n   - Files modified: 2025_12_14.md\n\n**Partial Success**:\
  \ [count]\n(None) OR\n- [[Topic X]] - Links added but zettel creation failed\n\n\
  **Failed**: [count]\n(None) OR\n- [[Topic Y]] - Reason: [error message]\n\n---\n\
  \n### Verification Phase\n\n**Link Additions**:\n- ✅ Expected links: [count]\n-\
  \ ✅ Verified links: [count]\n- ✅ Success rate: [percentage]%\n\n**Zettel Creation**:\n\
  - ✅ Expected zettels: [count]\n- ✅ Created and verified: [count]\n- ⚠️  Quality\
  \ warnings: [count]\n\n**Quality Issues** (if any):\n- [[Term]] - Only [X] words\
  \ (minimum 500 recommended)\n- [[Term]] - Missing Sources section\n\n---\n\n###\
  \ Impact Summary\n\n**Before**:\n- Unlinked concept mentions: [count] across [file_count]\
  \ files\n- Knowledge graph gaps: [count] missing pages\n- Manual linking required:\
  \ Yes\n\n**After**:\n- Wiki links added: [count]\n- New zettels created: [count]\n\
  - Files modified: [count]\n- Knowledge graph gaps resolved: [count]\n\n**Knowledge\
  \ Base Growth**:\n- New content: [total_words] words\n- New sources: [total_sources]\
  \ references\n- New connections: [total_links] wiki links\n\n---\n\n### Files Modified\n\
  \n**Journal Entries**: [count]\n- /storage/emulated/0/personal-wiki/logseq/journals/2025_12_14.md\
  \ (+8 links)\n- /storage/emulated/0/personal-wiki/logseq/journals/2025_12_13.md\
  \ (+2 links)\n\n**Pages Created**: [count]\n- /storage/emulated/0/personal-wiki/logseq/pages/Kubernetes.md\
  \ (new)\n- /storage/emulated/0/personal-wiki/logseq/pages/Network Policies.md (new)\n\
  \n**Daily Synthesis Updated**:\n- /storage/emulated/0/personal-wiki/logseq/pages/Knowledge\
  \ Synthesis - 2025-12-14.md\n\n---\n\n### Next Steps\n\n**Recommended Actions**:\n\
  1. Review newly created zettels for accuracy and completeness\n2. Add more sources\
  \ to zettels with < 3 references\n3. Expand related concepts mentioned in new zettels\n\
  \n**Remaining Unlinked Concepts** (not processed this run):\n\n**Medium Priority**\
  \ ([count]):\n- [[AWS Security Groups]] - 2 occurrences in 2025_12_14.md\n  - Action:\
  \ /knowledge/identify-unlinked-concepts today create-all medium\n\n**Low Priority**\
  \ ([count]):\n- [[token bucket algorithm]] - 1 occurrence\n  - Consider: Add to\
  \ \"Needs Synthesis\" for manual research\n\n**Suggestions**:\n- Run `/knowledge/validate-links`\
  \ to verify all links resolve correctly\n- Run `/knowledge/expand-missing-topics`\
  \ to discover more missing concepts\n- Continue daily practice of identifying and\
  \ linking concepts\n```\n\n### Success Criteria - Phase 5\n\n- ✅ All link additions\
  \ verified by re-reading files\n- ✅ All created zettels checked for existence and\
  \ quality\n- ✅ Quality issues identified and reported\n- ✅ Comprehensive report\
  \ generated with metrics\n- ✅ Before/after comparison shows clear impact\n- ✅ File\
  \ paths documented for all changes\n- ✅ Next steps provided for remaining work\n\
  - ✅ Success rate > 90% for link additions\n- ✅ All created zettels meet minimum\
  \ standards (or flagged)\n\n---\n\n## Edge Cases and Error Handling\n\n### Edge\
  \ Case 1: Ambiguous Terms\n\n**Scenario**: \"Lambda\" could be AWS Lambda or lambda\
  \ calculus.\n\n**Detection**:\n```python\nambiguous_terms = {\n    \"Lambda\": [\"\
  AWS Lambda\", \"lambda calculus\", \"Lambda function\"],\n    \"Delta\": [\"Delta\
  \ encoding\", \"Delta Lake\", \"River delta\"],\n    \"Stream\": [\"Java Stream\"\
  , \"Kafka Stream\", \"data stream\"],\n}\n\nif normalized_term in ambiguous_terms:\n\
  \    # Mark as ambiguous\n    candidate[\"ambiguous\"] = True\n    candidate[\"\
  possible_meanings\"] = ambiguous_terms[normalized_term]\n```\n\n**Handling**:\n\
  ```\n⚠️  Ambiguous Term: \"Lambda\"\n\n**Possible Meanings**:\n1. AWS Lambda (serverless\
  \ compute)\n2. Lambda calculus (formal system)\n3. Lambda function (programming)\n\
  \n**Contexts**:\n- \"deploying with Lambda functions\" → likely AWS Lambda\n- \"\
  functional programming with lambda\" → likely lambda calculus\n\n**Action Required**:\n\
  - Review contexts and specify which meaning to create\n- Manual invocation: /knowledge/synthesize-knowledge\
  \ \"AWS Lambda\"\n```\n\n**Resolution**:\n- Flag in report with possible meanings\n\
  - Show contexts to help user decide\n- Require manual clarification (don't auto-create)\n\
  \n---\n\n### Edge Case 2: Acronym Expansions\n\n**Scenario**: \"K8s\" is short for\
  \ \"Kubernetes\".\n\n**Detection**:\n```python\nacronym_expansions = {\n    \"K8s\"\
  : \"Kubernetes\",\n    \"i18n\": \"internationalization\",\n    \"a11y\": \"accessibility\"\
  ,\n    \"l10n\": \"localization\",\n}\n\nif term in acronym_expansions:\n    expanded\
  \ = acronym_expansions[term]\n    # Check if expanded form exists\n```\n\n**Handling**:\n\
  ```\nℹ️  Acronym Detected: \"K8s\"\n\n**Expanded Form**: Kubernetes\n**Status**:\
  \ Page exists (Kubernetes.md)\n\n**Action**: Adding wiki links using expanded form\
  \ [[Kubernetes]]\n- Replacing \"K8s\" → \"[[Kubernetes]]\" (or \"[[Kubernetes|K8s]]\"\
  \ to preserve display)\n```\n\n**Resolution**:\n- Maintain mapping of common acronyms\n\
  - Link to expanded form page\n- Consider using link aliases: `[[Kubernetes|K8s]]`\n\
  \n---\n\n### Edge Case 3: Already Partially Linked\n\n**Scenario**: \"Kubernetes\"\
  \ mentioned 5 times, 2 already as `[[Kubernetes]]`.\n\n**Detection**:\n```python\n\
  total_mentions = 5\nlinked_mentions = 2  # Already as [[Kubernetes]]\nunlinked_mentions\
  \ = total_mentions - linked_mentions  # = 3\n\nif unlinked_mentions > 0 and linked_mentions\
  \ > 0:\n    # Partially linked\n    candidate[\"partially_linked\"] = True\n```\n\
  \n**Handling**:\n```\nℹ️  Partially Linked: \"Kubernetes\"\n\n**Status**:\n- Total\
  \ mentions: 5\n- Already linked: 2\n- Unlinked: 3\n\n**Action**: Adding wiki links\
  \ to 3 unlinked instances only\n```\n\n**Resolution**:\n- Only add links to unlinked\
  \ instances\n- Report both counts clearly\n- Verify final state has all instances\
  \ linked\n\n---\n\n### Edge Case 4: Case Variations\n\n**Scenario**: \"kubernetes\"\
  \ (lowercase) and \"Kubernetes\" (capitalized).\n\n**Detection**:\n```python\n#\
  \ Group by normalized (lowercase) form\nnormalized_groups = {}\nfor candidate in\
  \ candidates:\n    norm = candidate[\"normalized\"]\n    if norm not in normalized_groups:\n\
  \        normalized_groups[norm] = []\n    normalized_groups[norm].append(candidate)\n\
  \n# Find groups with multiple case variations\nfor norm, group in normalized_groups.items():\n\
  \    if len(group) > 1:\n        # Case variations detected\n```\n\n**Handling**:\n\
  ```\n⚠️  Case Variations Detected: \"Kubernetes\"\n\n**Variations Found**:\n- \"\
  Kubernetes\" (capitalized) - 3 occurrences\n- \"kubernetes\" (lowercase) - 2 occurrences\n\
  \n**Action**: Using most common capitalization: \"Kubernetes\"\n**Page**: Kubernetes.md\n\
  \n**Note**: All variations will link to [[Kubernetes]] page.\nLogseq wiki links\
  \ are case-sensitive - recommend standardizing capitalization.\n```\n\n**Resolution**:\n\
  - Use most common capitalization for page name\n- Link all variations to same page\n\
  - Warn user about case sensitivity\n- Suggest manual standardization\n\n---\n\n\
  ### Edge Case 5: Compound Concepts\n\n**Scenario**: \"AWS Lambda functions\" - is\
  \ it \"AWS Lambda\" or \"Lambda Functions\"?\n\n**Detection**:\n```python\n# Detect\
  \ overlapping/nested concepts\nif \"AWS Lambda\" in candidates and \"Lambda Functions\"\
  \ in candidates:\n    # Check if they overlap in text\n    if overlaps_in_context(candidates[\"\
  AWS Lambda\"], candidates[\"Lambda Functions\"]):\n        # Compound concept\n\
  ```\n\n**Handling**:\n```\n⚠️  Overlapping Concepts Detected\n\n**Compound Phrase**:\
  \ \"AWS Lambda functions\"\n\n**Possible Interpretations**:\n1. [[AWS Lambda]] (the\
  \ service) + \"functions\" (generic term)\n   - Link: \"[[AWS Lambda]] functions\"\
  \n\n2. [[Lambda Functions]] (specific programming concept)\n   - Link: \"[[Lambda\
  \ Functions]]\"\n\n**Context**: \"deploying with AWS Lambda functions\"\n\n**Recommendation**:\
  \ Create [[AWS Lambda]] page (service)\nUsing \"[[AWS Lambda]] functions\" (service\
  \ + generic term)\n```\n\n**Resolution**:\n- Detect overlapping terms\n- Choose\
  \ longer, more specific term when appropriate\n- Or split into multiple links: `[[AWS\
  \ Lambda]] functions`\n- Prioritize based on context\n\n---\n\n### Edge Case 6:\
  \ Page Name Variations\n\n**Scenario**: Should it be \"Network Policy\" (singular)\
  \ or \"Network Policies\" (plural)?\n\n**Detection**:\n```python\ndef find_name_variations(term):\n\
  \    variations = []\n\n    # Check singular/plural\n    singular = singularize(term)\n\
  \    plural = pluralize(term)\n\n    for variant in [singular, plural]:\n      \
  \  page_path = f\"logseq/pages/{variant}.md\"\n        if os.path.exists(page_path):\n\
  \            variations.append((variant, page_path))\n\n    return variations\n\
  ```\n\n**Handling**:\n```\nℹ️  Name Variation Found\n\n**Detected Term**: \"Network\
  \ Policies\" (plural)\n**Existing Page**: Network Policy.md (singular)\n\n**Action**:\
  \ Linking to existing page [[Network Policy]]\nAll instances of \"network policies\"\
  \ → [[Network Policy]]\n\n**Note**: Logseq will display as \"Network Policy\" in\
  \ links.\nTo preserve plural display, use alias: [[Network Policy|network policies]]\n\
  ```\n\n**Resolution**:\n- Check both singular and plural forms\n- Link to whichever\
  \ exists\n- Use link aliases if display text matters: `[[Network Policy|network\
  \ policies]]`\n\n---\n\n### Edge Case 7: Term Inside Code Block\n\n**Scenario**:\
  \ \"Kubernetes\" mentioned in code block `kubectl get pods`.\n\n**Detection**:\n\
  ```python\ndef is_in_code_block(line, position):\n    # Check if position is inside\
  \ backticks\n    before = line[:position]\n    backtick_count = before.count('`')\n\
  \n    # If odd number of backticks before, we're inside code\n    return backtick_count\
  \ % 2 == 1\n\ndef is_in_fenced_code_block(lines, line_number):\n    # Check if line\
  \ is inside ``` ``` block\n    fence_count = 0\n    for i in range(line_number):\n\
  \        if lines[i].strip().startswith('```'):\n            fence_count += 1\n\n\
  \    # If odd number of fences before, we're inside code block\n    return fence_count\
  \ % 2 == 1\n```\n\n**Handling**:\n```\nℹ️  Skipping Code Block\n\n**Line**: `kubectl\
  \ get pods -n kubernetes-system`\n**Reason**: \"kubernetes\" appears inside inline\
  \ code backticks\n\n**Action**: Skipping (not creating wiki link inside code)\n\
  ```\n\n**Resolution**:\n- Detect inline code: `...`\n- Detect fenced code blocks:\
  \ ``` ... ```\n- Skip any matches inside code\n- Only link in prose text\n\n---\n\
  \n### Edge Case 8: Term in URL\n\n**Scenario**: \"kubernetes\" in URL `https://kubernetes.io/docs`.\n\
  \n**Detection**:\n```python\ndef is_in_url(line, term_position):\n    # Find all\
  \ URLs in line\n    url_pattern = r'https?://[^\\s)]+'\n\n    for match in re.finditer(url_pattern,\
  \ line):\n        url_start, url_end = match.span()\n        if url_start <= term_position\
  \ < url_end:\n            return True\n\n    return False\n```\n\n**Handling**:\n\
  ```\nℹ️  Skipping URL\n\n**Line**: \"See https://kubernetes.io/docs for details\"\
  \n**Reason**: \"kubernetes\" appears inside URL\n\n**Action**: Skipping (not creating\
  \ wiki link inside URL)\n```\n\n**Resolution**:\n- Detect URLs in line\n- Skip any\
  \ matches inside URL text\n- Maintain URL integrity\n\n---\n\n### Edge Case 9: Synthesis\
  \ Fails\n\n**Scenario**: `/knowledge/synthesize-knowledge` times out or fails.\n\
  \n**Detection**:\n```python\ntry:\n    result = invoke_command(\"/knowledge/synthesize-knowledge\"\
  , topic=term)\n    if result.status != \"SUCCESS\":\n        raise Exception(f\"\
  Synthesis failed: {result.error}\")\nexcept Exception as e:\n    # Synthesis failed\n\
  ```\n\n**Handling**:\n```\n❌ Zettel Creation Failed: [[Kubernetes]]\n\n**Error**:\
  \ Research timeout after 180 seconds\n\n**Action**:\n- Marked as FAILED\n- Wiki\
  \ links NOT added (page doesn't exist)\n- Continue with remaining concepts\n\n**Retry**:\n\
  Manual invocation: /knowledge/synthesize-knowledge \"Kubernetes\"\n```\n\n**Resolution**:\n\
  - Log error details\n- Mark concept as FAILED\n- Don't add wiki links (no page to\
  \ link to)\n- Continue with remaining concepts\n- Provide retry instructions in\
  \ final report\n\n---\n\n### Edge Case 10: No Concepts Found\n\n**Scenario**: Scan\
  \ completes but no concepts detected.\n\n**Detection**:\n```python\nif len(candidates)\
  \ == 0:\n    # No concepts found\n```\n\n**Handling**:\n```\n✅ No Unlinked Concepts\
  \ Found\n\n**Scan Results**:\n- Files scanned: 3\n- Lines processed: 847\n- Already\
  \ linked terms: 42\n- New concepts detected: 0\n\n**Status**: Your knowledge graph\
  \ is well-connected! ✓\n\nAll technical terms in the scanned content are already\
  \ wiki-linked.\n\n**Suggestions**:\n- Continue daily practice of linking concepts\
  \ as you write\n- Run `/knowledge/validate-links` for comprehensive link health\
  \ check\n- Run `/knowledge/expand-missing-topics` to find missing topic pages\n\
  ```\n\n**Resolution**:\n- Report success (well-connected knowledge graph)\n- Provide\
  \ positive feedback\n- Suggest related commands\n\n---\n\n## Usage Examples\n\n\
  ### Example 1: Daily Journal Review (Default)\n\n**Scenario**: Review today's journal\
  \ for unlinked concepts.\n\n**Command**:\n```\n/knowledge/identify-unlinked-concepts\n\
  ```\n\n**Equivalent to**:\n```\n/knowledge/identify-unlinked-concepts today report\
  \ medium 2\n```\n\n**Execution**:\n\n1. **Discovery**:\n   - Scanned: 2025_12_14.md\
  \ (247 lines)\n   - Detected: 12 potential concepts\n   - After filtering (2+ occurrences,\
  \ medium+ priority): 6 concepts\n\n2. **Report Generated**:\n   ```\n   ## Unlinked\
  \ Concepts Found\n\n   **High Priority** (2):\n   1. Kubernetes (Technology) - 5\
  \ occurrences\n   2. network policies (Concept) - 3 occurrences\n\n   **Medium Priority**\
  \ (4):\n   3. AWS Security Groups - 2 occurrences\n   4. CRDT - 2 occurrences (page\
  \ exists)\n   5. Calico - 2 occurrences\n   6. Cilium - 2 occurrences\n   ```\n\n\
  3. **User Action**: Reviews report, decides to process high-priority items.\n\n\
  4. **Next Command**:\n   ```\n   /knowledge/identify-unlinked-concepts today create-high\n\
  \   ```\n\n---\n\n### Example 2: Add Wiki Links Only\n\n**Scenario**: Add wiki links\
  \ for concepts where pages already exist.\n\n**Command**:\n```\n/knowledge/identify-unlinked-concepts\
  \ today link\n```\n\n**Execution**:\n\n1. **Discovery**: Found 6 concepts\n\n2.\
  \ **Filtering**: Only process concepts where page exists\n   - \"CRDT\" → found\
  \ Conflict-Free Replicated Data Types.md\n   - Others: MISSING (skip)\n\n3. **Processing**:\n\
  \   ```\n   \U0001F517 Adding Wiki Links\n\n   **Concept: CRDT**\n   - Page exists:\
  \ Conflict-Free Replicated Data Types.md\n   - Adding links to 2 occurrences\n\n\
  \   ✓ 2025_12_14.md line 45: Added [[Conflict-Free Replicated Data Types]]\n   ✓\
  \ 2025_12_13.md line 89: Added [[Conflict-Free Replicated Data Types]]\n\n   Status:\
  \ SUCCESS\n   ```\n\n4. **Report**:\n   ```\n   ## Wiki Links Added\n\n   **Modified\
  \ Files**: 2\n   - 2025_12_14.md: +1 link\n   - 2025_12_13.md: +1 link\n\n   **Links\
  \ to Existing Pages**: 2\n   - [[Conflict-Free Replicated Data Types]] (2 instances)\n\
  \n   **Concepts Skipped** (no existing page): 5\n   - Kubernetes, network policies,\
  \ AWS Security Groups, Calico, Cilium\n\n   **Next Steps**:\n   Run `/knowledge/identify-unlinked-concepts\
  \ today create-high` to create missing pages\n   ```\n\n---\n\n### Example 3: Create\
  \ Zettels for High-Priority\n\n**Scenario**: Research and create zettels for most\
  \ important unlinked concepts.\n\n**Command**:\n```\n/knowledge/identify-unlinked-concepts\
  \ today create-high high\n```\n\n**Execution**:\n\n1. **Discovery**: Found 2 high-priority\
  \ concepts\n\n2. **Processing**:\n   ```\n   \U0001F680 Creating Zettels (High Priority)\n\
  \n   **Concept 1/2: Kubernetes**\n\n   ✓ Delegating to /knowledge/synthesize-knowledge...\n\
  \   ✓ Research completed (4 sources)\n   ✓ Zettel created: Kubernetes.md (1,623\
  \ words)\n   ✓ Daily hub updated (65 words with links)\n   ✓ Adding wiki links:\
  \ 5 instances across 2 files\n\n   **Concept 2/2: network policies**\n\n   ✓ Delegating\
  \ to /knowledge/synthesize-knowledge...\n   ✓ Research completed (3 sources)\n \
  \  ✓ Zettel created: Network Policies.md (892 words)\n   ✓ Daily hub updated (58\
  \ words with links)\n   ✓ Adding wiki links: 3 instances in 1 file\n   ```\n\n3.\
  \ **Verification**:\n   ```\n   ✅ All Zettels Created Successfully\n\n   **Created**:\
  \ 2 zettels\n   - Kubernetes.md (1,623 words, 4 sources) ✓\n   - Network Policies.md\
  \ (892 words, 3 sources) ✓\n\n   **Wiki Links Added**: 8 total\n   - 2025_12_14.md:\
  \ +6 links\n   - 2025_12_13.md: +2 links\n\n   **Daily Synthesis Updated**:\n  \
  \ - Knowledge Synthesis - 2025-12-14.md (+2 sections)\n   ```\n\n---\n\n### Example\
  \ 4: Interactive Mode\n\n**Scenario**: Review each concept and choose action manually.\n\
  \n**Command**:\n```\n/knowledge/identify-unlinked-concepts week interactive medium\
  \ 1\n```\n\n**Execution**:\n\n1. **Discovery**: Found 18 concepts from past week\n\
  \n2. **Interactive Prompt**:\n   ```\n   \U0001F4CB Interactive Concept Selection\n\
  \n   Found 18 concepts. For each, choose action:\n   [L] Add wiki links only\n \
  \  [C] Create zettel + add links\n   [S] Skip\n   [A] Accept all remaining with\
  \ default action\n   [Q] Quit\n\n   ---\n\n   1/18: **Kubernetes** (Technology)\
  \ - 8 occurrences across 4 files\n         Page: MISSING | Links: NEVER_LINKED\n\
  \         Context: \"setting up Kubernetes cluster\"\n         Suggested: Create\
  \ zettel + add links\n\n         Action [L/C/S/A/Q]: C\n\n   ✓ Marked for zettel\
  \ creation\n\n   ---\n\n   2/18: **Docker** (Technology) - 6 occurrences across\
  \ 3 files\n         Page: EXISTS (Docker.md, 1,234 words)\n         Links: NEVER_LINKED\n\
  \         Suggested: Add wiki links only\n\n         Action [L/C/S/A/Q]: L\n\n \
  \  ✓ Marked for wiki linking\n\n   ---\n\n   3/18: **token bucket algorithm** (Algorithm)\
  \ - 1 occurrence\n         Page: MISSING | Links: NEVER_LINKED\n         Suggested:\
  \ Skip (low occurrence)\n\n         Action [L/C/S/A/Q]: S\n\n   ✓ Skipped\n\n  \
  \ ---\n\n   [... continues for all 18 concepts ...]\n\n   Summary:\n   - Create\
  \ zettel: 5 concepts\n   - Add links only: 8 concepts\n   - Skip: 5 concepts\n\n\
  \   Proceed with selected actions? [Y/n]: Y\n   ```\n\n3. **Processing**: Executes\
  \ selected actions\n\n4. **Report**: Shows results for each concept\n\n---\n\n###\
  \ Example 5: Weekly Comprehensive Scan\n\n**Scenario**: Find all unlinked concepts\
  \ from this week's journals.\n\n**Command**:\n```\n/knowledge/identify-unlinked-concepts\
  \ week create-all low 1\n```\n\n**Parameters**:\n- Scope: Past 7 days\n- Action:\
  \ Create zettels for all missing concepts\n- Min priority: low (include everything)\n\
  - Min occurrences: 1 (even single mentions)\n\n**Execution**:\n\n1. **Discovery**:\n\
  \   - Scanned: 7 journal files\n   - Detected: 45 potential concepts\n   - After\
  \ filtering (1+ occurrences, low+ priority): 45 concepts\n\n2. **Categorization**:\n\
  \   - High priority: 8 concepts\n   - Medium priority: 15 concepts\n   - Low priority:\
  \ 22 concepts\n\n3. **Processing**:\n   - Create zettels: 27 (18 missing, 9 failed)\n\
  \   - Add links only: 18 (existing pages)\n\n4. **Results**:\n   ```\n   ## Weekly\
  \ Comprehensive Scan Complete\n\n   **Concepts Processed**: 45/45\n\n   **Zettels\
  \ Created**: 18\n   **Zettels Failed**: 9 (research timeouts, low-quality sources)\n\
  \   **Wiki Links Added**: 67 across 7 files\n\n   **Impact**:\n   - New content:\
  \ 16,483 words\n   - New sources: 72 references\n   - Knowledge graph growth: 18\
  \ new nodes, 67 new connections\n\n   **Failed Concepts** (review and retry):\n\
  \   - [[Obscure Framework]] - No high-quality sources found\n   - [[Niche Technology]]\
  \ - Research timeout\n   ... (7 more)\n   ```\n\n---\n\n### Example 6: Specific\
  \ File Scan\n\n**Scenario**: Process concepts from specific synthesis page.\n\n\
  **Command**:\n```\n/knowledge/identify-unlinked-concepts file:/storage/emulated/0/personal-wiki/logseq/pages/Knowledge\
  \ Synthesis - 2025-12-10.md report\n```\n\n**Execution**:\n\n1. **Discovery**: Scanned\
  \ single file\n\n2. **Report**:\n   ```\n   ## Unlinked Concepts in Specific File\n\
  \n   **File**: Knowledge Synthesis - 2025-12-10.md\n\n   **Found**: 8 concepts\n\
  \n   **High Priority** (0): None\n\n   **Medium Priority** (2):\n   - Docker Compose\
  \ - 2 occurrences\n   - Container Networking - 2 occurrences\n\n   **Low Priority**\
  \ (6):\n   - Volume Mounts - 1 occurrence\n   - Port Binding - 1 occurrence\n  \
  \ ... (4 more)\n\n   **Recommendation**:\n   Run `/knowledge/identify-unlinked-concepts\
  \ file:/storage/emulated/0/personal-wiki/logseq/pages/Knowledge Synthesis - 2025-12-10.md\
  \ create-all medium` to create medium+ priority zettels\n   ```\n\n---\n\n## Integration\
  \ Patterns\n\n### Workflow 1: Daily Journal Writing + Linking\n\n**Daily Practice**:\n\
  ```bash\n# 1. Write journal entry naturally (don't worry about links)\n# Just write\
  \ in plain text\n\n# 2. After writing, identify unlinked concepts\n/knowledge/identify-unlinked-concepts\
  \ today report\n\n# 3. Review findings, then add links to existing pages\n/knowledge/identify-unlinked-concepts\
  \ today link\n\n# 4. Create zettels for important new concepts\n/knowledge/identify-unlinked-concepts\
  \ today create-high\n\n# 5. Validate all links\n/knowledge/validate-links\n```\n\
  \n**Benefits**:\n- Write naturally without interrupting flow\n- Systematically link\
  \ concepts after writing\n- Build knowledge graph incrementally\n\n---\n\n### Workflow\
  \ 2: Pre-Synthesis Discovery\n\n**Before running synthesis**:\n```bash\n# 1. Identify\
  \ concepts that need research\n/knowledge/identify-unlinked-concepts week report\
  \ high\n\n# 2. Review high-priority concepts - these are important topics mentioned\
  \ multiple times\n\n# 3. Manually research and synthesize the most important ones\n\
  /knowledge/synthesize-knowledge \"Important Concept from List\"\n\n# 4. After synthesis,\
  \ link remaining mentions\n/knowledge/identify-unlinked-concepts week link\n```\n\
  \n**Benefits**:\n- Discover what topics deserve deep research\n- Prioritize synthesis\
  \ efforts\n- Ensure comprehensive coverage of important concepts\n\n---\n\n### Workflow\
  \ 3: Weekly Knowledge Graph Maintenance\n\n**Weekly Cleanup**:\n```bash\n# 1. Find\
  \ all unlinked concepts from this week\n/knowledge/identify-unlinked-concepts week\
  \ report medium 2\n\n# 2. Create zettels for high-priority items\n/knowledge/identify-unlinked-concepts\
  \ week create-high high\n\n# 3. Add links for existing pages\n/knowledge/identify-unlinked-concepts\
  \ week link\n\n# 4. Validate entire wiki\n/knowledge/validate-links stats\n\n# 5.\
  \ Commit changes\ngit add .\ngit commit -m \"Weekly knowledge graph linking - [date]\"\
  \n```\n\n**Benefits**:\n- Regular maintenance keeps graph connected\n- Prevents\
  \ accumulation of unlinked mentions\n- Systematic knowledge base growth\n\n---\n\
  \n### Workflow 4: Post-Import Processing\n\n**After importing notes from external\
  \ sources**:\n```bash\n# 1. Import markdown files to journals/pages\n\n# 2. Identify\
  \ all unlinked concepts in imported content\n/knowledge/identify-unlinked-concepts\
  \ all report low 1\n\n# 3. Link to existing pages first\n/knowledge/identify-unlinked-concepts\
  \ all link\n\n# 4. Create zettels for frequently mentioned concepts\n/knowledge/identify-unlinked-concepts\
  \ all create-high medium\n\n# 5. Review remaining low-priority concepts\n# Manually\
  \ decide which to research further\n```\n\n**Benefits**:\n- Quickly integrate external\
  \ content\n- Discover important concepts in imported notes\n- Connect imported content\
  \ to existing knowledge\n\n---\n\n### Workflow 5: Automated Pre-Commit Hook\n\n\
  **Git Hook**: Check for unlinked high-priority concepts before commit.\n\n```bash\n\
  #!/bin/bash\n# .git/hooks/pre-commit\n\n# Run identification in report mode\nresult=$(/knowledge/identify-unlinked-concepts\
  \ today report high 3)\n\n# Parse result for high-priority count\nhigh_priority_count=$(echo\
  \ \"$result\" | grep -c \"High Priority\")\n\nif [ $high_priority_count -gt 0 ];\
  \ then\n    echo \"⚠️  Warning: High-priority unlinked concepts detected\"\n   \
  \ echo \"\"\n    echo \"$result\"\n    echo \"\"\n    echo \"Recommendation: Run\
  \ '/knowledge/identify-unlinked-concepts today create-high' before commit\"\n  \
  \  echo \"\"\n    echo \"Continue anyway? [y/N]\"\n    read -r response\n\n    if\
  \ [[ ! \"$response\" =~ ^[Yy]$ ]]; then\n        exit 1\n    fi\nfi\n\nexit 0\n\
  ```\n\n**Benefits**:\n- Gentle reminder to link concepts\n- Ensures consistent knowledge\
  \ graph quality\n- Can be bypassed when needed\n\n---\n\n## Quality Standards\n\n\
  ### Detection Accuracy Standards\n\n**MUST ACHIEVE**:\n- ✅ Precision > 80% (80%+\
  \ of detected concepts are legitimate)\n- ✅ Recall > 70% (70%+ of technical terms\
  \ detected)\n- ✅ False positive rate < 20%\n- ✅ No common words misidentified as\
  \ concepts\n- ✅ No proper names misidentified as concepts\n- ✅ Already-linked text\
  \ properly excluded\n\n**Detection Strategy Effectiveness**:\n- Capitalized terms:\
  \ 85%+ precision\n- Technical suffixes: 80%+ precision\n- Acronyms: 75%+ precision\
  \ (some ambiguity expected)\n- Cloud services: 90%+ precision\n- Quoted concepts:\
  \ 70%+ precision (more ambiguity)\n\n---\n\n### Categorization Accuracy Standards\n\
  \n**MUST ACHIEVE**:\n- ✅ Category assignment > 85% accurate\n- ✅ Priority scores\
  \ correlate with actual importance\n- ✅ High-priority concepts genuinely more important\
  \ than low-priority\n- ✅ Context signals properly weighted\n\n**Category Distribution**\
  \ (typical):\n- Technology/Product: 30-40% of concepts\n- Concept/Theory: 20-30%\n\
  - Algorithm/Pattern: 15-25%\n- Tool/Framework: 15-20%\n- Protocol/Standard: 5-10%\n\
  - General Concept: 5-10%\n\n---\n\n### Link Addition Safety Standards\n\n**MUST\
  \ ENSURE**:\n- ✅ No broken markdown after link addition\n- ✅ Original text meaning\
  \ preserved\n- ✅ No links created inside code blocks\n- ✅ No links created inside\
  \ URLs\n- ✅ Proper wiki link syntax: `[[Page Name]]`\n- ✅ All occurrences linked\
  \ consistently\n- ✅ File integrity maintained\n\n**Validation**:\n- Re-read all\
  \ modified files\n- Verify link count matches expected\n- Check markdown renders\
  \ correctly\n- Ensure no formatting corruption\n\n---\n\n### Zettel Creation Delegation\
  \ Standards\n\n**MUST DELEGATE WITH**:\n- ✅ Clear topic name\n- ✅ Relevant context\
  \ from occurrences\n- ✅ Related concepts identified\n- ✅ Category information\n\
  - ✅ Hub/spoke architecture instructions\n- ✅ Minimum quality requirements (500+\
  \ words, 3+ sources)\n\n**MUST VERIFY AFTER**:\n- ✅ Zettel created and exists\n\
  - ✅ Meets minimum word count (500+)\n- ✅ Has required sections\n- ✅ Sources cited\
  \ (3+)\n- ✅ Daily hub updated appropriately (30-80 words)\n- ✅ No comprehensive\
  \ content in hub\n\n---\n\n### Reporting Transparency Standards\n\n**MUST INCLUDE**:\n\
  - ✅ Scan scope and file counts\n- ✅ Detection method breakdown\n- ✅ Priority distribution\n\
  - ✅ Suggested actions for each concept\n- ✅ Context excerpts for user review\n-\
  \ ✅ Before/after comparison\n- ✅ Success and failure counts\n- ✅ File paths for\
  \ all changes\n- ✅ Next steps and recommendations\n\n---\n\n## Command Invocation\n\
  \n**Format**: `/knowledge/identify-unlinked-concepts [scope] [action] [min_priority]\
  \ [min_occurrences]`\n\n**Arguments**:\n\n1. **scope** (optional, default: `today`):\n\
  \   - `today`: Today's journal entry\n   - `week`: Last 7 days of journals\n   -\
  \ `month`: Last 30 days of journals\n   - `journals`: All journal entries\n   -\
  \ `pages`: All pages\n   - `file:<absolute_path>`: Specific file\n   - `all`: Everything\
  \ (journals + pages)\n\n2. **action** (optional, default: `report`):\n   - `report`:\
  \ Show findings, make no changes\n   - `link`: Add wiki links to existing pages\
  \ only\n   - `create-high`: Create zettels for high-priority concepts\n   - `create-all`:\
  \ Create zettels for all concepts\n   - `interactive`: Ask user for each concept\n\
  \n3. **min_priority** (optional, default: `medium`):\n   - `high`: Only concepts\
  \ with score ≥ 100\n   - `medium`: Concepts with score ≥ 50\n   - `low`: All concepts\
  \ (score ≥ 0)\n\n4. **min_occurrences** (optional, default: `2`):\n   - Integer\
  \ 1-10\n   - Minimum times term must appear to be considered\n   - Lower = more\
  \ sensitive, higher = more conservative\n\n**Examples**:\n\n```bash\n# Default:\
  \ Today's journal, report only, medium+ priority, 2+ occurrences\n/knowledge/identify-unlinked-concepts\n\
  \n# Add links for existing pages in this week's journals\n/knowledge/identify-unlinked-concepts\
  \ week link\n\n# Create zettels for high-priority concepts from today\n/knowledge/identify-unlinked-concepts\
  \ today create-high high\n\n# Interactive mode for all journals, low priority, single\
  \ occurrences\n/knowledge/identify-unlinked-concepts journals interactive low 1\n\
  \n# Create all missing zettels from specific file\n/knowledge/identify-unlinked-concepts\
  \ file:/storage/emulated/0/personal-wiki/logseq/journals/2025_12_14.md create-all\
  \ medium 2\n\n# Report on pages directory, high priority only\n/knowledge/identify-unlinked-concepts\
  \ pages report high 3\n\n# Everything, create all, including single mentions\n/knowledge/identify-unlinked-concepts\
  \ all create-all low 1\n```\n\n**Execution Mode**: Orchestration with delegation\
  \ to `/knowledge/synthesize-knowledge`\n\n**Expected Duration**:\n- Report only:\
  \ 10-30 seconds (scanning + analysis)\n- Link additions: 1-2 minutes (file modifications)\n\
  - Create 1 zettel: 5-10 minutes (research + synthesis)\n- Create 5 zettels: 25-50\
  \ minutes\n- Create 10 zettels: 50-100 minutes\n\n**Prerequisites**:\n- `/knowledge/synthesize-knowledge`\
  \ command available (for zettel creation)\n- `/knowledge/validate-links` command\
  \ available (for verification)\n- Read access to logseq/journals and logseq/pages\n\
  - Write access to logseq/journals and logseq/pages (for link additions)\n- Internet\
  \ access (for zettel research via Brave Search)\n\n**Success Criteria**:\n- ✅ All\
  \ concepts detected with >80% precision\n- ✅ Priority scores accurately reflect\
  \ importance\n- ✅ Wiki links added safely without breaking markdown\n- ✅ Zettels\
  \ created meet quality standards (500+ words, 3+ sources)\n- ✅ Hub/spoke architecture\
  \ maintained\n- ✅ Comprehensive report generated\n- ✅ Clear next steps provided\n\
  - ✅ All changes tracked and verifiable\n"
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
