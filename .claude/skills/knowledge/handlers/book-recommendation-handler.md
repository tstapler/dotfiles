# Book Recommendation Handler

**Purpose**: Process [[Book Recommendation]] tags from journal entries by adding books to the library, enriching metadata, and generating wiki pages.

**Status**: Production-ready handler for knowledge enrichment orchestrator

**Integration**: Works with `book-sync` tool in `/Users/tylerstapler/Documents/personal-wiki`

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
  - "[[Book Title]]"
  - "[[Author Name]]"
pages_updated: []
issues: []  # List of error messages if any
metadata:
  book_id: string        # Book sync internal ID
  title: string
  author: string
  has_audiobook: boolean
  enrichment_sources: ["openlibrary", "audible"]
```

---

## Processing Methodology

### Phase 1: Extract Book Information

Parse the entry content to extract book title and author using these patterns:

**Pattern Recognition Order** (try each until match found):

1. **Bracketed with "by" Author**
   - Pattern: `[[Title by Author]]`
   - Example: `[[The Creative Act by Rick Rubin]] [[Book Recommendation]]`
   - Extract: Title = "The Creative Act", Author = "Rick Rubin"

2. **Quoted with "by" Author**
   - Pattern: `"Title" by Author`
   - Example: `"Atomic Habits" by James Clear [[Book Recommendation]]`
   - Extract: Title = "Atomic Habits", Author = "James Clear"

3. **Bracketed Title Only**
   - Pattern: `[[Title]]` (no "by" clause)
   - Example: `Read about [[Thinking, Fast and Slow]] [[Book Recommendation]]`
   - Extract: Title = "Thinking, Fast and Slow", Author = null
   - Action: Attempt to look up author from OpenLibrary

4. **Context-Rich Format**
   - Pattern: `Person recommended [[Title by Author]]`
   - Example: `David recommended [[Range by David Epstein]] [[Book Recommendation]]`
   - Extract: Title = "Range", Author = "David Epstein", Recommender = "David"

5. **Multiple Books in Entry**
   - Pattern: Multiple book references before `[[Book Recommendation]]`
   - Example: `[[Book 1]], [[Book 2]], and [[Book 3]] [[Book Recommendation]]`
   - Action: Process each book separately

**Parsing Algorithm**:

```python
def extract_book_info(entry_content: str) -> list[dict]:
    """
    Extract all book recommendations from entry.
    Returns list of {title, author, recommender, context}
    """
    books = []

    # Find all lines with [[Book Recommendation]]
    lines = entry_content.split('\n')
    for line in lines:
        if '[[Book Recommendation]]' not in line:
            continue

        # Remove the tag for cleaner parsing
        text = line.replace('[[Book Recommendation]]', '').strip()

        # Try Pattern 1: [[Title by Author]]
        match = re.search(r'\[\[(.+?)\s+by\s+(.+?)\]\]', text)
        if match:
            books.append({
                'title': match.group(1).strip(),
                'author': match.group(2).strip(),
                'context': text
            })
            continue

        # Try Pattern 2: "Title" by Author
        match = re.search(r'"(.+?)"\s+by\s+(.+?)(?:\s|$|\[)', text)
        if match:
            books.append({
                'title': match.group(1).strip(),
                'author': match.group(2).strip(),
                'context': text
            })
            continue

        # Try Pattern 3: [[Title]] only
        matches = re.findall(r'\[\[(.+?)\]\]', text)
        for title in matches:
            # Skip if it looks like a tag (all caps, common tags)
            if title.isupper() or title in ['Book Recommendation', 'TODO', 'DONE']:
                continue

            books.append({
                'title': title.strip(),
                'author': None,  # Will try to look up
                'context': text
            })

    return books
```

**Edge Cases to Handle**:
- Books with subtitles: "Title: Subtitle by Author" → Title = "Title: Subtitle"
- Multiple authors: "by Author 1 and Author 2" → Author = "Author 1 and Author 2"
- Series notation: "Book Title (Series #1) by Author" → Extract cleanly
- Articles in titles: "The Book", "A Book" → Preserve articles
- Non-English characters: Unicode support required
- Empty/malformed entries: Return empty list, log warning

---

### Phase 2: Check for Existing Books

Before adding a book, check if it already exists in the library to avoid duplicates.

**Duplicate Detection Strategy**:

```bash
# Get list of all books in library
uv run book-sync list --format json > /tmp/books.json

