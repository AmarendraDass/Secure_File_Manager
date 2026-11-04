
from pathlib import Path
import zipfile


EXTENSION_TYPES = {
    ".jpg": "JPEG",
    ".jpeg": "JPEG",
    ".png": "PNG",
    ".gif": "GIF",
    ".bmp": "BMP",
    ".webp": "WEBP",
    ".pdf": "PDF",
    ".zip": "ZIP",
    ".exe": "EXE",
    ".dll": "EXE",
    ".elf": "ELF",
    ".so": "ELF",
    ".mp3": "MP3",
    ".wav": "WAV",
    ".txt": "TEXT",
    ".ini": "TEXT",
    ".log": "TEXT",
    ".csv": "TEXT",
    ".md": "TEXT",
    ".py": "TEXT",
    ".json": "TEXT",
    ".xml": "TEXT",
    ".html": "TEXT",
    ".css": "TEXT",
    ".js": "TEXT",
    ".sql": "TEXT",
    ".lnk": "LNK",
    ".docx": "DOCX",
    ".docm": "DOCM",
    ".pptx": "PPTX",
    ".pptm": "PPTM",
    ".xlsx": "XLSX",
    ".xlsm": "XLSM",
}


def identify_zip_container(file_path):
    """Identify Office documents stored inside ZIP containers."""
    try:
        with zipfile.ZipFile(file_path, "r") as archive:
            names = set(archive.namelist())
    except (OSError, zipfile.BadZipFile):
        return "UNKNOWN"

    if "[Content_Types].xml" in names:
        if "word/document.xml" in names:
            return "DOCM" if "word/vbaProject.bin" in names else "DOCX"

        if "ppt/presentation.xml" in names:
            return "PPTM" if "ppt/vbaProject.bin" in names else "PPTX"

        if "xl/workbook.xml" in names:
            return "XLSM" if "xl/vbaProject.bin" in names else "XLSX"

    return "ZIP"


def looks_like_text(data):
    """Heuristically identify readable text."""
    if not data:
        return False

    if data.startswith(b"\xff\xfe\x00\x00"):
        decoded = data.decode("utf-32-le", errors="ignore")
    elif data.startswith(b"\x00\x00\xfe\xff"):
        decoded = data.decode("utf-32-be", errors="ignore")
    elif data.startswith(b"\xff\xfe"):
        decoded = data.decode("utf-16-le", errors="ignore")
    elif data.startswith(b"\xfe\xff"):
        decoded = data.decode("utf-16-be", errors="ignore")
    elif data.startswith(b"\xef\xbb\xbf"):
        decoded = data[3:].decode("utf-8", errors="replace")
    else:
        if b"\x00" in data:
            return False

        try:
            decoded = data.decode("utf-8")
        except UnicodeDecodeError:
            try:
                decoded = data.decode("cp1252")
            except UnicodeDecodeError:
                return False

    if not decoded:
        return False

    printable = sum(
        char.isprintable() or char in "\r\n\t\f"
        for char in decoded
    )

    return printable / len(decoded) >= 0.85


def identify_file(file_path):
    """Identify a file using signatures and content checks."""
    try:
        with open(file_path, "rb") as file:
            header = file.read(4096)
    except OSError:
        return "ERROR"

    if not header:
        return "EMPTY"

    if header.startswith(b"\xff\xd8\xff"):
        return "JPEG"

    if header.startswith(b"\x89PNG\r\n\x1a\n"):
        return "PNG"

    if header.startswith((b"GIF87a", b"GIF89a")):
        return "GIF"

    if header.startswith(b"BM"):
        return "BMP"

    if header.startswith(b"%PDF-"):
        return "PDF"

    if header.startswith((b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08")):
        return identify_zip_container(file_path)

    if header.startswith(b"MZ"):
        return "EXE"

    if header.startswith(b"\x7fELF"):
        return "ELF"

    if header.startswith(b"\x4c\x00\x00\x00\x01\x14\x02\x00"):
        return "LNK"

    if header.startswith(b"ID3"):
        return "MP3"

    if (
        len(header) >= 3
        and header[0] == 0xFF
        and (header[1] & 0xE0) == 0xE0
    ):
        version = (header[1] >> 3) & 0x03
        layer = (header[1] >> 1) & 0x03
        bitrate_index = (header[2] >> 4) & 0x0F

        if version != 1 and layer != 0 and bitrate_index not in (0, 15):
            return "MP3"

    if header.startswith(b"RIFF") and len(header) >= 12:
        if header[8:12] == b"WEBP":
            return "WEBP"

        if header[8:12] == b"WAVE":
            return "WAV"

    if looks_like_text(header):
        return "TEXT"

    return "UNKNOWN"


def expected_type(file_path):
    """Get the expected type from the filename extension."""
    extension = Path(file_path).suffix.lower()
    return EXTENSION_TYPES.get(extension)


def check_extension(file_path, actual_type):
    """Compare the detected type with the expected type."""
    expected = expected_type(file_path)

    if actual_type == "ERROR":
        return "READ ERROR"

    if actual_type == "EMPTY":
        return "EMPTY FILE"

    if expected is None:
        return "NOT CHECKED"

    if actual_type == "UNKNOWN":
        return "UNRECOGNIZED SIGNATURE"

    if expected == actual_type:
        return "MATCH"

    return "MISMATCH"
