#!/usr/bin/env python3
"""
catalog_wardrobe.py — Catalog clothing receipts into the Logseq wiki.

Reads receipts.json (next to this script), downloads product images,
updates logseq/pages/Wardrobe.md with receipt links, and creates/updates
brand pages in logseq/pages/.

Usage:
  python3 catalog_wardrobe.py --wiki-root /path/to/personal-wiki [--dry-run] [--receipts /path/to/receipts.json]
"""
import argparse
import json
import os
import re
import sys
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime

SCRIPT_DIR = Path(__file__).parent

MONTH_ABBR = {
    1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr", 5: "May", 6: "Jun",
    7: "Jul", 8: "Aug", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec",
}

# Maps wardrobe_section → header text in Wardrobe.md
SECTION_HEADERS = {
    "Tops": "## Tops",
    "Bottoms": "## Bottoms",
    "Outerwear & Layering": "## Outerwear & Layering",
    "Dress Accessories": "## Dress Accessories",
    "Headwear & Accessories": "## Headwear & Accessories",
    "Footwear": "## Footwear",
    "Work & Trade Clothing": "## Work & Trade Clothing",
    "Sports & Fan Apparel": "## Sports & Fan Apparel",
}

# Maps subsection label → header text
SUBSECTION_HEADERS = {
    "Dress / Smart Casual": "### Dress / Smart Casual",
    "Button-Down & Woven Shirts": "### Button-Down & Woven Shirts",
    "T-Shirts & Athletic Shirts": "### T-Shirts & Athletic Shirts",
    "Hoodies & Long-Sleeve Performance": "### Hoodies & Long-Sleeve Performance",
    "Sun Protection & Neckwear": "### Sun Protection & Neckwear",
    "Pants": "### Pants",
    "Shorts": "### Shorts",
}


def load_processed_threads(wiki_root: Path) -> set:
    tracker = wiki_root / ".wardrobe-cataloged-threads"
    if tracker.exists():
        return set(tracker.read_text().splitlines())
    return set()


def save_processed_threads(wiki_root: Path, threads: set) -> None:
    tracker = wiki_root / ".wardrobe-cataloged-threads"
    tracker.write_text("\n".join(sorted(threads)) + "\n")


def download_image(url: str, dest: Path, dry_run: bool = False) -> bool:
    if dest.exists():
        print(f"  [skip] image already exists: {dest.name}")
        return True
    if dry_run:
        print(f"  [dry-run] would download {url} → {dest.name}")
        return True
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = resp.read()
        dest.write_bytes(data)
        print(f"  [ok] downloaded {dest.name} ({len(data)//1024}KB)")
        return True
    except (urllib.error.URLError, Exception) as e:
        print(f"  [warn] image download failed: {e}")
        return False


def format_month_year(date_str: str) -> str:
    """'2025-09-23' → 'Sep 2025'"""
    d = datetime.strptime(date_str[:10], "%Y-%m-%d")
    return f"{MONTH_ABBR[d.month]} {d.year}"


def gmail_link(thread_id: str) -> str:
    return f"https://mail.google.com/mail/u/0/#inbox/{thread_id}"


def wayback_link(url: str) -> str:
    if not url:
        return ""
    return f"https://web.archive.org/web/*/{url}"


def build_wardrobe_line(item: dict, thread_id: str, month_year: str, image_filename: str | None) -> str:
    """Build a 2-tab Logseq bullet line for an entry inside a subsection (### level)."""
    brand = item["brand"]
    name = item["product_name"]
    color = item.get("color")
    size = item["size"]
    product_url = item.get("product_url", "")
    image_fn = image_filename

    descriptor = f"{color}, {size}" if color else size

    line = f"\t\t- [[{brand}]] {name} — {descriptor} ({month_year})"

    links = []
    if product_url:
        links.append(f"[product]({product_url})")
        links.append(f"[archive]({wayback_link(product_url)})")
    links.append(f"[receipt]({gmail_link(thread_id)})")

    line += " · " + " · ".join(links)

    if image_fn:
        line += f"\n\t\t\t- ![{brand} {name}](../assets/{image_fn})"

    return line