# Check for duplicates using fuzzy matching
# - Exact title match (case-insensitive)
# - Levenshtein distance < 3 for titles
# - Author last name match
```

**Duplicate Scenarios**:

1. **Exact Match**: Same title and author → Skip, report as already exists
2. **Title Match, Different Author**: Likely different book → Add as new
3. **Similar Title (fuzzy match)**: Ask for confirmation or auto-add with note
4. **Same Author, Different Title**: Different book → Add as new

**Implementation**:

```python
def check_for_duplicates(title: str, author: str | None) -> dict:
    """
    Check if book already exists in library.
    Returns: {exists: bool, existing_book: dict | None, confidence: float}
    """
    # Run book-sync list command
    result = subprocess.run(
        ['uv', 'run', 'book-sync', 'list', '--format', 'json'],
        capture_output=True,
        text=True,
        cwd=repo_path
    )

    if result.returncode != 0:
        return {'exists': False, 'error': result.stderr}

    books = json.loads(result.stdout)

    # Check for exact match
    for book in books:
        if normalize_title(book['title']) == normalize_title(title):
            if author is None or normalize_author(book['author']) == normalize_author(author):
                return {
                    'exists': True,
                    'existing_book': book,
                    'confidence': 1.0,
                    'match_type': 'exact'
                }

    # Check for fuzzy match
    for book in books:
        similarity = calculate_similarity(title, book['title'])
        if similarity > 0.85:  # 85% threshold
            return {
                'exists': True,
                'existing_book': book,
                'confidence': similarity,
                'match_type': 'fuzzy'
            }

    return {'exists': False}

def normalize_title(title: str) -> str:
    """Normalize title for comparison."""
    # Remove articles, lowercase, strip whitespace
    title = title.lower().strip()
    for article in ['the ', 'a ', 'an ']:
        if title.startswith(article):
            title = title[len(article):]
    return title

def normalize_author(author: str) -> str:
    """Extract and normalize author last name."""
    # "First Last" → "last"
    return author.split()[-1].lower().strip()
```

---

### Phase 3: Add Book to Library

Add the book using `book-sync add` command with appropriate flags.

**Command Construction**:

```bash
# Basic add with title and author
uv run book-sync add --title "Book Title" --author "Author Name"

# Add with additional metadata (if available from parsing)
uv run book-sync add \
  --title "Book Title" \
  --author "Author Name" \
  --notes "Recommended by [Person] on [Date]"
```

**Implementation**:

```python
def add_book_to_library(
    title: str,
    author: str | None,
    context: str,
    journal_date: str
) -> dict:
    """
    Add book to library using book-sync.
    Returns: {success: bool, book_id: str | None, error: str | None}
    """
    cmd = ['uv', 'run', 'book-sync', 'add', '--title', title]

    if author:
        cmd.extend(['--author', author])

    # Add note about where recommendation came from
    note = f"Recommended in journal entry on {journal_date}"
    if context:
        # Extract recommender if present
        recommender_match = re.search(r'(\w+)\s+recommended', context, re.IGNORECASE)
        if recommender_match:
            note = f"Recommended by {recommender_match.group(1)} on {journal_date}"

    cmd.extend(['--notes', note])

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=repo_path
    )

    if result.returncode != 0:
        return {
            'success': False,
            'error': f"Failed to add book: {result.stderr}"
        }

    # Parse book ID from output
    # Expected output: "Added book: {book_id}"
    match = re.search(r'Added book:\s*(\S+)', result.stdout)
    book_id = match.group(1) if match else None

    return {
        'success': True,
        'book_id': book_id
    }
```

**Error Handling**:
- Missing title: Cannot proceed, return error
- Missing author: Proceed with title only, attempt lookup in Phase 4
- Command failure: Log full error, return partial status
- Invalid characters in title/author: Sanitize before passing to command

---

### Phase 4: Enrich with Metadata

Automatically enrich the book with metadata from OpenLibrary and Audible.

**Enrichment Strategy**:

```bash
# First: OpenLibrary (adds ISBN, publication date, page count, etc.)
uv run book-sync enrich openlibrary

