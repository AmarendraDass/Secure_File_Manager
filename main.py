from pathlib import Path

from file_identifier import (
    identify_file,
    expected_type,
    check_extension,
)

from organizer import organize_scan_results

from integrity_checker import (
    create_baseline,
    check_integrity,
)


# Store the baseline alongside this Python file.
BASE_DIR = Path(__file__).resolve().parent
BASELINE_PATH = BASE_DIR / "baseline.json"


def ask_folder(prompt):
    """Ask the user for an existing folder path."""

    raw_path = input(prompt).strip().strip('"').strip("'")

    if not raw_path:
        print("No folder path entered.")
        return None

    folder = Path(raw_path).expanduser().resolve()

    if not folder.is_dir():
        print("Error: folder does not exist.")
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
        actual = identify_file(path)

        results.append({
            "path": path,
            "actual_type": actual,
            "expected_type": expected_type(path),
            "status": check_extension(path, actual),
        })

    return results


def display_scan_results(results):
    """Print the file identification report."""

    print("\n========== FILE SCAN REPORT ==========")

    if not results:
        print("No files found in this folder.")
        return

    alerts = 0

    for result in results:

        filename = result["path"].name
        actual = result["actual_type"]
        expected = result["expected_type"] or "Not checked"
        status = result["status"]

        print(f"\nFile: {filename}")
        print(f"Actual type: {actual}")
        print(f"Expected type: {expected}")
        print(f"Result: {status}")

        if status in (
            "MISMATCH",
            "UNRECOGNIZED SIGNATURE",
            "READ ERROR",
        ):
            print("ALERT: Manual review recommended.")
            alerts += 1

    print("\nFiles scanned:", len(results))
    print("Files requiring review:", alerts)


def display_integrity_results(results):
    """Print the integrity check report."""

    print("\n========== INTEGRITY REPORT ==========")

    if not results:
        print("No files to compare.")
        return

    for filename, status in results:
        print(f"{filename}: {status}")

    changed = sum(
        status != "UNCHANGED"
        for _, status in results
    )

    print("\nFiles checked:", len(results))
    print("Changes detected:", changed)


def scan_option():
    folder = ask_folder("Enter the folder path to scan: ")

    if folder is None:
        return

    try:
        results = scan_folder(folder)
        display_scan_results(results)

    except OSError as error:
        print("Could not scan folder:", error)


def organize_option():
    folder = ask_folder("Enter the source folder path: ")

    if folder is None:
        return

    try:
        results = scan_folder(folder)
        display_scan_results(results)

        if not results:
            return

        output_text = input(
            "\nEnter a different output folder path: "
        ).strip().strip('"').strip("'")

        if not output_text:
            print("No output folder entered.")
            return

        output_folder = Path(output_text).expanduser().resolve()

        if output_folder == folder:
            print("Output must be different from the source folder.")
            return

        count = organize_scan_results(
            results,
            output_folder,
        )

        print(f"\nSuccessfully copied {count} files.")
        print("Output location:", output_folder)

    except (OSError, ValueError) as error:
        print("Organization failed:", error)


def baseline_option():
    folder = ask_folder(
        "Enter the folder to create a baseline for: "
    )

    if folder is None:
        return

    try:
        count = create_baseline(
            folder,
            BASELINE_PATH,
        )

        print("\nBaseline created successfully.")
        print("Files recorded:", count)
        print("Baseline location:", BASELINE_PATH)

    except (OSError, ValueError) as error:
        print("Could not create baseline:", error)


def integrity_option():
    folder = ask_folder(
        "Enter the folder to check: "
    )

    if folder is None:
        return

    try:
        results = check_integrity(
            folder,
            BASELINE_PATH,
        )

        display_integrity_results(results)

    except (OSError, ValueError) as error:
        print("Integrity check failed:", error)


def complete_scan_option():
    """Run identification, integrity checks, and optional organization."""

    folder = ask_folder(
        "Enter the folder for a complete scan: "
    )

    if folder is None:
        return

    try:
        results = scan_folder(folder)
        display_scan_results(results)

    except OSError as error:
        print("Could not scan folder:", error)
        return

    if BASELINE_PATH.is_file():

        try:
            integrity_results = check_integrity(
                folder,
                BASELINE_PATH,
            )

            display_integrity_results(integrity_results)

        except (OSError, ValueError) as error:
            print("\nIntegrity check unavailable:", error)

    else:
        print("\nNo baseline exists yet.")
        print("Use option 3 to create one.")

    answer = input(
        "\nAlso organize copies of these files? (y/n): "
    ).strip().lower()

    if answer == "y":

        output_text = input(
            "Enter a different output folder path: "
        ).strip().strip('"').strip("'")

        if not output_text:
            print("No output folder entered.")
            return

        output_folder = Path(output_text).expanduser().resolve()

        if output_folder == folder:
            print("Output must be different from the source folder.")
            return

        try:
            count = organize_scan_results(
                results,
                output_folder,
            )

            print(f"Organized {count} file copies.")

        except (OSError, ValueError) as error:
            print("Organization failed:", error)


def main():
    while True:

        print("\n" + "=" * 45)
        print("   SECURE FILE MANAGEMENT SYSTEM")
        print("=" * 45)

        print("1. Scan file types")
        print("2. Organize files")
        print("3. Create SHA-256 baseline")
        print("4. Check file integrity")
        print("5. Complete security scan")
        print("6. Exit")

        choice = input("\nEnter your choice: ").strip()

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
            print("Exiting Secure File Management System.")
            break

        else:
            print("Invalid choice. Please select 1-6.")


if __name__ == "__main__":
    main()