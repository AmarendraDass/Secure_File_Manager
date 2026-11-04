import sys
from pathlib import Path

# Ensure Windows terminal can print unicode without encoding errors
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from file_identifier import (
    identify_file,
    expected_type,
    check_extension,
    format_size,
)
from organizer import (
    organize_scan_results,
    choose_category,
)
from integrity_checker import (
    create_baseline,
    check_integrity,
)


BASE_DIR = Path(__file__).resolve().parent
BASELINE_PATH = BASE_DIR / "baseline.json"


# ANSI Terminal Colors & Styling
class TermColor:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    ITALIC = "\033[3m"
    UNDERLINE = "\033[4m"

    # Foreground
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"

    # Bright
    B_RED = "\033[91m"
    B_GREEN = "\033[92m"
    B_YELLOW = "\033[93m"
    B_BLUE = "\033[94m"
    B_MAGENTA = "\033[95m"
    B_CYAN = "\033[96m"
    B_WHITE = "\033[97m"

    # Background
    BG_RED = "\033[41m"
    BG_GREEN = "\033[42m"
    BG_YELLOW = "\033[43m"
    BG_BLUE = "\033[44m"


def ask_folder(prompt):
    """Ask the user for an existing folder path with clean validation."""
    print(f"\n{TermColor.B_CYAN}➜ {prompt}{TermColor.RESET}", end="")
    raw_path = input().strip().strip('"').strip("'")

    if not raw_path:
        print(f"{TermColor.YELLOW}⚠ No folder path entered.{TermColor.RESET}")
        return None

    folder = Path(raw_path).expanduser().resolve()

    if not folder.is_dir():
        print(f"{TermColor.RED}✖ Error: Directory '{folder}' does not exist.{TermColor.RESET}")
        return None

    return folder


def scan_folder(folder):
    """Identify files and check their extensions, including nested folders."""
    folder = Path(folder).expanduser().resolve()
    results = []

    for path in sorted(
        (p for p in folder.rglob("*") if p.is_file()),
        key=lambda item: str(item.relative_to(folder)).lower(),
    ):
        try:
            size = path.stat().st_size
        except OSError:
            size = 0

        actual = identify_file(path)
        expected = expected_type(path)
        status = check_extension(path, actual)

        preliminary_result = {
            "path": path,
            "name": path.name,
            "actual_type": actual,
            "expected_type": expected,
            "status": status,
            "size_bytes": size,
            "size_formatted": format_size(size),
            "relative_path": str(path.relative_to(folder)).replace("\\", "/"),
        }
        preliminary_result["category"] = choose_category(preliminary_result)
        results.append(preliminary_result)

    return results


def status_badge(status):
    """Return a color-coded status badge for terminal output."""
    if status == "MATCH":
        return f"{TermColor.B_GREEN}[✔ MATCH]{TermColor.RESET}"
    elif status == "MISMATCH":
        return f"{TermColor.B_RED}{TermColor.BOLD}[⚠ MISMATCH - SPOOFED]{TermColor.RESET}"
    elif status == "UNRECOGNIZED SIGNATURE":
        return f"{TermColor.B_YELLOW}[? UNKNOWN]{TermColor.RESET}"
    elif status == "READ ERROR":
        return f"{TermColor.B_RED}[✖ READ ERROR]{TermColor.RESET}"
    elif status == "EMPTY FILE":
        return f"{TermColor.DIM}[0 EMPTY]{TermColor.RESET}"
    return f"{TermColor.CYAN}[ℹ {status}]{TermColor.RESET}"


