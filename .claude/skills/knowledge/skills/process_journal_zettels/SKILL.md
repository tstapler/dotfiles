---
description: Takes a journal entry, analyzes linked pages, and generates any missing
  or empty zettels using synthesize_knowledge process
prompt: "# Journal Entry Zettel Processing\n\nI'll analyze a journal entry, check\
  \ all linked pages, and generate comprehensive zettels for any missing or empty\
  \ pages using the same systematic approach as the synthesize_knowledge command.\n\
  \n## Process Overview\n\n### Phase 1: Journal Entry Analysis\nI'll examine the specified\
  \ journal entry to:\n- **Process [[Needs Processing]] tags**: Specifically look\
  \ for this tag and recursively process all child bullet points and nested content\
  \ to ensure full context is captured for synthesis.\n- Extract all page links `[[Page\
  \ Name]]` and references\n- **Identify implicit topics and concepts** mentioned\
  \ in the text that could benefit from dedicated zettels\n- **Analyze key terms,\
  \ technical concepts, and domain-specific terminology** that appear significant\n\
  - **Detect emerging themes, patterns, or repeated concepts** across the journal\
  \ entry\n- **Identify proper nouns, methodologies, frameworks, or tools** mentioned\
  \ that warrant documentation\n- **Spot decision points, insights, or conclusions**\
  \ that could become standalone knowledge pages\n- Note any incomplete thoughts or\
  \ areas needing expansion\n- Understand the context and connections being made\n\
  - Focus particularly on: ${2:-[any specified focus topic]}\n\n### Phase 2: Comprehensive\
  \ Topic Assessment\nFor both explicit links and identified implicit topics, I'll:\n\
  - **Explicit Links**: Check if pages exist in `~/Documents/personal-wiki/logseq/pages/`\n\
  - **Implicit Topics**: Determine which concepts warrant dedicated zettel pages\n\
  - **Content Evaluation**: Assess existing pages for completeness (empty, minimal,\
  \ or incomplete)\n- **Priority Assessment**: Rank topics by importance, frequency\
  \ of mention, and knowledge value\n- **Gap Analysis**: Identify missing connections\
  \ and knowledge gaps\n- **Conceptual Mapping**: Map relationships between all identified\
  \ concepts (explicit and implicit)\n- **Zettel Candidacy**: Evaluate which implicit\
  \ topics would add most value as standalone pages\n\n### Phase 3: Content Generation\
  \ Strategy\nUsing the synthesize_knowledge approach, I'll:\n- **mcp__brave-search__brave_web_search**:\
  \ Research each missing/incomplete topic for authoritative sources\n- **mcp__read-website-fast__read_website**:\
  \ Extract detailed information from relevant sources\n- **WebFetch**: Gather additional\
  \ context and perspectives\n- Plan comprehensive zettel structure for each missing\
  \ page\n- Design linking strategy that connects to existing knowledge\n\n### Phase\
  \ 4: Zettel Creation\nFor each missing, incomplete, or newly identified topic, I'll:\n\
  - **Create comprehensive Zettelkasten-formatted content** for both explicit links\
  \ and implicit topics\n- **Follow your CLAUDE.md guidelines and conventions** for\
  \ all generated content\n- **Include proper cross-references and bidirectional links**\
  \ connecting new pages to existing knowledge\n- **Add semantic tags for discoverability**\
  \ (#concepts, #tools, #methodologies, etc.)\n- **Create concept hierarchies** where\
  \ implicit topics relate to broader themes\n- **Establish connection pathways**\
  \ between journal insights and broader knowledge domains\n- **Ensure content integrates\
  \ with existing knowledge base** and enhances the overall network\n- **Save directly\
  \ to `~/Documents/personal-wiki/logseq/pages/` when possible**\n\n### Phase 5: Integration\
  \ and Linking\nFinally, I'll:\n- Update the original journal entry with enhanced\
  \ links if needed\n- Create supporting concept pages where beneficial\n- Establish\
  \ meaningful connections between new and existing content\n- Ensure all references\
  \ are properly formatted and functional\n- Verify the knowledge network adds value\n\
  \n## Usage Examples\n\n**Basic usage:**\n`/process_journal_zettels 2025_09_08`\n\
  \n**With focus topic:**\n`/process_journal_zettels 2025_09_08 \"database performance\"\
  `\n\n**Specific date format:**\n`/process_journal_zettels \"Sep 8th, 2025\" \"system\
  \ architecture\"`\n\n## Implementation Process\n\n### Step 1: Journal Entry Location\n\
  I'll look for the journal entry in:\n- `~/Documents/personal-wiki/logseq/journals/${1:-[journal_date]}.md`\n\
  - Common date formats: `YYYY_MM_DD.md`, `YYYY-MM-DD.md`\n- If not found, I'll search\
  \ the journals directory for matching dates\n\n### Step 2: Comprehensive Content\
  \ Analysis\nFor the journal entry `${1:-[journal_date]}`, I'll:\n- **Parse all `[[Page\
  \ Name]]` references** (explicit links)\n- **Recursively process [[Needs Processing]]\
  \ tags**: For any block tagged with `[[Needs Processing]]`, recursively extract\
  \ and analyze all child bullet points and nested content to maintain full context.\n\
  - **Extract any `#tags` that might need pages**\n- **Perform semantic analysis**\
  \ to identify implicit topics:\n  - Technical terms and jargon that appear significant\n\
  \  - Proper nouns (tools, frameworks, methodologies, people, companies)\n  - Decision\
  \ frameworks or mental models mentioned\n  - Insights, conclusions, or \"aha moments\"\
  \ worth preserving\n  - Recurring themes or concepts that span multiple entries\n\
  \  - Problem-solution pairs that could become case studies\n  - Questions or hypotheses\
  \ that warrant investigation\n- **Note any `TODO` items or incomplete thoughts**\n\
  - **Analyze writing patterns** to detect concepts the author finds important\n-\
  \ **Identify cross-cutting concerns** that appear across different contexts\n\n\
  ### Step 3: Research and Content Generation\nFor each missing/incomplete page AND\
  \ newly identified implicit topics, I'll apply the full synthesize_knowledge process:\n\
  - **Research topics comprehensively** using available MCP tools (including all content\
  \ recursively extracted from `[[Needs Processing]]` blocks)\n- **Analyze multiple\
  \ authoritative sources** to build robust understanding\n- **Synthesize information\
  \ into coherent, valuable content** that serves long-term knowledge goals\n- **Structure\
  \ content for maximum knowledge network value** with proper interconnections\n-\
  \ **Prioritize high-value implicit topics** that frequently appear or connect to\
  \ multiple domains\n- **Create foundational pages** for concepts that enable understanding\
  \ of other topics\n\n### Step 4: File Creation and Integration\n- **Primary**: Save\
  \ directly to `~/Documents/personal-wiki/logseq/pages/[Page Name].md`\n- **Fallback**:\
  \ Provide markdown content in code blocks with intended file paths\n- Ensure all\
  \ content follows Logseq/Zettelkasten best practices\n- Create meaningful connections\
  \ to existing knowledge\n\n## Expected Outcomes\n\nThis command will:\n- **Transform\
  \ incomplete journal references into comprehensive knowledge pages**\n- **Surface\
  \ and formalize implicit knowledge** from journal writing into structured zettels\n\
  - **Create a robust network of interconnected concepts** linking explicit and implicit\
  \ topics\n- **Fill knowledge gaps identified in your journaling** through both obvious\
  \ and subtle patterns\n- **Enhance the value of your personal knowledge system**\
  \ by capturing tacit insights\n- **Provide research-backed content for topics you're\
  \ exploring** including concepts you mention but haven't formally documented\n-\
  \ **Build conceptual bridges** between disparate ideas mentioned in journal entries\n\
  - **Preserve intellectual breadcrumbs** that might otherwise be lost in stream-of-consciousness\
  \ writing\n\n## Quality Standards\n\nAll generated zettels will:\n- Include authoritative\
  \ source information and references\n- Follow proper Zettelkasten linking conventions\n\
  - Integrate seamlessly with existing knowledge base\n- Provide actionable insights\
  \ and clear explanations\n- Include appropriate tags and cross-references\n- Be\
  \ structured for long-term knowledge value\n\nThe goal is to transform your journal\
  \ entries from simple notes into comprehensive knowledge resources that become more\
  \ valuable over time through their connections and research-backed content.\n\n\
  Usage: `/process_journal_zettels [journal_date] [optional_focus_topic]`\n"