def build_section_line(item: dict, thread_id: str, month_year: str, image_filename: str | None) -> str:
    """Build bullet line for top-level sections (Outerwear, Footwear, etc)."""
    brand = item["brand"]
    name = item["product_name"]
    color = item.get("color")
    size = item["size"]
    product_url = item.get("product_url", "")
    image_fn = image_filename

    if color:
        descriptor = f"{color}, {size}"
    else:
        descriptor = size

    line = f"\t- [[{brand}]] {name} — {descriptor} ({month_year})"

    links = []
    if product_url:
        links.append(f"[product]({product_url})")
        links.append(f"[archive]({wayback_link(product_url)})")
    links.append(f"[receipt]({gmail_link(thread_id)})")

    line += " · " + " · ".join(links)

    if image_fn:
        line += f"\n\t\t- ![{brand} {name}](../assets/{image_fn})"

    return line


def add_receipt_link_to_existing(lines: list, search_text: str, thread_id: str, product_url: str) -> bool:
    """Find an existing wardrobe line and append receipt links if not already present."""
    receipt_link = gmail_link(thread_id)
    for i, line in enumerate(lines):
        if search_text in line:
            # Check if receipt link already present
            if thread_id in line or receipt_link in line:
                print(f"  [skip] receipt link already on line: {search_text[:60]}...")
                return True
            # Append links to end of line
            links = []
            if product_url:
                links.append(f"[product]({product_url})")
                links.append(f"[archive]({wayback_link(product_url)})")
            links.append(f"[receipt]({receipt_link})")
            lines[i] = line.rstrip() + " · " + " · ".join(links)
            print(f"  [ok] updated existing line: {search_text[:60]}...")
            return True
    return False


def find_section_insert_point(lines: list, section_header: str, subsection_header: str | None) -> int:
    """Return the line index after which to insert a new entry."""
    in_section = False
    in_subsection = not bool(subsection_header)  # True if no subsection needed
    last_entry_in_target = -1

    for i, line in enumerate(lines):
        stripped = line.strip()

        if not in_section:
            if section_header.strip() in stripped:
                in_section = True
            continue

        # Left the section? Another ## header signals end
        if re.search(r'^-?\s*##\s', stripped) and section_header.strip() not in stripped:
            break

        if subsection_header and not in_subsection:
            if subsection_header.strip() in stripped:
                in_subsection = True
            continue

        if in_subsection:
            # Left the subsection? Another ### header signals end
            if subsection_header and re.search(r'^-?\s*###\s', stripped) and subsection_header.strip() not in stripped:
                break
            # Any entry line containing [[ counts
            if "- [[" in line:
                last_entry_in_target = i

    return last_entry_in_target


def entry_already_exists(lines: list, brand: str, product_name: str, color: str | None, month_year: str) -> bool:
    """Check if a line for this brand+product+color+month_year already exists."""
    search = f"[[{brand}]] {product_name}"
    if color:
        search_with_color = f"{search} — {color}"
    else:
        search_with_color = search
    for line in lines:
        if search_with_color in line and month_year in line:
            return True
        # Also match without color if color is None
        if not color and search in line and month_year in line:
            return True
    return False


def insert_new_entry(lines: list, wardrobe_md: Path, item: dict, thread_id: str,
                     month_year: str, image_fn: str | None, dry_run: bool) -> None:
    """Insert a new wardrobe entry in the correct section."""
    brand = item.get("brand", "")
    color = item.get("color")

    # Dedup check before inserting
    if entry_already_exists(lines, brand, item["product_name"], color, month_year):
        print(f"  [skip] already in Wardrobe.md: {brand} {item['product_name']} ({month_year})")
        return

    section = item["wardrobe_section"]
    subsection = item.get("wardrobe_subsection")
    section_hdr = SECTION_HEADERS.get(section, f"## {section}")
    subsection_hdr = SUBSECTION_HEADERS.get(subsection) if subsection else None

    # Build the new line
    if subsection:
        new_line = build_wardrobe_line(item, thread_id, month_year, image_fn)
    else:
        new_line = build_section_line(item, thread_id, month_year, image_fn)

    insert_after = find_section_insert_point(lines, section_hdr, subsection_hdr)

    if insert_after == -1:
        # Fallback: insert right after the section header if no entries found
        header_to_find = section_hdr.strip() if not subsection_hdr else subsection_hdr.strip()
        header_idx = next((i for i, l in enumerate(lines) if header_to_find in l.strip()), -1)
        if header_idx != -1:
            lines.insert(header_idx + 1, new_line)
            print(f"  [ok] inserted new entry after section header ({header_to_find}): {item['product_name']}")
        else:
            print(f"  [warn] section '{section}'/'{subsection}' not found — appending at end")
            lines.append(new_line)
    else:
        lines.insert(insert_after + 1, new_line)
        print(f"  [ok] inserted new entry after line {insert_after+1}: {item['product_name']}")


