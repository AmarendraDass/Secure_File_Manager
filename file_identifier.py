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
    ".7z": "7Z",
    ".tar": "TAR",
    ".gz": "GZ",
    ".exe": "EXE",
    ".dll": "EXE",
    ".elf": "ELF",
    ".so": "ELF",
    ".mp3": "MP3",
    ".wav": "WAV",
    ".flac": "FLAC",
    ".ogg": "OGG",
    ".mp4": "MP4",
    ".m4v": "MP4",
    ".mov": "MP4",
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
    """Identify Office documents and archive formats stored inside ZIP containers."""
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
    """Identify a file using signatures (magic numbers) and content checks."""
    try:
        with open(file_path, "rb") as file:
            header = file.read(4096)
    except OSError:
        return "ERROR"

    if not header:
        return "EMPTY"

    # Images
    if header.startswith(b"\xff\xd8\xff"):
        return "JPEG"

    if header.startswith(b"\x89PNG\r\n\x1a\n"):
        return "PNG"

    if header.startswith((b"GIF87a", b"GIF89a")):
        return "GIF"

    if header.startswith(b"BM"):
        return "BMP"

    # PDF Document
    if header.startswith(b"%PDF-"):
        return "PDF"

    # ZIP or Office Document container
    if header.startswith((b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08")):
        return identify_zip_container(file_path)

    # 7-Zip Archive
    if header.startswith(b"7z\xbc\xaf\x27\x1c"):
        return "7Z"

    # GZIP Archive
    if header.startswith(b"\x1f\x8b"):
        return "GZ"

    # TAR Archive (check magic at offset 257)
    if len(header) >= 262 and header[257:262] == b"ustar":
        return "TAR"

    # Windows Executable / DLL
    if header.startswith(b"MZ"):
        return "EXE"

    # Linux ELF Executable / Shared Object
    if header.startswith(b"\x7fELF"):
        return "ELF"

    # Windows Shell Shortcut
    if header.startswith(b"\x4c\x00\x00\x00\x01\x14\x02\x00"):
        return "LNK"

    # Audio Formats
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

    if header.startswith(b"fLaC"):
        return "FLAC"

    if header.startswith(b"OggS"):
        return "OGG"

    # RIFF Containers (WEBP, WAV)
    if header.startswith(b"RIFF") and len(header) >= 12:
        if header[8:12] == b"WEBP":
            return "WEBP"

        if header[8:12] == b"WAVE":
            return "WAV"

    # MP4 / QuickTime Video container
    if len(header) >= 12 and header[4:8] == b"ftyp":
        return "MP4"

    # Text Heuristic
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


def format_size(size_bytes):
    """Return a clean human-readable file size string."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.2f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"


def get_hex_dump(file_path, num_bytes=64):
    """Generate a formatted forensic hex dump of the first N bytes of a file."""
    try:
        with open(file_path, "rb") as file:
            data = file.read(num_bytes)
        if not data:
            return "00000000:  (empty file)"

        lines = []
        for i in range(0, len(data), 16):
            chunk = data[i:i + 16]
            hex_part = " ".join(f"{b:02x}" for b in chunk)
            hex_part = hex_part.ljust(48)
            ascii_part = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
            lines.append(f"{i:08x}:  {hex_part}  |{ascii_part}|")
        return "\n".join(lines)
    except Exception as exc:
        return f"Error reading hex data: {exc}"


def get_magic_description(actual_type):
    """Return an informative security/type description for UI tooltips."""
    descriptions = {
        "JPEG": "JPEG image format (FF D8 FF magic signature)",
        "PNG": "Portable Network Graphics (89 50 4E 47 magic signature)",
        "GIF": "GIF graphics animation format (GIF87a / GIF89a)",
        "BMP": "Windows Bitmap uncompressed image (BM magic signature)",
        "WEBP": "Google WebP image format inside RIFF container",
        "PDF": "Adobe Portable Document Format (%PDF- header)",
        "ZIP": "Standard ZIP compressed archive (PK signature)",
        "7Z": "7-Zip high compression archive (7z signature)",
        "GZ": "Gzip compressed archive (1F 8B header)",
        "TAR": "POSIX tar archive tape format",
        "DOCX": "Microsoft Word OpenXML document inside ZIP container",
        "DOCM": "Microsoft Word Macro-Enabled document (Contains VBA Project!)",
        "PPTX": "Microsoft PowerPoint OpenXML presentation inside ZIP container",
        "PPTM": "Microsoft PowerPoint Macro-Enabled presentation (Contains VBA Project!)",
        "XLSX": "Microsoft Excel OpenXML spreadsheet inside ZIP container",
        "XLSM": "Microsoft Excel Macro-Enabled workbook (Contains VBA Project!)",
        "EXE": "Windows Portable Executable binary or DLL (MZ header)",
        "ELF": "Linux Executable and Linkable Format binary (\x7fELF header)",
        "MP3": "MPEG-1/2 Audio Layer III (ID3 tag or sync frame)",
        "WAV": "Waveform Audio File Format inside RIFF container",
        "FLAC": "Free Lossless Audio Codec (fLaC header)",
        "OGG": "Ogg multimedia bitstream container (OggS header)",
        "MP4": "MPEG-4 Part 14 / QuickTime video container (ftyp header)",
        "LNK": "Windows Shell Shortcut file",
        "TEXT": "Plaintext UTF-8 / ASCII / ANSI encoded human-readable text",
        "EMPTY": "Zero-byte file",
        "UNKNOWN": "Binary data with no known magic signature match",
        "ERROR": "Access or read error when scanning file",
    }
    return descriptions.get(actual_type, f"Identified as {actual_type}")