---

# Journal Entry Zettel Processing

I'll analyze a journal entry, check all linked pages, and generate comprehensive zettels for any missing or empty pages using the same systematic approach as the synthesize_knowledge command.

## Process Overview

### Phase 1: Journal Entry Analysis
I'll examine the specified journal entry to:
- **Process [[Needs Processing]] tags**: Specifically look for this tag and recursively process all child bullet points and nested content to ensure full context is captured for synthesis.
- Extract all page links `[[Page Name]]` and references
- **Identify implicit topics and concepts** mentioned in the text that could benefit from dedicated zettels
- **Analyze key terms, technical concepts, and domain-specific terminology** that appear significant
- **Detect emerging themes, patterns, or repeated concepts** across the journal entry
- **Identify proper nouns, methodologies, frameworks, or tools** mentioned that warrant documentation
- **Spot decision points, insights, or conclusions** that could become standalone knowledge pages
- Note any incomplete thoughts or areas needing expansion
- Understand the context and connections being made
- Focus particularly on: ${2:-[any specified focus topic]}

### Phase 2: Comprehensive Topic Assessment
For both explicit links and identified implicit topics, I'll:
- **Explicit Links**: Check if pages exist in `~/Documents/personal-wiki/logseq/pages/`
- **Implicit Topics**: Determine which concepts warrant dedicated zettel pages
- **Content Evaluation**: Assess existing pages for completeness (empty, minimal, or incomplete)
- **Priority Assessment**: Rank topics by importance, frequency of mention, and knowledge value
- **Gap Analysis**: Identify missing connections and knowledge gaps
- **Conceptual Mapping**: Map relationships between all identified concepts (explicit and implicit)
- **Zettel Candidacy**: Evaluate which implicit topics would add most value as standalone pages

