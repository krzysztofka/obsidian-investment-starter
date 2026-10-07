#!/usr/bin/env python3
"""Unified Rich Progress & Observability Module for Concurrent Tasks.

Provides reusable progress bars, spinners, and parallel execution helpers
powered by the `rich` library with graceful fallback support for headless/CI
or non-interactive environments.
"""

import concurrent.futures
from collections.abc import Callable, Sequence
from typing import Any, TypeVar

T = TypeVar("T")
R = TypeVar("R")

try:
    from rich.console import Console
    from rich.progress import (
        BarColumn,
        MofNCompleteColumn,
        Progress,
        SpinnerColumn,
        Task,
        TaskProgressColumn,
        TextColumn,
        TimeElapsedColumn,
    )
    from rich.text import Text

    HAVE_RICH = True
except ImportError:
    HAVE_RICH = False
    Console = None  # type: ignore[assignment, misc]
    Text = None  # type: ignore[assignment, misc]
    Progress = None  # type: ignore[assignment, misc]
    Task = None  # type: ignore[assignment, misc]

_global_console: Any | None = None


def get_console() -> Any:
    """Retrieve or initialize the global Rich Console instance."""
    global _global_console
    if not HAVE_RICH:
        return None
    if _global_console is None:
        _global_console = Console(stderr=False)
    return _global_console


if HAVE_RICH:

    class StatusColumn(TextColumn):
        """Custom TextColumn that safely extracts task.fields['status'] without throwing KeyError."""

        def __init__(self, text_format: str = "[dim]{task.fields[status]}[/dim]", **kwargs):
            super().__init__(text_format, **kwargs)

        def render(self, task: Task) -> Text:
            status = task.fields.get("status", "")
            if not status:
                return Text("")
            return super().render(task)
else:

    class StatusColumn:  # type: ignore
        pass


class DummyTask:
    """Fallback dummy task for environments without Rich."""

    def __init__(self, task_id: int = 0):
        self.id = task_id
        self.fields: dict[str, Any] = {}


class DummyProgress:
    """Fallback dummy progress manager when Rich is unavailable or explicitly disabled."""

    def __init__(self, *args, **kwargs):
        self.console = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def add_task(self, description: str, total: int | None = None, **kwargs) -> int:
        return 0

    def advance(self, task_id: int, advance: float = 1.0):
        pass

    def update(self, task_id: int, advance: float | None = None, **kwargs):
        pass

    def print(self, *args, **kwargs):
        print(*args, **kwargs)


def create_progress(
    description: str | None = None,
    total: int | None = None,
    transient: bool = False,
    disable: bool = False,
    console: Any | None = None,
    redirect_stdout: bool = True,
    redirect_stderr: bool = True,
) -> Any:
    """Create a configured Rich Progress instance with standardized columns.

    Columns included:
      - SpinnerColumn (dots animation)
      - TextColumn (task description in bold cyan)
      - BarColumn (adaptive width progress bar)
      - TaskProgressColumn (percentage completion)
      - MofNCompleteColumn (items processed e.g. [5/20])
      - TimeElapsedColumn (elapsed time e.g. [00:03])
      - StatusColumn (dynamic detail / status indicator)

    Parameters:
        description: Optional initial task description.
        total: Optional total count of items.
        transient: If True, clears progress display on context exit.
        disable: If True, completely disables rendering (no-op).
        console: Optional custom Rich Console instance.
        redirect_stdout: Intercept stdout so print statements appear above progress bar.
        redirect_stderr: Intercept stderr so warnings appear above progress bar.

    Returns:
        Configured Progress instance (or DummyProgress if Rich is unavailable).
    """
    if not HAVE_RICH or disable:
        return DummyProgress()

    active_console = console or get_console()

    columns = [
        SpinnerColumn(spinner_name="dots"),
        TextColumn("[bold cyan]{task.description}"),
        BarColumn(bar_width=None),
        TaskProgressColumn(),
        MofNCompleteColumn(),
        TimeElapsedColumn(),
        StatusColumn(),
    ]

    progress = Progress(
        *columns,
        console=active_console,
        transient=transient,
        redirect_stdout=redirect_stdout,
        redirect_stderr=redirect_stderr,
    )

    if description is not None and total is not None:
        progress.add_task(description, total=total, status="")

    return progress


def track_parallel(
    tasks: Sequence[T],
    worker_fn: Callable[[T], R],
    max_workers: int,
    description: str = "Processing...",
    get_item_label: Callable[[T], str] | None = None,
    disable: bool = False,
    on_complete: Callable[[T, R], None] | None = None,
    on_error: Callable[[T, Exception], None] | None = None,
) -> list[tuple[T, R | None, Exception | None]]:
    """Execute tasks concurrently across worker threads with a real-time Rich progress bar.

    Parameters:
        tasks: Sequence of task inputs to process.
        worker_fn: Worker function taking a task input and returning a result.
        max_workers: Concurrency thread pool size.
        description: Label displayed on the progress bar.
        get_item_label: Optional callable returning a brief string identifier for a task.
        disable: If True, runs without displaying the Rich progress bar.
        on_complete: Optional callback invoked on successful task completion: (task, result).
        on_error: Optional callback invoked on task exception: (task, exception).

    Returns:
        List of (task, result, exception) tuples in completion order.
    """
    if not tasks:
        return []

    results: list[tuple[T, R | None, Exception | None]] = []

    with create_progress(disable=disable) as progress:
        task_id = progress.add_task(description, total=len(tasks), status="Starting...")

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_task = {executor.submit(worker_fn, task): task for task in tasks}

            for future in concurrent.futures.as_completed(future_to_task):
                task = future_to_task[future]
                label = get_item_label(task) if get_item_label else str(task)

                try:
                    res = future.result()
                    results.append((task, res, None))
                    if on_complete:
                        on_complete(task, res)
                    progress.update(task_id, advance=1, status=f"[green]✓[/green] {label}")
                except Exception as exc:
                    results.append((task, None, exc))
                    if on_error:
                        on_error(task, exc)
                    else:
                        progress.console.print(f"[red]Error processing {label}:[/red] {exc}")
                    progress.update(task_id, advance=1, status=f"[red]✗[/red] {label}")

        progress.update(task_id, status="[bold green]Completed[/bold green]")

    return results
