---
description: Finds journal entries marked with [[Needs Research]], discovers and incorporates
  child topic pages, conducts research for projects or products, creates comprehensive
  zettels with hierarchical awareness, removes labels after success
prompt: "# Process Needs Research Entries\n\n**Command Purpose**: Systematically process\
  \ all journal entries marked with `[[Needs Research]]` by:\n1. Discovering and cataloging\
  \ all pending research entries\n2. Discovering existing child topic pages for hierarchical\
  \ context\n3. Conducting comprehensive research using web search and analysis\n\
  4. Incorporating child topic insights into research findings\n5. Creating detailed\
  \ zettels with findings, comparisons, and recommendations\n6. Establishing hierarchical\
  \ page structures when appropriate\n7. Removing research labels after successful\
  \ processing\n8. Verifying child topic integration and generating completion report\n\
  \n**When Invoked**: This command performs direct research and synthesis (unlike\
  \ process-needs-synthesis which delegates to an agent).\n\n---\n\n## Core Methodology\n\
  \n### Phase 1: Discovery and Cataloging\n\n**Objective**: Find all entries marked\
  \ for research and extract actionable items.\n\n**Actions**:\n1. **Search for research\
  \ markers**:\n   ```bash\n   grep -rn \"[[Needs Research]]\" ~/Documents/personal-wiki/logseq/journals/\n\
  \   ```\n   - Record file paths, line numbers, and content\n   - Handle case variations:\
  \ `[[needs research]]`, `[[Needs Research]]`\n   - Check both uppercase and lowercase\
  \ patterns\n\n2. **Parse each entry**:\n   - Extract project name or product type\
  \ from the line\n   - Capture surrounding context (3-5 lines before/after for context)\n\
  \   - Identify entry type (see Entry Types below)\n   - Note any specific requirements,\
  \ constraints, or criteria\n\n3. **Categorize and prioritize**:\n   - **High priority**:\
  \ Explicit \"urgent\", \"important\", upcoming deadlines\n   - **Medium priority**:\
  \ Standard projects/products with clear criteria\n   - **Low priority**: Exploratory\
  \ research, long-term planning\n   - **Requires clarification**: Vague requests,\
  \ missing criteria, ambiguous goals\n\n3.5. **Discover child topic pages** (NEW\
  \ - CRITICAL):\n\n   For each topic identified in research entries:\n\n   **Check\
  \ filesystem for child pages**:\n   ```bash\n   # Check if topic has a child pages\
  \ directory\n   ls -la \"/storage/emulated/0/personal-wiki/logseq/pages/[Topic Name]/\"\
  \ 2>/dev/null\n\n   # Example: Check for Kubernetes child pages\n   ls -la \"/storage/emulated/0/personal-wiki/logseq/pages/Kubernetes/\"\
  \ 2>/dev/null\n   ```\n\n   **Search for namespaced wiki link references**:\n  \
  \ ```bash\n   # Find all namespaced references to the topic\n   grep -r \"\\[\\\
  [Topic Name/\" /storage/emulated/0/personal-wiki/logseq/pages/ 2>/dev/null\n\n \
  \  # Example: Find all Kubernetes subtopics\n   grep -r \"\\[\\[Kubernetes/\" /storage/emulated/0/personal-wiki/logseq/pages/\n\
  \   ```\n\n   **Record child topic information**:\n   - List of child page files\
  \ found\n   - Namespaced references discovered\n   - Existing knowledge to incorporate\
  \ into research\n\n4. **Generate discovery report**:\n   ```\n   ## Research Queue\
  \ Discovery\n\n   **Total Entries Found**: [count]\n\n   **High Priority** ([count]):\n\
  \   - [Journal Date] - [Entry Preview] - [Research Topic]\n     - Child topics found:\
  \ [count] (e.g., [[Topic/Subtopic1]], [[Topic/Subtopic2]])\n\n   **Medium Priority**\
  \ ([count]):\n   - [Journal Date] - [Entry Preview] - [Research Topic]\n     - Child\
  \ topics found: [count]\n\n   **Low Priority** ([count]):\n   - [Journal Date] -\
  \ [Entry Preview] - [Research Topic]\n     - Child topics found: [count]\n\n   **Requires\
  \ Clarification** ([count]):\n   - [Journal Date] - [Entry Preview] - [Issue]\n\n\
  \   **Child Topic Summary**:\n   - Topics with existing child pages: [count]\n \
  \  - Total child pages discovered: [count]\n   - Child page content to incorporate:\
  \ [list]\n   ```\n\n**Success Criteria**:\n- All `[[Needs Research]]` markers found\
  \ and recorded\n- Each entry categorized by type and priority\n- Research topics/criteria\
  \ extracted successfully\n- **Child topic pages discovered for each topic** (NEW)\n\
  - Discovery report generated with counts and child topic information\n\n**Entry\
  \ Types to Recognize**:\n\n1. **Project research**:\n   ```markdown\n   - Need to\
  \ research best practices for implementing event sourcing in microservices [[Needs\
  \ Research]]\n   ```\n\n2. **Product comparison**:\n   ```markdown\n   - Looking\
  \ for a good password manager for the team [[Needs Research]]\n   ```\n\n3. **Technology\
  \ evaluation**:\n   ```markdown\n   - Compare Kafka vs Pulsar vs RabbitMQ for our\
  \ use case [[Needs Research]]\n   ```\n\n4. **Tool/service search**:\n   ```markdown\n\
  \   - Find a good CI/CD platform that supports monorepos [[Needs Research]]\n  \
  \ ```\n\n5. **Problem investigation**:\n   ```markdown\n   - Research why our PostgreSQL\
  \ queries are slow [[Needs Research]]\n   ```\n\n6. **Section header** (NOT actionable):\n\
  \   ```markdown\n   ## Research Queue [[Needs Research]]\n   ```\n   → **Skip**:\
  \ Section headers are organizational, not research targets\n\n7. **Nested items**:\n\
  \   ```markdown\n   - Project infrastructure decisions:\n     - Database selection\
  \ [[Needs Research]]\n     - Message broker evaluation [[Needs Research]]\n   ```\n\
  \   → **Process**: Each nested item separately\n\n8. **Topic with known child pages**\
  \ (NEW):\n   ```markdown\n   - Need to research Kubernetes deployment strategies\
  \ [[Needs Research]]\n   ```\n   → **Check for**: `Kubernetes/Pods.md`, `Kubernetes/Services.md`,\
  \ `Kubernetes/Deployments.md`, etc.\n   → **Action**: Read child pages and incorporate\
  \ existing knowledge into research\n\n---\n\n### Phase 2: Research and Analysis\n\
  \n**Objective**: Conduct comprehensive research for each entry using available tools.\n\
  \n**Actions**:\nFor each entry in priority order:\n\n1. **Analyze research requirements**:\n\
  \   - Identify key questions to answer\n   - Determine evaluation criteria (cost,\
  \ features, performance, etc.)\n   - Note any constraints (budget, timeline, technical\
  \ requirements)\n   - Extract specific use case or context\n\n1.5. **Read and incorporate\
  \ child topic pages** (NEW - CRITICAL):\n\n   If child pages were discovered in\
  \ Phase 1:\n\n   **Read child page content**:\n   ```bash\n   # Read each discovered\
  \ child page\n   cat \"/storage/emulated/0/personal-wiki/logseq/pages/[Topic]/[Subtopic].md\"\
  \n   ```\n\n   **Extract existing knowledge**:\n   - Note what's already documented\
  \ about the topic\n   - Identify gaps in existing knowledge\n   - Find connections\
  \ to research questions\n   - Determine what new research adds to existing content\n\
  \n   **Integration strategy**:\n   - Build upon existing knowledge (don't duplicate)\n\
  \   - Address gaps identified in child pages\n   - Create connections between new\
  \ research and existing pages\n   - Consider whether to update existing child pages\
  \ or create new ones\n\n2. **Conduct multi-source research**:\n\n   **For Product/Tool\
  \ Research**:\n   - Use Brave Search to find:\n     - Product comparisons and reviews\n\
  \     - Official documentation and pricing\n     - User experiences and case studies\n\
  \     - Alternative solutions\n   - Search patterns:\n     ```\n     \"[product\
  \ name] vs alternatives\"\n     \"best [tool category] for [use case]\"\n     \"\
  [product] review [year]\"\n     \"[product] pricing comparison\"\n     ```\n\n \
  \  **For Project/Technical Research**:\n   - Use Brave Search to find:\n     - Best\
  \ practices and patterns\n     - Architecture examples\n     - Common pitfalls and\
  \ solutions\n     - Performance considerations\n   - Search patterns:\n     ```\n\
  \     \"[technology] best practices\"\n     \"[pattern] implementation guide\"\n\
  \     \"[problem] solution\"\n     \"how to [accomplish goal]\"\n     ```\n\n  \
  \ **For Technology Comparison**:\n   - Create comparison matrix with:\n     - Core\
  \ features\n     - Performance characteristics\n     - Complexity/learning curve\n\
  \     - Community support\n     - Cost considerations\n     - Use case fit\n\n3.\
  \ **Deep dive with Puppeteer** (when needed):\n   - Navigate to official websites\
  \ for detailed information\n   - Screenshot key feature pages\n   - Extract pricing\
  \ information\n   - Review documentation structure\n   - Capture product demos or\
  \ examples\n\n4. **Synthesize findings**:\n   - Summarize research results\n   -\
  \ Create comparison tables/matrices\n   - Identify top recommendations\n   - Note\
  \ trade-offs and considerations\n   - Provide implementation guidance\n\n**Success\
  \ Criteria (per entry)**:\n- Minimum 3-5 quality sources consulted\n- Key questions\
  \ answered comprehensively\n- Clear recommendations provided\n- Trade-offs and considerations\
  \ documented\n- Sources properly cited with URLs and dates\n- **Child topic pages\
  \ read and incorporated** (NEW)\n- **Existing knowledge gaps identified and addressed**\
  \ (NEW)\n- **Child pages referenced in research zettel** (NEW)\n\n**Research Quality\
  \ Standards**:\n\n1. **Breadth**: Cover multiple perspectives and sources\n2. **Depth**:\
  \ Go beyond surface-level information\n3. **Recency**: Prioritize recent information\
  \ (last 1-2 years)\n4. **Relevance**: Focus on specific use case and requirements\n\
  5. **Actionability**: Provide clear next steps or recommendations\n6. **Context\
  \ awareness**: Build upon existing child page knowledge (NEW)\n7. **Hierarchical\
  \ integration**: Link parent and child topics appropriately (NEW)\n\n---\n\n###\
  \ Phase 3: Zettel Creation\n\n**Objective**: Create comprehensive zettels documenting\
  \ research findings.\n\n**Actions**:\nFor each research entry:\n\n1. **Determine\
  \ zettel structure**:\n\n   **For Product/Tool Research**:\n   ```markdown\n   #\
  \ [Product/Tool Name]\n\n   ## Overview\n   [Brief description, purpose, key value\
  \ proposition]\n\n   ## Key Features\n   - Feature 1: [description]\n   - Feature\
  \ 2: [description]\n\n   ## Pricing\n   [Pricing tiers, costs, free options]\n\n\
  \   ## Alternatives\n   - [[Alternative 1]] - [comparison point]\n   - [[Alternative\
  \ 2]] - [comparison point]\n\n   ## Pros\n   - [advantage]\n\n   ## Cons\n   - [limitation]\n\
  \n   ## Use Cases\n   - Best for: [scenario]\n   - Not ideal for: [scenario]\n\n\
  \   ## Recommendation\n   [Clear recommendation with reasoning]\n\n   ## Sources\n\
  \   - [URL 1] - [description] (accessed YYYY-MM-DD)\n   - [URL 2] - [description]\
  \ (accessed YYYY-MM-DD)\n\n   ## Child Topics\n   - [[Product/Subtopic 1]] - [Brief\
  \ description, if child page exists or was created]\n   - [[Product/Subtopic 2]]\
  \ - [Brief description, if child page exists or was created]\n\n   ## Related\n\
  \   [[Tag 1]] [[Tag 2]] [[Related Concept]]\n   ```\n\n   **For Project/Technical\
  \ Research**:\n   ```markdown\n   # [Topic/Pattern Name]\n\n   ## Overview\n   [What\
  \ it is, why it matters]\n\n   ## Key Concepts\n   - Concept 1: [explanation]\n\
  \   - Concept 2: [explanation]\n\n   ## Best Practices\n   1. [practice]: [reasoning]\n\
  \   2. [practice]: [reasoning]\n\n   ## Common Pitfalls\n   - [pitfall]: [how to\
  \ avoid]\n\n   ## Implementation Approach\n   [Step-by-step guidance or architecture\
  \ overview]\n\n   ## Examples\n   [Code snippets, architecture diagrams, real-world\
  \ examples]\n\n   ## Performance Considerations\n   [Scalability, efficiency, resource\
  \ usage]\n\n   ## When to Use\n   - Good fit: [scenario]\n   - Poor fit: [scenario]\n\
  \n   ## Sources\n   - [URL 1] - [description] (accessed YYYY-MM-DD)\n   - [URL 2]\
  \ - [description] (accessed YYYY-MM-DD)\n\n   ## Child Topics\n   - [[Topic/Subtopic\
  \ 1]] - [Brief description, if child page exists or was created]\n   - [[Topic/Subtopic\
  \ 2]] - [Brief description, if child page exists or was created]\n\n   ## Related\n\
  \   [[Tag 1]] [[Tag 2]] [[Related Concept]]\n   ```\n\n   **For Comparison Research**:\n\
  \   ```markdown\n   # [Technology A] vs [Technology B] vs [Technology C]\n\n   ##\
  \ Comparison Matrix\n   | Feature | Tech A | Tech B | Tech C |\n   |---------|--------|--------|--------|\n\
  \   | Performance | [rating/detail] | [rating/detail] | [rating/detail] |\n   |\
  \ Complexity | [rating/detail] | [rating/detail] | [rating/detail] |\n   | Cost\
  \ | [rating/detail] | [rating/detail] | [rating/detail] |\n\n   ## Detailed Analysis\n\
  \n   ### [[Technology A]]\n   - Strengths: [list]\n   - Weaknesses: [list]\n   -\
  \ Best for: [use case]\n\n   ### [[Technology B]]\n   - Strengths: [list]\n   -\
  \ Weaknesses: [list]\n   - Best for: [use case]\n\n   ## Recommendation\n   - For\
  \ [use case]: Choose [[Technology X]] because [reasoning]\n   - For [different use\
  \ case]: Choose [[Technology Y]] because [reasoning]\n\n   ## Sources\n   - [URL\
  \ 1] - [description] (accessed YYYY-MM-DD)\n\n   ## Related\n   [[Tag 1]] [[Tag\
  \ 2]]\n   ```\n\n2. **Create zettel files**:\n   - Use appropriate naming: `logseq/pages/[Topic\
  \ Name].md`\n   - Ensure proper Logseq format\n   - Include bidirectional links\n\
  \   - Add relevant tags\n\n3. **Link from journal entry**:\n   ```markdown\n   OLD:\
  \ - Need to research [topic] [[Needs Research]]\n   NEW: - Researched [topic] →\
  \ [[Topic Name]] [[Researched on YYYY-MM-DD]]\n   ```\n\n4. **Create comparison\
  \ pages** (for product/tech comparisons):\n   - Main comparison zettel\n   - Individual\
  \ product/tech zettels\n   - Cross-link all related zettels\n\n**Success Criteria**:\n\
  - Minimum 200 words per zettel (300+ for complex topics)\n- At least 3 cited sources\n\
  - Clear structure with headers\n- Bidirectional links established\n- Actionable\
  \ recommendations provided\n\n---\n\n### Phase 4: Label Management\n\n**Objective**:\
  \ Update processed entries by completely removing `[[Needs Research]]` markers and\
  \ transforming entries to indicate completion.\n\n**Actions**:\nFor each successfully\
  \ processed entry:\n\n1. **Locate exact line** in journal file:\n   - Use grep result\
  \ (file path + line number) from Phase 1\n   - Read file to confirm line still matches\
  \ expected content\n   - Verify no manual edits occurred during processing\n\n2.\
  \ **Transform the entry** (COMPLETE REPLACEMENT - no strikethrough):\n\n   **Pattern:\
  \ Transform verb tense AND remove marker entirely**\n\n   | Entry Type | Before\
  \ | After |\n   |------------|--------|-------|\n   | Standard | `- Need to research\
  \ [topic] [[Needs Research]]` | `- Researched [topic] - see [[Topic Zettel]] [[Researched\
  \ YYYY-MM-DD]]` |\n   | Product search | `- Looking for a good [product] [[Needs\
  \ Research]]` | `- Evaluated [product] options - see [[Product Comparison]] [[Researched\
  \ YYYY-MM-DD]]` |\n   | Comparison | `- Compare [A] vs [B] [[Needs Research]]` |\
  \ `- Compared [A] vs [B] - see [[A vs B Comparison]] [[Researched YYYY-MM-DD]]`\
  \ |\n   | Investigation | `- Research why [problem] [[Needs Research]]` | `- Investigated\
  \ [problem] - see [[Problem Analysis]] [[Researched YYYY-MM-DD]]` |\n   | Thinking/Considering\
  \ | `- Thinking about [topic] [[Needs Research]]` | `- Researched [topic] - see\
  \ [[Topic Zettel]] [[Researched YYYY-MM-DD]]` |\n\n   **Key transformation rules**:\n\
  \   - **REMOVE** the `[[Needs Research]]` marker entirely (NO strikethrough)\n \
  \  - **CHANGE** verb to past tense (\"Need to research\" -> \"Researched\")\n  \
  \ - **ADD** link to created zettel with \"- see [[Zettel Name]]\"\n   - **ADD**\
  \ completion marker `[[Researched YYYY-MM-DD]]`\n   - **NEST** supporting details\
  \ (URLs, notes) as sub-bullets\n\n3. **Use Edit tool** for precise replacement:\n\
  \   - Match entire line content (not just marker) for safety\n   - Preserve indentation\
  \ and formatting\n   - Handle special characters correctly\n   - Transform verb\
  \ tense as part of the edit\n\n4. **Verify edit success**:\n   - Confirm file was\
  \ modified\n   - Re-read line to verify change\n   - Ensure `[[Needs Research]]`\
  \ is completely gone (not just struck through)\n   - Verify new completion marker\
  \ present\n\n**Why Complete Removal (NOT Strikethrough)**:\n- **Discovery efficiency**:\
  \ `grep \"[[Needs Research]]\"` returns ONLY unprocessed entries\n- **Clean journals**:\
  \ No visual clutter from `~~[[Needs Research]]~~`\n- **Clear status**: Entry wording\
  \ itself indicates completion (past tense)\n- **Traceability**: `[[Researched YYYY-MM-DD]]`\
  \ provides audit trail\n\n**Success Criteria**:\n- All successful entries have `[[Needs\
  \ Research]]` completely removed\n- Verb tense transformed to past tense\n- Links\
  \ to research zettels added\n- Completion date marker present\n- No content loss\
  \ or corruption\n- File integrity maintained\n- All edits validated\n\n---\n\n###\
  \ Phase 5: Verification and Reporting\n\n**Objective**: Confirm all processing completed\
  \ successfully and generate comprehensive report.\n\n**Actions**:\n1. **Verify label\
  \ removal**:\n   ```bash\n   # Confirm no [[Needs Research]] labels remain (except\
  \ failures)\n   grep -rn \"[[Needs Research]]\" ~/Documents/personal-wiki/logseq/journals/\n\
  \   ```\n   - Expected: Only entries marked as \"Needs Manual Review\"\n   - If\
  \ unexpected labels found, investigate and report\n\n2. **Validate created zettels**:\n\
  \   - All referenced files exist in pages directory\n   - Each zettel has minimum\
  \ content (200+ words)\n   - Links are properly formatted and functional\n   - Sources\
  \ cited (minimum 3)\n   - Recommendations are clear and actionable\n   - **Child\
  \ Topics section present if child pages exist** (NEW)\n\n3. **Validate child topic\
  \ integration** (NEW - CRITICAL):\n\n   For each topic that had child pages discovered:\n\
  \n   **Child Page Discovery Verification**:\n   ```bash\n   # Re-check child pages\
  \ exist\n   ls -la \"/storage/emulated/0/personal-wiki/logseq/pages/[Topic Name]/\"\
  \ 2>/dev/null\n   ```\n\n   **Child Topic Content Integration Verification**:\n\
  \   - Read the created research zettel\n   - Verify it references child pages in\
  \ \"Child Topics\" section\n   - Check for `[[Topic/Subtopic]]` style links\n  \
  \ - Confirm research builds upon existing child page knowledge\n\n   **Bidirectional\
  \ Link Verification**:\n   - Verify parent page links to child pages\n   - Verify\
  \ child pages link back to parent (if updated)\n\n   **Validation Criteria**:\n\
  \   - **FAIL if**: Topic had child pages but research doesn't reference them\n \
  \  - **PASS if**: Child pages are linked and their content informed the research\n\
  \n4. **Check knowledge base integration**:\n   - New zettels linked from journal\
  \ entries\n   - Bidirectional links established\n   - Comparison pages properly\
  \ cross-linked\n   - No broken references introduced\n   - **Parent-child page relationships\
  \ established** (NEW)\n\n5. **Generate completion report**:\n   ```\n   ## Research\
  \ Processing Complete\n\n   **Processing Summary**:\n   - Total entries discovered:\
  \ [count]\n   - Successfully processed: [count]\n   - Partial success: [count]\n\
  \   - Failed: [count]\n   - Skipped (section headers): [count]\n\n   **Research\
  \ Zettels Created**: [count]\n   - [[Research Topic 1]] (from [journal date])\n\
  \   - [[Research Topic 2]] (from [journal date])\n\n   **Comparison Pages Created**:\
  \ [count]\n   - [[Tech A vs Tech B vs Tech C]]\n   - [[Product Comparison: Category]]\n\
  \n   **Child Topic Integration** (NEW):\n   - Topics with existing child pages:\
  \ [count]\n   - Total child pages discovered: [count]\n   - Child pages read and\
  \ incorporated: [count]\n   - New child pages created: [count]\n   - Parent-child\
  \ links established: [count]\n\n   **Child Topics Processed**:\n   - [[Parent Topic]]\n\
  \     - [[Parent Topic/Child 1]] - incorporated into research\n     - [[Parent Topic/Child\
  \ 2]] - incorporated into research\n   - [[Another Parent]]\n     - [[Another Parent/Subtopic]]\
  \ - new child page created\n\n   **Entries Requiring Manual Review**: [count]\n\
  \   - [Journal date] - [Issue description]\n\n   **Verification**:\n   - Labels\
  \ updated: ✓ [count]\n   - Files created successfully: ✓ [count]\n   - Links validated:\
  \ ✓\n   - Sources cited (min 3 per entry): ✓\n   - No broken references: ✓\n   -\
  \ **Child topics integrated**: ✓ [count] (NEW)\n\n   **Next Actions**:\n   [If any\
  \ entries need manual review, list them here]\n   ```\n\n**Success Criteria**:\n\
  - Completion report generated with all metrics\n- All successful entries verified\n\
  - Failed entries documented with reasons\n- User provided clear next actions\n\n\
  ---\n\n## Usage Examples\n\n### Example 1: Product Research (Password Manager)\n\
  **Journal Content** (`2025_10_15.md`):\n```markdown\n- Need to find a good password\
  \ manager for the engineering team [[Needs Research]]\n  - Must support: SSO, team\
  \ sharing, audit logs\n  - Budget: Up to $10/user/month\n```\n\n**Command**: `/knowledge:process-needs-research`\n\
  \n**Processing**:\n1. Discovery: 1 entry found (Medium priority)\n2. Research conducted:\n\
  \   - Brave Search: \"best password manager for teams 2025\"\n   - Brave Search:\
  \ \"1Password vs Bitwarden vs LastPass enterprise\"\n   - Puppeteer: Visit official\
  \ sites for pricing\n3. Zettels created:\n   - `[[1Password]]` - Full feature review\n\
  \   - `[[Bitwarden]]` - Full feature review\n   - `[[LastPass]]` - Full feature\
  \ review\n   - `[[Password Manager Comparison for Teams]]` - Comparison matrix\n\
  4. Recommendation: 1Password for ease of use, Bitwarden for cost\n5. Entry transformed\
  \ (marker removed, verb changed)\n\n**Result**:\n```markdown\n- Evaluated password\
  \ managers - see [[Password Manager Comparison for Teams]] [[Researched 2025-10-15]]\n\
  \  - Recommendation: [[1Password]] (best UX) or [[Bitwarden]] (best value)\n  -\
  \ Must support: SSO, team sharing, audit logs\n  - Budget: Up to $10/user/month\n\
  ```\n\n---\n\n### Example 2: Technical Research (Event Sourcing)\n**Journal Content**\
  \ (`2025_10_20.md`):\n```markdown\n- Need to research event sourcing implementation\
  \ for order processing service [[Needs Research]]\n```\n\n**Command**: `/knowledge:process-needs-research`\n\
  \n**Processing**:\n1. Discovery: 1 entry (Medium priority)\n2. Research conducted:\n\
  \   - \"event sourcing best practices\"\n   - \"event sourcing microservices implementation\"\
  \n   - \"event sourcing pitfalls\"\n   - \"event store comparison\"\n3. Zettel created:\
  \ `[[Event Sourcing Implementation Guide]]`\n   - Best practices section\n   - Common\
  \ pitfalls\n   - Architecture patterns\n   - Implementation steps\n   - Tool recommendations\
  \ (EventStore, Axon, etc.)\n4. Entry transformed\n\n**Result**:\n```markdown\n-\
  \ Researched event sourcing for order processing - see [[Event Sourcing Implementation\
  \ Guide]] [[Researched 2025-10-20]]\n```\n\n---\n\n### Example 3: Technology Comparison\n\
  **Journal Content** (`2025_10_25.md`):\n```markdown\n- Compare message brokers:\
  \ Kafka vs RabbitMQ vs Pulsar [[Needs Research]]\n  - Need: High throughput, reliable\
  \ delivery, easy operations\n```\n\n**Command**: `/knowledge:process-needs-research`\n\
  \n**Processing**:\n1. Discovery: 1 entry (High priority - architectural decision)\n\
  2. Research conducted:\n   - \"Kafka vs RabbitMQ vs Pulsar comparison\"\n   - Performance\
  \ benchmarks for each\n   - Operational complexity analysis\n   - Use case fit\n\
  3. Zettels created:\n   - `[[Apache Kafka]]` - Detailed profile\n   - `[[RabbitMQ]]`\
  \ - Detailed profile\n   - `[[Apache Pulsar]]` - Detailed profile\n   - `[[Message\
  \ Broker Comparison]]` - Full comparison matrix\n4. Recommendation based on criteria\n\
  5. Entry transformed\n\n**Result**:\n```markdown\n- Compared message brokers - see\
  \ [[Message Broker Comparison]] [[Researched 2025-10-25]]\n  - Recommendation: [[Apache\
  \ Kafka]] for high throughput use case\n  - Need: High throughput, reliable delivery,\
  \ easy operations\n```\n\n---\n\n### Example 4: Multiple Nested Research Items\n\
  **Journal Content** (`2025_10_30.md`):\n```markdown\n## Infrastructure Decisions\
  \ [[Needs Research]]\n- Database selection: [[Needs Research]]\n  - PostgreSQL vs\
  \ MySQL for high-write workload\n- Monitoring stack: [[Needs Research]]\n  - Prometheus\
  \ vs Datadog vs New Relic\n- Load balancer: [[Needs Research]]\n```\n\n**Command**:\
  \ `/knowledge:process-needs-research`\n\n**Processing**:\n1. Discovery: 4 labels\
  \ found\n   - Line 1 (section header): Skip\n   - Lines 2-4 (specific items): Process\
  \ each\n2. Research conducted for each:\n   - Database comparison with write performance\
  \ focus\n   - Monitoring stack comparison\n   - Load balancer options research\n\
  3. Zettels created:\n   - `[[PostgreSQL vs MySQL for Write-Heavy Workloads]]`\n\
  \   - `[[Monitoring Stack Comparison]]`\n   - `[[Load Balancer Options]]`\n4. All\
  \ entries transformed\n\n**Result**:\n```markdown\n## Infrastructure Decisions\n\
  - Evaluated databases - see [[PostgreSQL vs MySQL for Write-Heavy Workloads]] [[Researched\
  \ 2025-10-30]]\n  - PostgreSQL vs MySQL for high-write workload\n  - Recommendation:\
  \ [[PostgreSQL]] with tuned settings\n- Evaluated monitoring stacks - see [[Monitoring\
  \ Stack Comparison]] [[Researched 2025-10-30]]\n  - Prometheus vs Datadog vs New\
  \ Relic\n  - Recommendation: [[Datadog]] for full-stack visibility\n- Researched\
  \ load balancers - see [[Load Balancer Options]] [[Researched 2025-10-30]]\n  -\
  \ Recommendation: [[HAProxy]] or cloud-native options\n```\n\n---\n\n### Example\
  \ 5: Insufficient Information (Needs Clarification)\n**Journal Content** (`2025_11_01.md`):\n\
  ```markdown\n- Need to research CI/CD [[Needs Research]]\n```\n\n**Command**: `/knowledge:process-needs-research`\n\
  \n**Processing**:\n1. Discovery: 1 entry (vague, needs clarification)\n2. Attempt\
  \ basic research:\n   - Too broad to provide actionable recommendations\n   - Need:\
  \ use case, constraints, team size, etc.\n3. Apply error handling:\n   - Label changed\
  \ to `#needs-clarification`\n   - Add note requesting more context\n\n**Result**:\n\
  ```markdown\n- Need to research CI/CD #needs-clarification\n  - NOTE: Please add\
  \ more context:\n    - What is the use case? (e.g., monorepo, microservices)\n \
  \   - What are your requirements? (e.g., speed, cost, integrations)\n    - What\
  \ is your team size and tech stack?\n```\n\n---\n\n### Example 6: Appliance Repair\
  \ with URL (Real Example)\n**Journal Content** (`2026_01_05.md`):\n```markdown\n\
  - Thinking about [[ETW4400WQ0 Washer Suspension Repair]] https://g.co/gemini/share/898a1f5ec14e\
  \ [[Needs Research]]\n```\n\n**Command**: `/knowledge:process-needs-research`\n\n\
  **Processing**:\n1. Discovery: 1 entry (Medium priority - home maintenance)\n2.\
  \ Research conducted:\n   - \"ETW4400WQ0 Estate washer suspension repair guide\"\
  \n   - \"top load washer suspension rod replacement DIY\"\n   - \"Estate ETW4400WQ0\
  \ suspension spring parts numbers\"\n   - Website deep-dive: PartSelect.com for\
  \ parts and diagrams\n3. Zettel created: `[[ETW4400WQ0 Washer Suspension Repair]]`\n\
  \   - Complete diagnosis guide for shaking issues\n   - Part numbers and pricing\
  \ (WP63907, ~$10-15)\n   - Step-by-step repair instructions\n   - Tool requirements\n\
  \   - Cost comparison (DIY vs professional)\n   - Video resources\n4. Entry transformed\
  \ with URL nested\n\n**Result**:\n```markdown\n- Researched [[ETW4400WQ0 Washer\
  \ Suspension Repair]] - see comprehensive repair guide with part numbers, step-by-step\
  \ instructions, and cost comparison [[Researched 2026-01-05]]\n  - Gemini conversation:\
  \ https://g.co/gemini/share/898a1f5ec14e\n```\n\n**Notes**:\n- URL moved to nested\
  \ sub-bullet for cleaner main entry\n- Verb changed from \"Thinking about\" to \"\
  Researched\"\n- `[[Needs Research]]` completely removed (no strikethrough)\n- Completion\
  \ date added as `[[Researched 2026-01-05]]`\n\n---\n\n## Quality Standards\n\nAll\
  \ processing must satisfy:\n\n1. **Discovery Completeness**:\n   - All `[[Needs\
  \ Research]]` labels found (case-insensitive)\n   - Entries properly categorized\
  \ by type and priority\n   - Context and requirements extracted\n   - No entries\
  \ missed or skipped unintentionally\n\n2. **Research Thoroughness**:\n   - Minimum\
  \ 3-5 quality sources per entry\n   - Multiple perspectives considered\n   - Recent\
  \ information prioritized (within 1-2 years)\n   - Specific use case and requirements\
  \ addressed\n   - Trade-offs clearly documented\n\n3. **Zettel Quality**:\n   -\
  \ Minimum 200 words (300+ for complex topics)\n   - Clear structure with appropriate\
  \ headers\n   - Actionable recommendations provided\n   - Sources properly cited\
  \ with URLs and access dates\n   - Bidirectional links established\n\n4. **Comparison\
  \ Quality** (when applicable):\n   - Comparison matrix with relevant criteria\n\
  \   - Individual profiles for each option\n   - Clear recommendations based on use\
  \ cases\n   - Trade-offs explicitly stated\n\n5. **Label Management Accuracy**:\n\
  \   - Only successful entries have labels updated\n   - Failed entries clearly marked\
  \ with reasons\n   - No content corruption or loss\n   - Links to research zettels\
  \ added\n   - All edits validated\n\n6. **Reporting Completeness**:\n   - All metrics\
  \ included (counts, successes, failures)\n   - Failed entries documented with reasons\n\
  \   - Clear next actions provided\n   - Verification checklist completed\n\n---\n\
  \n## Error Handling\n\n### Vague or Broad Request\n**Pattern**: \"Research CI/CD\"\
  \ without context\n**Handling**: Add `#needs-clarification` tag, request specific\
  \ requirements, preserve original entry.\n\n### Insufficient Search Results\n**Issue**:\
  \ Cannot find quality information (niche topic, new technology)\n**Handling**: Document\
  \ limitation in zettel, note \"limited information available as of [date]\", mark\
  \ for future re-research.\n\n### Conflicting Information\n**Issue**: Sources contradict\
  \ each other\n**Handling**: Document multiple perspectives, cite sources for each\
  \ view, recommend further investigation or testing.\n\n### Section Headers with\
  \ Labels\n**Pattern**: `## Research Queue [[Needs Research]]`\n**Handling**: Skip\
  \ processing (organizational). Optionally remove label if section is empty.\n\n\
  ### Concurrent Edits\n**Issue**: Journal file modified during processing\n**Handling**:\
  \ Re-read file before editing, verify line still matches, retry once if mismatch,\
  \ report if persistent.\n\n### Partial Research\n**Issue**: Some questions answered,\
  \ others remain unclear\n**Handling**: Mark as \"Partial\", keep label with note\
  \ \"Requires additional research on [specific aspect]\".\n\n---\n\n## Command Invocation\n\
  \n**Format**: `/knowledge:process-needs-research`\n\n**Arguments**: None (processes\
  \ all pending entries)\n\n**Execution Mode**: Direct research and synthesis (no\
  \ agent delegation)\n\n**Tools Used**:\n- Brave Search for multi-source research\n\
  - Puppeteer for deep dives into specific sites\n- Analysis tools for data processing\
  \ (if needed)\n\n**Expected Duration**: 10-30 minutes depending on queue size (3-8\
  \ minutes per entry for thorough research)\n\n**Prerequisites**:\n- Brave Search\
  \ accessible\n- Web tools (Puppeteer) functional\n- Internet connection stable\n\
  \n**Post-Execution**:\n- Review completion report\n- Address any entries requiring\
  \ clarification\n- Verify new zettels integrate properly\n- Act on recommendations\
  \ as appropriate\n"