# Second: Audible (checks for audiobook availability)
uv run book-sync enrich audible
```

**Why This Order**:
1. OpenLibrary provides foundational metadata (ISBN, official title, etc.)
2. Audible uses ISBN from OpenLibrary for better matching
3. OpenLibrary is more reliable for basic metadata

**Implementation**:

```python
def enrich_book_metadata(book_id: str) -> dict:
    """
    Enrich book with metadata from OpenLibrary and Audible.
    Returns: {
        success: bool,
        openlibrary_success: bool,
        audible_success: bool,
        errors: list[str]
    }
    """
    errors = []

    # Enrich with OpenLibrary
    result = subprocess.run(
        ['uv', 'run', 'book-sync', 'enrich', 'openlibrary'],
        capture_output=True,
        text=True,
        cwd=repo_path,
        timeout=30  # Prevent hanging
    )

    openlibrary_success = result.returncode == 0
    if not openlibrary_success:
        errors.append(f"OpenLibrary enrichment failed: {result.stderr}")

    # Enrich with Audible
    result = subprocess.run(
        ['uv', 'run', 'book-sync', 'enrich', 'audible'],
        capture_output=True,
        text=True,
        cwd=repo_path,
        timeout=60  # Audible can be slow
    )

    audible_success = result.returncode == 0
    if not audible_success:
        errors.append(f"Audible enrichment failed: {result.stderr}")

    # Consider partial success if at least one source worked
    success = openlibrary_success or audible_success

    return {
        'success': success,
        'openlibrary_success': openlibrary_success,
        'audible_success': audible_success,
        'errors': errors if errors else []
    }
```

**Enrichment Failure Handling**:
- OpenLibrary fails: Continue to Audible, mark as partial success
- Audible fails: Not critical, book is still added with OpenLibrary data
- Both fail: Still return success for book addition, note enrichment failures
- Timeout: Log warning, continue processing

**Metadata Quality Checks**:
- If author was missing and OpenLibrary found it: Update book record
- If title differs slightly: Log for manual review
- If no ISBN found: Flag for manual enrichment later

---

### Phase 5: Generate Wiki Page

Generate a comprehensive Logseq wiki page for the book.

**Wiki Generation Command**:

```bash
# Generate pages for all books (idempotent)
uv run book-sync wiki generate
```

**Implementation**:

```python
def generate_wiki_pages() -> dict:
    """
    Generate Logseq wiki pages for all books.
    Returns: {success: bool, pages_created: list[str], error: str | None}
    """
    result = subprocess.run(
        ['uv', 'run', 'book-sync', 'wiki', 'generate'],
        capture_output=True,
        text=True,
        cwd=repo_path
    )

    if result.returncode != 0:
        return {
            'success': False,
            'error': f"Wiki generation failed: {result.stderr}"
        }

    # Parse output to find created pages
    # Expected output: "Created page: [[Book Title]]"
    pages = re.findall(r'Created page:\s*\[\[(.+?)\]\]', result.stdout)

    return {
        'success': True,
        'pages_created': [f"[[{page}]]" for page in pages]
    }
```

**Wiki Page Structure** (generated by book-sync):

```markdown
---
title: Book Title
author: [[Author Name]]
isbn: 1234567890
pages: 320
publisher: Publisher Name
publication_date: 2024-01-15
has_audiobook: true
audible_url: https://audible.com/...
goodreads_url: https://goodreads.com/...
status: to-read
tags: #[[Books]] #[[Book Recommendation]]
---

# Book Title

**Author**: [[Author Name]]
**ISBN**: 1234567890
**Pages**: 320
**Publisher**: Publisher Name
**Published**: 2024-01-15
**Audiobook**: ✅ Available on Audible

## Description

[Book description from OpenLibrary]

## Reading Notes

- Recommended by [[Person Name]] on [[YYYY_MM_DD]]
- Status: [[To Read]]

## Related

- [[Author Name]]
- Other books by this author...
```

**Auto-linking Strategy**:
- Author names → Create `[[Author Name]]` pages
- Genres → Link to `#[[Genre]]` tags
- Series → Create `[[Series Name]]` pages
- Recommender → Link to `[[Person Name]]` if exists

---

### Phase 6: Remove Tag from Journal

After successful processing, remove the `[[Book Recommendation]]` tag from the journal entry.

