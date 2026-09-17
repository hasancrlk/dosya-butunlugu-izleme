"""FIM-Sentinel command-line interface (Typer + Rich)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

# ── Bootstrap DB before any import that touches SQLAlchemy ──────
from app.db.session import get_session, init_db
from app.db.repository import (
    add_baseline_entries,
    add_scan_findings,
    create_baseline_session,
    create_scan_session,
    get_baseline_session,
)
from app.services.scanner import scan_directory
from app.services.diff_engine import compute_diff
from app.services.report_service import build_report, report_to_csv, report_to_json

cli = typer.Typer(
    name="fim-sentinel",
    help="FIM-Sentinel: File Integrity Monitoring & Forensics CLI",
    add_completion=False,
)
console = Console()


@cli.command()
def baseline(
    path: str = typer.Option(..., "--path", "-p", help="Directory to baseline."),
) -> None:
    """Create a baseline snapshot of the target directory."""
    init_db()
    target = str(Path(path).resolve())
    console.print(f"[bold cyan]Scanning:[/] {target}")

    scan_result = scan_directory(target)

    with get_session() as db:
        session_obj = create_baseline_session(
            db,
            target_path=target,
            file_count=scan_result.file_count,
            error_count=scan_result.error_count,
        )
        entries = [
            {
                "file_path": r.file_path,
                "sha256": r.sha256,
                "size_bytes": r.size_bytes,
                "mtime": r.mtime,
            }
            for r in scan_result.file_records
        ]
        add_baseline_entries(db, session_obj.id, entries)
        bid = session_obj.id

    console.print(
        f"[bold green]✓ Baseline created[/]  id={bid}  "
        f"files={scan_result.file_count}  errors={scan_result.error_count}"
    )
    if scan_result.errors:
        for err in scan_result.errors:
            console.print(f"  [yellow]⚠ {err}[/]")


@cli.command()
def scan(
    baseline_id: int = typer.Option(..., "--baseline-id", "-b", help="Baseline session ID."),
) -> None:
    """Run an integrity scan against an existing baseline."""
    init_db()

    with get_session() as db:
        bl = get_baseline_session(db, baseline_id)
        if bl is None:
            console.print("[bold red]✗ Baseline not found.[/]")
            raise typer.Exit(code=1)

        console.print(f"[bold cyan]Scanning:[/] {bl.target_path}")
        scan_result = scan_directory(bl.target_path)
        diff = compute_diff(bl.entries, scan_result.file_records)

        scan_obj = create_scan_session(
            db,
            baseline_id=bl.id,
            total_modified=diff.total_modified,
            total_added=diff.total_added,
            total_deleted=diff.total_deleted,
            total_errors=scan_result.error_count,
        )
        finding_dicts = [
            {
                "file_path": f.file_path,
                "change_type": f.change_type,
                "old_hash": f.old_hash,
                "new_hash": f.new_hash,
                "old_size": f.old_size,
                "new_size": f.new_size,
                "detail": f.detail,
            }
            for f in diff.findings
        ]
        add_scan_findings(db, scan_obj.id, finding_dicts)
        sid = scan_obj.id

    # Summary table
    table = Table(title=f"Scan #{sid} Results")
    table.add_column("Metric", style="cyan")
    table.add_column("Count", justify="right")
    table.add_row("Modified", str(diff.total_modified))
    table.add_row("Added", str(diff.total_added))
    table.add_row("Deleted", str(diff.total_deleted))
    table.add_row("Errors", str(scan_result.error_count))
    console.print(table)

    if diff.findings:
        detail_table = Table(title="Findings")
        detail_table.add_column("Type", style="bold")
        detail_table.add_column("File Path")
        detail_table.add_column("Detail")
        for f in diff.findings:
            color = {"MODIFIED": "yellow", "ADDED": "green", "DELETED": "red"}.get(
                f.change_type.value, "white"
            )
            detail_table.add_row(
                f"[{color}]{f.change_type.value}[/{color}]",
                f.file_path,
                f.detail or "",
            )
        console.print(detail_table)


@cli.command()
def report(
    scan_id: int = typer.Option(..., "--scan-id", "-s", help="Scan session ID."),
    format: str = typer.Option("json", "--format", "-f", help="Output format: json or csv."),
) -> None:
    """Export a scan report as JSON or CSV."""
    init_db()

    with get_session() as db:
        rpt = build_report(db, scan_id)

    if rpt is None:
        console.print("[bold red]✗ Scan not found.[/]")
        raise typer.Exit(code=1)

    if format.lower() == "csv":
        sys.stdout.write(report_to_csv(rpt))
    else:
        sys.stdout.write(json.dumps(report_to_json(rpt), indent=2, default=str))
        sys.stdout.write("\n")


def main() -> None:
    cli()


if __name__ == "__main__":
    main()
