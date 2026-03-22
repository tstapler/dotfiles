# Research Handler

**Purpose**: Process [[Needs Research]] tags from journal entries by conducting comprehensive research and creating detailed reference pages.

**Status**: Production-ready handler for knowledge enrichment orchestrator

**Integration**: Works as part of knowledge enrichment pipeline

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
  research_type: "product|concept|technical|general"
  sources_found: int
  has_images: boolean
  word_count: int
```

---

## Processing Methodology

### Phase 1: Identify Research Topic

Extract what needs research from the entry:

```python
def extract_research_topic(entry_content: str) -> dict:
    """
    Extract research topic from entry.

    Patterns:
    1. Product research: "Research [[Product X]] [[Needs Research]]"
    2. Technical concept: "[[Technical Topic]] [[Needs Research]]"
    3. How-to: "How to do X [[Needs Research]]"
    4. Question form: "What is X? [[Needs Research]]"
    """
    # Pattern 1: Topic in brackets
    match = re.search(r'\[\[(.+?)\]\].*?\[\[Needs Research\]\]', entry_content)
    if match:
        topic = match.group(1)
        return {
            'topic': topic,
            'type': classify_research_type(topic, entry_content),
            'context': entry_content
        }

    # Pattern 2: Question form
    match = re.search(r'(What|How|Why|When|Where)\s+(.+?)\?.*?\[\[Needs Research\]\]',
                     entry_content, re.IGNORECASE)
    if match:
        return {
            'topic': match.group(2).strip(),
            'type': 'question',
            'question_type': match.group(1).lower(),
            'context': entry_content
        }

    return {'topic': None, 'type': 'unknown'}


def classify_research_type(topic: str, context: str) -> str:
    """
    Classify type of research needed.

    Types:
    - product: Brand names, model numbers, specific products
    - technical: Programming, engineering, scientific concepts
    - conceptual: Abstract ideas, theories, frameworks
    - how-to: Process, procedure, tutorial
    - general: Everything else
    """
    # Product indicators
    product_patterns = [
        r'\b\d{3,}\b',  # Model numbers
        r'[A-Z]{2,}\s*\d+',  # Model codes like "AOU12RLS2"
        r'(Model|Version|v\d)',
        r'(Inc\.|LLC|Corp)'
    ]
    for pattern in product_patterns:
        if re.search(pattern, topic + ' ' + context):
            return 'product'

    # Technical indicators
    technical_terms = ['API', 'algorithm', 'protocol', 'function', 'class',
                       'database', 'programming', 'compiler']
    if any(term.lower() in (topic + ' ' + context).lower() for term in technical_terms):
        return 'technical'

    # How-to indicators
    if re.search(r'\bhow\s+to\b', context, re.IGNORECASE):
        return 'how-to'

    return 'general'
```

### Phase 2: Conduct Research

Perform web search and gather information:

```python
def conduct_research(topic: str, research_type: str, context: str) -> dict:
    """
    Conduct research using web search and analysis.

    Returns: {
        success: bool,
        sources: list[dict],  # {url, title, snippet}
        summary: str,
        key_facts: list[str],
        images: list[str]
    }
    """
    # Build search query based on type
    query = build_search_query(topic, research_type, context)

    # Perform web search
    # (Uses Claude's WebSearch tool or mcp__brave-search)
    search_results = perform_web_search(query, max_results=10)

    # Analyze and synthesize findings
    analysis = analyze_search_results(search_results, topic, research_type)

    return {
        'success': True,
        'sources': search_results[:5],  # Top 5 sources
        'summary': analysis['summary'],
        'key_facts': analysis['key_facts'],
        'images': extract_images(search_results),
        'metadata': {
            'search_query': query,
            'results_found': len(search_results),
            'research_date': datetime.now().isoformat()
        }
    }


def build_search_query(topic: str, research_type: str, context: str) -> str:
    """
    Build optimized search query based on research type.
    """
    if research_type == 'product':
        # Add qualifiers for product research
        return f'"{topic}" specifications reviews comparison'
    elif research_type == 'technical':
        return f'"{topic}" documentation tutorial examples'
    elif research_type == 'how-to':
        return f'how to {topic} guide step-by-step'
    else:
        return topic