**Tag Removal Strategy**:

```python
def remove_book_recommendation_tag(
    file_path: str,
    line_number: int,
    entry_content: str
) -> dict:
    """
    Remove [[Book Recommendation]] tag from journal entry.
    Preserves all other content and formatting.
    Returns: {success: bool, error: str | None}
    """
    try:
        # Read journal file
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # Remove tag from specific line
        if 0 <= line_number < len(lines):
            # Remove [[Book Recommendation]] but preserve rest of line
            lines[line_number] = lines[line_number].replace('[[Book Recommendation]]', '').strip()

            # If line is now empty or just whitespace, remove it
            if not lines[line_number].strip():
                lines[line_number] = ''

        # Write back to file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(lines)

        return {'success': True}

    except Exception as e:
        return {
            'success': False,
            'error': f"Failed to remove tag: {str(e)}"
        }
```

**Safety Considerations**:
- Always read entire file first
- Preserve line endings
- Handle UTF-8 encoding
- Don't remove line if it has other content
- Verify file exists before writing

---

## Complete Handler Implementation

```python
#!/usr/bin/env python3
"""
Book Recommendation Handler

Process [[Book Recommendation]] tags from journal entries by:
1. Extracting book title and author
2. Checking for duplicates
3. Adding to book-sync library
4. Enriching with metadata
5. Generating wiki pages
6. Removing the tag
"""

import json
import re
import subprocess
from pathlib import Path
from typing import Any


def handle_book_recommendation(
    entry_content: str,
    journal_date: str,
    line_number: int,
    file_path: str,
    repo_path: str
) -> dict[str, Any]:
    """
    Main handler function for [[Book Recommendation]] tags.

    Args:
        entry_content: Full journal entry text
        journal_date: YYYY-MM-DD format
        line_number: Line number in journal file
        file_path: Absolute path to journal file
        repo_path: Repository root path

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
    pages_created = []
    all_metadata = []

    # Phase 1: Extract book information
    try:
        books = extract_book_info(entry_content)
        if not books:
            return {
                'status': 'failed',
                'pages_created': [],
                'pages_updated': [],
                'issues': ['No valid book references found in entry'],
                'metadata': {}
            }
    except Exception as e:
        return {
            'status': 'failed',
            'pages_created': [],
            'pages_updated': [],
            'issues': [f'Failed to parse entry: {str(e)}'],
            'metadata': {}
        }

    # Process each book
    for book in books:
        book_issues = []

        # Phase 2: Check for duplicates
        dup_check = check_for_duplicates(
            book['title'],
            book.get('author'),
            repo_path
        )

        if dup_check.get('exists'):
            if dup_check.get('confidence', 0) == 1.0:
                book_issues.append(
                    f"Book '{book['title']}' already exists in library (exact match)"
                )
                continue
            else:
                book_issues.append(
                    f"Book '{book['title']}' might be duplicate "
                    f"(similarity: {dup_check['confidence']:.0%}), adding anyway"
                )

        # Phase 3: Add to library
        add_result = add_book_to_library(
            book['title'],
            book.get('author'),
            book.get('context', ''),
            journal_date,
            repo_path
        )

        if not add_result['success']:
            book_issues.append(add_result.get('error', 'Unknown error'))
            issues.extend(book_issues)
            continue

        book_id = add_result.get('book_id')

        # Phase 4: Enrich metadata
        enrich_result = enrich_book_metadata(book_id, repo_path)
        if not enrich_result['success']:
            book_issues.append('Metadata enrichment failed')
            book_issues.extend(enrich_result.get('errors', []))

        # Track metadata
        metadata = {
            'book_id': book_id,
            'title': book['title'],
            'author': book.get('author', 'Unknown'),
            'enrichment_sources': []
        }

        if enrich_result.get('openlibrary_success'):
            metadata['enrichment_sources'].append('openlibrary')
        if enrich_result.get('audible_success'):
            metadata['enrichment_sources'].append('audible')

        all_metadata.append(metadata)
        issues.extend(book_issues)

    # Phase 5: Generate wiki pages (once for all books)
    wiki_result = generate_wiki_pages(repo_path)
    if wiki_result['success']:
        pages_created = wiki_result.get('pages_created', [])
    else:
        issues.append(wiki_result.get('error', 'Wiki generation failed'))

    # Phase 6: Remove tag from journal
    tag_removal = remove_book_recommendation_tag(file_path, line_number)
    if not tag_removal['success']:
        issues.append(f"Failed to remove tag: {tag_removal.get('error')}")

    # Determine overall status
    if not pages_created and not all_metadata:
        status = 'failed'
    elif issues:
        status = 'partial'
    else:
        status = 'success'

    return {
        'status': status,
        'pages_created': pages_created,
        'pages_updated': [],  # Not applicable for this handler
        'issues': issues if issues else [],
        'metadata': {
            'books_processed': len(all_metadata),
            'books': all_metadata
        }
    }


def extract_book_info(entry_content: str) -> list[dict[str, Any]]:
    """Extract all book recommendations from entry."""
    books = []
    lines = entry_content.split('\n')

    for line in lines:
        if '[[Book Recommendation]]' not in line:
            continue

        text = line.replace('[[Book Recommendation]]', '').strip()

        # Pattern 1: [[Title by Author]]
        match = re.search(r'\[\[(.+?)\s+by\s+(.+?)\]\]', text)
        if match:
            books.append({
                'title': match.group(1).strip(),
                'author': match.group(2).strip(),
                'context': text
            })
            continue

        # Pattern 2: "Title" by Author
        match = re.search(r'"(.+?)"\s+by\s+(.+?)(?:\s|$|\[)', text)
        if match:
            books.append({
                'title': match.group(1).strip(),
                'author': match.group(2).strip(),
                'context': text
            })
            continue

        # Pattern 3: [[Title]] only
        matches = re.findall(r'\[\[(.+?)\]\]', text)
        for title in matches:
            if title.isupper() or title in ['Book Recommendation', 'TODO', 'DONE']:
                continue
            books.append({
                'title': title.strip(),
                'author': None,
                'context': text
            })

    return books


def check_for_duplicates(
    title: str,
    author: str | None,
    repo_path: str
) -> dict[str, Any]:
    """Check if book already exists in library."""
    try:
        result = subprocess.run(
            ['uv', 'run', 'book-sync', 'list', '--format', 'json'],
            capture_output=True,
            text=True,
            cwd=repo_path,
            timeout=10
        )

        if result.returncode != 0:
            return {'exists': False, 'error': result.stderr}

        # Parse JSON output
        books = json.loads(result.stdout) if result.stdout.strip() else []

        # Normalize for comparison
        normalized_title = normalize_title(title)

        for book in books:
            book_title = normalize_title(book.get('title', ''))

            # Exact title match
            if book_title == normalized_title:
                if author is None:
                    return {
                        'exists': True,
                        'existing_book': book,
                        'confidence': 1.0,
                        'match_type': 'exact'
                    }

                # Check author if provided
                book_author = normalize_author(book.get('author', ''))
                normalized_author = normalize_author(author)

                if book_author == normalized_author:
                    return {
                        'exists': True,
                        'existing_book': book,
                        'confidence': 1.0,
                        'match_type': 'exact'
                    }

        return {'exists': False}

    except Exception as e:
        return {'exists': False, 'error': str(e)}


def normalize_title(title: str) -> str:
    """Normalize title for comparison."""
    title = title.lower().strip()
    for article in ['the ', 'a ', 'an ']:
        if title.startswith(article):
            title = title[len(article):]
    return title


def normalize_author(author: str) -> str:
    """Extract and normalize author last name."""
    return author.split()[-1].lower().strip()


def add_book_to_library(
    title: str,
    author: str | None,
    context: str,
    journal_date: str,
    repo_path: str
) -> dict[str, Any]:
    """Add book to library using book-sync."""
    cmd = ['uv', 'run', 'book-sync', 'add', '--title', title]

    if author:
        cmd.extend(['--author', author])

    # Add note about recommendation source
    note = f"Recommended in journal entry on {journal_date}"
    recommender_match = re.search(r'(\w+)\s+recommended', context, re.IGNORECASE)
    if recommender_match:
        note = f"Recommended by {recommender_match.group(1)} on {journal_date}"

    cmd.extend(['--notes', note])

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=repo_path,
            timeout=10
        )

        if result.returncode != 0:
            return {
                'success': False,
                'error': f"Failed to add book: {result.stderr}"
            }

        # Parse book ID from output
        match = re.search(r'Added book:\s*(\S+)', result.stdout)
        book_id = match.group(1) if match else None

        return {
            'success': True,
            'book_id': book_id
        }

    except Exception as e:
        return {
            'success': False,
            'error': f"Exception adding book: {str(e)}"
        }


def enrich_book_metadata(book_id: str, repo_path: str) -> dict[str, Any]:
    """Enrich book with metadata from OpenLibrary and Audible."""
    errors = []

    # OpenLibrary enrichment
    try:
        result = subprocess.run(
            ['uv', 'run', 'book-sync', 'enrich', 'openlibrary'],
            capture_output=True,
            text=True,
            cwd=repo_path,
            timeout=30
        )
        openlibrary_success = result.returncode == 0
        if not openlibrary_success:
            errors.append(f"OpenLibrary enrichment failed: {result.stderr}")
    except Exception as e:
        openlibrary_success = False
        errors.append(f"OpenLibrary enrichment exception: {str(e)}")

    # Audible enrichment
    try:
        result = subprocess.run(
            ['uv', 'run', 'book-sync', 'enrich', 'audible'],
            capture_output=True,
            text=True,
            cwd=repo_path,
            timeout=60
        )
        audible_success = result.returncode == 0
        if not audible_success:
            errors.append(f"Audible enrichment failed: {result.stderr}")
    except Exception as e:
        audible_success = False
        errors.append(f"Audible enrichment exception: {str(e)}")

    return {
        'success': openlibrary_success or audible_success,
        'openlibrary_success': openlibrary_success,
        'audible_success': audible_success,
        'errors': errors
    }


def generate_wiki_pages(repo_path: str) -> dict[str, Any]:
    """Generate Logseq wiki pages for all books."""
    try:
        result = subprocess.run(
            ['uv', 'run', 'book-sync', 'wiki', 'generate'],
            capture_output=True,
            text=True,
            cwd=repo_path,
            timeout=30
        )

        if result.returncode != 0:
            return {
                'success': False,
                'error': f"Wiki generation failed: {result.stderr}"
            }

        # Parse created pages
        pages = re.findall(r'Created page:\s*\[\[(.+?)\]\]', result.stdout)

        return {
            'success': True,
            'pages_created': [f"[[{page}]]" for page in pages]
        }

    except Exception as e:
        return {
            'success': False,
            'error': f"Wiki generation exception: {str(e)}"
        }


def remove_book_recommendation_tag(file_path: str, line_number: int) -> dict[str, Any]:
    """Remove [[Book Recommendation]] tag from journal entry."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        if 0 <= line_number < len(lines):
            original_line = lines[line_number]
            lines[line_number] = original_line.replace('[[Book Recommendation]]', '').strip()

            # Add newline back if line has content
            if lines[line_number]:
                lines[line_number] += '\n'

        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(lines)

        return {'success': True}

    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


if __name__ == '__main__':
    # Example usage
    result = handle_book_recommendation(
        entry_content="- [[The Creative Act by Rick Rubin]] [[Book Recommendation]]",
        journal_date="2026-01-07",
        line_number=5,
        file_path="/path/to/journal/2026_01_07.md",
        repo_path="/Users/tylerstapler/Documents/personal-wiki"
    )
    print(json.dumps(result, indent=2))
```