def update_wardrobe_md(wardrobe_md: Path, receipt: dict, item: dict,
                       image_fn: str | None, dry_run: bool) -> None:
    """Apply one item update to Wardrobe.md."""
    thread_id = receipt["thread_id"]
    month_year = format_month_year(receipt["order_date"])
    product_url = item.get("product_url", "")

    lines = wardrobe_md.read_text().splitlines()

    existing_search = item.get("existing_search")
    if existing_search:
        found = add_receipt_link_to_existing(lines, existing_search, thread_id, product_url)
        if not found:
            print(f"  [warn] existing_search not found, inserting as new: {existing_search}")
            item_with_brand = dict(item)
            item_with_brand["brand"] = item.get("brand", receipt.get("brand", ""))
            insert_new_entry(lines, wardrobe_md, item_with_brand, thread_id, month_year, image_fn, dry_run)
    else:
        item_with_brand = dict(item)
        item_with_brand["brand"] = item.get("brand", receipt.get("brand", ""))
        insert_new_entry(lines, wardrobe_md, item_with_brand, thread_id, month_year, image_fn, dry_run)

    if not dry_run:
        wardrobe_md.write_text("\n".join(lines) + "\n")


def update_brand_page(pages_dir: Path, receipt: dict, item: dict,
                      image_fn: str | None, dry_run: bool) -> None:
    """Create or update a brand page for this item."""
    brand = receipt["brand"]
    month_year = format_month_year(receipt["order_date"])
    year = receipt["order_date"][:4]
    thread_id = receipt["thread_id"]
    product_url = item.get("product_url", "")
    color = item.get("color")
    size = item["size"]
    price = item.get("price", 0)
    name = item["product_name"]

    descriptor = f"{color}, {size}" if color else size

    # Safe filename: replace spaces with hyphens, remove unsafe chars
    safe_brand = brand.replace(" ", " ")  # keep spaces for Logseq
    brand_file = pages_dir / f"{brand}.md"

    receipt_link = gmail_link(thread_id)

    # Build purchase entry block
    purchase_lines = []
    purchase_lines.append(f"\t\t\t- **{name}** — {descriptor} ({month_year})")
    if image_fn:
        purchase_lines.append(f"\t\t\t\t- ![{brand} {name}](../assets/{image_fn})")
    price_str = "Free" if price == 0.0 else (f"${price:.2f}" if price else "price unknown")
    detail_parts = [f"Purchased {month_year} · {price_str}"]
    if product_url:
        detail_parts.append(f"[product]({product_url})")
        detail_parts.append(f"[archive]({wayback_link(product_url)})")
    detail_parts.append(f"[receipt]({receipt_link})")
    purchase_lines.append(f"\t\t\t\t- " + " · ".join(detail_parts))
    purchase_block = "\n".join(purchase_lines)

    if not brand_file.exists():
        content = f"""tags:: [[Clothing]], [[Brand]], [[Shopping]]

- **{brand}**
- ## Purchases
\t- ### {year}
{purchase_block}
- ## Related
\t- [[Wardrobe]]
"""
        print(f"  [ok] creating brand page: {brand_file.name}")
        if not dry_run:
            brand_file.write_text(content)
    else:
        text = brand_file.read_text()
        # Check if this item is already recorded
        if name in text and month_year in text:
            print(f"  [skip] {brand} page already has {name} ({month_year})")
            return

        lines = text.splitlines()
        year_hdr = f"\t- ### {year}"

        # Find or insert the year section
        year_idx = next((i for i, l in enumerate(lines) if year_hdr.strip() in l.strip()), -1)

        if year_idx == -1:
            # Find ## Purchases and insert year section after it
            purchases_idx = next((i for i, l in enumerate(lines) if "## Purchases" in l), -1)
            if purchases_idx == -1:
                lines.append("\n- ## Purchases")
                lines.append(year_hdr)
                purchases_idx = len(lines) - 1
                year_idx = purchases_idx
            else:
                lines.insert(purchases_idx + 1, year_hdr)
                year_idx = purchases_idx + 1

        # Insert purchase block after year header
        insert_at = year_idx + 1
        for new_line in reversed(purchase_block.splitlines()):
            lines.insert(insert_at, new_line)

        print(f"  [ok] updated brand page: {brand_file.name}")
        if not dry_run:
            brand_file.write_text("\n".join(lines) + "\n")


