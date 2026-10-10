#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "typer>=0.12",
#   "loguru>=0.7",
#   "rich>=13",
#   "pydantic>=2.0",
# ]
# ///
"""Google Photos Childhood Album Organizer & EXIF Fixer for Antigravity (agy)."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import List, Optional

import typer
from loguru import logger
from rich import print as rprint
from rich.console import Console
from rich.table import Table

from ai_enrich import enrich_mapping_data
from locations import find_location_in_string
from metadata import update_album_metadata
from models import AlbumMapping, ScanResults
from report import generate_markdown_report
from scanner import scan_usb_drive
from uploader import load_manifest, upload_album_to_gphotos, verify_rclone_remote

app = typer.Typer(
    name="gphotos-organizer",
    help="CLI tool to map USB photo folders, update date/GPS EXIF metadata, and upload to Google Photos albums.",
    add_completion=False,
)

console = Console()


@app.command("scan")
def scan_cmd(
    source_dir: Path = typer.Option(
        Path("/run/media/tstapler/EE5B-3D9B"),
        "--src",
        "-s",
        help="Path to attached USB drive or photos folder",
    ),
    out_mapping: Path = typer.Option(
        Path("album_mapping.json"),
        "--out",
        "-o",
        help="Output mapping JSON file",
    ),
    out_report: Optional[Path] = typer.Option(
        Path("album_report.md"),
        "--report",
        "-r",
        help="Output Markdown report file",
    ),
    sample_exif: bool = typer.Option(
        False,
        "--sample-exif/--no-sample-exif",
        help="Sample EXIF data to detect missing dates/GPS",
    ),
) -> None:
    """Scan USB drive, infer dates and locations, evaluate quality flags, and generate album mapping."""
    logger.info(f"Starting scan of {source_dir}...")
    try:
        results = scan_usb_drive(source_dir, sample_exif=sample_exif)
    except Exception as e:
        logger.error(f"Scan failed: {e}")
        raise typer.Exit(1)

    out_mapping.write_text(json.dumps(results.model_dump(), indent=2))
    logger.success(f"Mapping saved to {out_mapping}")

    if out_report:
        generate_markdown_report(results, out_report)
        logger.success(f"Markdown report saved to {out_report}")

    table = Table(title="Scan Summary")
    table.add_column("Total Albums", style="cyan")
    table.add_column("Total Media Files", style="green")
    table.add_column("High Conf. Dates", style="blue")
    table.add_column("Flagged for Review", style="red")

    high_conf = sum(1 for a in results.albums if a.date_confidence == "high")

    table.add_row(
        str(results.total_albums),
        str(results.total_media_files),
        str(high_conf),
        str(results.flagged_albums_count),
    )
    console.print(table)


@app.command("infer")
def infer_cmd(
    mapping_file: Path = typer.Option(
        Path("album_mapping.json"),
        "--mapping",
        "-m",
        help="Path to album_mapping.json",
        exists=True,
    ),
    out_report: Optional[Path] = typer.Option(
        Path("album_report.md"),
        "--report",
        "-r",
        help="Output Markdown report file",
    ),
) -> None:
    """Run AI & Filename Inference engine to resolve missing dates and locations."""
    logger.info(f"Running inference engine on {mapping_file}...")
    updated_cnt, summaries = enrich_mapping_data(mapping_file)

    if out_report:
        data = json.loads(mapping_file.read_text())
        results = ScanResults(**data)
        generate_markdown_report(results, out_report)
        logger.success(f"Updated Markdown report at {out_report}")

    logger.success(f"Inferred dates and locations for {updated_cnt} albums!")

    if summaries:
        table = Table(title=f"AI Inferred Date & Location Suggestions ({updated_cnt} Albums)")
        table.add_column("Folder Name", style="cyan")
        table.add_column("Inferred Date", style="green")
        table.add_column("Inferred Location", style="magenta")
        table.add_column("Inference Source", style="yellow")

        for item in summaries[:35]:
            table.add_row(
                item["folder_name"],
                item["inferred_date"],
                item["inferred_location"],
                item["source"],
            )

        console.print(table)


@app.command("review")
def review_cmd(
    mapping_file: Path = typer.Option(
        Path("album_mapping.json"),
        "--mapping",
        "-m",
        help="Path to album_mapping.json",
        exists=True,
    ),
    severity: str = typer.Option(
        "all",
        "--severity",
        "-s",
        help="Filter by severity: high, medium, low, all",
    ),
    json_out: bool = typer.Option(
        False,
        "--json",
        help="Output as formatted JSON for AI/LLM consumption",
    ),
) -> None:
    """List questionable data entries flagged for review by LLM or user."""
    data = json.loads(mapping_file.read_text())
    results = ScanResults(**data)

    flagged = [a for a in results.albums if a.needs_review]

    if severity.lower() != "all":
        flagged = [a for a in flagged if a.flag_severity.lower() == severity.lower()]

    if json_out:
        review_data = [
            {
                "id": a.id,
                "folder_name": a.folder_name,
                "suggested_album_name": a.album_name,
                "inferred_date": a.inferred_date,
                "date_confidence": a.date_confidence,
                "severity": a.flag_severity,
                "flag_reasons": a.flag_reasons,
                "media_count": a.file_stats.images_count + a.file_stats.videos_count,
            }
            for a in flagged
        ]
        rprint(json.dumps(review_data, indent=2))
        return

    table = Table(title=f"Flagged Albums Needing Review ({len(flagged)} Total)")
    table.add_column("Severity", style="bold red")
    table.add_column("Folder Name", style="cyan")
    table.add_column("Suggested Album Name", style="green")
    table.add_column("Issues / Reasons", style="yellow")

    for a in sorted(flagged, key=lambda x: (x.flag_severity != "high", x.flag_severity != "medium")):
        sev_color = "red" if a.flag_severity == "high" else "yellow" if a.flag_severity == "medium" else "blue"
        reasons = "\n".join(a.flag_reasons)
        table.add_row(
            f"[{sev_color}]{a.flag_severity.upper()}[/{sev_color}]",
            a.folder_name,
            a.album_name,
            reasons,
        )

    console.print(table)


@app.command("update-album")
def update_album_cmd(
    album_id: str = typer.Option(..., "--id", "-i", help="Album ID or folder name to update"),
    date: Optional[str] = typer.Option(None, "--date", "-d", help="Date in YYYY:MM:DD HH:MM:SS format"),
    album_name: Optional[str] = typer.Option(None, "--album-name", "-n", help="New Google Photos album name"),
    location: Optional[str] = typer.Option(None, "--location", "-l", help="Location name (e.g. 'Seattle, WA')"),
    clear_flags: bool = typer.Option(True, "--clear-flags/--keep-flags", help="Clear review flags upon update"),
    mapping_file: Path = typer.Option(
        Path("album_mapping.json"),
        "--mapping",
        "-m",
        help="Path to album_mapping.json",
        exists=True,
    ),
) -> None:
    """Update album date, location, or name mapping for a specific album."""
    data = json.loads(mapping_file.read_text())
    results = ScanResults(**data)

    target: Optional[AlbumMapping] = None
    for a in results.albums:
        if a.id == album_id or a.folder_name == album_id or a.album_name == album_id:
            target = a
            break

    if not target:
        logger.error(f"Album with ID or name '{album_id}' not found.")
        raise typer.Exit(1)

    if date:
        if "-" in date and ":" not in date:
            parts = date.split("-")
            if len(parts) == 3:
                date = f"{parts[0]}:{parts[1]}:{parts[2]} 12:00:00"
        target.inferred_date = date
        target.date_confidence = "high"
        target.date_source = "user_override"

    if album_name:
        target.album_name = album_name

    if location:
        loc = find_location_in_string(location)
        if loc:
            target.inferred_location = loc
        else:
            logger.warning(f"Location '{location}' not recognized in default lookup table.")

    if clear_flags:
        target.needs_review = False
        target.flag_reasons = []
        target.flag_severity = "none"

    mapping_file.write_text(json.dumps(results.model_dump(), indent=2))
    logger.success(f"Updated album '{target.folder_name}' successfully!")


@app.command("report")
def report_cmd(
    mapping_file: Path = typer.Option(
        Path("album_mapping.json"),
        "--mapping",
        "-m",
        help="Path to album_mapping.json",
        exists=True,
    ),
    out_report: Path = typer.Option(
        Path("album_report.md"),
        "--out",
        "-o",
        help="Output Markdown report file",
    ),
) -> None:
    """Generate Markdown report from existing mapping JSON."""
    data = json.loads(mapping_file.read_text())
    results = ScanResults(**data)
    content = generate_markdown_report(results, out_report)
    logger.success(f"Report generated at {out_report}")


@app.command("fix-metadata")
def fix_metadata_cmd(
    mapping_file: Path = typer.Option(
        Path("album_mapping.json"),
        "--mapping",
        "-m",
        help="Path to album_mapping.json",
        exists=True,
    ),
    apply: bool = typer.Option(
        False,
        "--apply",
        help="Apply changes to EXIF metadata (default is dry-run)",
    ),
    album_id: Optional[str] = typer.Option(
        None,
        "--album-id",
        help="Process only a specific album by ID",
    ),
    offset_seconds: int = typer.Option(
        5,
        "--offset",
        help="Seconds offset between photos to maintain filename order",
    ),
) -> None:
    """Fix EXIF date and GPS metadata across mapped albums using exiftool."""
    dry_run = not apply
    data = json.loads(mapping_file.read_text())
    results = ScanResults(**data)

    albums = results.albums
    if album_id:
        albums = [a for a in albums if a.id == album_id or a.folder_name == album_id]

    if dry_run:
        logger.warning("Running in DRY-RUN mode. Use --apply to write EXIF tags.")

    updated_albums = 0
    total_files_updated = 0

    for album in albums:
        if not album.inferred_date:
            continue

        success, files_cnt, _ = update_album_metadata(
            album,
            dry_run=dry_run,
            offset_seconds=offset_seconds,
        )
        if success:
            updated_albums += 1
            total_files_updated += files_cnt
            if not dry_run:
                album.metadata_status = "fixed"

    if apply:
        mapping_file.write_text(json.dumps(results.model_dump(), indent=2))
        logger.success(f"Updated metadata for {total_files_updated} files across {updated_albums} albums!")
    else:
        logger.info(f"[DRY-RUN] Would update metadata for {total_files_updated} files across {updated_albums} albums.")


@app.command("upload")
def upload_cmd(
    mapping_file: Path = typer.Option(
        Path("album_mapping.json"),
        "--mapping",
        "-m",
        help="Path to album_mapping.json",
        exists=True,
    ),
    remote: str = typer.Option(
        "gphotos",
        "--remote",
        "-r",
        help="rclone remote name for Google Photos",
    ),
    manifest_file: Path = typer.Option(
        Path("upload_manifest.json"),
        "--manifest",
        help="Path to upload state manifest file",
    ),
    apply: bool = typer.Option(
        False,
        "--apply",
        help="Execute upload to Google Photos (default is dry-run)",
    ),
    album_id: Optional[str] = typer.Option(
        None,
        "--album-id",
        help="Upload only a specific album by ID or folder name",
    ),
) -> None:
    """Upload mapped albums to Google Photos via rclone."""
    dry_run = not apply

    if not dry_run and not verify_rclone_remote(remote):
        logger.error(f"Cannot proceed with upload. Rclone remote '{remote}:' is not configured.")
        logger.info("Run 'gphotos-organizer setup-rclone' for instructions.")
        raise typer.Exit(1)

    data = json.loads(mapping_file.read_text())
    results = ScanResults(**data)
    manifest = load_manifest(manifest_file, remote)

    albums = results.albums
    if album_id:
        albums = [a for a in albums if a.id == album_id or a.folder_name == album_id]

    if dry_run:
        logger.warning("Running in DRY-RUN mode. Use --apply to execute upload.")

    for album in albums:
        if album.id in manifest.completed_albums:
            logger.info(f"Skipping already uploaded album '{album.album_name}'")
            continue

        ok, msg = upload_album_to_gphotos(
            album,
            remote_name=remote,
            dry_run=dry_run,
            manifest_path=manifest_file if apply else None,
        )
        if ok and apply:
            album.upload_status = "completed"

    if apply:
        mapping_file.write_text(json.dumps(results.model_dump(), indent=2))
        logger.success("Upload operations finished!")


@app.command("setup-rclone")
def setup_rclone_cmd(
    remote: str = typer.Option("gphotos", "--remote", "-r"),
) -> None:
    """Guide setting up Google Photos rclone remote."""
    rprint(f"[bold cyan]Setting up rclone for Google Photos remote '{remote}:'[/bold cyan]")
    rprint("1. Run the following command in your terminal:")
    rprint(f"   [bold yellow]rclone config create {remote} gphotos[/bold yellow]")
    rprint("2. Follow the browser prompt to authorize access to your Google Photos account.")
    rprint("3. Verify the remote is working with:")
    rprint(f"   [bold green]rclone listremotes[/bold green]")


@app.command("status")
def status_cmd(
    mapping_file: Path = typer.Option(
        Path("album_mapping.json"),
        "--mapping",
        "-m",
        help="Path to album_mapping.json",
    ),
    manifest_file: Path = typer.Option(
        Path("upload_manifest.json"),
        "--manifest",
        help="Path to upload_manifest.json",
    ),
) -> None:
    """Show current scan, metadata fix, and upload status."""
    if not mapping_file.exists():
        logger.error(f"No mapping file found at {mapping_file}. Run 'gphotos-organizer scan' first.")
        raise typer.Exit(1)

    data = json.loads(mapping_file.read_text())
    results = ScanResults(**data)

    manifest = load_manifest(manifest_file) if manifest_file.exists() else None

    completed_cnt = len(manifest.completed_albums) if manifest else 0

    table = Table(title="Organizing & Upload Status")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Scanned Source", results.source_root)
    table.add_row("Total Albums", str(results.total_albums))
    table.add_row("Total Media Files", str(results.total_media_files))
    table.add_row("Flagged for Review", str(results.flagged_albums_count))
    table.add_row("Uploaded Albums", f"{completed_cnt} / {results.total_albums}")

    console.print(table)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
