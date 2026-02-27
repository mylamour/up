"""Concurrency utilities for up-cli.

Provides a shared thread pool for running subprocess calls so that
long-running or blocking subprocesses do not block the main thread.
"""

import subprocess
from concurrent.futures import ThreadPoolExecutor
from typing import Any

# Shared executor for subprocess.run offload (max 8 concurrent subprocesses)
_subprocess_executor = ThreadPoolExecutor(max_workers=8, thread_name_prefix="up-subprocess")


def run_subprocess(*args: Any, **kwargs: Any) -> subprocess.CompletedProcess:
    """Run subprocess.run in the shared thread pool.

    Same signature as subprocess.run; use as a drop-in replacement
    where blocking the main thread should be avoided.
    """
    future = _subprocess_executor.submit(subprocess.run, *args, **kwargs)
    return future.result()
