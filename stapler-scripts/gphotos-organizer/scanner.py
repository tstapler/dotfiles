from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from loguru import logger
from locations import find_location_in_string
from models import AlbumMapping, FileStats, LocationInfo, ScanResults

MEDIA_EXTENSIONS = {
    "images": {".jpg", ".jpeg", ".png", ".heic", ".webp", ".bmp", ".gif", ".tiff", ".tif"},
    "videos": {".mp4", ".mov", ".3gp", ".m4v", ".webm", ".avi", ".mod", ".mkv"},
}

EXIFTOOL_PATH = os.environ.get("EXIFTOOL_PATH", "/home/linuxbrew/.linuxbrew/bin/exiftool")


def sanitize_id(folder_path: Path, root_path: Path) -> str:
    try:
        rel = folder_path.relative_to(root_path)
        rel_str = str(rel)
    except ValueError:
        rel_str = str(folder_path)
    return hashlib.md5(rel_str.encode("utf-8")).hexdigest()[:12]


def parse_date_and_location(folder_name: str) -> Tuple[Optional[str], str, str, Optional[LocationInfo]]:
    """Returns (inferred_date_str, date_confidence, date_source, inferred_location)."""
    
    # 1. Exact full date: YYYY-MM-DD or YYYY-M-D or YYYY.MM.DD or YYYY_MM_DD
    m_full = re.search(r"\b(19\d\d|20\d\d)[-._](\d{1,2})[-._](\d{1,2})\b", folder_name)
    if m_full:
        y, m, d = int(m_full.group(1)), int(m_full.group(2)), int(m_full.group(3))
        if 1 <= m <= 12 and 1 <= d <= 31:
            date_str = f"{y:04d}:{m:02d}:{d:02d} 12:00:00"
            loc = find_location_in_string(folder_name)
            return date_str, "high", "folder_full_date", loc

    # 2. Year + Month: YYYY-MM or YYYY-M
    m_ym = re.search(r"\b(19\d\d|20\d\d)[-._](\d{1,2})\b", folder_name)
    if m_ym:
        y, m = int(m_ym.group(1)), int(m_ym.group(2))
        if 1 <= m <= 12:
            day = 15
            fn_lower = folder_name.lower()
            if "christmas" in fn_lower or "xmas" in fn_lower:
                m, day = 12, 25
            elif "father" in fn_lower:
                m, day = 6, 15
            elif "mother" in fn_lower:
                m, day = 5, 10
            elif "halloween" in fn_lower:
                m, day = 10, 31
            date_str = f"{y:04d}:{m:02d}:{day:02d} 12:00:00"
            loc = find_location_in_string(folder_name)
            return date_str, "medium", "folder_year_month", loc

    # 3. Year range: YYYY-YYYY or YYYY-present
    m_range = re.search(r"\b(19\d\d|20\d\d)-(19\d\d|20\d\d|present)\b", folder_name, re.IGNORECASE)
    if m_range:
        y1 = int(m_range.group(1))
        date_str = f"{y1:04d}:01:01 12:00:00"
        loc = find_location_in_string(folder_name)
        return date_str, "medium", "folder_year_range", loc

    # 4. Single year: YYYY
    m_year = re.search(r"\b(19\d\d|20\d\d)\b", folder_name)
    if m_year:
        y = int(m_year.group(1))
        m, day = 1, 1
        fn_lower = folder_name.lower()
        if "christmas" in fn_lower or "xmas" in fn_lower:
            m, day = 12, 25
        elif "father" in fn_lower:
            m, day = 6, 15
        elif "mother" in fn_lower:
            m, day = 5, 10
        elif "halloween" in fn_lower:
            m, day = 10, 31
        elif "graduation" in fn_lower or "grad" in fn_lower:
            m, day = 6, 15
        date_str = f"{y:04d}:{m:02d}:{day:02d} 12:00:00"
        loc = find_location_in_string(folder_name)
        return date_str, "medium", "folder_year", loc

    loc = find_location_in_string(folder_name)
    return None, "low", "none", loc


def clean_album_name(folder_name: str) -> str:
    name = folder_name.strip()
    name = re.sub(r"\s+", " ", name)
    return name


def inspect_folder_fast(folder_path: Path) -> Tuple[FileStats, List[Path]]:
    stats = FileStats()
    media_files = []

    try:
        with os.scandir(folder_path) as it:
            for entry in it:
                if entry.is_file(follow_symlinks=False):
                    stats.total_files += 1
                    ext = os.path.splitext(entry.name)[1].lower()
                    if ext in MEDIA_EXTENSIONS["images"]:
                        stats.images_count += 1
                        media_files.append(Path(entry.path))
                    elif ext in MEDIA_EXTENSIONS["videos"]:
                        stats.videos_count += 1
                        media_files.append(Path(entry.path))
                    else:
                        stats.non_media_count += 1
    except Exception as e:
        logger.error(f"Error scanning {folder_path}: {e}")

    return stats, media_files