### Phase 3: Content Generation Strategy
Using the synthesize_knowledge approach, I'll:
- **mcp__brave-search__brave_web_search**: Research each missing/incomplete topic for authoritative sources
- **mcp__read-website-fast__read_website**: Extract detailed information from relevant sources
- **WebFetch**: Gather additional context and perspectives
- Plan comprehensive zettel structure for each missing page
- Design linking strategy that connects to existing knowledge

### Phase 4: Zettel Creation
For each missing, incomplete, or newly identified topic, I'll:
- **Create comprehensive Zettelkasten-formatted content** for both explicit links and implicit topics
- **Follow your CLAUDE.md guidelines and conventions** for all generated content
- **Include proper cross-references and bidirectional links** connecting new pages to existing knowledge
- **Add semantic tags for discoverability** (#concepts, #tools, #methodologies, etc.)
- **Create concept hierarchies** where implicit topics relate to broader themes
- **Establish connection pathways** between journal insights and broader knowledge domains
- **Ensure content integrates with existing knowledge base** and enhances the overall network
- **Save directly to `~/Documents/personal-wiki/logseq/pages/` when possible**

### Phase 5: Integration and Linking
Finally, I'll:
- Update the original journal entry with enhanced links if needed
- Create supporting concept pages where beneficial
- Establish meaningful connections between new and existing content
- Ensure all references are properly formatted and functional
- Verify the knowledge network adds value

## Usage Examples

**Basic usage:**
`/process_journal_zettels 2025_09_08`

**With focus topic:**
`/process_journal_zettels 2025_09_08 "database performance"`

**Specific date format:**
`/process_journal_zettels "Sep 8th, 2025" "system architecture"`

## Implementation Process

### Step 1: Journal Entry Location
I'll look for the journal entry in:
- `~/Documents/personal-wiki/logseq/journals/${1:-[journal_date]}.md`
- Common date formats: `YYYY_MM_DD.md`, `YYYY-MM-DD.md`
- If not found, I'll search the journals directory for matching dates

### Step 2: Comprehensive Content Analysis
For the journal entry `${1:-[journal_date]}`, I'll:
- **Parse all `[[Page Name]]` references** (explicit links)
- **Recursively process [[Needs Processing]] tags**: For any block tagged with `[[Needs Processing]]`, recursively extract and analyze all child bullet points and nested content to maintain full context.
- **Extract any `#tags` that might need pages**
- **Perform semantic analysis** to identify implicit topics:
  - Technical terms and jargon that appear significant
  - Proper nouns (tools, frameworks, methodologies, people, companies)
  - Decision frameworks or mental models mentioned
  - Insights, conclusions, or "aha moments" worth preserving
  - Recurring themes or concepts that span multiple entries
  - Problem-solution pairs that could become case studies
  - Questions or hypotheses that warrant investigation
- **Note any `TODO` items or incomplete thoughts**
- **Analyze writing patterns** to detect concepts the author finds important
- **Identify cross-cutting concerns** that appear across different contexts

### Step 3: Research and Content Generation
For each missing/incomplete page AND newly identified implicit topics, I'll apply the full synthesize_knowledge process:
- **Research topics comprehensively** using available MCP tools (including all content recursively extracted from `[[Needs Processing]]` blocks)
- **Analyze multiple authoritative sources** to build robust understanding
- **Synthesize information into coherent, valuable content** that serves long-term knowledge goals
- **Structure content for maximum knowledge network value** with proper interconnections
- **Prioritize high-value implicit topics** that frequently appear or connect to multiple domains
- **Create foundational pages** for concepts that enable understanding of other topics

### Step 4: File Creation and Integration
- **Primary**: Save directly to `~/Documents/personal-wiki/logseq/pages/[Page Name].md`
- **Fallback**: Provide markdown content in code blocks with intended file paths
- Ensure all content follows Logseq/Zettelkasten best practices
- Create meaningful connections to existing knowledge

## Expected Outcomes

This command will:
- **Transform incomplete journal references into comprehensive knowledge pages**
- **Surface and formalize implicit knowledge** from journal writing into structured zettels
- **Create a robust network of interconnected concepts** linking explicit and implicit topics
- **Fill knowledge gaps identified in your journaling** through both obvious and subtle patterns
- **Enhance the value of your personal knowledge system** by capturing tacit insights
- **Provide research-backed content for topics you're exploring** including concepts you mention but haven't formally documented
- **Build conceptual bridges** between disparate ideas mentioned in journal entries
- **Preserve intellectual breadcrumbs** that might otherwise be lost in stream-of-consciousness writing

## Quality Standards

All generated zettels will:
- Include authoritative source information and references
- Follow proper Zettelkasten linking conventions
- Integrate seamlessly with existing knowledge base
- Provide actionable insights and clear explanations
- Include appropriate tags and cross-references
- Be structured for long-term knowledge value

The goal is to transform your journal entries from simple notes into comprehensive knowledge resources that become more valuable over time through their connections and research-backed content.

Usage: `/process_journal_zettels [journal_date] [optional_focus_topic]`
