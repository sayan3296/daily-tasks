import json
import os
import sys
import fcntl
from contextlib import contextmanager
from datetime import datetime, timedelta

# --- PATH SETUP (Compatible with RPM system-wide install) ---
# DAILY_TASKS_DIR lets tests (and future backends) redirect the data location.
DATA_DIR = os.environ.get("DAILY_TASKS_DIR", os.path.expanduser("~/Daily-Tasks"))
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)
DATA_FILE = os.path.join(DATA_DIR, "tasks.json")
CONFIG_FILE = os.path.join(DATA_DIR, "config.json")
LOCK_FILE = os.path.join(DATA_DIR, ".tasks.lock")

# Deleted tasks are kept as tombstones this long so the deletion can propagate
# to other devices before the record is dropped for good.
TOMBSTONE_MAX_AGE_DAYS = 30


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


def _purge_tombstones(tasks):
    # Drop tombstoned tasks whose deletion is older than the retention window.
    cutoff = (datetime.now() - timedelta(days=TOMBSTONE_MAX_AGE_DAYS)).isoformat()
    return {tid: t for tid, t in tasks.items()
            if not (t.get("deleted") and _ts(t) < cutoff)}


def save_tasks(tasks):
    with task_lock():
        _write_json(DATA_FILE, _purge_tombstones(tasks))


def mutate(update_fn):
    # Locked read-modify-write against the on-disk tasks. Loads the current
    # truth, applies update_fn(tasks), purges old tombstones, and atomically
    # saves. Because load and save happen under a single lock, a writer never
    # clobbers fields another writer (e.g. the daemon's reminder metadata)
    # changed concurrently. Returns the current tasks dict.
    #
    # update_fn contract:
    #   return a dict  -> that dict is saved (replace)
    #   return None    -> in-place mutations are saved
    #   return False   -> nothing changed; skip the write entirely
    with task_lock():
        tasks = _read_json(DATA_FILE, {})
        result = update_fn(tasks)
        if result is False:
            return tasks
        if result is not None:
            tasks = result
        tasks = _purge_tombstones(tasks)
        _write_json(DATA_FILE, tasks)
        return tasks


def load_config():
    with task_lock():
        cfg = _read_json(CONFIG_FILE, None)
    return cfg if cfg is not None else {"dark_mode": False}


def save_config(config):
    with task_lock():
        _write_json(CONFIG_FILE, config)


def now_iso():
    # Timestamp used to stamp every task mutation (see _ts / merge_tasks).
    return datetime.now().isoformat()


def _ts(task):
    # Comparable last-modified value; missing/blank sorts as oldest. ISO strings
    # from now_iso() compare lexicographically in chronological order.
    return task.get("updated_at") or ""


def merge_tasks(local, remote):
    # Union by UUID; per id keep the record with the newer updated_at (local wins
    # exact ties). Tombstones compete by timestamp like any other record, so a
    # newer delete propagates and a newer edit resurrects nothing incorrectly.
    # Pure function (no I/O) -- callers persist the result via mutate/save_tasks.
    # This is the primitive the Phase 2 Google Drive sync will call.
    merged = dict(local)
    for tid, r in remote.items():
        l = merged.get(tid)
        if l is None or _ts(r) > _ts(l):
            merged[tid] = r
    return merged


def merge_into_local(remote):
    # Merge a remote task dict into the on-disk local tasks under the file lock,
    # purge old tombstones, persist, and return the merged result. Used by the
    # sync layer; keeps all locking/merge logic here in storage.
    with task_lock():
        local = _read_json(DATA_FILE, {})
        merged = _purge_tombstones(merge_tasks(local, remote))
        _write_json(DATA_FILE, merged)
        return merged


def weekday(date_str):
    # Return the weekday name for a YYYY-MM-DD string, or "?" if unparseable.
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").strftime("%A")
    except (ValueError, TypeError):
        return "?"
