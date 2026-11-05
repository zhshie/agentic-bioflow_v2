"""
File discovery utilities for FASTQ, BAM, and CRAM files.

This module provides functions to recursively discover sequencing data files
in a directory structure.
"""
# Nothing existing: nf-core pipelines expect a samplesheet already built; no
# shared tool discovers raw FASTQ/BAM/CRAM files from a directory to feed one.

import os
from dataclasses import dataclass
from typing import Dict, List


@dataclass
class FileInfo:
    """Information about a discovered file."""
    path: str
    name: str
    stem: str
    extension: str
    size: int
    file_type: str  # fastq, bam, cram

    def __repr__(self):
        return f"FileInfo({self.name}, type={self.file_type})"


# Supported file extensions by type
EXTENSIONS = {
    "fastq": [".fastq.gz", ".fq.gz", ".fastq", ".fq"],
    "bam": [".bam"],
    "cram": [".cram"],
}


def discover_files(
    directory: str,
    file_type: str = "fastq",
    follow_symlinks: bool = True
) -> List[FileInfo]:
    """
    Recursively discover files of specified type.

    Args:
        directory: Root directory to search
        file_type: One of 'fastq', 'bam', 'cram'
        follow_symlinks: Whether to follow symbolic links

    Returns:
        List of FileInfo objects sorted by path
    """
    if file_type not in EXTENSIONS:
        raise ValueError(f"Unknown file type: {file_type}. Supported: {list(EXTENSIONS.keys())}")

    directory = os.path.abspath(directory)
    if not os.path.isdir(directory):
        raise ValueError(f"Not a directory: {directory}")

    extensions = EXTENSIONS[file_type]
    files = []
    seen_paths = set()  # Avoid duplicates from symlinks

    for root, _, filenames in os.walk(directory, followlinks=follow_symlinks):
        for filename in filenames:
            # Check each extension
            for ext in extensions:
                if filename.lower().endswith(ext.lower()):
                    full_path = os.path.join(root, filename)

                    # Resolve to handle symlinks
                    try:
                        real_path = os.path.realpath(full_path)
                    except OSError:
                        real_path = full_path

                    if real_path in seen_paths:
                        continue
                    seen_paths.add(real_path)

                    try:
                        size = os.path.getsize(full_path)
                    except OSError:
                        size = 0

                    # Extract stem (remove extension)
                    stem = filename
                    for e in extensions:
                        if stem.lower().endswith(e.lower()):
                            stem = stem[:-len(e)]
                            break

                    files.append(FileInfo(
                        path=full_path,
                        name=filename,
                        stem=stem,
                        extension=ext,
                        size=size,
                        file_type=file_type
                    ))
                    break  # Found matching extension, no need to check others

    return sorted(files, key=lambda f: f.path)


def count_files_by_type(directory: str) -> Dict[str, int]:
    """
    Count files by type in directory.

    Args:
        directory: Directory to scan

    Returns:
        Dict mapping file_type to count
    """
    counts = {}
    for file_type in EXTENSIONS:
        try:
            files = discover_files(directory, file_type)
            counts[file_type] = len(files)
        except (ValueError, PermissionError):
            counts[file_type] = 0
    return counts