def evaluate_album_flags(album: AlbumMapping, album_names_seen: Dict[str, str]) -> None:
    """Evaluates quality and ambiguity rules to set flag_reasons, needs_review, and flag_severity."""
    flags: List[str] = []
    severity = "none"

    media_cnt = album.file_stats.images_count + album.file_stats.videos_count

    # 1. Missing date
    if not album.inferred_date or album.date_confidence == "low":
        flags.append("MISSING_DATE: No year or date extracted from folder title")
        severity = "high"

    # 2. Broad or open date range (e.g. 1980-present or 1965-1980)
    if album.date_source == "folder_year_range" or "present" in album.folder_name.lower():
        flags.append("BROAD_DATE_RANGE: Folder covers multiple years or open range")
        if severity != "high":
            severity = "medium"

    # 3. Empty album
    if media_cnt == 0:
        flags.append("EMPTY_ALBUM: Folder contains 0 photo/video files")
        severity = "high"

    # 4. Duplicate or near-duplicate album name
    clean_name_lower = album.album_name.lower()
    if clean_name_lower in album_names_seen and album_names_seen[clean_name_lower] != album.id:
        flags.append(f"DUPLICATE_NAME: Shares album title with another folder")
        if severity != "high":
            severity = "medium"
    else:
        album_names_seen[clean_name_lower] = album.id

    # 5. Major event / trip without mapped location
    fn_lower = album.folder_name.lower()
    event_keywords = {"trip", "cruise", "vacation", "wedding", "graduation", "funeral", "reunion"}
    if any(k in fn_lower for k in event_keywords) and not album.inferred_location:
        flags.append("UNMAPPED_LOCATION: Event/trip folder missing location metadata hint")
        if severity == "none":
            severity = "low"

    if flags:
        album.needs_review = True
        album.flag_reasons = flags
        album.flag_severity = severity


def scan_usb_drive(source_root: Path, sample_exif: bool = False) -> ScanResults:
    logger.info(f"Scanning USB drive at: {source_root}")
    results = ScanResults(
        timestamp=datetime.now().isoformat(),
        source_root=str(source_root),
    )

    if not source_root.exists():
        raise FileNotFoundError(f"Source directory does not exist: {source_root}")

    subdirs = [p for p in source_root.iterdir() if p.is_dir() and not p.name.startswith(".")]

    total_media = 0
    mapped_albums: List[AlbumMapping] = []
    album_names_seen: Dict[str, str] = {}

    for folder_path in sorted(subdirs, key=lambda p: p.name.lower()):
        folder_name = folder_path.name
        
        if folder_name.lower() in {"system volume information", "$recycle.bin", ".trashes"}:
            continue

        file_stats, media_files = inspect_folder_fast(folder_path)

        if file_stats.images_count == 0 and file_stats.videos_count == 0:
            nested_subdirs = [p for p in folder_path.iterdir() if p.is_dir()]
            if nested_subdirs:
                for sub in nested_subdirs:
                    sub_stats, sub_media = inspect_folder_fast(sub)
                    if sub_stats.images_count > 0 or sub_stats.videos_count > 0:
                        inferred_date, conf, src, loc = parse_date_and_location(f"{folder_name} - {sub.name}")
                        album = AlbumMapping(
                            id=sanitize_id(sub, source_root),
                            source_path=str(sub),
                            folder_name=f"{folder_name}/{sub.name}",
                            album_name=clean_album_name(f"{folder_name} - {sub.name}"),
                            inferred_date=inferred_date,
                            date_confidence=conf,
                            date_source=src,
                            inferred_location=loc,
                            file_stats=sub_stats,
                        )
                        evaluate_album_flags(album, album_names_seen)
                        mapped_albums.append(album)
                        total_media += (sub_stats.images_count + sub_stats.videos_count)
            else:
                # Flag empty folder
                inferred_date, conf, src, loc = parse_date_and_location(folder_name)
                album = AlbumMapping(
                    id=sanitize_id(folder_path, source_root),
                    source_path=str(folder_path),
                    folder_name=folder_name,
                    album_name=clean_album_name(folder_name),
                    inferred_date=inferred_date,
                    date_confidence=conf,
                    date_source=src,
                    inferred_location=loc,
                    file_stats=file_stats,
                )
                evaluate_album_flags(album, album_names_seen)
                mapped_albums.append(album)
            continue

        inferred_date, conf, src, loc = parse_date_and_location(folder_name)

        album = AlbumMapping(
            id=sanitize_id(folder_path, source_root),
            source_path=str(folder_path),
            folder_name=folder_name,
            album_name=clean_album_name(folder_name),
            inferred_date=inferred_date,
            date_confidence=conf,
            date_source=src,
            inferred_location=loc,
            file_stats=file_stats,
        )

        evaluate_album_flags(album, album_names_seen)
        mapped_albums.append(album)
        total_media += (file_stats.images_count + file_stats.videos_count)

    flagged_cnt = sum(1 for a in mapped_albums if a.needs_review)

    results.total_albums = len(mapped_albums)
    results.total_media_files = total_media
    results.flagged_albums_count = flagged_cnt
    results.albums = mapped_albums

    logger.success(f"Fast scan complete: {len(mapped_albums)} albums mapped ({flagged_cnt} flagged for review) with {total_media} media files.")
    return results
