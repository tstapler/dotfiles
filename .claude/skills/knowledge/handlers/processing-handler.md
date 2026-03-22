# Processing Handler (Unified)

**Purpose**: Intelligently process `[[Needs Processing]]` tags by automatically detecting context and choosing the optimal approach: pure research, synthesis, or hybrid.

**Status**: Production-ready unified handler

**Integration**: Works as part of knowledge enrichment pipeline, replaces need to choose between `[[Needs Research]]` and `[[Needs Synthesis]]`

---

## Core Concept

**Problem Solved**: Users shouldn't need to decide between "research" vs "synthesis" when capturing knowledge. The system should detect context and choose the best approach.

**Approach Detection**:
```
Has rich context (URL, quotes, notes)?
├─ YES → Synthesis-focused (expand on what you consumed)
│   └─ But also research to fill gaps
│
└─ NO → Research-focused (discover from scratch)
    └─ But synthesize findings into evergreen note
```

---

## Handler Interface

### Input Parameters

```yaml
entry_content: string      # Full journal entry text
journal_date: string       # YYYY-MM-DD format
line_number: int          # Line number in journal file
file_path: string         # Absolute path to journal file
repo_path: string         # Repository root path
```

### Output Format

```yaml
status: "success|partial|failed"
pages_created:
  - "[[Topic Name]]"
pages_updated: []
issues: []
metadata:
  topic: string
  processing_approach: "research|synthesis|hybrid"
  context_indicators:
    has_urls: boolean
    has_quotes: boolean
    has_detailed_notes: boolean
    references_consumption: boolean
  sources_found: int
  word_count: int
```

---

## Processing Methodology

### Phase 1: Context Analysis

**Objective**: Analyze entry to determine what context is already available.

```python
def analyze_context(entry_content: str) -> dict:
    """
    Analyze journal entry for context indicators.

    Returns: {
        topic: str,
        urls: list[str],
        quotes: list[str],
        related_topics: list[str],
        has_detailed_notes: bool,
        references_consumption: bool,
        context_richness: float  # 0.0 to 1.0
    }
    """
    # Extract topic
    match = re.search(r'\[\[(.+?)\]\].*?\[\[Needs Processing\]\]', entry_content)
    topic = match.group(1) if match else None

    # Extract context elements
    urls = re.findall(r'https?://\S+', entry_content)
    quotes = re.findall(r'"([^"]+)"', entry_content)
    related_topics = [
        t for t in re.findall(r'\[\[([^\]]+)\]\]', entry_content)
        if t not in ['Needs Processing', 'TODO', 'DONE']
    ]

    # Detect consumption indicators
    consumption_keywords = [
        'reading', 'read', 'watched', 'watched',
        'listened', 'discussed', 'talking about',
        'learned', 'discovered', 'found out'
    ]
    references_consumption = any(
        keyword in entry_content.lower()
        for keyword in consumption_keywords
    )

    # Calculate context richness
    word_count = len(entry_content.split())
    has_detailed_notes = word_count > 30

    context_score = 0.0
    if urls:
        context_score += 0.3
    if quotes:
        context_score += 0.2
    if has_detailed_notes:
        context_score += 0.3
    if references_consumption:
        context_score += 0.2

    return {
        'topic': topic,
        'urls': urls,
        'quotes': quotes,
        'related_topics': related_topics,
        'has_detailed_notes': has_detailed_notes,
        'references_consumption': references_consumption,
        'context_richness': context_score
    }
```

**Context Indicators**:
- **URLs**: Direct links to articles, docs, videos
- **Quotes**: Extracted key insights or phrases
- **Related Topics**: Other [[Topic]] links mentioned
- **Detailed Notes**: Entry has >30 words beyond just the tag
- **Consumption Verbs**: "reading", "watched", "discussed", etc.

---

### Phase 2: Determine Processing Approach

**Objective**: Choose optimal processing strategy based on context analysis.