---

## Error Handling Strategies

### Common Failure Scenarios

1. **Book-sync command not found**
   - Issue: `uv run book-sync` fails with command not found
   - Cause: Not running from correct directory
   - Solution: Always pass `cwd=repo_path` to subprocess.run()

2. **Invalid book title/author**
   - Issue: Special characters cause parsing errors
   - Cause: Shell escaping issues
   - Solution: Use subprocess with list args, not shell=True

3. **Enrichment timeout**
   - Issue: OpenLibrary/Audible API calls hang
   - Cause: Network issues or rate limiting
   - Solution: Set timeout=30 for OpenLibrary, timeout=60 for Audible

4. **Duplicate detection false positives**
   - Issue: Similar but different books flagged as duplicates
   - Cause: Aggressive fuzzy matching
   - Solution: Use high threshold (85%) for fuzzy matches

5. **Wiki generation fails**
   - Issue: Cannot write to pages directory
   - Cause: Permission issues or disk full
   - Solution: Check file permissions, report clear error

### Graceful Degradation

- **Missing author**: Continue with title only, OpenLibrary will attempt lookup
- **Enrichment fails**: Book is still added, just with less metadata
- **Tag removal fails**: Log error but don't fail entire operation
- **Multiple books in one entry**: Process each independently, report per-book status

