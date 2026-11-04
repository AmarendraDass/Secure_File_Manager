from pathlib import Path
import shutil


# Categories based on detected file type
TYPE_FOLDERS = {
    "JPEG": "Images",
    "PNG": "Images",
    "GIF": "Images",
    "BMP": "Images",
    "WEBP": "Images",
    "PDF": "Documents",
    "ZIP": "Archives",
    "EXE": "Executables",
    "ELF": "Linux_Executables",
    "MP3": "Audio",
    "WAV": "Audio",
}


# Fallback categories for files without recognized signatures
EXTENSION_FOLDERS = {
    ".txt": "Documents",
    ".md": "Documents",
    ".doc": "Documents",
    ".docx": "Documents",
    ".rtf": "Documents",
    ".csv": "Spreadsheets",
    ".xls": "Spreadsheets",
    ".xlsx": "Spreadsheets",
    ".ppt": "Presentations",
    ".pptx": "Presentations",
    ".py": "Code_and_Data",
    ".js": "Code_and_Data",
    ".html": "Code_and_Data",
    ".css": "Code_and_Data",
    ".json": "Code_and_Data",
    ".xml": "Code_and_Data",
    ".sql": "Code_and_Data",
    ".log": "Logs",
    ".mp4": "Videos",
    ".mov": "Videos",
    ".mkv": "Videos",
    ".avi": "Videos",
    ".7z": "Archives",
    ".rar": "Archives",
    ".tar": "Archives",
    ".gz": "Archives",
}


def choose_category(result):
    """Choose a destination folder for a scanned file."""

    status = result["status"]

    if status in (
        "MISMATCH",
        "UNRECOGNIZED SIGNATURE",
        "READ ERROR",
    ):
        return "Review_Mismatches"

    actual_type = result["actual_type"]

    if actual_type in TYPE_FOLDERS:
        return TYPE_FOLDERS[actual_type]

    extension = result["path"].suffix.lower()

    return EXTENSION_FOLDERS.get(extension, "Others")


def unique_destination(destination):
    """Avoid overwriting files with the same name."""

    if not destination.exists():
        return destination

    number = 1

    while True:
        candidate = destination.with_name(
            f"{destination.stem}_{number}{destination.suffix}"
        )

        if not candidate.exists():
            return candidate

        number += 1


def organize_scan_results(results, output_folder):
    """Copy scanned files into their destination categories."""

    output_folder = Path(output_folder).expanduser().resolve()

    source_roots = {
        Path(result["path"]).resolve().parent
        for result in results
    }

    for source_root in source_roots:
        try:
            output_folder.relative_to(source_root)
        except ValueError:
            continue
        raise ValueError(
            "Choose a different output folder from the source folder."
        )

    copied = 0

    for result in results:
        source = Path(result["path"])

        category = choose_category(result)

        category_folder = output_folder / category
        category_folder.mkdir(parents=True, exist_ok=True)

        destination = unique_destination(
            category_folder / source.name
        )

        shutil.copy2(source, destination)

        print(f"Copied: {source.name} -> {category}/")

        copied += 1

    return copied