```python
def determine_approach(context: dict) -> str:
    """
    Determine processing approach based on context richness.

    Returns: "research" | "synthesis" | "hybrid"

    Decision Rules:
    - Research (0.0-0.3): Minimal context, focus on discovery
    - Hybrid (0.3-0.6): Some context, both research + expand
    - Synthesis (0.6-1.0): Rich context, focus on expansion
    """
    richness = context['context_richness']

    if richness >= 0.6:
        return 'synthesis'
    elif richness >= 0.3:
        return 'hybrid'
    else:
        return 'research'


def get_approach_strategy(approach: str) -> dict:
    """
    Define strategy for each approach type.
    """
    strategies = {
        'research': {
            'name': 'Pure Research',
            'description': 'Discover information from scratch',
            'primary_focus': 'web_search',
            'web_search_emphasis': 0.8,
            'context_expansion': 0.2,
            'output_style': 'reference_page',
            'min_sources': 3
        },
        'synthesis': {
            'name': 'Content Synthesis',
            'description': 'Expand on consumed content',
            'primary_focus': 'context_analysis',
            'web_search_emphasis': 0.3,
            'context_expansion': 0.7,
            'output_style': 'zettelkasten',
            'min_sources': 2  # URLs already provided + some research
        },
        'hybrid': {
            'name': 'Hybrid Research + Synthesis',
            'description': 'Research to fill gaps + expand context',
            'primary_focus': 'both',
            'web_search_emphasis': 0.5,
            'context_expansion': 0.5,
            'output_style': 'comprehensive',
            'min_sources': 3
        }
    }

    return strategies[approach]
```

**Approach Definitions**:

| Approach | Context Richness | Primary Focus | Output Style |
|----------|------------------|---------------|--------------|
| **Research** | 0.0 - 0.3 | Web search, external discovery | Reference page |
| **Hybrid** | 0.3 - 0.6 | Both research + context expansion | Comprehensive note |
| **Synthesis** | 0.6 - 1.0 | Expand on provided context | Zettelkasten note |

---

### Phase 3: Execute Processing

**Objective**: Gather information and create content based on chosen approach.

#### 3A: Research-Focused Processing

```python
def process_research_focused(topic: str, context: dict) -> dict:
    """
    Research-focused: Discover information from scratch.
    Primary tool: Web search
    """
    # Build comprehensive search query
    query = f'{topic} overview guide documentation'

    # Perform extensive web search
    search_results = web_search(query, count=10)

    # Read top sources
    sources = []
    for result in search_results[:5]:
        content = read_website(result['url'])
        sources.append({
            'url': result['url'],
            'title': result['title'],
            'content': content,
            'relevance': 'high'
        })

    # Analyze and synthesize
    analysis = {
        'overview': synthesize_overview(sources),
        'key_concepts': extract_key_concepts(sources),
        'practical_info': extract_practical_info(sources),
        'related_topics': identify_related_topics(sources)
    }

    return {
        'success': True,
        'approach': 'research',
        'sources': sources,
        'analysis': analysis,
        'context_used': 0.2  # Minimal context influence
    }
```

#### 3B: Synthesis-Focused Processing

```python
def process_synthesis_focused(topic: str, context: dict) -> dict:
    """
    Synthesis-focused: Expand on provided context.
    Primary tool: Context analysis + targeted research
    """
    sources = []

    # Start with provided URLs
    for url in context['urls']:
        content = read_website(url)
        sources.append({
            'url': url,
            'title': extract_title(content),
            'content': content,
            'relevance': 'primary'
        })

    # Targeted research to fill specific gaps
    gaps = identify_knowledge_gaps(context, sources)
    for gap in gaps:
        query = f'{topic} {gap}'
        results = web_search(query, count=3)
        for result in results[:2]:
            content = read_website(result['url'])
            sources.append({
                'url': result['url'],
                'title': result['title'],
                'content': content,
                'relevance': 'supporting'
            })

    # Expand on context
    analysis = {
        'core_insights': expand_on_quotes(context['quotes'], sources),
        'connections': find_connections(topic, context['related_topics']),
        'deeper_concepts': explore_deeper(topic, sources),
        'practical_applications': identify_applications(topic, sources)
    }

    return {
        'success': True,
        'approach': 'synthesis',
        'sources': sources,
        'analysis': analysis,
        'context_used': 0.7  # Heavy context influence
    }
```

#### 3C: Hybrid Processing

```python
def process_hybrid(topic: str, context: dict) -> dict:
    """
    Hybrid: Balance research discovery with context expansion.
    """
    sources = []

    # Use provided URLs first
    for url in context['urls']:
        content = read_website(url)
        sources.append({
            'url': url,
            'title': extract_title(content),
            'content': content,
            'relevance': 'context'
        })

    # Then research comprehensively
    query = f'{topic} guide overview'
    search_results = web_search(query, count=8)
    for result in search_results[:4]:
        content = read_website(result['url'])
        sources.append({
            'url': result['url'],
            'title': result['title'],
            'content': content,
            'relevance': 'research'
        })

    # Synthesize both perspectives
    analysis = {
        'foundation': synthesize_basics(sources),
        'context_insights': expand_context(context, sources),
        'comprehensive_view': merge_perspectives(sources),
        'practical_guide': create_practical_guide(topic, sources)
    }

    return {
        'success': True,
        'approach': 'hybrid',
        'sources': sources,
        'analysis': analysis,
        'context_used': 0.5  # Balanced
    }
```

