---
title: Process Book Recommendation Entries
description: Finds journal entries marked with [[Book Recommendation]], researches books, integrates with book-sync system, creates wiki pages, and removes labels after success
arguments: []
tools: Read, Write, Edit, Glob, Grep, WebFetch, mcp__read-website-fast__read_website, mcp__brave-search__brave_web_search, Bash, TodoWrite
model: opus
---

# Process Book Recommendation Entries

**Command Purpose**: Systematically process all journal entries marked with `[[Book Recommendation]]` by:
1. Discovering and cataloging all pending book recommendations
2. Researching book details (author, synopsis, reviews, audiobook availability)
3. Adding books to the book-sync system with appropriate metadata
4. Creating Logseq wiki pages for each book
5. Removing recommendation labels after successful processing
6. Generating completion report with audiobook recommendations

**When to Use**: Tag entries with `[[Book Recommendation]]` when someone recommends a book, you see an interesting book mentioned, or you want to add a book to your reading list for evaluation.

**Semantic Definition**:
> `[[Book Recommendation]]` = "This is a book I've been recommended or want to consider adding to my reading list. I need to research it, evaluate it, and decide whether to add it to my library."

**Contrast with Other Tags**:
- `[[Needs Synthesis]]`: For learning from articles/papers - creating evergreen knowledge notes
- `[[Needs Research]]`: For technology evaluations, product comparisons, technical deep-dives
- `[[Needs Handy Plan]]`: For physical construction/DIY projects requiring tools and materials

---

## Core Methodology

### Phase 1: Discovery and Cataloging

**Objective**: Find all entries marked with book recommendations and extract book details.

**Actions**:
1. **Search for book recommendation markers**:
   ```bash
   grep -rn "[[Book Recommendation]]" ~/Documents/personal-wiki/logseq/journals/
   ```
   - Record file paths, line numbers, and content
   - Handle case variations

2. **Parse each entry**:
   - Extract book title and author (if provided)
   - Capture recommendation source (who recommended it, why)
   - Note any context (genre preferences, specific interests)
   - Identify entry type (see Entry Types below)

3. **Check existing library**:
   - Search book-sync storage for duplicates
   - Check if book already has a wiki page
   - Note existing status if found

4. **Generate discovery report**:
   ```
   ## Book Recommendation Queue Discovery

   **Total Entries Found**: [count]

   **New Books** ([count]):
   - [Journal Date] - "[Title]" by [Author] (recommended by [source])

   **Already in Library** ([count]):
   - [Journal Date] - "[Title]" - [current status]

   **Requires Clarification** ([count]):
   - [Journal Date] - [Issue: missing title/author]
   ```

**Entry Types to Recognize**:

1. **Complete recommendation**:
   ```markdown
   - "Atomic Habits" by James Clear - recommended by John for productivity [[Book Recommendation]]
   ```

2. **Title only**:
   ```markdown
   - Should read "The Pragmatic Programmer" [[Book Recommendation]]
   ```

3. **Author mention**:
   ```markdown
   - Check out anything by Cal Newport [[Book Recommendation]]
   ```

4. **Contextual recommendation**:
   ```markdown
   - For learning about distributed systems: "Designing Data-Intensive Applications" [[Book Recommendation]]
   ```

5. **Podcast/article mention**:
   ```markdown
   - Book mentioned on Tim Ferriss podcast: "Tools of Titans" [[Book Recommendation]]
   ```

---

### Phase 2: Research and Enrichment

**Objective**: Gather comprehensive information about each recommended book.

**Actions**:
For each book recommendation:

1. **Research book details**:
   - Use Brave Search to find:
     - Full title and subtitle
     - Author(s) and credentials
     - Publication date and publisher
     - ISBN-10 and ISBN-13
     - Genre and categories
     - Synopsis/description
     - Average ratings (Goodreads, Amazon)
     - Key themes and topics
   - Search patterns:
     ```
     "[Book Title]" "[Author]" book
     "[Book Title]" ISBN
     "[Book Title]" goodreads
     "[Book Title]" summary review
     ```

2. **Check audiobook availability**:
   - Search for Audible availability
   - Note narrator(s)
   - Note length in hours
   - Check if available through Audible credits

3. **Gather recommendations context**:
   - Who recommends this book
   - What makes it notable
   - Target audience
   - Prerequisites or related reading

4. **Assess fit for library**:
   - Matches user interests?
   - Complements existing collection?
   - Fiction or non-fiction?
   - Reading priority (immediate/queue/someday)

**Success Criteria (per book)**:
- Full title and author confirmed
- ISBN obtained (at least one)
- Synopsis available
- Audiobook status known
- Genre categorized

---

### Phase 3: Book-Sync Integration