```

### Phase 3: Create Research Page

Generate comprehensive reference page:

```python
def create_research_page(
    topic: str,
    research_data: dict,
    research_type: str,
    repo_path: str
) -> dict:
    """
    Create Logseq page with research findings.

    Page structure:
    - tags:: [[Research]], [[Topic Category]]
    - category:: Reference

    # Topic Name

    ## Overview
    [Summary from research]

    ## Key Information
    [Bulleted facts and findings]

    ## Specifications (for products)
    [Technical specs if applicable]

    ## How-To Guide (for procedures)
    [Step-by-step if applicable]

    ## Sources
    - [Source 1](url)
    - [Source 2](url)

    ## Related Topics
    - [[Related Topic 1]]
    - [[Related Topic 2]]
    """
    page_content = generate_page_content(topic, research_data, research_type)

    # Write to pages directory
    page_path = Path(repo_path) / 'logseq' / 'pages' / f'{topic}.md'

    try:
        page_path.parent.mkdir(parents=True, exist_ok=True)
        with open(page_path, 'w', encoding='utf-8') as f:
            f.write(page_content)

        return {
            'success': True,
            'page_created': f'[[{topic}]]',
            'word_count': len(page_content.split())
        }

    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


def generate_page_content(topic: str, research_data: dict, research_type: str) -> str:
    """Generate formatted Logseq page content."""
    category = get_category_for_type(research_type)

    content = f"""tags:: [[Research]], [[{category}]]
category:: Reference
research_date:: {research_data['metadata']['research_date']}

# {topic}

## Overview

{research_data['summary']}

## Key Information

{format_key_facts(research_data['key_facts'])}

"""

    # Add type-specific sections
    if research_type == 'product':
        content += """## Specifications

[Add specific product specs here]

"""

    if research_type == 'how-to':
        content += """## Step-by-Step Guide

1. [Step 1]
2. [Step 2]
3. [Step 3]

"""

    # Sources section
    content += f"""## Sources

{format_sources(research_data['sources'])}

## Related Topics

{extract_related_topics(research_data)}
"""

    return content


def format_key_facts(facts: list[str]) -> str:
    """Format key facts as bulleted list."""
    return '\n'.join(f'- {fact}' for fact in facts)


def format_sources(sources: list[dict]) -> str:
    """Format sources as numbered markdown links."""
    return '\n'.join(
        f'{i+1}. [{source["title"]}]({source["url"]})'
        for i, source in enumerate(sources)
    )
```

### Phase 4: Update Journal

Mark research as complete:

```python
def mark_research_complete(
    file_path: str,
    line_number: int,
    topic: str
) -> dict:
    """
    Replace [[Needs Research]] with completion marker.
    Format: ~~[[Needs Research]]~~ ✓ Researched - [summary]
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        if 0 <= line_number < len(lines):
            line = lines[line_number]
            # Replace with completion marker
            updated_line = line.replace(
                '[[Needs Research]]',
                f'~~[[Needs Research]]~~ ✓ Researched - comprehensive guide created'
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
Research Handler

Process [[Needs Research]] tags by conducting research and creating reference pages.
"""

import re
from datetime import datetime
from pathlib import Path
from typing import Any