---

### Phase 4: Create Page

**Objective**: Generate wiki page with format adapted to processing approach.

```python
def create_page(
    topic: str,
    processing_result: dict,
    approach: str,
    repo_path: str
) -> dict:
    """
    Create Logseq page with format adapted to approach.

    MANDATORY: All pages must include ## Sources section with ≥2 sources
    """
    page_content = generate_page_content(topic, processing_result, approach)

    # Validate sources before writing
    validation = validate_sources(page_content)
    if not validation['valid']:
        return {
            'success': False,
            'error': f"Source validation failed: {validation['reason']}"
        }

    # Write page
    page_path = Path(repo_path) / 'logseq' / 'pages' / f'{topic}.md'
    page_path.parent.mkdir(parents=True, exist_ok=True)

    with open(page_path, 'w', encoding='utf-8') as f:
        f.write(page_content)

    return {
        'success': True,
        'page_created': f'[[{topic}]]',
        'word_count': len(page_content.split()),
        'sources_count': validation['source_count']
    }


def generate_page_content(topic: str, result: dict, approach: str) -> str:
    """
    Generate page content with format adapted to approach.
    """
    analysis = result['analysis']
    sources = result['sources']

    # Common header
    content = f"""- # {topic}
- **Type**: [[Knowledge Note]] | [[{approach.title()} Processing]]
- **Processed**: {datetime.now().strftime('%Y-%m-%d')}
- **Approach**: {approach.title()}
- ---
"""

    # Approach-specific content
    if approach == 'research':
        content += generate_research_page(topic, analysis, sources)
    elif approach == 'synthesis':
        content += generate_synthesis_page(topic, analysis, sources)
    else:  # hybrid
        content += generate_hybrid_page(topic, analysis, sources)

    # MANDATORY: Sources section
    content += "\n- ---\n- ## Sources\n"
    for i, source in enumerate(sources, 1):
        content += f"\t- {i}. [{source['title']}]({source['url']})\n"

    # Related topics
    content += "\n- ---\n- ## Related Topics\n"
    related = result.get('related_topics', [])
    for topic_link in related:
        content += f"\t- [[{topic_link}]]\n"

    return content


def generate_research_page(topic: str, analysis: dict, sources: list) -> str:
    """Reference-style page for pure research."""
    return f"""- ## Overview
\t- {analysis['overview']}

- ## Key Concepts
{format_concepts(analysis['key_concepts'])}

- ## Practical Information
{format_practical(analysis['practical_info'])}
"""


def generate_synthesis_page(topic: str, analysis: dict, sources: list) -> str:
    """Zettelkasten-style page for synthesis."""
    return f"""- ## Core Insights
{format_insights(analysis['core_insights'])}

- ## Connections
{format_connections(analysis['connections'])}

- ## Deeper Exploration
{format_concepts(analysis['deeper_concepts'])}

- ## Practical Applications
{format_applications(analysis['practical_applications'])}
"""


def generate_hybrid_page(topic: str, analysis: dict, sources: list) -> str:
    """Comprehensive page for hybrid approach."""
    return f"""- ## Foundation
\t- {analysis['foundation']}

- ## Key Insights from Context
{format_insights(analysis['context_insights'])}

- ## Comprehensive Overview
{format_comprehensive(analysis['comprehensive_view'])}

- ## Practical Guide
{format_practical_guide(analysis['practical_guide'])}
"""
```

---

### Phase 5: Update Journal

**Objective**: Mark entry as processed with approach indicator.

```python
def mark_processing_complete(
    file_path: str,
    line_number: int,
    topic: str,
    approach: str,
    sources_count: int
) -> dict:
    """
    Replace [[Needs Processing]] with completion marker.

    Format variations by approach:
    - Research: "✓ Processed (Research) - 3 sources"
    - Synthesis: "✓ Processed (Synthesis) - expanded from article, 2 sources"
    - Hybrid: "✓ Processed (Hybrid) - comprehensive guide, 4 sources"
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        if 0 <= line_number < len(lines):
            line = lines[line_number]

            # Create completion marker based on approach
            markers = {
                'research': f'✓ Processed (Research) - {sources_count} sources [[Processed {datetime.now().strftime("%Y-%m-%d")}]]',
                'synthesis': f'✓ Processed (Synthesis) - expanded from content, {sources_count} sources [[Processed {datetime.now().strftime("%Y-%m-%d")}]]',
                'hybrid': f'✓ Processed (Hybrid) - comprehensive guide, {sources_count} sources [[Processed {datetime.now().strftime("%Y-%m-%d")}]]'
            }

            completion_marker = markers.get(approach, markers['research'])

            # Replace tag
            updated_line = line.replace(
                '[[Needs Processing]]',
                f'~~[[Needs Processing]]~~ {completion_marker}'
            )
            lines[line_number] = updated_line

        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(lines)

        return {'success': True}

    except Exception as e:
        return {'success': False, 'error': str(e)}
```

