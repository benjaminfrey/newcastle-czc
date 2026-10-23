"""What an uploaded file is, decided by its first bytes, never by its name or the
browser's say-so; and a file name safe to show and to send back."""

import re
import unicodedata

_HEIF_BRANDS = {b"heic", b"heix", b"hevc", b"hevx", b"mif1", b"msf1"}
FILENAME_MAX = 200


def sniff(head: bytes) -> str | None:
    if head.startswith(b"%PDF-"):
        return "application/pdf"
    if head.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if len(head) >= 12 and head[4:8] == b"ftyp" and head[8:12] in _HEIF_BRANDS:
        return "image/heic"
    return None


def safe_filename(name: str) -> str:
    """Keep the last path component, drop control characters, trim to 200 characters
    (keeping the extension)."""
    name = re.split(r"[\\/]", name or "")[-1]
    name = "".join(ch for ch in name if unicodedata.category(ch)[0] != "C").strip().strip(".") or "file"
    if len(name) > FILENAME_MAX:
        stem, dot, ext = name.rpartition(".")
        ext = dot + ext if dot and len(ext) <= 10 else ""
        name = (stem if dot else name)[:FILENAME_MAX - len(ext)] + ext
    return name