---

# Process Needs Research Entries

**Command Purpose**: Systematically process all journal entries marked with `[[Needs Research]]` by:
1. Discovering and cataloging all pending research entries
2. Discovering existing child topic pages for hierarchical context
3. Conducting comprehensive research using web search and analysis
4. Incorporating child topic insights into research findings
5. Creating detailed zettels with findings, comparisons, and recommendations
6. Establishing hierarchical page structures when appropriate
7. Removing research labels after successful processing
8. Verifying child topic integration and generating completion report

**When Invoked**: This command performs direct research and synthesis (unlike process-needs-synthesis which delegates to an agent).

---

## Core Methodology

### Phase 1: Discovery and Cataloging

**Objective**: Find all entries marked for research and extract actionable items.

**Actions**:
1. **Search for research markers**:
   ```bash
   grep -rn "[[Needs Research]]" ~/Documents/personal-wiki/logseq/journals/
   ```
   - Record file paths, line numbers, and content
   - Handle case variations: `[[needs research]]`, `[[Needs Research]]`
   - Check both uppercase and lowercase patterns

2. **Parse each entry**:
   - Extract project name or product type from the line
   - Capture surrounding context (3-5 lines before/after for context)
   - Identify entry type (see Entry Types below)
   - Note any specific requirements, constraints, or criteria

