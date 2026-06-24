---
description: Finds journal entries marked with [[Book Recommendation]], researches
  books, integrates with book-sync system, creates wiki pages, and removes labels
  after success
prompt: "# Process Book Recommendation Entries\n\n**Command Purpose**: Systematically\
  \ process all journal entries marked with `[[Book Recommendation]]` by:\n1. Discovering\
  \ and cataloging all pending book recommendations\n2. Researching book details (author,\
  \ synopsis, reviews, audiobook availability)\n3. Adding books to the book-sync system\
  \ with appropriate metadata\n4. Creating Logseq wiki pages for each book\n5. Removing\
  \ recommendation labels after successful processing\n6. Generating completion report\
  \ with audiobook recommendations\n\n**When to Use**: Tag entries with `[[Book Recommendation]]`\
  \ when someone recommends a book, you see an interesting book mentioned, or you\
  \ want to add a book to your reading list for evaluation.\n\n**Semantic Definition**:\n\
  > `[[Book Recommendation]]` = \"This is a book I've been recommended or want to\
  \ consider adding to my reading list. I need to research it, evaluate it, and decide\
  \ whether to add it to my library.\"\n\n**Contrast with Other Tags**:\n- `[[Needs\
  \ Synthesis]]`: For learning from articles/papers - creating evergreen knowledge\
  \ notes\n- `[[Needs Research]]`: For technology evaluations, product comparisons,\
  \ technical deep-dives\n- `[[Needs Handy Plan]]`: For physical construction/DIY\
  \ projects requiring tools and materials\n\n---\n\n## Core Methodology\n\n### Phase\
  \ 1: Discovery and Cataloging\n\n**Objective**: Find all entries marked with book\
  \ recommendations and extract book details.\n\n**Actions**:\n1. **Search for book\
  \ recommendation markers**:\n   ```bash\n   grep -rn \"[[Book Recommendation]]\"\
  \ ~/Documents/personal-wiki/logseq/journals/\n   ```\n   - Record file paths, line\
  \ numbers, and content\n   - Handle case variations\n\n2. **Parse each entry**:\n\
  \   - Extract book title and author (if provided)\n   - Capture recommendation source\
  \ (who recommended it, why)\n   - Note any context (genre preferences, specific\
  \ interests)\n   - Identify entry type (see Entry Types below)\n\n3. **Check existing\
  \ library**:\n   - Search book-sync storage for duplicates\n   - Check if book already\
  \ has a wiki page\n   - Note existing status if found\n\n4. **Generate discovery\
  \ report**:\n   ```\n   ## Book Recommendation Queue Discovery\n\n   **Total Entries\
  \ Found**: [count]\n\n   **New Books** ([count]):\n   - [Journal Date] - \"[Title]\"\
  \ by [Author] (recommended by [source])\n\n   **Already in Library** ([count]):\n\
  \   - [Journal Date] - \"[Title]\" - [current status]\n\n   **Requires Clarification**\
  \ ([count]):\n   - [Journal Date] - [Issue: missing title/author]\n   ```\n\n**Entry\
  \ Types to Recognize**:\n\n1. **Complete recommendation**:\n   ```markdown\n   -\
  \ \"Atomic Habits\" by James Clear - recommended by John for productivity [[Book\
  \ Recommendation]]\n   ```\n\n2. **Title only**:\n   ```markdown\n   - Should read\
  \ \"The Pragmatic Programmer\" [[Book Recommendation]]\n   ```\n\n3. **Author mention**:\n\
  \   ```markdown\n   - Check out anything by Cal Newport [[Book Recommendation]]\n\
  \   ```\n\n4. **Contextual recommendation**:\n   ```markdown\n   - For learning\
  \ about distributed systems: \"Designing Data-Intensive Applications\" [[Book Recommendation]]\n\
  \   ```\n\n5. **Podcast/article mention**:\n   ```markdown\n   - Book mentioned\
  \ on Tim Ferriss podcast: \"Tools of Titans\" [[Book Recommendation]]\n   ```\n\n\
  ---\n\n### Phase 2: Research and Enrichment\n\n**Objective**: Gather comprehensive\
  \ information about each recommended book.\n\n**Actions**:\nFor each book recommendation:\n\
  \n1. **Research book details**:\n   - Use Brave Search to find:\n     - Full title\
  \ and subtitle\n     - Author(s) and credentials\n     - Publication date and publisher\n\
  \     - ISBN-10 and ISBN-13\n     - Genre and categories\n     - Synopsis/description\n\
  \     - Average ratings (Goodreads, Amazon)\n     - Key themes and topics\n   -\
  \ Search patterns:\n     ```\n     \"[Book Title]\" \"[Author]\" book\n     \"[Book\
  \ Title]\" ISBN\n     \"[Book Title]\" goodreads\n     \"[Book Title]\" summary\
  \ review\n     ```\n\n2. **Check audiobook availability**:\n   - Search for Audible\
  \ availability\n   - Note narrator(s)\n   - Note length in hours\n   - Check if\
  \ available through Audible credits\n\n3. **Gather recommendations context**:\n\
  \   - Who recommends this book\n   - What makes it notable\n   - Target audience\n\
  \   - Prerequisites or related reading\n\n4. **Assess fit for library**:\n   - Matches\
  \ user interests?\n   - Complements existing collection?\n   - Fiction or non-fiction?\n\
  \   - Reading priority (immediate/queue/someday)\n\n**Success Criteria (per book)**:\n\
  - Full title and author confirmed\n- ISBN obtained (at least one)\n- Synopsis available\n\
  - Audiobook status known\n- Genre categorized\n\n---\n\n### Phase 3: Book-Sync Integration\n\
  \n**Objective**: Add books to the book-sync system for unified library management.\n\
  \n**Actions**:\nFor each researched book:\n\n1. **Check if book exists in storage**:\n\
  \   ```bash\n   # Search existing books by title\n   uv run book-sync list-books\
  \ | grep -i \"[title]\"\n   ```\n\n2. **If book is NEW - add to system**:\n\n  \
  \ **Create YAML file** at:\n   `/Users/tylerstapler/Documents/personal-wiki/books/unified/[unified-id].yaml`\n\
  \n   **File format**:\n   ```yaml\n   unified_id: \"recommendation-[timestamp]\"\
  \n   title: \"[Full Title]\"\n   subtitle: \"[Subtitle if any]\"\n   authors:\n\
  \     - \"[Author 1]\"\n     - \"[Author 2]\"\n   isbn_10: \"[ISBN-10]\"\n   isbn_13:\
  \ \"[ISBN-13]\"\n   status: \"to-read\"\n   date_added: \"[YYYY-MM-DDTHH:MM:SS]\"\
  \n\n   # Metadata\n   description: \"[Synopsis]\"\n   publisher: \"[Publisher]\"\
  \n   publication_date: \"[YYYY-MM-DD]\"\n   num_pages: [number]\n   language: \"\
  en\"\n\n   # Categorization\n   tags:\n     - \"[genre]\"\n     - \"[topic]\"\n\
  \   shelves:\n     - \"to-read\"\n     - \"[genre-shelf]\"\n   categories:\n   \
  \  - \"[category]\"\n\n   # Recommendation context\n   notes: |\n     Recommended\
  \ by: [source]\n     Reason: [why recommended]\n     Added from: [[YYYY_MM_DD]]\
  \ journal\n\n   # Platform mappings (empty for now)\n   goodreads_id: null\n   hardcover_id:\
  \ null\n   openlibrary_id: null\n   audible_id: null\n\n   # Enrichments (empty,\
  \ will be populated by enrichment)\n   enrichments: []\n   ```\n\n3. **If book EXISTS\
  \ - update**:\n   - Add recommendation notes to existing entry\n   - Update shelves/tags\
  \ if needed\n   - Don't overwrite existing ratings/reviews\n\n4. **Run enrichment**\
  \ (optional, if time permits):\n   ```bash\n   uv run book-sync enrich run --limit\
  \ 1\n   ```\n\n---\n\n### Phase 4: Wiki Page Creation\n\n**Objective**: Create Logseq\
  \ wiki pages for each book.\n\n**Actions**:\nFor each processed book:\n\n1. **Create\
  \ book zettel** at:\n   `/Users/tylerstapler/Documents/personal-wiki/logseq/pages/[Book\
  \ Title].md`\n\n2. **Use this structure**:\n\n```markdown\n# [Book Title]\n\n##\
  \ Overview\n- **Author**: [[Author Name]]\n- **Published**: [Year] by [Publisher]\n\
  - **Pages**: [count]\n- **Genre**: [genre/category]\n- **Status**: [[To Read]]\n\
  \n## Synopsis\n[Book description/synopsis]\n\n## Why Read This\n[Recommendation\
  \ context - who recommended, why notable]\n\n## Key Topics\n- [Topic 1]\n- [Topic\
  \ 2]\n- [Topic 3]\n\n## Audiobook\n- **Available**: [Yes/No]\n- **Narrator**: [Narrator\
  \ name if known]\n- **Length**: [X hours Y minutes]\n- **Audible Rating**: [rating\
  \ if known]\n\n## Recommendation Source\n- Recommended by: [source]\n- Context:\
  \ [why/when recommended]\n- Journal entry: [[YYYY_MM_DD]]\n\n## Related Books\n\
  - [[Related Book 1]]\n- [[Related Book 2]]\n\n## Notes\n[Space for notes once reading\
  \ begins]\n\n## Review\n[Space for review once completed]\n\n## Tags\n#[[Books]]\
  \ #[[To Read]] #[[Genre]]\n```\n\n3. **Add to today's journal**:\n   ```markdown\n\
  \   - Added [[Book Title]] by [[Author Name]] to reading list #[[Books]] #[[To Read]]\n\
  \     - Recommended by: [source]\n     - Genre: [genre]\n     - Audiobook: [available/not\
  \ available]\n     - Priority: [high/medium/low]\n   ```\n\n---\n\n### Phase 5:\
  \ Label Management\n\n**Objective**: Remove `[[Book Recommendation]]` markers from\
  \ processed entries.\n\n**Actions**:\nFor each successfully processed entry:\n\n\
  1. **Transform the entry**:\n\n   | Before | After |\n   |--------|-------|\n  \
  \ | `- \"Book Title\" by Author [[Book Recommendation]]` | `- Added [[Book Title]]\
  \ to reading list - see book page [[Added YYYY-MM-DD]]` |\n   | `- Check out [book]\
  \ [[Book Recommendation]]` | `- [[Book Title]] added to library [[Added YYYY-MM-DD]]`\
  \ |\n\n2. **Key transformation rules**:\n   - **REMOVE** the `[[Book Recommendation]]`\
  \ marker\n   - **ADD** wiki link to book page `[[Book Title]]`\n   - **ADD** completion\
  \ marker `[[Added YYYY-MM-DD]]`\n\n---\n\n### Phase 6: Verification and Reporting\n\
  \n**Objective**: Confirm all processing completed successfully.\n\n**Actions**:\n\
  1. **Verify label removal**:\n   ```bash\n   grep -rn \"[[Book Recommendation]]\"\
  \ ~/Documents/personal-wiki/logseq/journals/\n   ```\n\n2. **Validate created content**:\n\
  \   - All book wiki pages exist\n   - Book-sync entries created\n   - Journal entries\
  \ updated\n\n3. **Generate completion report**:\n   ```\n   ## Book Recommendation\
  \ Processing Complete\n\n   **Processing Summary**:\n   - Total recommendations\
  \ discovered: [count]\n   - Successfully processed: [count]\n   - Already in library:\
  \ [count]\n   - Failed/skipped: [count]\n\n   **Books Added to Library**: [count]\n\
  \   - [[Book Title 1]] by Author - [genre]\n     - Audiobook: [Yes/No] ([length]\
  \ hours)\n     - Recommended by: [source]\n   - [[Book Title 2]] by Author - [genre]\n\
  \     - Audiobook: [Yes/No]\n     - Recommended by: [source]\n\n   **Audiobook Highlights**:\n\
  \   Books with audiobooks available:\n   - [[Book 1]] - [X hours] - [narrator]\n\
  \   - [[Book 2]] - [X hours] - [narrator]\n\n   **Genre Distribution**:\n   - Fiction:\
  \ [count]\n   - Non-Fiction: [count]\n   - Technical: [count]\n\n   **Next Steps**:\n\
  \   - Run `uv run book-sync enrich run` to add Audible/OpenLibrary metadata\n  \
  \ - Run `uv run book-sync recommend list` for purchase recommendations\n   - Review\
  \ books in [[To Read]] shelf\n\n   **Entries Requiring Clarification**: [count]\n\
  \   - [Journal date] - [Issue]\n   ```\n\n---\n\n## Usage Examples\n\n### Example\
  \ 1: Complete Recommendation\n**Journal Content** (`2026_01_07.md`):\n```markdown\n\
  - \"Deep Work\" by Cal Newport - recommended by colleague for focus strategies [[Book\
  \ Recommendation]]\n```\n\n**Processing**:\n1. Discovery: 1 entry with full details\n\
  2. Research: Confirm details, find ISBN, check audiobook\n3. Book-sync: Create unified\
  \ entry\n4. Wiki page: Create `[[Deep Work]]` page\n5. Label removed\n\n**Result**:\n\
  ```markdown\n- Added [[Deep Work]] by [[Cal Newport]] to reading list - comprehensive\
  \ book page created [[Added 2026-01-07]]\n  - Audiobook available: 7 hours, narrated\
  \ by Jeff Bottoms\n```\n\n### Example 2: Title Only\n**Journal Content** (`2026_01_07.md`):\n\
  ```markdown\n- Need to read \"The Phoenix Project\" [[Book Recommendation]]\n```\n\
  \n**Processing**:\n1. Discovery: 1 entry, author unknown\n2. Research: Find author\
  \ (Gene Kim et al), full details\n3. Process normally\n\n### Example 3: Author Recommendation\n\
  **Journal Content** (`2026_01_07.md`):\n```markdown\n- Someone said to check out\
  \ books by Nassim Taleb [[Book Recommendation]]\n```\n\n**Processing**:\n1. Discovery:\
  \ Author recommendation, no specific title\n2. Research: Find most popular/recommended\
  \ Taleb books\n3. Add note requesting specific title preference\n4. Optionally create\
  \ entries for top 2-3 books by author\n\n---\n\n## Integration with Book-Sync\n\n\
  This command integrates with the existing book-sync system:\n\n### Storage Location\n\
  Books are stored in:\n```\n/Users/tylerstapler/Documents/personal-wiki/books/\n\
  ├── unified/           # Book YAML files\n├── covers/            # Cover images\n\
  └── .book_sync_config.yaml\n```\n\n### Post-Processing Commands\nAfter running this\
  \ command, users can:\n\n```bash\n# Enrich books with Audible/OpenLibrary metadata\n\
  uv run book-sync enrich run\n\n# Get audiobook purchase recommendations\nuv run\
  \ book-sync recommend list\n\n# Generate wiki pages with enrichment data\nuv run\
  \ book-sync wiki generate\n\n# Check library status\nuv run book-sync status\n```\n\
  \n### Duplicate Handling\n- Check existing library before adding\n- If book exists,\
  \ add recommendation notes\n- Don't create duplicate entries\n- Link to existing\
  \ wiki page if present\n\n---\n\n## Quality Standards\n\nAll processing must satisfy:\n\
  \n1. **Book Identification**:\n   - Full title confirmed (including subtitle)\n\
  \   - Author(s) verified\n   - At least one ISBN obtained\n   - Genre/category assigned\n\
  \n2. **Wiki Page Quality**:\n   - Synopsis included\n   - Recommendation context\
  \ captured\n   - Audiobook status noted\n   - Proper Logseq formatting\n\n3. **Library\
  \ Integration**:\n   - Book-sync entry created\n   - Status set to \"to-read\"\n\
  \   - Tags and shelves assigned\n   - Notes include recommendation source\n\n---\n\
  \n## Error Handling\n\n### Unable to Identify Book\n**Pattern**: Vague title, no\
  \ author\n**Handling**: Add `#needs-clarification` tag, request more details from\
  \ user.\n\n### Book Already in Library\n**Pattern**: Duplicate recommendation\n\
  **Handling**: Add recommendation notes to existing entry, link to existing page,\
  \ mark as already processed.\n\n### No ISBN Found\n**Pattern**: Obscure or self-published\
  \ book\n**Handling**: Create entry without ISBN, flag for manual enrichment later.\n\
  \n### Audiobook Not Available\n**Pattern**: No Audible listing\n**Handling**: Note\
  \ \"audiobook not available\" in wiki page, may become available later.\n\n---\n\
  \n## Command Invocation\n\n**Format**: `/knowledge/process-book-recommendations`\n\
  \n**Arguments**: None (processes all pending entries)\n\n**Expected Duration**:\
  \ 2-5 minutes per book\n\n**Prerequisites**:\n- Brave Search accessible\n- book-sync\
  \ system initialized (`uv run book-sync init`)\n- Web tools functional\n\n**Post-Execution**:\n\
  - Review completion report\n- Run enrichment for new books\n- Check audiobook recommendations\n\
  - Update reading priorities as needed\n"
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