---

## Testing Strategy

### Unit Tests

Test each phase independently:

```bash
# Test book extraction
pytest tests/test_book_recommendation_handler.py::test_extract_book_info

# Test duplicate detection
pytest tests/test_book_recommendation_handler.py::test_check_duplicates

# Test tag removal
pytest tests/test_book_recommendation_handler.py::test_remove_tag
```

### Integration Tests

Test full workflow:

```bash
# Create test journal entry
echo '- [[Test Book by Test Author]] [[Book Recommendation]]' > test_journal.md

# Run handler
python book_recommendation_handler.py

# Verify:
# 1. Book added to library
# 2. Metadata enriched
# 3. Wiki page created
# 4. Tag removed from journal
```

### Test Data

```python
TEST_ENTRIES = [
    {
        'content': '- [[The Creative Act by Rick Rubin]] [[Book Recommendation]]',
        'expected': {'title': 'The Creative Act', 'author': 'Rick Rubin'}
    },
    {
        'content': '- "Atomic Habits" by James Clear [[Book Recommendation]]',
        'expected': {'title': 'Atomic Habits', 'author': 'James Clear'}
    },
    {
        'content': '- Read [[Thinking, Fast and Slow]] [[Book Recommendation]]',
        'expected': {'title': 'Thinking, Fast and Slow', 'author': None}
    },
    {
        'content': '- Sarah recommended [[Range by David Epstein]] [[Book Recommendation]]',
        'expected': {'title': 'Range', 'author': 'David Epstein'}
    }
]
```

