"""
Sample name inference and R1/R2 pairing from filenames.

Scope is deliberately narrow: work out a sample name, and work out which files
belong together as a pair. Nothing else is inferred from a filename.

What used to live here and why it is gone:

  tumour/normal detection - matched things like `[-_]T[-_]` anywhere in a name,
    so any sample with `_T_` in it was labelled a tumour. Guessing clinical
    status from a filename is not a defensible thing for this tool to do, and
    no supported pipeline asked for it.

  TCGA / patient-ID extraction, replicate numbers - left over from a retired
    WGS pipeline. The replicate rule matched an R followed by digits between
    separators, carrying a comment saying "but not R1/R2 for reads!" - which
    is exactly what it matched.

  Single-end detection - the samplesheet template now makes the user state it.
    See generate_samplesheet.py.

Dead inference is worse than no inference: the next person to read this assumes
it was verified.
"""

import os
import re
from typing import Dict, List, Optional, Tuple


# R1/R2 patterns with priority scores (higher = more confident)
R1_PATTERNS = [
    (r'_R1_\d{3}', 10),      # _R1_001 (Illumina standard)
    (r'_R1[_.]', 8),         # _R1. or _R1_
    (r'\.R1[_.]', 8),        # .R1. or .R1_
    (r'_1[_.]', 5),          # _1. or _1_
    (r'_R1\.f', 6),          # _R1.fastq
    (r'_1\.f', 4),           # _1.fastq
]

R2_PATTERNS = [
    (r'_R2_\d{3}', 10),      # _R2_001 (Illumina standard)
    (r'_R2[_.]', 8),         # _R2. or _R2_
    (r'\.R2[_.]', 8),        # .R2. or .R2_
    (r'_2[_.]', 5),          # _2. or _2_
    (r'_R2\.f', 6),          # _R2.fastq
    (r'_2\.f', 4),           # _2.fastq
]

# Lane pattern
LANE_PATTERN = r'[_.]L(\d{3})[_.]'


def extract_sample_info(filepath: str) -> Dict[str, str]:
    """
    Extract sample metadata from filepath.

    Args:
        filepath: Path to sequencing file

    Returns:
        Dict with: sample, lane
    """
    filename = os.path.basename(filepath)

    # Remove extensions
    stem = filename
    for ext in ['.fastq.gz', '.fq.gz', '.fastq', '.fq', '.bam', '.cram', '.bai', '.crai']:
        if stem.lower().endswith(ext):
            stem = stem[:-len(ext)]
            break

    info = {}

    # Extract lane
    lane_match = re.search(LANE_PATTERN, stem)
    info['lane'] = f"L{lane_match.group(1)}" if lane_match else "L001"

    # Remove lane from stem
    clean_stem = re.sub(LANE_PATTERN, '_', stem)

    # Remove R1/R2 indicators and everything after
    for pattern, _ in R1_PATTERNS + R2_PATTERNS:
        clean_stem = re.sub(pattern + r'.*', '', clean_stem, flags=re.IGNORECASE)

    # Clean up trailing/multiple underscores and dots
    clean_stem = re.sub(r'[_.-]+$', '', clean_stem)
    clean_stem = re.sub(r'[_.-]{2,}', '_', clean_stem)

    # Sample is the cleaned stem
    info['sample'] = clean_stem if clean_stem else filename.split('.')[0]

    return info




def _get_pattern_score(filename: str, patterns: List[Tuple[str, int]]) -> int:
    """Get highest matching pattern score."""
    max_score = 0
    for pattern, score in patterns:
        if re.search(pattern, filename, re.IGNORECASE):
            max_score = max(max_score, score)
    return max_score


def _get_sample_key(filepath: str) -> str:
    """Generate a key for grouping related files."""
    info = extract_sample_info(filepath)
    sample = info['sample']
    lane = info.get('lane', 'L001')

    # Include lane in key for multi-lane samples
    if lane != "L001":
        return f"{sample}_{lane}"
    return sample


def match_read_pairs(files) -> Dict[str, Dict]:
    """
    Match R1/R2 read pairs using scored pattern matching.

    Args:
        files: List of FileInfo objects (from file_discovery)

    Returns:
        Dict mapping sample_key to {'r1': path, 'r2': path, 'info': dict}
    """
    # Classify files
    r1_files = []
    r2_files = []

    for file in files:
        filename = file.name if hasattr(file, 'name') else os.path.basename(str(file))
        filepath = file.path if hasattr(file, 'path') else str(file)

        r1_score = _get_pattern_score(filename, R1_PATTERNS)
        r2_score = _get_pattern_score(filename, R2_PATTERNS)

        if r2_score > r1_score and r2_score > 0:
            r2_files.append((filepath, r2_score))
        elif r1_score > 0:
            r1_files.append((filepath, r1_score))
        else:
            # No clear indicator - assume R1 (single-end or non-standard naming)
            r1_files.append((filepath, 0))

    # Build pairs by matching sample keys
    pairs = {}

    # Process R1 files first
    for r1_path, score in r1_files:
        key = _get_sample_key(r1_path)
        info = extract_sample_info(r1_path)

        if key not in pairs:
            pairs[key] = {
                'r1': r1_path,
                'r2': None,
                'info': info,
                'score': score
            }
        else:
            # Multiple R1 files for same sample (should not happen)
            pairs[key]['r1'] = r1_path

    # Match R2 files
    for r2_path, score in r2_files:
        key = _get_sample_key(r2_path)
        info = extract_sample_info(r2_path)

        if key in pairs:
            pairs[key]['r2'] = r2_path
        else:
            # R2 without matching R1
            pairs[key] = {
                'r1': None,
                'r2': r2_path,
                'info': info,
                'score': score
            }

    return pairs


