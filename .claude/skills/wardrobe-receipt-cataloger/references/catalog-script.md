# Catalog Script — Usage and Data Format

Detail supporting the "Execution — Reusable Scripts" step of the main `SKILL.md`
workflow. Rather than making individual file edits (which require per-call approval),
this skill uses two reusable scripts that only need one approval to run.

### Files

| File | Purpose |
|---|---|
| `~/.claude/skills/wardrobe-receipt-cataloger/catalog_wardrobe.py` | Main script: downloads images, updates Wardrobe.md, creates/updates brand pages |
| `~/.claude/skills/wardrobe-receipt-cataloger/receipts.json` | Data: extracted receipt data in structured JSON format |

### Workflow

1. **Extract** receipt data from Gmail threads into `receipts.json`
2. **Run** `catalog_wardrobe.py` once — single script approval covers all file writes
3. **Verify** with `--dry-run` first, then execute for real

```bash
# Dry run (preview only)
python3 ~/.claude/skills/wardrobe-receipt-cataloger/catalog_wardrobe.py \
  --wiki-root /path/to/personal-wiki \
  --dry-run

# Execute
python3 ~/.claude/skills/wardrobe-receipt-cataloger/catalog_wardrobe.py \
  --wiki-root /path/to/personal-wiki

# Skip already-processed receipts on re-runs
python3 ~/.claude/skills/wardrobe-receipt-cataloger/catalog_wardrobe.py \
  --wiki-root /path/to/personal-wiki \
  --skip-processed
```

### Adding new receipts

When new receipts are found, add entries to `receipts.json` in this format:
```json
{
  "thread_id": "19e75dd...",
  "brand": "Brand Name",
  "order_number": "12345",
  "order_date": "2026-05-29",
  "items": [
    {
      "product_name": "Product Name",
      "color": "Color Name",
      "size": "M",
      "price": 89.00,
      "wardrobe_section": "Tops",
      "wardrobe_subsection": "Button-Down & Woven Shirts",
      "existing_search": null,
      "image_url": "https://cdn.example.com/image.jpg",
      "image_filename": "brand-product-color.jpg",
      "product_url": "https://brand.com/product"
    }
  ]
}
```

Set `existing_search` to the exact text of an existing Wardrobe.md line to add receipt links to it instead of creating a new entry.
