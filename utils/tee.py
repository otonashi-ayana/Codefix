import os
import sys
import threading


class _TeeStream:
    """A stream that writes to both the original stream and a log file.

    - Preserves print behavior (newline handling, flush).
    - Thread-safe to avoid interleaved writes from concurrent threads.
    """

    def __init__(self, original, file_handle):
        self._original = original
        self._file = file_handle
        self._lock = threading.Lock()

    def write(self, data):
        # Ensure writes are atomic across both targets
        with self._lock:
            self._original.write(data)
            try:
                self._file.write(data)
            except Exception:
                # Don't break the app if the file write fails
                pass

    def flush(self):
        with self._lock:
            try:
                self._original.flush()
            except Exception:
                pass
            try:
                self._file.flush()
            except Exception:
                pass

    # Support Python interfaces that check for isatty
    def isatty(self):
        try:
            return self._original.isatty()
        except Exception:
            return False


def setup_stdout_stderr_tee(log_file_path: str = "logs/output.log"):
    """Redirect sys.stdout and sys.stderr to also write to a log file.

    Creates the parent directory if missing. Opens the file in append mode so
    logs across runs accumulate. Returns a cleanup function to close the file.
    """
    os.makedirs(os.path.dirname(log_file_path), exist_ok=True)

    # Open once and keep handle for the lifetime of the process
    file_handle = open(log_file_path, "a", buffering=1, encoding="utf-8")

    # Wrap stdout/stderr
    sys.stdout = _TeeStream(sys.stdout, file_handle)
    sys.stderr = _TeeStream(sys.stderr, file_handle)

    def _cleanup():
        try:
            file_handle.flush()
        except Exception:
            pass
        try:
            file_handle.close()
        except Exception:
            pass

    return _cleanup


def setup_run_log(directory: str = "logs", prefix: str = "output", use_uuid: bool = False):
    """Create a unique log file for this run and tee stdout/stderr to it.

    - directory: folder to store logs (created if missing)
    - prefix: filename prefix
    - use_uuid: when True, use a UUID suffix; otherwise use timestamp

    Returns (log_file_path, cleanup_fn)
    """
    import datetime
    import uuid

    os.makedirs(directory, exist_ok=True)
    if use_uuid:
        suffix = uuid.uuid4().hex
    else:
        # e.g., 2025-12-14_13-45-02
        suffix = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    log_file_path = os.path.join(directory, f"{prefix}_{suffix}.log")
    cleanup = setup_stdout_stderr_tee(log_file_path)
    return log_file_path, cleanup