3. **Categorize and prioritize**:
   - **High priority**: Explicit "urgent", "important", upcoming deadlines
   - **Medium priority**: Standard projects/products with clear criteria
   - **Low priority**: Exploratory research, long-term planning
   - **Requires clarification**: Vague requests, missing criteria, ambiguous goals

3.5. **Discover child topic pages** (NEW - CRITICAL):

   For each topic identified in research entries:

   **Check filesystem for child pages**:
   ```bash
   # Check if topic has a child pages directory
   ls -la "/storage/emulated/0/personal-wiki/logseq/pages/[Topic Name]/" 2>/dev/null

   # Example: Check for Kubernetes child pages
   ls -la "/storage/emulated/0/personal-wiki/logseq/pages/Kubernetes/" 2>/dev/null
   ```

   **Search for namespaced wiki link references**:
   ```bash
   # Find all namespaced references to the topic
   grep -r "\[\[Topic Name/" /storage/emulated/0/personal-wiki/logseq/pages/ 2>/dev/null

   # Example: Find all Kubernetes subtopics
   grep -r "\[\[Kubernetes/" /storage/emulated/0/personal-wiki/logseq/pages/
   ```

   **Record child topic information**:
   - List of child page files found
   - Namespaced references discovered
   - Existing knowledge to incorporate into research

