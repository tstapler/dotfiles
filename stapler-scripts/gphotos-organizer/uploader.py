from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from loguru import logger
from models import AlbumMapping, UploadManifest, UploadRecord
from scanner import MEDIA_EXTENSIONS

RCLONE_PATH = os.environ.get("RCLONE_PATH", "/home/linuxbrew/.linuxbrew/bin/rclone")
ALL_MEDIA_EXTS = MEDIA_EXTENSIONS["images"].union(MEDIA_EXTENSIONS["videos"])


def verify_rclone_remote(remote_name: str = "gphotos") -> bool:
    """Verifies if rclone is available and the specified remote is configured."""
    if not Path(RCLONE_PATH).exists():
        logger.error(f"rclone binary not found at {RCLONE_PATH}")
        return False

    try:
        res = subprocess.run([RCLONE_PATH, "listremotes"], capture_output=True, text=True, check=True)
        remotes = [r.strip().rstrip(":") for r in res.stdout.splitlines()]
        if remote_name not in remotes:
            logger.warning(f"rclone remote '{remote_name}:' is not configured. Configured remotes: {remotes}")
            return False
        return True
    except Exception as e:
        logger.error(f"Failed to list rclone remotes: {e}")
        return False


def load_manifest(manifest_path: Path, remote_name: str = "gphotos") -> UploadManifest:
    if manifest_path.exists():
        try:
            data = json.loads(manifest_path.read_text())
            return UploadManifest(**data)
        except Exception as e:
            logger.warning(f"Could not parse manifest at {manifest_path}: {e}")

    return UploadManifest(remote=remote_name, updated_at=datetime.now().isoformat())


def save_manifest(manifest: UploadManifest, manifest_path: Path) -> None:
    manifest.updated_at = datetime.now().isoformat()
    manifest_path.write_text(json.dumps(manifest.model_dump(), indent=2))


def upload_album_to_gphotos(
    album: AlbumMapping,
    remote_name: str = "gphotos",
    dry_run: bool = True,
    manifest_path: Optional[Path] = None,
) -> Tuple[bool, str]:
    """Uploads an album folder to Google Photos using rclone."""
    source_dir = Path(album.source_path)
    if not source_dir.exists():
        msg = f"Source directory missing: {source_dir}"
        logger.error(msg)
        return False, msg

    destination = f"{remote_name}:album/{album.album_name}"

    # Build rclone include filters for media files
    cmd = [RCLONE_PATH, "copy", str(source_dir), destination]
    for ext in ALL_MEDIA_EXTS:
        cmd.extend(["--include", f"*{ext}", "--include", f"*{ext.upper()}"])

    cmd.extend(["--stats", "5s", "--progress"])

    if dry_run:
        cmd.append("--dry-run")
        logger.info(f"[DRY-RUN] Would upload '{album.folder_name}' ({album.file_stats.images_count + album.file_stats.videos_count} files) to '{destination}'")
        return True, "Dry run completed successfully"

    logger.info(f"Uploading '{album.folder_name}' -> '{destination}'...")

    try:
        res = subprocess.run(cmd, text=True, check=True)
        logger.success(f"Uploaded album '{album.album_name}' successfully!")
        
        if manifest_path:
            manifest = load_manifest(manifest_path, remote_name)
            manifest.completed_albums[album.id] = UploadRecord(
                album_id=album.id,
                album_name=album.album_name,
                source_path=album.source_path,
                uploaded_at=datetime.now().isoformat(),
                file_count=album.file_stats.images_count + album.file_stats.videos_count,
                status="success",
            )
            save_manifest(manifest, manifest_path)

        return True, "Upload successful"
    except subprocess.CalledProcessError as e:
        msg = f"rclone failed for '{album.album_name}': {e}"
        logger.error(msg)
        return False, msg
