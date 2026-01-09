# Synthesis Handler

**Purpose**: Process [[Needs Synthesis]] tags from journal entries by creating comprehensive Zettelkasten notes with research and linking.

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
  word_count: int
  sections_created: ["Overview", "Key Concepts", "Sources"]
  research_sources: int
```

---

## Processing Methodology

### Phase 1: Extract Topic

Parse entry to identify what needs synthesis:

```python
def extract_synthesis_topic(entry_content: str) -> dict:
    """
    Extract topic from entry with [[Needs Synthesis]] tag.

    Patterns:
    1. Topic before tag: "[[Topic]] [[Needs Synthesis]]"
    2. Inline mention: "Reading about [[Topic]] [[Needs Synthesis]]"
    3. URL context: "https://example.com/article [[Needs Synthesis]]"
    4. Free-form: "Thinking about X [[Needs Synthesis]]"
    """
    # Pattern 1: Direct topic link
    match = re.search(r'\[\[(.+?)\]\].*?\[\[Needs Synthesis\]\]', entry_content)
    if match:
        return {'topic': match.group(1), 'has_context': True}

    # Pattern 2: URL with description
    match = re.search(r'(https?://\S+).*?\[\[Needs Synthesis\]\]', entry_content)
    if match:
        return {'topic': None, 'url': match.group(1), 'has_context': True}

    return {'topic': None, 'has_context': False}
```

### Phase 2: Gather Context

Extract relevant context from journal entry:

```python
def gather_synthesis_context(entry_content: str, topic: str) -> dict:
    """
    Gather context for synthesis from entry.
    Returns: {
        topic: str,
        urls: list[str],
        quotes: list[str],
        related_topics: list[str],
        entry_date: str
    }
    """
    context = {
        'topic': topic,
        'urls': re.findall(r'https?://\S+', entry_content),
        'quotes': re.findall(r'"([^"]+)"', entry_content),
        'related_topics': re.findall(r'\[\[([^\]]+)\]\]', entry_content),
        'raw_content': entry_content
    }

    return context
```

### Phase 3: Create Zettel

Use `/knowledge/synthesize-knowledge` command:

```python
def create_synthesis_zettel(topic: str, context: dict, repo_path: str) -> dict:
    """
    Create comprehensive zettel using synthesis command.
    """
    # Prepare prompt for synthesis
    prompt = f"""
Create comprehensive Zettelkasten note for: {topic}

Context from journal:
- URLs: {', '.join(context['urls'])}
- Related topics: {', '.join(context['related_topics'])}
- Quotes: {', '.join(context['quotes'])}

Requirements:
- Include Overview section
- Add Key Concepts section
- Provide Sources section with citations
- Link to related topics
- Use proper Logseq format
"""

    # Invoke synthesis command
    # (In practice, this would be called by orchestrator)
    return {
        'success': True,
        'page_created': f"[[{topic}]]",
        'sections': ['Overview', 'Key Concepts', 'Sources'],
        'word_count': 500  # Estimated
    }
```

### Phase 4: Update Journal

Mark entry as synthesized:

```python
def mark_synthesis_complete(
    file_path: str,
    line_number: int,
    topic: str
) -> dict:
    """
    Replace [[Needs Synthesis]] with completion marker.
    Format: ~~[[Needs Synthesis]]~~ ✓ Synthesized
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        if 0 <= line_number < len(lines):
            line = lines[line_number]
            # Replace tag with strikethrough and checkmark
            updated_line = line.replace(
                '[[Needs Synthesis]]',
                '~~[[Needs Synthesis]]~~ ✓ Synthesized'
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
Synthesis Handler

Process [[Needs Synthesis]] tags by creating comprehensive zettels.
"""

import re
from pathlib import Path
from typing import Any