4. **Generate discovery report**:
   ```
   ## Research Queue Discovery

   **Total Entries Found**: [count]

   **High Priority** ([count]):
   - [Journal Date] - [Entry Preview] - [Research Topic]
     - Child topics found: [count] (e.g., [[Topic/Subtopic1]], [[Topic/Subtopic2]])

   **Medium Priority** ([count]):
   - [Journal Date] - [Entry Preview] - [Research Topic]
     - Child topics found: [count]

   **Low Priority** ([count]):
   - [Journal Date] - [Entry Preview] - [Research Topic]
     - Child topics found: [count]

   **Requires Clarification** ([count]):
   - [Journal Date] - [Entry Preview] - [Issue]

   **Child Topic Summary**:
   - Topics with existing child pages: [count]
   - Total child pages discovered: [count]
   - Child page content to incorporate: [list]
   ```

**Success Criteria**:
- All `[[Needs Research]]` markers found and recorded
- Each entry categorized by type and priority
- Research topics/criteria extracted successfully
- **Child topic pages discovered for each topic** (NEW)
- Discovery report generated with counts and child topic information

**Entry Types to Recognize**:

1. **Project research**:
   ```markdown
   - Need to research best practices for implementing event sourcing in microservices [[Needs Research]]
   ```

2. **Product comparison**:
   ```markdown
   - Looking for a good password manager for the team [[Needs Research]]
   ```