def display_scan_results(results):
    """Print the file identification report with a clean tabular design."""
    print("\n" + "═" * 78)
    print(f" {TermColor.BOLD}{TermColor.B_BLUE}🛡  SECURESHIELD FILE IDENTIFICATION & AUDIT REPORT{TermColor.RESET}")
    print("═" * 78)

    if not results:
        print(f"\n{TermColor.YELLOW}No files found in the specified folder.{TermColor.RESET}")
        return

    # Table Header
    print(
        f"{TermColor.DIM}{'FILE NAME':<30} "
        f"{'DETECTED':<12} "
        f"{'EXPECTED':<12} "
        f"{'SIZE':<10} "
        f"{'STATUS'}{TermColor.RESET}"
    )
    print("─" * 78)

    alerts = 0
    total_bytes = 0

    for result in results:
        filename = result["path"].name
        if len(filename) > 28:
            filename = filename[:25] + "..."

        actual = result["actual_type"]
        expected = result["expected_type"] or "Plain/Data"
        size_str = result.get("size_formatted", format_size(result.get("size_bytes", 0)))
        status = result["status"]
        total_bytes += result.get("size_bytes", 0)

        print(
            f"{filename:<30} "
            f"{actual:<12} "
            f"{expected:<12} "
            f"{size_str:<10} "
            f"{status_badge(status)}"
        )

        if status in ("MISMATCH", "UNRECOGNIZED SIGNATURE", "READ ERROR"):
            alerts += 1
            if status == "MISMATCH":
                print(
                    f"  {TermColor.B_RED}↳ SECURITY ALERT: Declared extension does not match binary magic bytes!{TermColor.RESET}"
                )

    print("─" * 78)
    print(f"{TermColor.BOLD}Scan Summary:{TermColor.RESET}")
    print(f" • Total Files Scanned  : {TermColor.B_CYAN}{len(results)}{TermColor.RESET}")
    print(f" • Total Workspace Size : {TermColor.B_CYAN}{format_size(total_bytes)}{TermColor.RESET}")
    if alerts > 0:
        print(f" • Flagged For Review   : {TermColor.B_RED}{TermColor.BOLD}{alerts} file(s) requiring attention{TermColor.RESET}")
    else:
        print(f" • Security Verdict     : {TermColor.B_GREEN}✔ All file extensions match detected signatures{TermColor.RESET}")
    print("═" * 78)


def display_integrity_results(results):
    """Print the integrity check report with colored status indicators."""
    print("\n" + "═" * 78)
    print(f" {TermColor.BOLD}{TermColor.B_MAGENTA}🔐  SHA-256 INTEGRITY VERIFICATION REPORT{TermColor.RESET}")
    print("═" * 78)

    if not results:
        print(f"\n{TermColor.YELLOW}No files found to compare against baseline.{TermColor.RESET}")
        return

    print(f"{TermColor.DIM}{'FILE':<55} {'INTEGRITY VERDICT'}{TermColor.RESET}")
    print("─" * 78)

    changed = 0
    added = 0
    deleted = 0
    intact = 0

    for item in results:
        # Backward-compatible unpacking
        filename, status = item[0], item[1]
        disp_name = filename if len(filename) <= 52 else "..." + filename[-49:]

        if status == "UNCHANGED":
            badge = f"{TermColor.B_GREEN}✔ UNCHANGED (VERIFIED){TermColor.RESET}"
            intact += 1
        elif status == "MODIFIED":
            badge = f"{TermColor.B_RED}{TermColor.BOLD}✖ MODIFIED / TAMPERED{TermColor.RESET}"
            changed += 1
        elif status == "ADDED":
            badge = f"{TermColor.B_CYAN}+ NEWLY ADDED{TermColor.RESET}"
            added += 1
        elif status == "DELETED":
            badge = f"{TermColor.B_YELLOW}- MISSING / DELETED{TermColor.RESET}"
            deleted += 1
        else:
            badge = f"{status}"

        print(f"{disp_name:<55} {badge}")

    print("─" * 78)
    print(f"{TermColor.BOLD}Integrity Statistics:{TermColor.RESET}")
    print(f" • Files Verified Intact : {TermColor.B_GREEN}{intact}{TermColor.RESET}")
    if changed > 0:
        print(f" • Files Tampered/Changed: {TermColor.B_RED}{TermColor.BOLD}{changed} (HASH MISMATCH!){TermColor.RESET}")
    if added > 0:
        print(f" • Files Newly Added     : {TermColor.B_CYAN}{added}{TermColor.RESET}")
    if deleted > 0:
        print(f" • Files Removed/Missing : {TermColor.B_YELLOW}{deleted}{TermColor.RESET}")
    print("═" * 78)


