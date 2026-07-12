"""
Small file-hashing utility, used for content-based duplicate detection.
"""

import hashlib
from pathlib import Path


def hash_file(file_path: str | Path, chunk_size: int = 8192) -> str:
    """Compute a SHA-256 hash of a file's contents, reading in chunks to
    avoid loading large files entirely into memory."""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(chunk_size):
            sha256.update(chunk)
    return sha256.hexdigest()