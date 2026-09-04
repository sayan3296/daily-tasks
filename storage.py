import json
import os
import sys
import fcntl
from contextlib import contextmanager
from datetime import datetime

# --- PATH SETUP (Compatible with RPM system-wide install) ---
# DAILY_TASKS_DIR lets tests (and future backends) redirect the data location.
DATA_DIR = os.environ.get("DAILY_TASKS_DIR", os.path.expanduser("~/Daily-Tasks"))
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)
DATA_FILE = os.path.join(DATA_DIR, "tasks.json")
CONFIG_FILE = os.path.join(DATA_DIR, "config.json")
LOCK_FILE = os.path.join(DATA_DIR, ".tasks.lock")


@contextmanager
def task_lock():
    # Exclusive flock on a dedicated lock file. A fresh open() per call gives
    # mutual exclusion across processes (app vs daemon) and threads, so the
    # app and daemon never read/write tasks.json at the same time.
    fd = open(LOCK_FILE, 'w')
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        fd.close()


def _write_json(path, data):
    # Atomic write: dump to a temp file in the same dir, fsync, keep the previous
    # good copy as <path>.bak, then os.replace (atomic on POSIX). A crash never
    # leaves a truncated primary, and .bak allows recovery of the last version.
    # Lock-free on purpose so callers can hold task_lock across read+write.
    tmp = f"{path}.tmp"
    with open(tmp, 'w') as f:
        json.dump(data, f)
        f.flush()
        os.fsync(f.fileno())
    if os.path.exists(path):
        try:
            os.replace(path, f"{path}.bak")
        except OSError:
            pass
    os.replace(tmp, path)


def _read_json(path, default):
    # Try the primary file, then fall back to the .bak copy. Lock-free on purpose.
    for candidate in (path, f"{path}.bak"):
        if os.path.exists(candidate):
            try:
                with open(candidate, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError) as e:
                print(f"Warning: could not read {candidate}: {e}", file=sys.stderr)
    return default


def load_tasks():
    with task_lock():
        return _read_json(DATA_FILE, {})


def save_tasks(tasks):
    with task_lock():
        _write_json(DATA_FILE, tasks)


def load_config():
    with task_lock():
        cfg = _read_json(CONFIG_FILE, None)
    return cfg if cfg is not None else {"dark_mode": False}


def save_config(config):
    with task_lock():
        _write_json(CONFIG_FILE, config)


def weekday(date_str):
    # Return the weekday name for a YYYY-MM-DD string, or "?" if unparseable.
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").strftime("%A")
    except (ValueError, TypeError):
        return "?"
