from pathlib import Path
from datetime import datetime
import hashlib
import json


class IntegrityItem(tuple):
    """
    A 2-tuple (filename, status) with extra attributes (original_hash, current_hash).
    Provides 100% backward compatibility for (fn, status) unpacking while offering full hash details.
    """
    def __new__(cls, filename, status, original_hash=None, current_hash=None):
        return super().__new__(cls, (filename, status))

    def __init__(self, filename, status, original_hash=None, current_hash=None):
        self.filename = filename
        self.status = status
        self.original_hash = original_hash
        self.current_hash = current_hash


def calculate_sha256(file_path):
    """Calculate the SHA-256 hash of a file."""
    sha256 = hashlib.sha256()

    with open(file_path, "rb") as file:
        while True:
            chunk = file.read(65536)
            if not chunk:
                break
            sha256.update(chunk)

    return sha256.hexdigest()


def get_file_hashes(folder, excluded_paths=()):
    """Hash files inside a folder, including nested subfolders."""
    folder = Path(folder).expanduser().resolve()
    excluded = {
        str(Path(path).resolve())
        for path in excluded_paths
    }

    hashes = {}

    for path in sorted(
        (p for p in folder.rglob("*") if p.is_file()),
        key=lambda item: str(item.relative_to(folder)).lower(),
    ):
        resolved = str(path.resolve())

        if resolved in excluded:
            continue

        hashes[str(path.relative_to(folder)).replace("\\", "/")] = calculate_sha256(path)

    return hashes


def create_baseline(folder, baseline_path):
    """Save the current file hashes as the original baseline."""
    folder = Path(folder).expanduser().resolve()
    baseline_path = Path(baseline_path).expanduser().resolve()

    if not folder.is_dir():
        raise ValueError("The selected folder does not exist.")

    temporary_path = baseline_path.with_name(
        baseline_path.name + ".tmp"
    )

    hashes = get_file_hashes(
        folder,
        excluded_paths=[baseline_path, temporary_path],
    )

    data = {
        "folder": str(folder),
        "created_at": datetime.now().astimezone().isoformat(
            timespec="seconds"
        ),
        "algorithm": "SHA-256",
        "total_files": len(hashes),
        "files": hashes,
    }

    baseline_path.parent.mkdir(parents=True, exist_ok=True)

    temporary_path.write_text(
        json.dumps(data, indent=4),
        encoding="utf-8",
    )

    temporary_path.replace(baseline_path)

    return len(hashes)


def compare_hashes(original_hashes, current_hashes):
    """Compare two dictionaries of {relative_path: sha256} and return IntegrityItem list."""
    results = []

    all_files = sorted(
        set(original_hashes) | set(current_hashes),
        key=str.lower,
    )

    for filename in all_files:
        orig = original_hashes.get(filename)
        curr = current_hashes.get(filename)

        if filename not in original_hashes:
            status = "ADDED"
        elif filename not in current_hashes:
            status = "DELETED"
        elif orig != curr:
            status = "MODIFIED"
        else:
            status = "UNCHANGED"

        results.append(IntegrityItem(filename, status, original_hash=orig, current_hash=curr))

    return results


def check_integrity(folder, baseline_path, strict_folder_check=False):
    """Compare current files with the saved baseline."""
    folder = Path(folder).expanduser().resolve()
    baseline_path = Path(baseline_path).expanduser().resolve()

    if not baseline_path.is_file():
        raise FileNotFoundError(
            "No baseline found. Create a baseline first."
        )

    data = json.loads(
        baseline_path.read_text(encoding="utf-8")
    )

    baseline_folder = data.get("folder")
    if strict_folder_check and baseline_folder and baseline_folder != str(folder):
        raise ValueError(
            "This baseline belongs to a different folder. "
            "Create a baseline for the selected folder."
        )

    original_hashes = data.get("files", {})

    temporary_path = baseline_path.with_name(
        baseline_path.name + ".tmp"
    )

    current_hashes = get_file_hashes(
        folder,
        excluded_paths=[baseline_path, temporary_path],
    )

    return compare_hashes(original_hashes, current_hashes)
