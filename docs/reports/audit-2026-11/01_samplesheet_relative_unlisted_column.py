"""PR #260 / #301 (abf_station/launch.py): a samplesheet cell is confined to the allowed read roots only when it is
a 'path cell' -- in a column named like DEFAULT_PATH_COLUMN, in --path-columns, or starting with '/'.
Fact the safety rests on: every column that holds a file is recognised by name. Prove or refute with the real code.
Run: python3 -I docs/reports/audit-2026-11/01_samplesheet_relative_unlisted_column.py"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "platform"))
from abf_station import launch

roots = ["/work/alice"]
for header in ("fastq_1", "short_reads_1", "long_reads", "bai", "input_reads", "forward"):
    rows = [["sample", header], ["s1", "../../bob/secret_R1.fastq.gz"]]
    try:
        launch._check_samplesheet(rows, [], roots)
        print("%-14s ACCEPTED  cells judged as paths: %s" % (header, launch.path_cells(rows, [])))
    except launch.BundleError as e:
        print("%-14s refused   %s" % (header, str(e)[:70]))
