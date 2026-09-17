"""FIM-Sentinel command-line interface (Typer + Rich)."""

from __future__ import annotations

import json
import sys

import typer
from rich.console import Console
from rich.table import Table

from app.db.repository import verify_audit_chain
from app.db.session import get_session, init_db
from app.services.report_service import build_report, report_to_csv, report_to_json
from app.services.workflow import (
    BaselineNotFoundError,
    BaselineTamperedError,
    create_baseline,
    run_scan,
)

cli = typer.Typer(
    name="fim-sentinel",
    help="FIM-Sentinel: File Integrity Monitoring & Forensics CLI",
    add_completion=False,
)
console = Console()
COLORS = {"MODIFIED": "yellow", "ADDED": "green", "DELETED": "red"}


def _fail(msg: str) -> None:
    console.print(f"[bold red]✗ {msg}[/]")
    raise typer.Exit(code=1)


@cli.command()
def baseline(
    path: str = typer.Option(..., "--path", "-p", help="Directory to baseline."),
    follow_symlinks: bool = typer.Option(False, "--follow-symlinks", help="Follow symlinks."),
) -> None:
    """Create a signed baseline snapshot of the target directory."""
    init_db()
    with get_session() as db:
        session, result = create_baseline(db, path, follow_symlinks)
        bid, target = session.id, session.target_path

    console.print(
        f"[bold green]✓ Baseline created[/]  id={bid}  path={target}  "
        f"files={result.file_count}  errors={result.error_count}"
    )
    for err in result.errors:
        console.print(f"  [yellow]⚠ {err}[/]")


@cli.command()
def scan(
    baseline_id: int = typer.Option(..., "--baseline-id", "-b", help="Baseline session ID."),
) -> None:
    """Run an integrity scan against an existing baseline. Exit code 2 = changes found."""
    init_db()
    try:
        with get_session() as db:
            scan_obj, diff, result = run_scan(db, baseline_id)
            sid = scan_obj.id
    except BaselineNotFoundError:
        _fail("Baseline not found.")
    except BaselineTamperedError:
        _fail("Baseline signature invalid — baseline may be tampered!")

    table = Table(title=f"Scan #{sid} Results")
    table.add_column("Metric", style="cyan")
    table.add_column("Count", justify="right")
    for label, value in (
        ("Modified", diff.total_modified),
        ("Added", diff.total_added),
        ("Deleted", diff.total_deleted),
        ("Errors", result.error_count),
    ):
        table.add_row(label, str(value))
    console.print(table)

    if diff.findings:
        details = Table(title="Findings")
        details.add_column("Type", style="bold")
        details.add_column("File Path")
        details.add_column("Detail")
        for f in diff.findings:
            c = COLORS.get(f.change_type.value, "white")
            details.add_row(f"[{c}]{f.change_type.value}[/{c}]", f.file_path, f.detail or "")
        console.print(details)
        raise typer.Exit(code=2)  # lets cron/CI react to changes


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
        _fail("Scan not found.")

    if format.lower() == "csv":
        sys.stdout.write(report_to_csv(rpt))
    else:
        sys.stdout.write(json.dumps(report_to_json(rpt), indent=2, default=str) + "\n")


@cli.command("verify-audit")
def verify_audit() -> None:
    """Verify the tamper-evident audit log chain."""
    init_db()
    with get_session() as db:
        ok, broken = verify_audit_chain(db)
    if not ok:
        _fail(f"Audit chain broken at row id={broken}")
    console.print("[bold green]✓ Audit chain intact[/]")


def main() -> None:
    cli()


if __name__ == "__main__":
    main()
