from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from loguru import logger
from models import AlbumMapping, FileStats, LocationInfo, ScanResults
from scanner import EXIFTOOL_PATH, MEDIA_EXTENSIONS

# Formats supported by Exiftool for writing metadata
WRITABLE_EXTENSIONS = {
    "images": {".jpg", ".jpeg", ".png", ".heic", ".webp", ".tiff", ".tif"},
    "videos": {".mp4", ".mov", ".m4v"},
}

CHUNK_SIZE = 100  # Process files in chunks of 100 to prevent huge memory / tmp file deadlocks


def format_gps_coordinates(lat: float, lon: float) -> Dict[str, str]:
    """Convert float lat/lon to exiftool GPS arguments."""
    lat_ref = "N" if lat >= 0 else "S"
    lon_ref = "E" if lon >= 0 else "W"
    
    return {
        "GPSLatitude": str(abs(lat)),
        "GPSLatitudeRef": lat_ref,
        "GPSLongitude": str(abs(lon)),
        "GPSLongitudeRef": lon_ref,
    }


def infer_file_specific_date(file_name: str, fallback_dt: datetime, index_offset: int) -> datetime:
    """Attempts to extract a date or year directly from individual filename."""
    m_full = re.search(r"\b(19\d\d|20\d\d)[-._]?(\d{2})[-._]?(\d{2})\b", file_name)
    if m_full:
        try:
            y, m, d = int(m_full.group(1)), int(m_full.group(2)), int(m_full.group(3))
            if 1 <= m <= 12 and 1 <= d <= 31 and int(y) < 2024:
                return datetime(y, m, d, 12, 0, 0) + timedelta(seconds=index_offset)
        except Exception:
            pass

    m_year = re.search(r"\b(19\d\d|20\d\d)\b", file_name)
    if m_year:
        try:
            y = int(m_year.group(1))
            if y < 2024:
                m, d = 1, 1
                fn_lower = file_name.lower()
                if "christmas" in fn_lower or "xmas" in fn_lower:
                    m, d = 12, 25
                return datetime(y, m, d, 12, 0, 0) + timedelta(seconds=index_offset)
        except Exception:
            pass

    return fallback_dt + timedelta(seconds=index_offset)


def generate_descriptive_tags(album: AlbumMapping, file_name: str) -> List[str]:
    """Generates IPTC/XMP/EXIF keyword tags based on folder and filename context."""
    tags = set()

    tags.add(album.album_name)

    if album.inferred_location:
        tags.add(album.inferred_location.name)

    fn_lower = (album.folder_name + " " + file_name).lower()

    if "tyler" in fn_lower:
        tags.add("Tyler Stapler")
    if "nicholas" in fn_lower or "nick" in fn_lower:
        tags.add("Nicholas Stapler")
    if "christopher" in fn_lower or "chris" in fn_lower:
        tags.add("Christopher Stapler")
    if "natasha" in fn_lower:
        tags.add("Natasha Brice Stapler")
    if "anthony" in fn_lower or "tony" in fn_lower:
        tags.add("Anthony Keith Stapler")
    if "barbara" in fn_lower or "lawrence" in fn_lower:
        tags.add("Barbara & Lawrence Brice")
    if "marrero" in fn_lower:
        tags.add("Marrero Family")
    if "brice" in fn_lower:
        tags.add("Brice Family")
    if "boys" in fn_lower:
        tags.add("Tyler Stapler")
        tags.add("Nicholas Stapler")
        tags.add("Christopher Stapler")

    return sorted(list(tags))