**Objective**: Add books to the book-sync system for unified library management.

**Actions**:
For each researched book:

1. **Check if book exists in storage**:
   ```bash
   # Search existing books by title
   uv run book-sync list-books | grep -i "[title]"
   ```

2. **If book is NEW - add to system**:

   **Create YAML file** at:
   `/Users/tylerstapler/Documents/personal-wiki/books/unified/[unified-id].yaml`

   **File format**:
   ```yaml
   unified_id: "recommendation-[timestamp]"
   title: "[Full Title]"
   subtitle: "[Subtitle if any]"
   authors:
     - "[Author 1]"
     - "[Author 2]"
   isbn_10: "[ISBN-10]"
   isbn_13: "[ISBN-13]"
   status: "to-read"
   date_added: "[YYYY-MM-DDTHH:MM:SS]"

   # Metadata
   description: "[Synopsis]"
   publisher: "[Publisher]"
   publication_date: "[YYYY-MM-DD]"
   num_pages: [number]
   language: "en"

   # Categorization
   tags:
     - "[genre]"
     - "[topic]"
   shelves:
     - "to-read"
     - "[genre-shelf]"
   categories:
     - "[category]"

   # Recommendation context
   notes: |
     Recommended by: [source]
     Reason: [why recommended]
     Added from: [[YYYY_MM_DD]] journal

   # Platform mappings (empty for now)
   goodreads_id: null
   hardcover_id: null
   openlibrary_id: null
   audible_id: null

   # Enrichments (empty, will be populated by enrichment)
   enrichments: []
   ```

3. **If book EXISTS - update**:
   - Add recommendation notes to existing entry
   - Update shelves/tags if needed
   - Don't overwrite existing ratings/reviews

4. **Run enrichment** (optional, if time permits):
   ```bash
   uv run book-sync enrich run --limit 1
   ```

---

### Phase 4: Wiki Page Creation

**Objective**: Create Logseq wiki pages for each book.

**Actions**:
For each processed book:

1. **Create book zettel** at:
   `/Users/tylerstapler/Documents/personal-wiki/logseq/pages/[Book Title].md`

2. **Use this structure**:

```markdown
# [Book Title]

## Overview
- **Author**: [[Author Name]]
- **Published**: [Year] by [Publisher]
- **Pages**: [count]
- **Genre**: [genre/category]
- **Status**: [[To Read]]

## Synopsis
[Book description/synopsis]

## Why Read This
[Recommendation context - who recommended, why notable]

## Key Topics
- [Topic 1]
- [Topic 2]
- [Topic 3]

## Audiobook
- **Available**: [Yes/No]
- **Narrator**: [Narrator name if known]
- **Length**: [X hours Y minutes]
- **Audible Rating**: [rating if known]

## Recommendation Source
- Recommended by: [source]
- Context: [why/when recommended]
- Journal entry: [[YYYY_MM_DD]]

## Related Books
- [[Related Book 1]]
- [[Related Book 2]]

## Notes
[Space for notes once reading begins]

## Review
[Space for review once completed]

## Tags
#[[Books]] #[[To Read]] #[[Genre]]
```

3. **Add to today's journal**:
   ```markdown
   - Added [[Book Title]] by [[Author Name]] to reading list #[[Books]] #[[To Read]]
     - Recommended by: [source]
     - Genre: [genre]
     - Audiobook: [available/not available]
     - Priority: [high/medium/low]
   ```

---

### Phase 5: Label Management

**Objective**: Remove `[[Book Recommendation]]` markers from processed entries.

**Actions**:
For each successfully processed entry:

1. **Transform the entry**:

   | Before | After |
   |--------|-------|
   | `- "Book Title" by Author [[Book Recommendation]]` | `- Added [[Book Title]] to reading list - see book page [[Added YYYY-MM-DD]]` |
   | `- Check out [book] [[Book Recommendation]]` | `- [[Book Title]] added to library [[Added YYYY-MM-DD]]` |

2. **Key transformation rules**:
   - **REMOVE** the `[[Book Recommendation]]` marker
   - **ADD** wiki link to book page `[[Book Title]]`
   - **ADD** completion marker `[[Added YYYY-MM-DD]]`

---

### Phase 6: Verification and Reporting

**Objective**: Confirm all processing completed successfully.

**Actions**:
1. **Verify label removal**:
   ```bash
   grep -rn "[[Book Recommendation]]" ~/Documents/personal-wiki/logseq/journals/
   ```

2. **Validate created content**:
   - All book wiki pages exist
   - Book-sync entries created
   - Journal entries updated

