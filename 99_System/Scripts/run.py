#!/usr/bin/env python3
"""Shim for Unified CLI Runner located at repository root.

Allows running `python 99_System/Scripts/run.py` identically to `python run.py`.
"""

import os
import sys
import importlib.util

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
VAULT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "../.."))

if VAULT_ROOT not in sys.path:
    sys.path.insert(0, VAULT_ROOT)

# Import root runner module directly
spec = importlib.util.spec_from_file_location("root_runner", os.path.join(VAULT_ROOT, "run.py"))
root_runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(root_runner)

main = root_runner.main
build_parser = getattr(root_runner, "build_parser", None)
print_summary = getattr(root_runner, "print_summary", None)
TeeLogger = getattr(root_runner, "TeeLogger", None)

if __name__ == "__main__":
    sys.exit(main())