3. **Technology evaluation**:
   ```markdown
   - Compare Kafka vs Pulsar vs RabbitMQ for our use case [[Needs Research]]
   ```

4. **Tool/service search**:
   ```markdown
   - Find a good CI/CD platform that supports monorepos [[Needs Research]]
   ```

5. **Problem investigation**:
   ```markdown
   - Research why our PostgreSQL queries are slow [[Needs Research]]
   ```

6. **Section header** (NOT actionable):
   ```markdown
   ## Research Queue [[Needs Research]]
   ```
   → **Skip**: Section headers are organizational, not research targets

7. **Nested items**:
   ```markdown
   - Project infrastructure decisions:
     - Database selection [[Needs Research]]
     - Message broker evaluation [[Needs Research]]
   ```
   → **Process**: Each nested item separately

8. **Topic with known child pages** (NEW):
   ```markdown
   - Need to research Kubernetes deployment strategies [[Needs Research]]
   ```
   → **Check for**: `Kubernetes/Pods.md`, `Kubernetes/Services.md`, `Kubernetes/Deployments.md`, etc.
   → **Action**: Read child pages and incorporate existing knowledge into research

---

### Phase 2: Research and Analysis

**Objective**: Conduct comprehensive research for each entry using available tools.

**Actions**:
For each entry in priority order:

