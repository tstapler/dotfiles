from __future__ import annotations

from pathlib import Path
from typing import Optional
from models import ScanResults


def generate_markdown_report(results: ScanResults, output_path: Optional[Path] = None) -> str:
    high_conf = [a for a in results.albums if a.date_confidence == "high"]
    med_conf = [a for a in results.albums if a.date_confidence == "medium"]
    low_conf = [a for a in results.albums if a.date_confidence == "low"]
    flagged = [a for a in results.albums if a.needs_review]
    with_loc = [a for a in results.albums if a.inferred_location]

    total_images = sum(a.file_stats.images_count for a in results.albums)
    total_videos = sum(a.file_stats.videos_count for a in results.albums)

    md = []
    md.append(f"# Google Photos Import & Metadata Mapping Report")
    md.append(f"**Scanned Root**: `{results.source_root}`  ")
    md.append(f"**Timestamp**: `{results.timestamp}`  ")
    md.append(f"**Total Folders/Albums**: `{results.total_albums}`  ")
    md.append(f"**Total Media Files**: `{results.total_media_files}` (`{total_images}` images, `{total_videos}` videos)  ")
    md.append(f"**Flagged for Review**: `{len(flagged)}`  ")
    md.append("")

    md.append("## Summary Statistics")
    md.append("| Category | Count | Percentage | Description |")
    md.append("|---|---|---|---|")
    md.append(f"| High Confidence Dates | {len(high_conf)} | {len(high_conf)/results.total_albums*100:.1f}% | Exact YYYY-MM-DD in folder title |")
    md.append(f"| Medium Confidence Dates | {len(med_conf)} | {len(med_conf)/results.total_albums*100:.1f}% | Year/Month/Season/Holiday matched |")
    md.append(f"| Needs Review / Questionable | {len(flagged)} | {len(flagged)/results.total_albums*100:.1f}% | Flagged for LLM/User verification |")
    md.append(f"| Tagged Locations | {len(with_loc)} | {len(with_loc)/results.total_albums*100:.1f}% | Geocoded city/landmark matched |")
    md.append("")

    if flagged:
        md.append("## 🚩 Questionable Data Flagged for Review")
        md.append("| Severity | Original Folder | Mapped Album Name | Issue / Flag Reasons |")
        md.append("|---|---|---|---|")
        for a in sorted(flagged, key=lambda x: (x.flag_severity != "high", x.flag_severity != "medium")):
            reasons_str = "; ".join(a.flag_reasons)
            md.append(f"| **{a.flag_severity.upper()}** | `{a.folder_name}` | `{a.album_name}` | {reasons_str} |")
        md.append("")

    if with_loc:
        md.append("## 📍 Mapped Locations")
        md.append("| Original Folder | Inferred Location | Coordinates |")
        md.append("|---|---|---|")
        for a in with_loc:
            loc = a.inferred_location
            md.append(f"| `{a.folder_name}` | **{loc.name}** | `({loc.lat}, {loc.lon})` |")
        md.append("")

    md.append("## 📁 Full Directory Mapping Index")
    md.append("| Folder Name | Mapped Album Title | Inferred Date | Confidence | Location | Review Needed |")
    md.append("|---|---|---|---|---|---|")
    for a in results.albums:
        date_str = a.inferred_date or "*Unset*"
        loc_str = a.inferred_location.name if a.inferred_location else "-"
        rev_str = f"🚩 YES ({a.flag_severity})" if a.needs_review else "OK"
        md.append(f"| `{a.folder_name}` | `{a.album_name}` | `{date_str}` | {a.date_confidence} | {loc_str} | {rev_str} |")

    content = "\n".join(md)

    if output_path:
        output_path.write_text(content)

    return content
