#!/usr/bin/env python3
"""Shim for Unified CLI Runner located at repository root.

Allows running `python 99_System/Scripts/run.py` identically to `python run.py`.
"""

import os
import sys

# Find repository root and add to sys.path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
VAULT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "../.."))

if VAULT_ROOT not in sys.path:
    sys.path.insert(0, VAULT_ROOT)

import run

if __name__ == "__main__":
    sys.exit(run.main())