---

## Complete Handler Implementation

```python
#!/usr/bin/env python3
"""
Processing Handler (Unified)

Intelligently process [[Needs Processing]] tags with automatic approach detection.
"""

import re
from datetime import datetime
from pathlib import Path
from typing import Any


def handle_processing_request(
    entry_content: str,
    journal_date: str,
    line_number: int,
    file_path: str,
    repo_path: str
) -> dict[str, Any]:
    """
    Main handler for [[Needs Processing]] tags.

    Returns:
        {
            status: "success|partial|failed",
            pages_created: list[str],
            pages_updated: list[str],
            issues: list[str],
            metadata: dict
        }
    """
    issues = []

    # Phase 1: Analyze context
    context = analyze_context(entry_content)

    if not context['topic']:
        return {
            'status': 'failed',
            'pages_created': [],
            'pages_updated': [],
            'issues': ['Could not extract topic from entry'],
            'metadata': {}
        }

    topic = context['topic']

    # Phase 2: Determine approach
    approach = determine_approach(context)
    strategy = get_approach_strategy(approach)

    # Phase 3: Execute processing
    if approach == 'research':
        result = process_research_focused(topic, context)
    elif approach == 'synthesis':
        result = process_synthesis_focused(topic, context)
    else:  # hybrid
        result = process_hybrid(topic, context)

    if not result['success']:
        return {
            'status': 'failed',
            'pages_created': [],
            'pages_updated': [],
            'issues': ['Processing failed during execution'],
            'metadata': {}
        }

    # Phase 4: Create page
    page_result = create_page(topic, result, approach, repo_path)

    if not page_result['success']:
        return {
            'status': 'failed',
            'pages_created': [],
            'pages_updated': [],
            'issues': [page_result.get('error', 'Page creation failed')],
            'metadata': {}
        }

    # Phase 5: Mark complete
    mark_result = mark_processing_complete(
        file_path,
        line_number,
        topic,
        approach,
        page_result['sources_count']
    )

    if not mark_result['success']:
        issues.append(f"Failed to update journal: {mark_result.get('error')}")

    return {
        'status': 'success' if not issues else 'partial',
        'pages_created': [page_result['page_created']],
        'pages_updated': [],
        'issues': issues,
        'metadata': {
            'topic': topic,
            'processing_approach': approach,
            'strategy_used': strategy['name'],
            'context_indicators': {
                'has_urls': bool(context['urls']),
                'has_quotes': bool(context['quotes']),
                'has_detailed_notes': context['has_detailed_notes'],
                'references_consumption': context['references_consumption'],
                'context_richness': context['context_richness']
            },
            'sources_found': page_result['sources_count'],
            'word_count': page_result['word_count']
        }
    }


# Implementation functions from above...
# (analyze_context, determine_approach, process_*, create_page, etc.)
```

---

## Example Scenarios

### Example 1: Pure Research (No Context)

**Input**:
```markdown
- [[Dating Ball Glass Jars]] [[Needs Processing]]
```

**Context Analysis**:
```yaml
urls: []
quotes: []
detailed_notes: false
references_consumption: false
context_richness: 0.0
```

**Approach**: Research (0.0 richness)

**Processing**:
1. Web search: "Dating Ball Glass Jars overview guide"
2. Read top 5 sources (Minnetrista, wikiHow, Taste of Home, etc.)
3. Synthesize into reference page
4. Create with logo charts, identification tips

**Output**: Reference page with 5 sources

**Journal Update**:
```markdown
- ~~[[Dating Ball Glass Jars]]~~ [[Dating Ball Glass Jars]] ✓ Processed (Research) - 5 sources [[Processed 2026-01-09]]
```

---

### Example 2: Rich Synthesis (Strong Context)

**Input**:
```markdown
- Reading about [[Unix Philosophy]] https://homepage.cs.uri.edu/~thenry/resources/unix_art/ch01s06.html

Key insight from article: "Write programs that do one thing and do it well. Write programs to work together."

This connects to [[Microservices]], [[Single Responsibility Principle]], and [[Composition Over Inheritance]]. [[Needs Processing]]
```