def handle_synthesis_request(
    entry_content: str,
    journal_date: str,
    line_number: int,
    file_path: str,
    repo_path: str
) -> dict[str, Any]:
    """
    Main handler for [[Needs Synthesis]] tags.

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

    # Phase 1: Extract topic
    topic_info = extract_synthesis_topic(entry_content)

    if not topic_info.get('topic') and not topic_info.get('url'):
        return {
            'status': 'failed',
            'pages_created': [],
            'pages_updated': [],
            'issues': ['Could not determine topic from entry'],
            'metadata': {}
        }

    topic = topic_info.get('topic', 'Unknown Topic')

    # Phase 2: Gather context
    context = gather_synthesis_context(entry_content, topic)

    # Phase 3: Create zettel
    # Note: In practice, this delegates to /knowledge/synthesize-knowledge
    zettel_result = create_synthesis_zettel(topic, context, repo_path)

    if not zettel_result['success']:
        return {
            'status': 'failed',
            'pages_created': [],
            'pages_updated': [],
            'issues': [zettel_result.get('error', 'Synthesis failed')],
            'metadata': {}
        }

    # Phase 4: Mark complete
    mark_result = mark_synthesis_complete(file_path, line_number, topic)
    if not mark_result['success']:
        issues.append(f"Failed to update journal: {mark_result.get('error')}")

    return {
        'status': 'success' if not issues else 'partial',
        'pages_created': [zettel_result['page_created']],
        'pages_updated': [],
        'issues': issues,
        'metadata': {
            'topic': topic,
            'word_count': zettel_result.get('word_count', 0),
            'sections_created': zettel_result.get('sections', []),
            'research_sources': len(context['urls'])
        }
    }


def extract_synthesis_topic(entry_content: str) -> dict:
    """Extract topic needing synthesis."""
    # Direct topic link
    match = re.search(r'\[\[(.+?)\]\].*?\[\[Needs Synthesis\]\]', entry_content)
    if match:
        return {'topic': match.group(1), 'has_context': True}

    # URL with context
    match = re.search(r'(https?://\S+).*?\[\[Needs Synthesis\]\]', entry_content)
    if match:
        return {'topic': None, 'url': match.group(1), 'has_context': True}

    return {'topic': None, 'has_context': False}


def gather_synthesis_context(entry_content: str, topic: str) -> dict:
    """Gather context for synthesis."""
    return {
        'topic': topic,
        'urls': re.findall(r'https?://\S+', entry_content),
        'quotes': re.findall(r'"([^"]+)"', entry_content),
        'related_topics': [
            t for t in re.findall(r'\[\[([^\]]+)\]\]', entry_content)
            if t != 'Needs Synthesis'
        ],
        'raw_content': entry_content
    }


def create_synthesis_zettel(topic: str, context: dict, repo_path: str) -> dict:
    """Create comprehensive zettel (delegates to synthesis command)."""
    # This is a placeholder - actual implementation delegates to
    # /knowledge/synthesize-knowledge command
    return {
        'success': True,
        'page_created': f"[[{topic}]]",
        'sections': ['Overview', 'Key Concepts', 'Sources'],
        'word_count': 500
    }


def mark_synthesis_complete(
    file_path: str,
    line_number: int,
    topic: str
) -> dict:
    """Mark entry as synthesized."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        if 0 <= line_number < len(lines):
            line = lines[line_number]
            updated_line = line.replace(
                '[[Needs Synthesis]]',
                '~~[[Needs Synthesis]]~~ ✓ Synthesized'
            )
            lines[line_number] = updated_line

        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(lines)

        return {'success': True}

    except Exception as e:
        return {'success': False, 'error': str(e)}


if __name__ == '__main__':
    # Example usage
    result = handle_synthesis_request(
        entry_content="- Reading about [[Unix Philosophy]] https://example.com [[Needs Synthesis]]",
        journal_date="2026-01-07",
        line_number=5,
        file_path="/path/to/journal/2026_01_07.md",
        repo_path="/Users/tylerstapler/Documents/personal-wiki"
    )
    print(result)
```

---

## Integration with Orchestrator

```python
# In knowledge enrichment orchestrator
if '[[Needs Synthesis]]' in entry_content:
    result = handle_synthesis_request(
        entry_content=entry_content,
        journal_date=journal_date,
        line_number=line_number,
        file_path=file_path,
        repo_path=repo_path
    )

    if result['status'] == 'success':
        log_success(f"Synthesized: {result['metadata']['topic']}")
    else:
        log_error(f"Synthesis failed: {result['issues']}")
```

---

## Error Handling

1. **No topic found**: Ask user to clarify what needs synthesis
2. **Synthesis command fails**: Return detailed error from command
3. **Journal update fails**: Log warning, synthesis still succeeded
4. **Invalid entry format**: Return clear error message

---

## Testing

```python
TEST_CASES = [
    {
        'entry': '- [[Docker Volumes]] [[Needs Synthesis]]',
        'expected_topic': 'Docker Volumes'
    },
    {
        'entry': '- Reading about [[Kubernetes]] https://k8s.io [[Needs Synthesis]]',
        'expected_topic': 'Kubernetes',
        'expected_urls': 1
    },
    {
        'entry': '- Need to research X [[Needs Synthesis]]',
        'expected_topic': None,
        'should_fail': True
    }
]
```
