#!/usr/bin/env python3
"""Unit tests for Rich progress and multi-threaded processing."""

import os
import sys
import unittest
import tempfile
import shutil

VAULT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SCRIPTS_DIR = os.path.join(VAULT_ROOT, "99_System", "Scripts")
if VAULT_ROOT not in sys.path:
    sys.path.insert(0, VAULT_ROOT)
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(1, SCRIPTS_DIR)

import ui_progress
from ui_progress import create_progress, track_parallel, DummyProgress, HAVE_RICH
from platforms.common import save_or_update_assets_parallel
from update_currencies import update_currencies
from sync_etf_holdings import sync_all_etfs
from run import build_parser, print_summary, TeeLogger


class TestRichProgress(unittest.TestCase):
    """Test suite for ui_progress module and concurrent progress handling."""

    def test_have_rich_is_true(self):
        """Verify that the rich library is installed and detected."""
        self.assertTrue(HAVE_RICH, "Expected rich library to be detected and imported.")

    def test_create_progress_active(self):
        """Test creating an active Rich progress instance."""
        with create_progress("Test Task", total=5, disable=False) as progress:
            self.assertIsNotNone(progress)
            task_id = progress.add_task("Subtask", total=3, status="init")
            progress.advance(task_id, 1)
            progress.update(task_id, advance=1, status="in-progress")
            progress.update(task_id, advance=1, status="done")

    def test_create_progress_disabled(self):
        """Test creating a disabled progress instance returns DummyProgress."""
        with create_progress("Disabled Task", total=5, disable=True) as progress:
            self.assertIsInstance(progress, DummyProgress)
            t = progress.add_task("Subtask", total=2)
            progress.advance(t, 1)
            progress.update(t, advance=1)

    def test_track_parallel_success(self):
        """Test executing tasks concurrently with track_parallel."""
        items = [10, 20, 30, 40]

        def square(x):
            return x * x

        completed = []
        results = track_parallel(
            tasks=items,
            worker_fn=square,
            max_workers=2,
            description="Squaring numbers",
            get_item_label=lambda x: f"item-{x}",
            on_complete=lambda task, res: completed.append((task, res)),
            disable=False,
        )

        self.assertEqual(len(results), 4)
        for task, res, exc in results:
            self.assertIsNone(exc)
            self.assertEqual(res, task * task)
        self.assertEqual(len(completed), 4)

    def test_track_parallel_with_errors(self):
        """Test track_parallel handling exceptions in worker threads gracefully."""
        items = [1, 0, 2]

        def divide(x):
            return 10 / x

        errors = []
        results = track_parallel(
            tasks=items,
            worker_fn=divide,
            max_workers=2,
            description="Dividing numbers",
            on_error=lambda task, exc: errors.append((task, exc)),
            disable=False,
        )

        self.assertEqual(len(results), 3)
        self.assertEqual(len(errors), 1)
        err_task, err_exc = errors[0]
        self.assertEqual(err_task, 0)
        self.assertIsInstance(err_exc, ZeroDivisionError)

    def test_save_or_update_assets_parallel_empty(self):
        """Test save_or_update_assets_parallel with empty tasks."""
        paths, tickers, count = save_or_update_assets_parallel([], max_workers=2, show_progress=True)
        self.assertEqual(count, 0)
        self.assertEqual(len(paths), 0)
        self.assertEqual(len(tickers), 0)

        paths, tickers, count = save_or_update_assets_parallel([], max_workers=2, show_progress=False)
        self.assertEqual(count, 0)

    def test_run_parser_no_progress_flag(self):
        """Verify that run.py CLI parser includes the --no-progress option."""
        parser = build_parser()
        args = parser.parse_args(["--no-progress", "--rates"])
        self.assertTrue(args.no_progress)
        self.assertTrue(args.action_update_rates)

    def test_tee_logger_strips_ansi(self):
        """Verify TeeLogger strips ANSI escape codes and consolidates carriage returns for clean log output."""
        import io
        stream = io.StringIO()
        with tempfile.NamedTemporaryFile("w+", delete=False, encoding="utf-8") as temp_log:
            temp_log_path = temp_log.name

        try:
            logger = TeeLogger(stream, temp_log_path)
            # Write ANSI-colored string and carriage returns
            logger.write("\x1b[32mLine 1\x1b[0m\n")
            logger.write("Progress 1\rProgress 2\rProgress 3\n")
            logger.flush()
            logger.close()

            with open(temp_log_path, "r", encoding="utf-8") as f:
                log_content = f.read()

            self.assertIn("Line 1", log_content)
            self.assertNotIn("\x1b[32m", log_content)
            self.assertNotIn("Progress 1", log_content)
            self.assertIn("Progress 3", log_content)
        finally:
            if os.path.exists(temp_log_path):
                os.remove(temp_log_path)

    def test_print_summary_rich_and_plain(self):
        """Verify print_summary works with both use_rich=True and use_rich=False."""
        results = [
            ("step1", "Description 1", "SUCCESS", 1.23),
            ("step2", "Description 2", "FAILED", 0.45),
            ("step3", "Description 3", "SKIPPED", 0.0),
        ]
        # Should execute without errors
        print_summary(results, use_rich=True)
        print_summary(results, use_rich=False)

    def test_update_currencies_with_rich_progress(self):
        """Test update_currencies execution in a temp directory with show_progress=True and False."""
        temp_dir = tempfile.mkdtemp()
        try:
            # Create a mock asset note
            asset_path = os.path.join(temp_dir, "test_asset.md")
            with open(asset_path, "w", encoding="utf-8") as f:
                f.write(
                    "---\n"
                    "ticker: 'PLN_CASH'\n"
                    "name: 'Cash Balance'\n"
                    "platform: 'Manual'\n"
                    "quantity: 1000\n"
                    "current_price: 1.0\n"
                    "currency: 'PLN'\n"
                    "value_pln: 1000.0\n"
                    "---\n\n"
                    "# Cash Balance\n"
                )

            # Test with show_progress=True
            update_currencies(temp_dir, max_workers=2, show_progress=True)

            # Test with show_progress=False
            update_currencies(temp_dir, max_workers=2, show_progress=False)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_sync_all_etfs_dry_run_with_rich_progress(self):
        """Test sync_all_etfs dry-run in a temp directory with show_progress=True and False."""
        temp_assets = tempfile.mkdtemp()
        temp_holdings = tempfile.mkdtemp()
        try:
            # Empty dir run with show_progress=True
            sync_all_etfs(
                assets_dir=temp_assets,
                holdings_dir=temp_holdings,
                dry_run=True,
                max_workers=2,
                show_progress=True,
            )
            # Empty dir run with show_progress=False
            sync_all_etfs(
                assets_dir=temp_assets,
                holdings_dir=temp_holdings,
                dry_run=True,
                max_workers=2,
                show_progress=False,
            )
        finally:
            shutil.rmtree(temp_assets, ignore_errors=True)
            shutil.rmtree(temp_holdings, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