**Context Analysis**:
```yaml
urls: ['https://homepage.cs.uri.edu/...']
quotes: ['Write programs that do one thing...']
detailed_notes: true (>30 words)
references_consumption: true ('Reading about')
related_topics: ['Microservices', 'Single Responsibility Principle', 'Composition Over Inheritance']
context_richness: 1.0
```

**Approach**: Synthesis (1.0 richness)

**Processing**:
1. Read provided URL thoroughly
2. Targeted research on specific gaps (history, modern applications)
3. Expand on quoted insights
4. Connect to related topics in knowledge graph
5. Create Zettelkasten-style note

**Output**: Zettelkasten note with connections, 3 sources (URL + 2 supporting)

**Journal Update**:
```markdown
- ~~Reading about [[Unix Philosophy]]...~~ ✓ Processed (Synthesis) - expanded from article, 3 sources [[Processed 2026-01-09]]
```

---

### Example 3: Hybrid (Partial Context)

**Input**:
```markdown
- [[PostgreSQL MVCC]] https://wiki.postgresql.org/wiki/MVCC [[Needs Processing]]
```

**Context Analysis**:
```yaml
urls: ['https://wiki.postgresql.org/wiki/MVCC']
quotes: []
detailed_notes: false
references_consumption: false
context_richness: 0.3
```

**Approach**: Hybrid (0.3 richness)

**Processing**:
1. Read provided URL (Wikipedia)
2. Research additional perspectives (official docs, tutorials, blog posts)
3. Synthesize comprehensive view
4. Include both foundational info and practical applications

**Output**: Comprehensive note, 5 sources (wiki + 4 research)

**Journal Update**:
```markdown
- ~~[[PostgreSQL MVCC]] https://...~~ ✓ Processed (Hybrid) - comprehensive guide, 5 sources [[Processed 2026-01-09]]
```

---

## Quality Assurance

### Source Requirements (MANDATORY)

**ALL approaches must include ≥2 sources in "## Sources" section.**

| Approach | Minimum Sources | Source Mix |
|----------|----------------|------------|
| Research | 3+ | All from web search |
| Synthesis | 2+ | Provided URLs + targeted research |
| Hybrid | 3+ | Provided URLs + comprehensive research |

### Validation Rules

Same as research-handler:
- ✅ Has "## Sources" section
- ✅ ≥2 sources documented
- ✅ Real URLs (not placeholders)
- ✅ Markdown link format: `[Title](URL)`

---

## Integration with Orchestrator

```python
# In knowledge enrichment orchestrator
if '[[Needs Processing]]' in entry_content:
    result = handle_processing_request(
        entry_content=entry_content,
        journal_date=journal_date,
        line_number=line_number,
        file_path=file_path,
        repo_path=repo_path
    )

    if result['status'] == 'success':
        metadata = result['metadata']
        log_success(
            f"Processed: {metadata['topic']} "
            f"({metadata['processing_approach']}) - "
            f"{metadata['sources_found']} sources"
        )
        log_info(f"Context richness: {metadata['context_indicators']['context_richness']:.1f}")
    else:
        log_error(f"Processing failed: {result['issues']}")
```

---

## Advantages Over Separate Tags

1. **✅ Zero user decision required** - Just add `[[Needs Processing]]`
2. **✅ Handles edge cases automatically** - Hybrid approach for partial context
3. **✅ Consistent quality** - All approaches produce well-sourced pages
4. **✅ Adaptive output** - Format matches the approach taken
5. **✅ Clear reporting** - Journal update shows which approach was used
6. **✅ Lower cognitive load** - One tag to remember

---

## Migration Notes

### Backward Compatibility

Old tags continue to work:
- `[[Needs Research]]` → research-handler.md
- `[[Needs Synthesis]]` → synthesis-handler.md
- `[[Needs Processing]]` → processing-handler.md (NEW)

Users can use either old-style explicit tags OR new unified tag.

### Gradual Migration

No forced migration required. Users can:
1. Start using `[[Needs Processing]]` for new entries
2. Keep using old tags if they prefer explicit control
3. Gradually migrate old tags over time (or never)

---

## Testing

```python
TEST_CASES = [
    {
        'entry': '- [[Topic]] [[Needs Processing]]',
        'expected_approach': 'research',
        'expected_sources': 3
    },
    {
        'entry': '- Reading [[Topic]] https://... "quote" detailed notes here [[Needs Processing]]',
        'expected_approach': 'synthesis',
        'expected_sources': 2
    },
    {
        'entry': '- [[Topic]] https://url.com [[Needs Processing]]',
        'expected_approach': 'hybrid',
        'expected_sources': 3
    }
]
```