---

## Performance Considerations

### Optimization Opportunities

1. **Batch enrichment**: Instead of enriching after each book, batch all books and enrich once
2. **Cache API responses**: Store OpenLibrary/Audible responses to avoid re-querying
3. **Parallel processing**: Process multiple books concurrently using asyncio
4. **Index duplicate checks**: Build local index of book titles for faster duplicate detection

### Resource Usage

- **Network calls**: 2-3 per book (add, enrich OpenLibrary, enrich Audible)
- **Disk I/O**: 2 writes per book (library storage, wiki page)
- **Memory**: Minimal, processes one journal entry at a time
- **Time**: ~5-10 seconds per book (mostly API latency)

---

## Integration with Knowledge Orchestrator

The orchestrator invokes this handler when it finds `[[Book Recommendation]]` tags:

```python
# In knowledge enrichment orchestrator
if '[[Book Recommendation]]' in entry_content:
    result = handle_book_recommendation(
        entry_content=entry_content,
        journal_date=journal_date,
        line_number=line_number,
        file_path=file_path,
        repo_path=repo_path
    )

    # Process result
    if result['status'] == 'success':
        log_success(f"Added {len(result['metadata']['books'])} books")
        pages_created.extend(result['pages_created'])
    elif result['status'] == 'partial':
        log_warning(f"Partial success: {result['issues']}")
    else:
        log_error(f"Failed: {result['issues']}")
```

---

## Future Enhancements

### Phase 2 Improvements

1. **Author disambiguation**: When multiple authors exist with same name
2. **Series detection**: Automatically link books in a series
3. **Reading list integration**: Add to "Currently Reading" or "To Read" status
4. **Recommendation network**: Track who recommended which books
5. **Reading goals**: Track progress toward annual reading goals

### Advanced Features

1. **AI-powered parsing**: Use LLM to extract book info from free-form text
2. **Cover image download**: Fetch and store book cover images
3. **Quote extraction**: Parse any quotes about the book from journal
4. **Related books**: Suggest similar books based on genre/author
5. **Reading analytics**: Track reading patterns and preferences

---

## Changelog

**v1.0.0** (2026-01-07)
- Initial implementation
- Support for multiple book reference formats
- Integration with book-sync tool
- Automatic metadata enrichment
- Wiki page generation
- Tag removal after processing