def scan_option():
    folder = ask_folder("Enter the folder path to scan: ")
    if folder is None:
        return

    try:
        results = scan_folder(folder)
        display_scan_results(results)
    except OSError as error:
        print(f"{TermColor.RED}✖ Could not scan folder: {error}{TermColor.RESET}")


def organize_option():
    folder = ask_folder("Enter the source folder path: ")
    if folder is None:
        return

    try:
        results = scan_folder(folder)
        display_scan_results(results)

        if not results:
            return

        print(f"\n{TermColor.B_CYAN}➜ Enter a different output folder path for organized files:{TermColor.RESET} ", end="")
        output_text = input().strip().strip('"').strip("'")

        if not output_text:
            print(f"{TermColor.YELLOW}⚠ No output folder entered. Operation cancelled.{TermColor.RESET}")
            return

        output_folder = Path(output_text).expanduser().resolve()

        if output_folder == folder:
            print(f"{TermColor.RED}✖ Error: Output folder must be different from source folder.{TermColor.RESET}")
            return

        count = organize_scan_results(results, output_folder)
        print(f"\n{TermColor.B_GREEN}✔ Successfully organized and copied {count} files.{TermColor.RESET}")
        print(f"  Target directory: {TermColor.CYAN}{output_folder}{TermColor.RESET}")

    except (OSError, ValueError) as error:
        print(f"{TermColor.RED}✖ Organization failed: {error}{TermColor.RESET}")


def baseline_option():
    folder = ask_folder("Enter the folder to create a SHA-256 baseline for: ")
    if folder is None:
        return

    try:
        count = create_baseline(folder, BASELINE_PATH)
        print(f"\n{TermColor.B_GREEN}✔ SHA-256 cryptographic baseline created successfully.{TermColor.RESET}")
        print(f" • Files Recorded  : {TermColor.B_CYAN}{count}{TermColor.RESET}")
        print(f" • Baseline Saved  : {TermColor.CYAN}{BASELINE_PATH}{TermColor.RESET}")

    except (OSError, ValueError) as error:
        print(f"{TermColor.RED}✖ Could not create baseline: {error}{TermColor.RESET}")


def integrity_option():
    folder = ask_folder("Enter the folder to verify against baseline: ")
    if folder is None:
        return

    try:
        results = check_integrity(folder, BASELINE_PATH, strict_folder_check=False)
        display_integrity_results(results)
    except (OSError, ValueError, FileNotFoundError) as error:
        print(f"{TermColor.RED}✖ Integrity check failed: {error}{TermColor.RESET}")


def complete_scan_option():
    """Run full signature inspection, integrity comparison, and optional organization."""
    folder = ask_folder("Enter the target folder for complete security audit: ")
    if folder is None:
        return

    try:
        results = scan_folder(folder)
        display_scan_results(results)
    except OSError as error:
        print(f"{TermColor.RED}✖ Could not scan folder: {error}{TermColor.RESET}")
        return

    if BASELINE_PATH.is_file():
        try:
            integrity_results = check_integrity(folder, BASELINE_PATH, strict_folder_check=False)
            display_integrity_results(integrity_results)
        except (OSError, ValueError) as error:
            print(f"\n{TermColor.YELLOW}Integrity check note: {error}{TermColor.RESET}")
    else:
        print(f"\n{TermColor.DIM}ℹ No baseline snapshot exists yet. Use Option 3 to create one.{TermColor.RESET}")

    print(f"\n{TermColor.B_CYAN}➜ Also organize sorted copies of these files? (y/n): {TermColor.RESET}", end="")
    answer = input().strip().lower()

    if answer in ("y", "yes"):
        print(f"{TermColor.B_CYAN}➜ Enter destination output folder: {TermColor.RESET}", end="")
        output_text = input().strip().strip('"').strip("'")

        if not output_text:
            print(f"{TermColor.YELLOW}⚠ No output folder specified.{TermColor.RESET}")
            return

        output_folder = Path(output_text).expanduser().resolve()

        if output_folder == folder:
            print(f"{TermColor.RED}✖ Error: Destination must be different from source.{TermColor.RESET}")
            return

        try:
            count = organize_scan_results(results, output_folder)
            print(f"{TermColor.B_GREEN}✔ Successfully organized {count} files into categories.{TermColor.RESET}")
        except (OSError, ValueError) as error:
            print(f"{TermColor.RED}✖ Organization failed: {error}{TermColor.RESET}")