3. **Generate completion report**:
   ```
   ## Book Recommendation Processing Complete

   **Processing Summary**:
   - Total recommendations discovered: [count]
   - Successfully processed: [count]
   - Already in library: [count]
   - Failed/skipped: [count]

   **Books Added to Library**: [count]
   - [[Book Title 1]] by Author - [genre]
     - Audiobook: [Yes/No] ([length] hours)
     - Recommended by: [source]
   - [[Book Title 2]] by Author - [genre]
     - Audiobook: [Yes/No]
     - Recommended by: [source]

   **Audiobook Highlights**:
   Books with audiobooks available:
   - [[Book 1]] - [X hours] - [narrator]
   - [[Book 2]] - [X hours] - [narrator]

   **Genre Distribution**:
   - Fiction: [count]
   - Non-Fiction: [count]
   - Technical: [count]

   **Next Steps**:
   - Run `uv run book-sync enrich run` to add Audible/OpenLibrary metadata
   - Run `uv run book-sync recommend list` for purchase recommendations
   - Review books in [[To Read]] shelf

   **Entries Requiring Clarification**: [count]
   - [Journal date] - [Issue]
   ```

---

## Usage Examples

### Example 1: Complete Recommendation
**Journal Content** (`2026_01_07.md`):
```markdown
- "Deep Work" by Cal Newport - recommended by colleague for focus strategies [[Book Recommendation]]
```

**Processing**:
1. Discovery: 1 entry with full details
2. Research: Confirm details, find ISBN, check audiobook
3. Book-sync: Create unified entry
4. Wiki page: Create `[[Deep Work]]` page
5. Label removed

**Result**:
```markdown
- Added [[Deep Work]] by [[Cal Newport]] to reading list - comprehensive book page created [[Added 2026-01-07]]
  - Audiobook available: 7 hours, narrated by Jeff Bottoms
```

### Example 2: Title Only
**Journal Content** (`2026_01_07.md`):
```markdown
- Need to read "The Phoenix Project" [[Book Recommendation]]
```

**Processing**:
1. Discovery: 1 entry, author unknown
2. Research: Find author (Gene Kim et al), full details
3. Process normally

### Example 3: Author Recommendation
**Journal Content** (`2026_01_07.md`):
```markdown
- Someone said to check out books by Nassim Taleb [[Book Recommendation]]
```

**Processing**:
1. Discovery: Author recommendation, no specific title
2. Research: Find most popular/recommended Taleb books
3. Add note requesting specific title preference
4. Optionally create entries for top 2-3 books by author

---

## Integration with Book-Sync

This command integrates with the existing book-sync system:

### Storage Location
Books are stored in:
```
/Users/tylerstapler/Documents/personal-wiki/books/
├── unified/           # Book YAML files
├── covers/            # Cover images
└── .book_sync_config.yaml
```

### Post-Processing Commands
After running this command, users can:

```bash
# Enrich books with Audible/OpenLibrary metadata
uv run book-sync enrich run

# Get audiobook purchase recommendations
uv run book-sync recommend list

# Generate wiki pages with enrichment data
uv run book-sync wiki generate

# Check library status
uv run book-sync status
```

### Duplicate Handling
- Check existing library before adding
- If book exists, add recommendation notes
- Don't create duplicate entries
- Link to existing wiki page if present

---

## Quality Standards

All processing must satisfy:

1. **Book Identification**:
   - Full title confirmed (including subtitle)
   - Author(s) verified
   - At least one ISBN obtained
   - Genre/category assigned

2. **Wiki Page Quality**:
   - Synopsis included
   - Recommendation context captured
   - Audiobook status noted
   - Proper Logseq formatting

3. **Library Integration**:
   - Book-sync entry created
   - Status set to "to-read"
   - Tags and shelves assigned
   - Notes include recommendation source

---

## Error Handling

### Unable to Identify Book
**Pattern**: Vague title, no author
**Handling**: Add `#needs-clarification` tag, request more details from user.

### Book Already in Library
**Pattern**: Duplicate recommendation
**Handling**: Add recommendation notes to existing entry, link to existing page, mark as already processed.

### No ISBN Found
**Pattern**: Obscure or self-published book
**Handling**: Create entry without ISBN, flag for manual enrichment later.

### Audiobook Not Available
**Pattern**: No Audible listing
**Handling**: Note "audiobook not available" in wiki page, may become available later.

---

## Command Invocation

**Format**: `/knowledge/process-book-recommendations`

**Arguments**: None (processes all pending entries)

**Expected Duration**: 2-5 minutes per book

**Prerequisites**:
- Brave Search accessible
- book-sync system initialized (`uv run book-sync init`)
- Web tools functional

**Post-Execution**:
- Review completion report
- Run enrichment for new books
- Check audiobook recommendations
- Update reading priorities as needed