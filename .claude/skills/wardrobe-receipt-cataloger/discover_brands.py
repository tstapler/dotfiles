#!/usr/bin/env python3
"""
discover_brands.py — Scan Gmail for all clothing brand order confirmations.

Searches for purchase/order confirmation emails across all history, extracts
unique senders, and classifies them as likely clothing brands vs. non-clothing.
Outputs a ranked list of brands not yet in receipts.json.

Usage:
  python3 discover_brands.py [--receipts /path/to/receipts.json] [--output brands_found.json]

Requires: gmail MCP credentials (run within Claude Code session), or pass
  --gmail-export /path/to/exported_senders.txt (one "sender|subject" per line).
"""
import json
import re
import sys
from pathlib import Path
from collections import defaultdict

SCRIPT_DIR = Path(__file__).parent

# Known non-clothing senders to skip (domain patterns)
SKIP_DOMAINS = {
    "amazon.com", "paypal.com", "usps.com", "fedex.com", "ups.com",
    "shop.app", "tixr.com", "google.com", "apple.com", "github.com",
    "lollapalooza.com", "zola.com", "chipotle.com", "mcdonalds.com",
    "vanguard.com", "chewy.com", "toasttab.com", "paramount.com",
    "informeddelivery.usps.com", "shopifyemail.com",
    "express-scripts.com", "bedjet.com", "aussiechiller.com",
    "skilhunt.com", "iship.com",
}

# Known clothing brand senders (already cataloged or confirmed)
KNOWN_CLOTHING = {
    "thetiebar.com", "roark.com", "1620usa.com", "patagonia.com",
    "na.patagonia.com", "strauss.com", "bombas.com", "bonobos.com",
    "westernrise.com", "tripleaughtdesign.com", "vuoriclothing.com",
    "rei.com", "dandydelmar.com", "lululemon.com", "likenew.lululemon.com",
    "enwild.com", "campsaver.com", "huckberry.com", "marmot.com",
    "llbean.com", "jcrew.com", "fanatics.com", "chubbiesshorts.com",
    "oascompany.com", "kuhl.com", "hellyhansen.com", "teddystratford.com",
    "express.com", "narvar.com",  # narvar = express shipping
    "blundstone.com", "royalrobbins.com", "prana.com", "1620workwear.com",
}

# Clothing keyword signals in subject lines
CLOTHING_SUBJECT_KEYWORDS = [
    "shirt", "pant", "jacket", "short", "shoe", "boot", "hoodie",
    "coat", "vest", "blazer", "tee", "sweater", "pullover", "polo",
    "trouser", "chino", "denim", "jean", "sock", "underwear", "brief",
    "apparel", "clothing", "wear", "fashion", "outfit", "wardrobe",
    "gear", "performance", "athletic", "sport", "merino", "fleece",
    "linen", "cotton", "wool", "nylon", "puffer", "anorak", "poncho",
    "scarf", "beanie", "hat", "cap", "glove", "pocket square", "tie",
    "sneaker", "loafer", "oxford", "chelsea", "sandal",
]


def extract_domain(sender: str) -> str:
    """Extract domain from 'Name <email@domain.com>' or 'email@domain.com'."""
    m = re.search(r'@([a-zA-Z0-9._-]+\.[a-zA-Z]{2,})', sender)
    if m:
        domain = m.group(1).lower()
        # Strip common subdomain prefixes that are not brand-specific
        for prefix in ["email.", "e.", "e1.", "notices.", "e.", "mail.", "no-reply.", "noreply.", "support.", "shop.", "order.", "orders.", "help.", "orderreply@"]:
            if domain.startswith(prefix):
                domain = domain[len(prefix):]
        return domain
    return ""


def is_clothing_subject(subject: str) -> bool:
    s = subject.lower()
    return any(kw in s for kw in CLOTHING_SUBJECT_KEYWORDS)


def load_known_brands(receipts_path: Path) -> set:
    """Load thread IDs and brands already in receipts.json."""
    if not receipts_path.exists():
        return set()
    data = json.loads(receipts_path.read_text())
    brands = set()
    for r in data.get("receipts", []):
        brands.add(r["brand"].lower())
    return brands


def analyze_threads(threads: list) -> dict:
    """
    Analyze a list of thread dicts (from Gmail search results).
    Each thread has: id, messages[{sender, subject, date, snippet}]
    Returns dict: domain -> {count, subjects, dates, senders, likely_clothing}
    """
    brands = defaultdict(lambda: {
        "count": 0,
        "subjects": [],
        "dates": [],
        "senders": set(),
        "likely_clothing": False,
        "domain": "",
    })

    for thread in threads:
        for msg in thread.get("messages", []):
            sender = msg.get("sender", "")
            subject = msg.get("subject", "")
            date = msg.get("date", "")
            domain = extract_domain(sender)

            if not domain:
                continue

            # Skip known non-clothing domains
            if any(skip in domain for skip in SKIP_DOMAINS):
                continue

            entry = brands[domain]
            entry["count"] += 1
            entry["domain"] = domain
            entry["senders"].add(sender)
            if subject not in entry["subjects"]:
                entry["subjects"].append(subject)
            if date:
                entry["dates"].append(date)

            if domain in KNOWN_CLOTHING or is_clothing_subject(subject):
                entry["likely_clothing"] = True

    return dict(brands)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Discover clothing brands from Gmail threads JSON")
    parser.add_argument("--threads-json", required=True,
                        help="Path to JSON file containing Gmail thread search results")
    parser.add_argument("--receipts", default=str(SCRIPT_DIR / "receipts.json"),
                        help="Path to receipts.json (to exclude already-cataloged brands)")
    parser.add_argument("--output", default=str(SCRIPT_DIR / "brands_found.json"),
                        help="Output JSON path")
    parser.add_argument("--clothing-only", action="store_true",
                        help="Only show likely clothing brands")
    args = parser.parse_args()

    threads_data = json.loads(Path(args.threads_json).read_text())
    # Support both {"threads": [...]} and raw list
    threads = threads_data if isinstance(threads_data, list) else threads_data.get("threads", [])

    known_brands = load_known_brands(Path(args.receipts))
    brands = analyze_threads(threads)

    # Sort by clothing likelihood then count
    sorted_brands = sorted(
        brands.values(),
        key=lambda b: (not b["likely_clothing"], -b["count"])
    )

    if args.clothing_only:
        sorted_brands = [b for b in sorted_brands if b["likely_clothing"]]

    # Convert sets to lists for JSON
    for b in sorted_brands:
        b["senders"] = sorted(b["senders"])
        b["dates"] = sorted(b["dates"], reverse=True)[:3]  # last 3 dates
        b["subjects"] = b["subjects"][:5]  # first 5 subjects
        b["already_cataloged"] = any(
            kb in b["domain"] or b["domain"] in kb
            for kb in known_brands
        )

    output = {
        "total_unique_domains": len(sorted_brands),
        "likely_clothing": sum(1 for b in sorted_brands if b["likely_clothing"]),
        "brands": sorted_brands,
    }

    Path(args.output).write_text(json.dumps(output, indent=2))
    print(f"Found {len(sorted_brands)} unique senders ({output['likely_clothing']} likely clothing)")
    print(f"Output: {args.output}")

    print("\n=== Likely Clothing Brands ===")
    for b in sorted_brands:
        if b["likely_clothing"]:
            status = "[CATALOGED]" if b["already_cataloged"] else "[NEW]"
            latest = b["dates"][0][:10] if b["dates"] else "?"
            print(f"  {status} {b['domain']} ({b['count']} emails, latest {latest})")


if __name__ == "__main__":
    main()