def print_banner():
    """Display an executive ASCII header banner."""
    print(f"{TermColor.B_CYAN}")
    print(r"""
   ███████╗███████╗ ██████╗██╗   ██╗██████╗ ███████╗███████╗██╗  ██╗██╗███████╗██╗     ██████╗ 
   ██╔════╝██╔════╝██╔════╝██║   ██║██╔══██╗██╔════╝██╔════╝██║  ██║██║██╔════╝██║     ██╔══██╗
   ███████╗█████╗  ██║     ██║   ██║██████╔╝█████╗  ███████╗███████║██║█████╗  ██║     ██║  ██║
   ╚════██║██╔══╝  ██║     ██║   ██║██╔══██╗██╔══╝  ╚════██║██╔══██║██║██╔══╝  ██║     ██║  ██║
   ███████║███████╗╚██████╗╚██████╔╝██║  ██║███████╗███████║██║  ██║██║███████╗███████╗██████╔╝
   ╚══════╝╚══════╝ ╚═════╝ ╚═════╝ ╚═╝  ╚═╝╚══════╝╚══════╝╚═╝  ╚═╝╚═╝╚══════╝╚══════╝╚═════╝ 
    """ + f"{TermColor.RESET}")
    print(f"        {TermColor.BOLD}ENTERPRISE FILE INSPECTOR, INTEGRITY MONITOR & ORGANIZER{TermColor.RESET}")
    print(f"        {TermColor.DIM}Anti-Spoofing Detection • SHA-256 Baselines • Automated Categorization{TermColor.RESET}")
    print("═" * 84)


def main():
    print_banner()

    while True:
        print(f"\n{TermColor.BOLD}MAIN CONTROL PANEL:{TermColor.RESET}")
        print(f"  {TermColor.B_CYAN}1.{TermColor.RESET} 🔍 Deep file signature scan & threat detection")
        print(f"  {TermColor.B_CYAN}2.{TermColor.RESET} 🗂  Organize files into verified category folders")
        print(f"  {TermColor.B_CYAN}3.{TermColor.RESET} 📸 Create SHA-256 cryptographic baseline snapshot")
        print(f"  {TermColor.B_CYAN}4.{TermColor.RESET} 🔐 Verify file integrity against baseline")
        print(f"  {TermColor.B_CYAN}5.{TermColor.RESET} ⚡ Complete security audit (Scan + Integrity + Organize)")
        print(f"  {TermColor.B_CYAN}6.{TermColor.RESET} 🚪 Exit")

        print(f"\n{TermColor.B_CYAN}➜ Enter choice [1-6]: {TermColor.RESET}", end="")
        choice = input().strip()

        if choice == "1":
            scan_option()
        elif choice == "2":
            organize_option()
        elif choice == "3":
            baseline_option()
        elif choice == "4":
            integrity_option()
        elif choice == "5":
            complete_scan_option()
        elif choice == "6":
            print(f"\n{TermColor.B_GREEN}✔ Exiting SecureShield File Manager. Goodbye!{TermColor.RESET}\n")
            break
        else:
            print(f"{TermColor.RED}✖ Invalid selection. Please choose an option from 1 to 6.{TermColor.RESET}")


if __name__ == "__main__":
    main()