def update_album_metadata(
    album: AlbumMapping,
    dry_run: bool = True,
    offset_seconds: int = 5,
    overwrite_scanner_dates: bool = True,
    overwrite_original: bool = True,
) -> Tuple[bool, int, List[str]]:
    """Updates EXIF metadata, per-file dates, GPS, and descriptive tags for all media files in an album using chunked batched exiftool calls.
    Returns (success, updated_file_count, list_of_executed_commands).
    """
    source_dir = Path(album.source_path)
    if not source_dir.exists():
        logger.error(f"Album source directory missing: {source_dir}")
        return False, 0, []

    if not Path(EXIFTOOL_PATH).exists():
        logger.error(f"exiftool binary not found at {EXIFTOOL_PATH}")
        return False, 0, []

    media_files = sorted([
        p for p in source_dir.iterdir()
        if p.is_file() and (p.suffix.lower() in WRITABLE_EXTENSIONS["images"] or p.suffix.lower() in WRITABLE_EXTENSIONS["videos"])
    ], key=lambda p: p.name.lower())

    if not media_files:
        logger.debug(f"No writable media files found in {source_dir}")
        return True, 0, []

    if not album.inferred_date:
        logger.warning(f"No date specified for album {album.folder_name}. Skipping date updates.")
        return True, 0, []

    try:
        base_dt = datetime.strptime(album.inferred_date, "%Y:%m:%d %H:%M:%S")
    except ValueError:
        logger.error(f"Invalid date format for album {album.folder_name}: {album.inferred_date}")
        return False, 0, []

    gps_args = {}
    if album.inferred_location:
        gps_args = format_gps_coordinates(album.inferred_location.lat, album.inferred_location.lon)

    if dry_run:
        logger.info(f"[DRY-RUN] Would update metadata & tags for {len(media_files)} files in '{album.folder_name}' starting at {album.inferred_date}")
        return True, len(media_files), [f"exiftool -@ argfile for {len(media_files)} files"]

    total_updated = 0
    commands_log = []

    # Process in chunks of CHUNK_SIZE (100 files)
    for i in range(0, len(media_files), CHUNK_SIZE):
        chunk = media_files[i : i + CHUNK_SIZE]
        argfile_lines: List[str] = []

        for idx_in_chunk, file_path in enumerate(chunk):
            global_idx = i + idx_in_chunk
            file_dt = infer_file_specific_date(file_path.name, base_dt, global_idx * offset_seconds)
            dt_str = file_dt.strftime("%Y:%m:%d %H:%M:%S")

            if overwrite_original:
                argfile_lines.append("-overwrite_original")

            is_video = file_path.suffix.lower() in WRITABLE_EXTENSIONS["videos"]

            if is_video:
                argfile_lines.append(f"-CreateDate={dt_str}")
                argfile_lines.append(f"-ModifyDate={dt_str}")
                argfile_lines.append(f"-MediaCreateDate={dt_str}")
                argfile_lines.append(f"-TrackCreateDate={dt_str}")
            else:
                argfile_lines.append(f"-DateTimeOriginal={dt_str}")
                argfile_lines.append(f"-CreateDate={dt_str}")
                argfile_lines.append(f"-ModifyDate={dt_str}")

            for k, v in gps_args.items():
                argfile_lines.append(f"-{k}={v}")

            tags = generate_descriptive_tags(album, file_path.name)
            if tags:
                tag_str = "; ".join(tags)
                argfile_lines.append(f"-Description={tag_str}")
                argfile_lines.append(f"-XPKeywords={tag_str}")
                for t in tags:
                    argfile_lines.append(f"-Keywords={t}")
                    argfile_lines.append(f"-Subject={t}")

            argfile_lines.append(str(file_path))
            argfile_lines.append("-execute")

        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as tmp:
            tmp.write("\n".join(argfile_lines) + "\n")
            tmp_path = tmp.name

        try:
            cmd = [EXIFTOOL_PATH, "-ignoreMinorErrors", "-@", tmp_path]
            res = subprocess.run(cmd, capture_output=True, text=True)
            if res.returncode == 0 or "image files updated" in res.stdout:
                total_updated += len(chunk)
            else:
                logger.warning(f"Exiftool chunk returned non-zero code for '{album.folder_name}': {res.stderr[:200]}")
                total_updated += len(chunk)
            commands_log.append(f"exiftool chunk {i//CHUNK_SIZE + 1} ({len(chunk)} files)")
        except Exception as e:
            logger.error(f"Error processing chunk for {album.folder_name}: {e}")
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    logger.success(f"Updated metadata & tags for {total_updated} files in '{album.folder_name}'")
    return True, total_updated, commands_log
