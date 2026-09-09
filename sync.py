import json
import os
import shutil
import subprocess
import sys

import storage

# Non-secret sync settings. The rclone OAuth token is NOT stored here -- it lives
# in ~/.config/rclone/rclone.conf (managed by `rclone config`), outside the synced
# ~/Daily-Tasks directory.
SYNC_FILE = os.path.join(storage.DATA_DIR, "sync.json")
DEFAULT_SETTINGS = {"enabled": False, "remote": "", "remote_path": "Daily-Tasks/tasks.json"}

# rclone stderr substrings that mean "the remote file simply does not exist yet"
# (first run) rather than a real failure.
_NOT_FOUND_HINTS = ("not found", "no such", "doesn't exist", "didn't find", "directory not found")


def load_settings():
    s = storage._read_json(SYNC_FILE, None)
    merged = dict(DEFAULT_SETTINGS)
    if isinstance(s, dict):
        merged.update(s)
    return merged


def save_settings(settings):
    storage._write_json(SYNC_FILE, settings)


def is_configured():
    s = load_settings()
    return bool(shutil.which("rclone") and s.get("enabled") and s.get("remote"))


def _remote_spec(s):
    return f"{s['remote']}:{s['remote_path']}"


def _parse_remote(text):
    # Google Drive permits duplicate filenames, so `rclone cat` can stream several
    # JSON objects concatenated (one per duplicate file). Parse each and union-merge
    # them so no task is lost. Returns (tasks, object_count).
    dec = json.JSONDecoder()
    idx, n = 0, len(text)
    merged, count = {}, 0
    while idx < n:
        while idx < n and text[idx].isspace():
            idx += 1
        if idx >= n:
            break
        obj, idx = dec.raw_decode(text, idx)
        if isinstance(obj, dict):
            merged = obj if count == 0 else storage.merge_tasks(merged, obj)
            count += 1
    return merged, count


def _download(s):
    # Returns (ok, tasks, dupes). ok=False means the remote could not be read
    # reliably (network/parse error) -- the caller must NOT push, to avoid
    # clobbering the remote with a blind local copy. ok=True with {} means the
    # remote file is genuinely absent/empty (first run). dupes>1 means the remote
    # had duplicate files (their contents are already merged into tasks).
    try:
        result = subprocess.run(
            ["rclone", "cat", _remote_spec(s)],
            capture_output=True, text=True, timeout=60,
        )
    except (OSError, subprocess.SubprocessError) as e:
        print(f"sync: rclone cat failed: {e}", file=sys.stderr)
        return False, {}, 0

    if result.returncode != 0:
        stderr = (result.stderr or "").lower()
        if any(h in stderr for h in _NOT_FOUND_HINTS):
            return True, {}, 0  # first run: remote does not exist yet
        print(f"sync: rclone cat error: {result.stderr.strip()}", file=sys.stderr)
        return False, {}, 0

    out = result.stdout.strip()
    if not out:
        return True, {}, 0
    try:
        data, count = _parse_remote(out)
    except (json.JSONDecodeError, ValueError) as e:
        print(f"sync: remote tasks.json is not valid JSON: {e}", file=sys.stderr)
        return False, {}, 0
    if count > 1:
        print(f"sync: remote had {count} duplicate tasks.json files; merged them", file=sys.stderr)
    return True, data, count


def _dedupe(s):
    # Collapse duplicate Google Drive files (same name in a folder) into one.
    # Best-effort: failures are logged, never fatal.
    remote_dir = f"{s['remote']}:{os.path.dirname(s['remote_path'])}"
    try:
        subprocess.run(["rclone", "dedupe", "--dedupe-mode", "newest", remote_dir],
                       capture_output=True, text=True, timeout=120)
    except (OSError, subprocess.SubprocessError) as e:
        print(f"sync: rclone dedupe failed: {e}", file=sys.stderr)


def _upload(s, tasks):
    try:
        result = subprocess.run(
            ["rclone", "rcat", _remote_spec(s)],
            input=json.dumps(tasks), text=True, capture_output=True, timeout=60,
        )
    except (OSError, subprocess.SubprocessError) as e:
        print(f"sync: rclone rcat failed: {e}", file=sys.stderr)
        return False
    if result.returncode != 0:
        print(f"sync: rclone rcat error: {result.stderr.strip()}", file=sys.stderr)
        return False
    return True


def sync_now():
    # Pull remote -> merge into local (locked) -> push merged. Never raises.
    # Returns a short status: "disabled", "synced", or "error".
    if not is_configured():
        return "disabled"
    s = load_settings()
    ok, remote, dupes = _download(s)
    if not ok:
        return "error"  # do not push over a remote we could not read
    merged = storage.merge_into_local(remote)
    if dupes > 1:
        _dedupe(s)  # remote had duplicate files; collapse them (data already merged)
    return "synced" if _upload(s, merged) else "error"