def handle_research_request(
    entry_content: str,
    journal_date: str,
    line_number: int,
    file_path: str,
    repo_path: str
) -> dict[str, Any]:
    """
    Main handler for [[Needs Research]] tags.

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

    # Phase 1: Extract research topic
    topic_info = extract_research_topic(entry_content)

    if not topic_info.get('topic'):
        return {
            'status': 'failed',
            'pages_created': [],
            'pages_updated': [],
            'issues': ['Could not determine research topic'],
            'metadata': {}
        }

    topic = topic_info['topic']
    research_type = topic_info.get('type', 'general')

    # Phase 2: Conduct research
    research_data = conduct_research(topic, research_type, entry_content)

    if not research_data['success']:
        return {
            'status': 'failed',
            'pages_created': [],
            'pages_updated': [],
            'issues': ['Research failed'],
            'metadata': {}
        }

    # Phase 3: Create research page
    page_result = create_research_page(topic, research_data, research_type, repo_path)

    if not page_result['success']:
        return {
            'status': 'failed',
            'pages_created': [],
            'pages_updated': [],
            'issues': [page_result.get('error', 'Page creation failed')],
            'metadata': {}
        }

    # Phase 4: Mark complete
    mark_result = mark_research_complete(file_path, line_number, topic)
    if not mark_result['success']:
        issues.append(f"Failed to update journal: {mark_result.get('error')}")

    return {
        'status': 'success' if not issues else 'partial',
        'pages_created': [page_result['page_created']],
        'pages_updated': [],
        'issues': issues,
        'metadata': {
            'topic': topic,
            'research_type': research_type,
            'sources_found': len(research_data['sources']),
            'has_images': len(research_data.get('images', [])) > 0,
            'word_count': page_result.get('word_count', 0)
        }
    }


# Implementation functions from above...
# (extract_research_topic, classify_research_type, etc.)
```

---

## Research Type Examples

### Product Research

```
Input: "Research [[Fireplace Dampers]] [[Needs Research]]"
Output:
- Searches for product specifications
- Compares different types/brands
- Includes pricing and availability
- Links to manufacturer websites
```

### Technical Research

```
Input: "[[PostgreSQL MVCC]] [[Needs Research]]"
Output:
- Technical documentation
- How it works
- Common use cases
- Best practices
- Example code
```

### How-To Research

```
Input: "How to fix slipping thumb turn [[Needs Research]]"
Output:
- Step-by-step guide
- Tools required
- Safety considerations
- Troubleshooting tips
- Visual diagrams (if available)
```

---

## Integration with Orchestrator

```python
if '[[Needs Research]]' in entry_content:
    result = handle_research_request(
        entry_content=entry_content,
        journal_date=journal_date,
        line_number=line_number,
        file_path=file_path,
        repo_path=repo_path
    )

    if result['status'] == 'success':
        log_success(f"Researched: {result['metadata']['topic']}")
        log_info(f"Found {result['metadata']['sources_found']} sources")
    else:
        log_error(f"Research failed: {result['issues']}")
```

---

## Quality Assurance

### Source Validation (MANDATORY)

**CRITICAL REQUIREMENT**: All research pages MUST include a "## Sources" section with minimum 2 documented sources. Pages without sources will FAIL validation.

#### Minimum Requirements
- **Minimum 2 sources** (3+ preferred)
- Sources must be in dedicated "## Sources" section
- Sources must use markdown link format: `[Title](URL)`
- Sources must be real URLs, not placeholders like `[Source 1](url)`
- Sources must be numbered or bulleted

#### Source Quality Standards
- Prefer authoritative sources (.edu, .gov, official docs, established sites)
- Verify information across multiple sources
- Date-check for currency (especially technical info)
- Include diverse perspectives
- Document ALL tools used:
  - Web search queries (Brave Search, WebSearch, etc.)
  - Websites read (mcp__read-website-fast__read_website, WebFetch)
  - APIs accessed

#### Valid Sources Section Example
```markdown
## Sources

1. [How to Date a Ball Jar — Minnetrista](https://www.minnetrista.net/blog/blog/2013/06/27/ball-family-history/how-to-date-a-ball-jar)
2. [How to Date Old Ball Mason Jars - wikiHow](https://www.wikihow.com/Date-Old-Ball-Mason-Jars)
3. [Ball Mason Jar Age Chart - Taste of Home](https://www.tasteofhome.com/article/ball-mason-jar-age-chart/)
```

#### Invalid Examples (Will Fail Validation)
```markdown
# Missing section entirely
[no sources section]

# Wrong section name
## Resources
- Link 1

# Placeholder URLs
## Sources
- [Source 1](url)
- [Source 2](url)

# Only 1 source (minimum 2 required)
## Sources
1. [Single Source](https://example.com)
```

### Content Quality
- Minimum 2 reliable sources (MANDATORY - validated)
- Clear, concise summaries
- Proper attribution with specific page/line references
- Actionable information
- Document research methodology (what tools were used)

---

## Error Handling

1. **No search results**: Broaden query, try alternative terms
2. **Low-quality sources**: Filter by domain authority
3. **Conflicting information**: Note discrepancies, cite both
4. **Research timeout**: Save partial results, mark for review

---

## Testing

```python
TEST_CASES = [
    {
        'entry': '- Research [[Fireplace Dampers]] [[Needs Research]]',
        'expected_type': 'product',
        'should_find_specs': True
    },
    {
        'entry': '- [[PostgreSQL Transaction Isolation]] [[Needs Research]]',
        'expected_type': 'technical',
        'should_include_examples': True
    },
    {
        'entry': '- How to install ceiling fan [[Needs Research]]',
        'expected_type': 'how-to',
        'should_have_steps': True
    }
]
```
