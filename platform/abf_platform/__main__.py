# Nothing existing: the two-line entry point that lets 'python -m abf_platform' run the command line in cli.py.
import sys

from .cli import main

if __name__ == "__main__":
    sys.exit(main())
