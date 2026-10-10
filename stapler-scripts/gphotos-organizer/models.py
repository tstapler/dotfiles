from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class LocationInfo(BaseModel):
    name: str
    lat: float
    lon: float


class FileStats(BaseModel):
    total_files: int = 0
    images_count: int = 0
    videos_count: int = 0
    non_media_count: int = 0
    missing_date_count: int = 0
    missing_gps_count: int = 0


class AlbumMapping(BaseModel):
    id: str  # Unique identifier
    source_path: str  # Full path to USB folder
    folder_name: str  # Original directory name
    album_name: str  # Mapped Google Photos album name
    inferred_date: Optional[str] = None  # YYYY:MM:DD HH:MM:SS format
    date_confidence: str = "low"  # high, medium, low
    date_source: str = "none"  # folder_title, holiday_rule, file_name, exif, user_override
    inferred_location: Optional[LocationInfo] = None
    file_stats: FileStats = Field(default_factory=FileStats)
    needs_review: bool = False
    flag_reasons: List[str] = Field(default_factory=list)
    flag_severity: str = "none"  # high, medium, low, none
    metadata_status: str = "pending"  # verified, pending_fix, fixed, skipped
    upload_status: str = "pending"  # pending, in_progress, completed, failed
    notes: Optional[str] = None


class ScanResults(BaseModel):
    timestamp: str
    source_root: str
    total_albums: int = 0
    total_media_files: int = 0
    flagged_albums_count: int = 0
    albums: List[AlbumMapping] = Field(default_factory=list)


class UploadRecord(BaseModel):
    album_id: str
    album_name: str
    source_path: str
    uploaded_at: str
    file_count: int
    status: str  # success, error
    error_message: Optional[str] = None


class UploadManifest(BaseModel):
    remote: str
    updated_at: str
    completed_albums: Dict[str, UploadRecord] = Field(default_factory=dict)
