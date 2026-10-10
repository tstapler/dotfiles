from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from locations import find_location_in_string
from models import AlbumMapping, ScanResults


def enrich_mapping_data(mapping_file: Path) -> Tuple[int, List[Dict[str, str]]]:
    data = json.loads(mapping_file.read_text())
    results = ScanResults(**data)

    updated_count = 0
    updates_summary: List[Dict[str, str]] = []

    for album in results.albums:
        source_path = Path(album.source_path)
        folder_name = album.folder_name

        inferred_date = album.inferred_date
        inferred_loc = album.inferred_location
        reasons_before = list(album.flag_reasons)

        # 1. Folder Title Embedded Hints (e.g. facebook2014 -> 2014)
        m_title_year = re.search(r"(19\d\d|20\d\d)", folder_name)
        if not inferred_date and m_title_year:
            y = m_title_year.group(1)
            inferred_date = f"{y}:01:01 12:00:00"
            album.date_source = "folder_title_embedded"
            album.date_confidence = "medium"

        # 2. Known Family Event Context
        fn_lower = folder_name.lower()
        if not inferred_date:
            if "natasha 60th" in fn_lower:
                inferred_date = "2022:10:22 12:00:00"
                album.date_source = "family_event_context"
                album.date_confidence = "medium"
            elif "lets make a deal" in fn_lower:
                inferred_date = "2020:08:13 12:00:00"
                album.date_source = "family_event_context"
                album.date_confidence = "medium"

        # 3. Location Inferences
        if not inferred_loc:
            loc = find_location_in_string(folder_name)
            if loc:
                inferred_loc = loc

        # 4. Filename Inspection
        dates_from_files = set()
        years_from_files = set()

        if source_path.exists():
            try:
                with os.scandir(source_path) as it:
                    for entry in it:
                        if entry.is_file(follow_symlinks=False):
                            fn = entry.name
                            m_dt = re.search(r"\b(19\d\d|20\d\d)[-._]?(\d{2})[-._]?(\d{2})\b", fn)
                            m_yr = re.search(r"\b(19\d\d|20\d\d)\b", fn)
                            if m_dt:
                                y, m, d = m_dt.group(1), m_dt.group(2), m_dt.group(3)
                                if 1 <= int(m) <= 12 and 1 <= int(d) <= 31:
                                    # Filter out scan dates like 2024 or 2025 if photo is old
                                    if int(y) < 2024:
                                        dates_from_files.add(f"{y}:{m}:{d} 12:00:00")
                                        years_from_files.add(y)
                            elif m_yr and int(m_yr.group(1)) < 2024:
                                years_from_files.add(m_yr.group(1))
            except Exception:
                pass

        if not inferred_date:
            if dates_from_files:
                sorted_dates = sorted(list(dates_from_files))
                inferred_date = sorted_dates[0]
                album.date_source = "file_name_inspection"
                album.date_confidence = "medium"
            elif years_from_files:
                sorted_years = sorted(list(years_from_files))
                inferred_date = f"{sorted_years[0]}:01:01 12:00:00"
                album.date_source = "file_name_year_inspection"
                album.date_confidence = "medium"

        # Apply changes if anything was inferred
        changed = False
        if inferred_date and inferred_date != album.inferred_date:
            album.inferred_date = inferred_date
            changed = True

        if inferred_loc and album.inferred_location != inferred_loc:
            album.inferred_location = inferred_loc
            changed = True

        if changed:
            # Re-evaluate flags
            album.flag_reasons = [r for r in album.flag_reasons if not r.startswith("MISSING_DATE")]
            if not album.flag_reasons:
                album.needs_review = False
                album.flag_severity = "none"

            updated_count += 1
            updates_summary.append({
                "folder_name": folder_name,
                "inferred_date": album.inferred_date or "-",
                "inferred_location": album.inferred_location.name if album.inferred_location else "-",
                "source": album.date_source,
            })

    results.flagged_albums_count = sum(1 for a in results.albums if a.needs_review)
    mapping_file.write_text(json.dumps(results.model_dump(), indent=2))

    return updated_count, updates_summary
