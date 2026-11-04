from pathlib import Path
import io
import shutil
import zipfile


# Categories based on detected file type
TYPE_FOLDERS = {
    "JPEG": "Images",
    "PNG": "Images",
    "GIF": "Images",
    "BMP": "Images",
    "WEBP": "Images",
    "PDF": "Documents",
    "DOCX": "Documents",
    "DOCM": "Documents",
    "PPTX": "Presentations",
    "PPTM": "Presentations",
    "XLSX": "Spreadsheets",
    "XLSM": "Spreadsheets",
    "ZIP": "Archives",
    "7Z": "Archives",
    "TAR": "Archives",
    "GZ": "Archives",
    "EXE": "Executables",
    "ELF": "Linux_Executables",
    "LNK": "Shortcuts",
    "MP3": "Audio",
    "WAV": "Audio",
    "FLAC": "Audio",
    "OGG": "Audio",
    "MP4": "Videos",
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
    ".zip": "Archives",
}


def choose_category(result):
    """Choose a destination folder for a scanned file."""
    status = result.get("status")

    if status in (
        "MISMATCH",
        "UNRECOGNIZED SIGNATURE",
        "READ ERROR",
    ):
        return "Review_Mismatches"

    actual_type = result.get("actual_type")

    if actual_type in TYPE_FOLDERS:
        return TYPE_FOLDERS[actual_type]

    path = Path(result["path"])
    extension = path.suffix.lower()

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
        copied += 1

    return copied


def create_organized_zip(results, output_zip_path=None):
    """
    Bundle scanned files into a categorized ZIP archive.
    If output_zip_path is None, returns an in-memory io.BytesIO object.
    """
    buffer = io.BytesIO() if output_zip_path is None else None
    target = output_zip_path if output_zip_path is not None else buffer

    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
        name_counts = {}

        for result in results:
            source = Path(result["path"])
            if not source.is_file():
                continue

            category = choose_category(result)
            base_name = source.name

            key = (category, base_name)
            count = name_counts.get(key, 0)
            if count > 0:
                stem = Path(base_name).stem
                suffix = Path(base_name).suffix
                archive_filename = f"{stem}_{count}{suffix}"
            else:
                archive_filename = base_name

            name_counts[key] = count + 1
            archive_path = f"{category}/{archive_filename}"
            archive.write(source, arcname=archive_path)

    if buffer is not None:
        buffer.seek(0)
        return buffer

    return output_zip_path