def main():
    parser = argparse.ArgumentParser(description="Catalog clothing receipts into Logseq wiki")
    parser.add_argument("--wiki-root", required=True, help="Path to the wiki git repo root")
    parser.add_argument("--receipts", default=str(SCRIPT_DIR / "receipts.json"),
                        help="Path to receipts.json (default: next to this script)")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without writing")
    parser.add_argument("--skip-processed", action="store_true",
                        help="Skip receipts whose thread_id is in .wardrobe-cataloged-threads")
    args = parser.parse_args()

    wiki_root = Path(args.wiki_root).resolve()
    wardrobe_md = wiki_root / "logseq" / "pages" / "Wardrobe.md"
    assets_dir = wiki_root / "logseq" / "assets"
    pages_dir = wiki_root / "logseq" / "pages"

    if not wardrobe_md.exists():
        print(f"ERROR: Wardrobe.md not found at {wardrobe_md}")
        sys.exit(1)

    receipts_path = Path(args.receipts)
    if not receipts_path.exists():
        print(f"ERROR: receipts.json not found at {receipts_path}")
        sys.exit(1)

    receipts_data = json.loads(receipts_path.read_text())
    processed = load_processed_threads(wiki_root) if args.skip_processed else set()

    total_items = 0
    skipped_items = 0
    new_images = 0

    for receipt in receipts_data["receipts"]:
        thread_id = receipt["thread_id"]
        brand = receipt["brand"]
        order_num = receipt["order_number"]
        order_date = receipt["order_date"]

        if args.skip_processed and thread_id in processed:
            print(f"\n[SKIP] Already processed: {brand} #{order_num} (thread {thread_id})")
            continue

        print(f"\n{'='*60}")
        print(f"Processing: {brand} #{order_num} ({order_date}) — thread {thread_id}")

        for item in receipt["items"]:
            total_items += 1
            print(f"\n  Item: {item['product_name']} — {item.get('color','')} {item['size']}")

            # Step 1: Download image
            image_fn = item.get("image_filename")
            image_url = item.get("image_url")
            downloaded = False

            if image_url and image_fn:
                dest = assets_dir / image_fn
                downloaded = download_image(image_url, dest, args.dry_run)
                if downloaded:
                    new_images += 1

            # Attach brand to item for line building
            item["brand"] = brand

            # Step 2: Update Wardrobe.md
            update_wardrobe_md(wardrobe_md, receipt, item,
                               image_fn if downloaded else None, args.dry_run)

            # Step 3: Update brand page
            update_brand_page(pages_dir, receipt, item,
                              image_fn if downloaded else None, args.dry_run)

        processed.add(thread_id)

    # Save processed thread IDs
    if not args.dry_run:
        save_processed_threads(wiki_root, processed)

    print(f"\n{'='*60}")
    print(f"Done. Processed {total_items} items, {new_images} images downloaded.")
    if args.dry_run:
        print("[DRY RUN — no files were modified]")


if __name__ == "__main__":
    main()
