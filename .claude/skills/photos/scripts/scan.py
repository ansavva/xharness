# /// script
# requires-python = ">=3.13"
# dependencies = [
#   "rich>=13.5.2,<14.0.0",
#   "osxphotos==0.75.6",
# ]
# ///
"""Entry point for photo scanning tools."""
import argparse
import os
import sys
from pathlib import Path

# Allow sibling modules (cache, takeout_scanner, icloud_scanner) to be imported directly.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def cmd_scan_takeout(args):
    from takeout_scanner import scan_takeout
    scan_takeout(args.path, quiet=args.quiet, reset=args.reset)


def cmd_scan_icloud(args):
    from icloud_scanner import scan_icloud
    try:
        scan_icloud(library_path=args.library, quiet=args.quiet)
    except (FileNotFoundError, ValueError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_setup(args):
    import shutil
    from rich.console import Console

    console = Console()

    console.print("[bold cyan]Google Takeout Export Instructions[/bold cyan]\n")
    console.print(
        "  1. Go to https://takeout.google.com\n"
        "  2. Click 'Deselect all', then check only 'Google Photos'\n"
        "  3. Choose file type .zip, size 2GB (multiple files for large libraries)\n"
        "  4. Click 'Create export' — Google will email you when ready (may take hours)\n"
        "  5. Download ALL zip files (e.g., takeout-20240101-001.zip, ...)\n"
        "  6. Extract ALL zips into the same folder so all 'Takeout/' contents merge\n"
        "  7. Run: /photos scan-takeout /path/to/that/folder\n"
    )

    console.print("[bold cyan]System Requirement Checks[/bold cyan]\n")

    exiftool = shutil.which("exiftool")
    if exiftool:
        console.print(f"[green]✓[/green] exiftool found at {exiftool}")
    else:
        console.print("[yellow]![/yellow] exiftool not found — required for Phase 3 (metadata embedding).")
        console.print("  Install with: [bold]brew install exiftool[/bold]")

    from osxphotos.utils import list_photo_libraries

    default_lib = Path.home() / "Pictures" / "Photos Library.photoslibrary"
    if default_lib.exists():
        console.print(f"[green]✓[/green] Photos library found at {default_lib}")
    else:
        libraries = list_photo_libraries()
        if libraries:
            console.print("[yellow]![/yellow] Default Photos library not at expected path.")
            console.print(f"  Found {len(libraries)} library/libraries via Spotlight:")
            for lib in libraries:
                console.print(f"    {lib}")
            console.print("  Use --library <path> with scan-icloud if needed.")
        else:
            console.print("[red]✗[/red] No Photos library found. Is Photos.app installed?")

    console.print(
        "\n[yellow]Note:[/yellow] If your export had multiple ZIP files, "
        "ensure ALL are extracted into the same parent directory before running scan-takeout."
    )


def main():
    parser = argparse.ArgumentParser(description="Photo scanning tools.")
    sub = parser.add_subparsers(dest="command", required=True)

    p_takeout = sub.add_parser("scan-takeout", help="Index a Google Takeout export to SQLite")
    p_takeout.add_argument("path", help="Path to extracted Google Takeout folder")
    p_takeout.add_argument("--quiet", "-q", action="store_true", help="Suppress progress bar")
    p_takeout.add_argument("--reset", action="store_true", help="Wipe and recreate the SQLite database")

    p_icloud = sub.add_parser("scan-icloud", help="Index Photos.app library to SQLite")
    p_icloud.add_argument("--library", default=None, help="Path to Photos Library (default: auto-detect)")
    p_icloud.add_argument("--quiet", "-q", action="store_true", help="Suppress progress bar")

    sub.add_parser("setup", help="Print export instructions and check system requirements")

    args = parser.parse_args()

    if args.command == "scan-takeout":
        cmd_scan_takeout(args)
    elif args.command == "scan-icloud":
        cmd_scan_icloud(args)
    elif args.command == "setup":
        cmd_setup(args)


if __name__ == "__main__":
    main()