1. **Analyze research requirements**:
   - Identify key questions to answer
   - Determine evaluation criteria (cost, features, performance, etc.)
   - Note any constraints (budget, timeline, technical requirements)
   - Extract specific use case or context

1.5. **Read and incorporate child topic pages** (NEW - CRITICAL):

   If child pages were discovered in Phase 1:

   **Read child page content**:
   ```bash
   # Read each discovered child page
   cat "/storage/emulated/0/personal-wiki/logseq/pages/[Topic]/[Subtopic].md"
   ```

   **Extract existing knowledge**:
   - Note what's already documented about the topic
   - Identify gaps in existing knowledge
   - Find connections to research questions
   - Determine what new research adds to existing content

   **Integration strategy**:
   - Build upon existing knowledge (don't duplicate)
   - Address gaps identified in child pages
   - Create connections between new research and existing pages
   - Consider whether to update existing child pages or create new ones

2. **Conduct multi-source research**:

   **For Product/Tool Research**:
   - Use Brave Search to find:
     - Product comparisons and reviews
     - Official documentation and pricing
     - User experiences and case studies
     - Alternative solutions
   - Search patterns:
     ```
     "[product name] vs alternatives"
     "best [tool category] for [use case]"
     "[product] review [year]"
     "[product] pricing comparison"
     ```

   **For Project/Technical Research**:
   - Use Brave Search to find:
     - Best practices and patterns
     - Architecture examples
     - Common pitfalls and solutions
     - Performance considerations
   - Search patterns:
     ```
     "[technology] best practices"
     "[pattern] implementation guide"
     "[problem] solution"
     "how to [accomplish goal]"
     ```

   **For Technology Comparison**:
   - Create comparison matrix with:
     - Core features
     - Performance characteristics
     - Complexity/learning curve
     - Community support
     - Cost considerations
     - Use case fit

3. **Deep dive with Puppeteer** (when needed):
   - Navigate to official websites for detailed information
   - Screenshot key feature pages
   - Extract pricing information
   - Review documentation structure
   - Capture product demos or examples

4. **Synthesize findings**:
   - Summarize research results
   - Create comparison tables/matrices
   - Identify top recommendations
   - Note trade-offs and considerations
   - Provide implementation guidance

**Success Criteria (per entry)**:
- Minimum 3-5 quality sources consulted
- Key questions answered comprehensively
- Clear recommendations provided
- Trade-offs and considerations documented
- Sources properly cited with URLs and dates
- **Child topic pages read and incorporated** (NEW)
- **Existing knowledge gaps identified and addressed** (NEW)
- **Child pages referenced in research zettel** (NEW)

**Research Quality Standards**:

1. **Breadth**: Cover multiple perspectives and sources
2. **Depth**: Go beyond surface-level information
3. **Recency**: Prioritize recent information (last 1-2 years)
4. **Relevance**: Focus on specific use case and requirements
5. **Actionability**: Provide clear next steps or recommendations
6. **Context awareness**: Build upon existing child page knowledge (NEW)
7. **Hierarchical integration**: Link parent and child topics appropriately (NEW)

---

### Phase 3: Zettel Creation

**Objective**: Create comprehensive zettels documenting research findings.

**Actions**:
For each research entry:

1. **Determine zettel structure**:

   **For Product/Tool Research**:
   ```markdown
   # [Product/Tool Name]

   ## Overview
   [Brief description, purpose, key value proposition]

   ## Key Features
   - Feature 1: [description]
   - Feature 2: [description]

   ## Pricing
   [Pricing tiers, costs, free options]

   ## Alternatives
   - [[Alternative 1]] - [comparison point]
   - [[Alternative 2]] - [comparison point]

   ## Pros
   - [advantage]

   ## Cons
   - [limitation]

   ## Use Cases
   - Best for: [scenario]
   - Not ideal for: [scenario]

   ## Recommendation
   [Clear recommendation with reasoning]

   ## Sources
   - [URL 1] - [description] (accessed YYYY-MM-DD)
   - [URL 2] - [description] (accessed YYYY-MM-DD)

   ## Child Topics
   - [[Product/Subtopic 1]] - [Brief description, if child page exists or was created]
   - [[Product/Subtopic 2]] - [Brief description, if child page exists or was created]

   ## Related
   [[Tag 1]] [[Tag 2]] [[Related Concept]]
   ```

   **For Project/Technical Research**:
   ```markdown
   # [Topic/Pattern Name]

   ## Overview
   [What it is, why it matters]

   ## Key Concepts
   - Concept 1: [explanation]
   - Concept 2: [explanation]

   ## Best Practices
   1. [practice]: [reasoning]
   2. [practice]: [reasoning]

   ## Common Pitfalls
   - [pitfall]: [how to avoid]

   ## Implementation Approach
   [Step-by-step guidance or architecture overview]

   ## Examples
   [Code snippets, architecture diagrams, real-world examples]

   ## Performance Considerations
   [Scalability, efficiency, resource usage]

   ## When to Use
   - Good fit: [scenario]
   - Poor fit: [scenario]

   ## Sources
   - [URL 1] - [description] (accessed YYYY-MM-DD)
   - [URL 2] - [description] (accessed YYYY-MM-DD)

   ## Child Topics
   - [[Topic/Subtopic 1]] - [Brief description, if child page exists or was created]
   - [[Topic/Subtopic 2]] - [Brief description, if child page exists or was created]

   ## Related
   [[Tag 1]] [[Tag 2]] [[Related Concept]]
   ```

   **For Comparison Research**:
   ```markdown
   # [Technology A] vs [Technology B] vs [Technology C]

   ## Comparison Matrix
   | Feature | Tech A | Tech B | Tech C |
   |---------|--------|--------|--------|
   | Performance | [rating/detail] | [rating/detail] | [rating/detail] |
   | Complexity | [rating/detail] | [rating/detail] | [rating/detail] |
   | Cost | [rating/detail] | [rating/detail] | [rating/detail] |

   ## Detailed Analysis

   ### [[Technology A]]
   - Strengths: [list]
   - Weaknesses: [list]
   - Best for: [use case]

   ### [[Technology B]]
   - Strengths: [list]
   - Weaknesses: [list]
   - Best for: [use case]

   ## Recommendation
   - For [use case]: Choose [[Technology X]] because [reasoning]
   - For [different use case]: Choose [[Technology Y]] because [reasoning]

   ## Sources
   - [URL 1] - [description] (accessed YYYY-MM-DD)

   ## Related
   [[Tag 1]] [[Tag 2]]
   ```

2. **Create zettel files**:
   - Use appropriate naming: `logseq/pages/[Topic Name].md`
   - Ensure proper Logseq format
   - Include bidirectional links
   - Add relevant tags

3. **Link from journal entry**:
   ```markdown
   OLD: - Need to research [topic] [[Needs Research]]
   NEW: - Researched [topic] → [[Topic Name]] [[Researched on YYYY-MM-DD]]
   ```

4. **Create comparison pages** (for product/tech comparisons):
   - Main comparison zettel
   - Individual product/tech zettels
   - Cross-link all related zettels

**Success Criteria**:
- Minimum 200 words per zettel (300+ for complex topics)
- At least 3 cited sources
- Clear structure with headers
- Bidirectional links established
- Actionable recommendations provided

---

### Phase 4: Label Management

**Objective**: Update processed entries by completely removing `[[Needs Research]]` markers and transforming entries to indicate completion.

**Actions**:
For each successfully processed entry:

1. **Locate exact line** in journal file:
   - Use grep result (file path + line number) from Phase 1
   - Read file to confirm line still matches expected content
   - Verify no manual edits occurred during processing

2. **Transform the entry** (COMPLETE REPLACEMENT - no strikethrough):

   **Pattern: Transform verb tense AND remove marker entirely**

   | Entry Type | Before | After |
   |------------|--------|-------|
   | Standard | `- Need to research [topic] [[Needs Research]]` | `- Researched [topic] - see [[Topic Zettel]] [[Researched YYYY-MM-DD]]` |
   | Product search | `- Looking for a good [product] [[Needs Research]]` | `- Evaluated [product] options - see [[Product Comparison]] [[Researched YYYY-MM-DD]]` |
   | Comparison | `- Compare [A] vs [B] [[Needs Research]]` | `- Compared [A] vs [B] - see [[A vs B Comparison]] [[Researched YYYY-MM-DD]]` |
   | Investigation | `- Research why [problem] [[Needs Research]]` | `- Investigated [problem] - see [[Problem Analysis]] [[Researched YYYY-MM-DD]]` |
   | Thinking/Considering | `- Thinking about [topic] [[Needs Research]]` | `- Researched [topic] - see [[Topic Zettel]] [[Researched YYYY-MM-DD]]` |

   **Key transformation rules**:
   - **REMOVE** the `[[Needs Research]]` marker entirely (NO strikethrough)
   - **CHANGE** verb to past tense ("Need to research" -> "Researched")
   - **ADD** link to created zettel with "- see [[Zettel Name]]"
   - **ADD** completion marker `[[Researched YYYY-MM-DD]]`
   - **NEST** supporting details (URLs, notes) as sub-bullets

3. **Use Edit tool** for precise replacement:
   - Match entire line content (not just marker) for safety
   - Preserve indentation and formatting
   - Handle special characters correctly
   - Transform verb tense as part of the edit

4. **Verify edit success**:
   - Confirm file was modified
   - Re-read line to verify change
   - Ensure `[[Needs Research]]` is completely gone (not just struck through)
   - Verify new completion marker present

**Why Complete Removal (NOT Strikethrough)**:
- **Discovery efficiency**: `grep "[[Needs Research]]"` returns ONLY unprocessed entries
- **Clean journals**: No visual clutter from `~~[[Needs Research]]~~`
- **Clear status**: Entry wording itself indicates completion (past tense)
- **Traceability**: `[[Researched YYYY-MM-DD]]` provides audit trail

**Success Criteria**:
- All successful entries have `[[Needs Research]]` completely removed
- Verb tense transformed to past tense
- Links to research zettels added
- Completion date marker present
- No content loss or corruption
- File integrity maintained
- All edits validated

---

### Phase 5: Verification and Reporting

**Objective**: Confirm all processing completed successfully and generate comprehensive report.

**Actions**:
1. **Verify label removal**:
   ```bash
   # Confirm no [[Needs Research]] labels remain (except failures)
   grep -rn "[[Needs Research]]" ~/Documents/personal-wiki/logseq/journals/
   ```
   - Expected: Only entries marked as "Needs Manual Review"
   - If unexpected labels found, investigate and report

2. **Validate created zettels**:
   - All referenced files exist in pages directory
   - Each zettel has minimum content (200+ words)
   - Links are properly formatted and functional
   - Sources cited (minimum 3)
   - Recommendations are clear and actionable
   - **Child Topics section present if child pages exist** (NEW)

3. **Validate child topic integration** (NEW - CRITICAL):

   For each topic that had child pages discovered:

   **Child Page Discovery Verification**:
   ```bash
   # Re-check child pages exist
   ls -la "/storage/emulated/0/personal-wiki/logseq/pages/[Topic Name]/" 2>/dev/null
   ```

   **Child Topic Content Integration Verification**:
   - Read the created research zettel
   - Verify it references child pages in "Child Topics" section
   - Check for `[[Topic/Subtopic]]` style links
   - Confirm research builds upon existing child page knowledge

   **Bidirectional Link Verification**:
   - Verify parent page links to child pages
   - Verify child pages link back to parent (if updated)

   **Validation Criteria**:
   - **FAIL if**: Topic had child pages but research doesn't reference them
   - **PASS if**: Child pages are linked and their content informed the research

4. **Check knowledge base integration**:
   - New zettels linked from journal entries
   - Bidirectional links established
   - Comparison pages properly cross-linked
   - No broken references introduced
   - **Parent-child page relationships established** (NEW)

5. **Generate completion report**:
   ```
   ## Research Processing Complete

   **Processing Summary**:
   - Total entries discovered: [count]
   - Successfully processed: [count]
   - Partial success: [count]
   - Failed: [count]
   - Skipped (section headers): [count]

   **Research Zettels Created**: [count]
   - [[Research Topic 1]] (from [journal date])
   - [[Research Topic 2]] (from [journal date])

   **Comparison Pages Created**: [count]
   - [[Tech A vs Tech B vs Tech C]]
   - [[Product Comparison: Category]]

   **Child Topic Integration** (NEW):
   - Topics with existing child pages: [count]
   - Total child pages discovered: [count]
   - Child pages read and incorporated: [count]
   - New child pages created: [count]
   - Parent-child links established: [count]

   **Child Topics Processed**:
   - [[Parent Topic]]
     - [[Parent Topic/Child 1]] - incorporated into research
     - [[Parent Topic/Child 2]] - incorporated into research
   - [[Another Parent]]
     - [[Another Parent/Subtopic]] - new child page created

   **Entries Requiring Manual Review**: [count]
   - [Journal date] - [Issue description]

   **Verification**:
   - Labels updated: ✓ [count]
   - Files created successfully: ✓ [count]
   - Links validated: ✓
   - Sources cited (min 3 per entry): ✓
   - No broken references: ✓
   - **Child topics integrated**: ✓ [count] (NEW)

   **Next Actions**:
   [If any entries need manual review, list them here]
   ```

**Success Criteria**:
- Completion report generated with all metrics
- All successful entries verified
- Failed entries documented with reasons
- User provided clear next actions

---

## Usage Examples

### Example 1: Product Research (Password Manager)
**Journal Content** (`2025_10_15.md`):
```markdown
- Need to find a good password manager for the engineering team [[Needs Research]]
  - Must support: SSO, team sharing, audit logs
  - Budget: Up to $10/user/month
```

**Command**: `/knowledge:process-needs-research`

**Processing**:
1. Discovery: 1 entry found (Medium priority)
2. Research conducted:
   - Brave Search: "best password manager for teams 2025"
   - Brave Search: "1Password vs Bitwarden vs LastPass enterprise"
   - Puppeteer: Visit official sites for pricing
3. Zettels created:
   - `[[1Password]]` - Full feature review
   - `[[Bitwarden]]` - Full feature review
   - `[[LastPass]]` - Full feature review
   - `[[Password Manager Comparison for Teams]]` - Comparison matrix
4. Recommendation: 1Password for ease of use, Bitwarden for cost
5. Entry transformed (marker removed, verb changed)

**Result**:
```markdown
- Evaluated password managers - see [[Password Manager Comparison for Teams]] [[Researched 2025-10-15]]
  - Recommendation: [[1Password]] (best UX) or [[Bitwarden]] (best value)
  - Must support: SSO, team sharing, audit logs
  - Budget: Up to $10/user/month
```

---

### Example 2: Technical Research (Event Sourcing)
**Journal Content** (`2025_10_20.md`):
```markdown
- Need to research event sourcing implementation for order processing service [[Needs Research]]
```

**Command**: `/knowledge:process-needs-research`

**Processing**:
1. Discovery: 1 entry (Medium priority)
2. Research conducted:
   - "event sourcing best practices"
   - "event sourcing microservices implementation"
   - "event sourcing pitfalls"
   - "event store comparison"
3. Zettel created: `[[Event Sourcing Implementation Guide]]`
   - Best practices section
   - Common pitfalls
   - Architecture patterns
   - Implementation steps
   - Tool recommendations (EventStore, Axon, etc.)
4. Entry transformed

**Result**:
```markdown
- Researched event sourcing for order processing - see [[Event Sourcing Implementation Guide]] [[Researched 2025-10-20]]
```

---

### Example 3: Technology Comparison
**Journal Content** (`2025_10_25.md`):
```markdown
- Compare message brokers: Kafka vs RabbitMQ vs Pulsar [[Needs Research]]
  - Need: High throughput, reliable delivery, easy operations
```

**Command**: `/knowledge:process-needs-research`

**Processing**:
1. Discovery: 1 entry (High priority - architectural decision)
2. Research conducted:
   - "Kafka vs RabbitMQ vs Pulsar comparison"
   - Performance benchmarks for each
   - Operational complexity analysis
   - Use case fit
3. Zettels created:
   - `[[Apache Kafka]]` - Detailed profile
   - `[[RabbitMQ]]` - Detailed profile
   - `[[Apache Pulsar]]` - Detailed profile
   - `[[Message Broker Comparison]]` - Full comparison matrix
4. Recommendation based on criteria
5. Entry transformed

**Result**:
```markdown
- Compared message brokers - see [[Message Broker Comparison]] [[Researched 2025-10-25]]
  - Recommendation: [[Apache Kafka]] for high throughput use case
  - Need: High throughput, reliable delivery, easy operations
```

---

### Example 4: Multiple Nested Research Items
**Journal Content** (`2025_10_30.md`):
```markdown
## Infrastructure Decisions [[Needs Research]]
- Database selection: [[Needs Research]]
  - PostgreSQL vs MySQL for high-write workload
- Monitoring stack: [[Needs Research]]
  - Prometheus vs Datadog vs New Relic
- Load balancer: [[Needs Research]]
```

**Command**: `/knowledge:process-needs-research`

**Processing**:
1. Discovery: 4 labels found
   - Line 1 (section header): Skip
   - Lines 2-4 (specific items): Process each
2. Research conducted for each:
   - Database comparison with write performance focus
   - Monitoring stack comparison
   - Load balancer options research
3. Zettels created:
   - `[[PostgreSQL vs MySQL for Write-Heavy Workloads]]`
   - `[[Monitoring Stack Comparison]]`
   - `[[Load Balancer Options]]`
4. All entries transformed

**Result**:
```markdown
## Infrastructure Decisions
- Evaluated databases - see [[PostgreSQL vs MySQL for Write-Heavy Workloads]] [[Researched 2025-10-30]]
  - PostgreSQL vs MySQL for high-write workload
  - Recommendation: [[PostgreSQL]] with tuned settings
- Evaluated monitoring stacks - see [[Monitoring Stack Comparison]] [[Researched 2025-10-30]]
  - Prometheus vs Datadog vs New Relic
  - Recommendation: [[Datadog]] for full-stack visibility
- Researched load balancers - see [[Load Balancer Options]] [[Researched 2025-10-30]]
  - Recommendation: [[HAProxy]] or cloud-native options
```

---

### Example 5: Insufficient Information (Needs Clarification)
**Journal Content** (`2025_11_01.md`):
```markdown
- Need to research CI/CD [[Needs Research]]
```

**Command**: `/knowledge:process-needs-research`

**Processing**:
1. Discovery: 1 entry (vague, needs clarification)
2. Attempt basic research:
   - Too broad to provide actionable recommendations
   - Need: use case, constraints, team size, etc.
3. Apply error handling:
   - Label changed to `#needs-clarification`
   - Add note requesting more context

**Result**:
```markdown
- Need to research CI/CD #needs-clarification
  - NOTE: Please add more context:
    - What is the use case? (e.g., monorepo, microservices)
    - What are your requirements? (e.g., speed, cost, integrations)
    - What is your team size and tech stack?
```

---

### Example 6: Appliance Repair with URL (Real Example)
**Journal Content** (`2026_01_05.md`):
```markdown
- Thinking about [[ETW4400WQ0 Washer Suspension Repair]] https://g.co/gemini/share/898a1f5ec14e [[Needs Research]]
```

**Command**: `/knowledge:process-needs-research`

**Processing**:
1. Discovery: 1 entry (Medium priority - home maintenance)
2. Research conducted:
   - "ETW4400WQ0 Estate washer suspension repair guide"
   - "top load washer suspension rod replacement DIY"
   - "Estate ETW4400WQ0 suspension spring parts numbers"
   - Website deep-dive: PartSelect.com for parts and diagrams
3. Zettel created: `[[ETW4400WQ0 Washer Suspension Repair]]`
   - Complete diagnosis guide for shaking issues
   - Part numbers and pricing (WP63907, ~$10-15)
   - Step-by-step repair instructions
   - Tool requirements
   - Cost comparison (DIY vs professional)
   - Video resources
4. Entry transformed with URL nested

**Result**:
```markdown
- Researched [[ETW4400WQ0 Washer Suspension Repair]] - see comprehensive repair guide with part numbers, step-by-step instructions, and cost comparison [[Researched 2026-01-05]]
  - Gemini conversation: https://g.co/gemini/share/898a1f5ec14e
```

**Notes**:
- URL moved to nested sub-bullet for cleaner main entry
- Verb changed from "Thinking about" to "Researched"
- `[[Needs Research]]` completely removed (no strikethrough)
- Completion date added as `[[Researched 2026-01-05]]`

---

## Quality Standards

All processing must satisfy:

1. **Discovery Completeness**:
   - All `[[Needs Research]]` labels found (case-insensitive)
   - Entries properly categorized by type and priority
   - Context and requirements extracted
   - No entries missed or skipped unintentionally

2. **Research Thoroughness**:
   - Minimum 3-5 quality sources per entry
   - Multiple perspectives considered
   - Recent information prioritized (within 1-2 years)
   - Specific use case and requirements addressed
   - Trade-offs clearly documented

3. **Zettel Quality**:
   - Minimum 200 words (300+ for complex topics)
   - Clear structure with appropriate headers
   - Actionable recommendations provided
   - Sources properly cited with URLs and access dates
   - Bidirectional links established

4. **Comparison Quality** (when applicable):
   - Comparison matrix with relevant criteria
   - Individual profiles for each option
   - Clear recommendations based on use cases
   - Trade-offs explicitly stated

5. **Label Management Accuracy**:
   - Only successful entries have labels updated
   - Failed entries clearly marked with reasons
   - No content corruption or loss
   - Links to research zettels added
   - All edits validated

6. **Reporting Completeness**:
   - All metrics included (counts, successes, failures)
   - Failed entries documented with reasons
   - Clear next actions provided
   - Verification checklist completed

---

## Error Handling

### Vague or Broad Request
**Pattern**: "Research CI/CD" without context
**Handling**: Add `#needs-clarification` tag, request specific requirements, preserve original entry.

### Insufficient Search Results
**Issue**: Cannot find quality information (niche topic, new technology)
**Handling**: Document limitation in zettel, note "limited information available as of [date]", mark for future re-research.

### Conflicting Information
**Issue**: Sources contradict each other
**Handling**: Document multiple perspectives, cite sources for each view, recommend further investigation or testing.

### Section Headers with Labels
**Pattern**: `## Research Queue [[Needs Research]]`
**Handling**: Skip processing (organizational). Optionally remove label if section is empty.

### Concurrent Edits
**Issue**: Journal file modified during processing
**Handling**: Re-read file before editing, verify line still matches, retry once if mismatch, report if persistent.

### Partial Research
**Issue**: Some questions answered, others remain unclear
**Handling**: Mark as "Partial", keep label with note "Requires additional research on [specific aspect]".

---

## Command Invocation

**Format**: `/knowledge:process-needs-research`

**Arguments**: None (processes all pending entries)

**Execution Mode**: Direct research and synthesis (no agent delegation)

**Tools Used**:
- Brave Search for multi-source research
- Puppeteer for deep dives into specific sites
- Analysis tools for data processing (if needed)

**Expected Duration**: 10-30 minutes depending on queue size (3-8 minutes per entry for thorough research)

**Prerequisites**:
- Brave Search accessible
- Web tools (Puppeteer) functional
- Internet connection stable

**Post-Execution**:
- Review completion report
- Address any entries requiring clarification
- Verify new zettels integrate properly
- Act on recommendations as appropriate
