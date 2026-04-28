#!/usr/bin/env python3
"""Backward-compatible entry point. Equivalent to `python -m daemon`."""
from daemon.cli.main import main

if __name__ == "__main__":
    main()
