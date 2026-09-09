import os
import json
import stat
import tempfile
import unittest

# Redirect storage I/O to a throwaway dir and put a stub `rclone` on PATH BEFORE
# importing the modules under test.
os.environ["DAILY_TASKS_DIR"] = tempfile.mkdtemp(prefix="daily-tasks-synctest-")

_BINDIR = tempfile.mkdtemp(prefix="daily-tasks-stubbin-")
# The stub backs a single file (the "cloud"), path taken from RCLONE_STUB_FILE.
# It fails cat with "object not found" when that file is absent (first run) and
# fails everything when RCLONE_STUB_OFFLINE is set (simulated network error).
_STUB = os.path.join(_BINDIR, "rclone")
with open(_STUB, "w") as f:
    f.write(
        "#!/bin/sh\n"
        'if [ -n "$RCLONE_STUB_OFFLINE" ]; then echo "connection refused" >&2; exit 1; fi\n'
        'case "$1" in\n'
        '  cat)\n'
        '    if [ -f "$RCLONE_STUB_FILE" ]; then cat "$RCLONE_STUB_FILE"; exit 0;\n'
        '    else echo "object not found" >&2; exit 3; fi ;;\n'
        '  rcat) cat > "$RCLONE_STUB_FILE"; exit 0 ;;\n'
        '  *) echo "unsupported $1" >&2; exit 2 ;;\n'
        'esac\n'
    )
os.chmod(_STUB, os.stat(_STUB).st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
os.environ["PATH"] = _BINDIR + os.pathsep + os.environ["PATH"]

import storage
import sync


def _use_device(dirpath):
    # Point storage + sync at a given device's data dir.
    os.makedirs(dirpath, exist_ok=True)
    storage.DATA_DIR = dirpath
    storage.DATA_FILE = os.path.join(dirpath, "tasks.json")
    storage.LOCK_FILE = os.path.join(dirpath, ".tasks.lock")
    sync.SYNC_FILE = os.path.join(dirpath, "sync.json")
    sync.save_settings({"enabled": True, "remote": "cloud", "remote_path": "tasks.json"})


class SyncTest(unittest.TestCase):
    def setUp(self):
        self.cloud = os.path.join(tempfile.mkdtemp(), "remote.json")
        os.environ["RCLONE_STUB_FILE"] = self.cloud
        os.environ.pop("RCLONE_STUB_OFFLINE", None)
        self.devA = tempfile.mkdtemp(prefix="devA-")
        self.devB = tempfile.mkdtemp(prefix="devB-")

    def _task(self, text, ts, **extra):
        t = {"text": text, "date": "2999-01-01", "updated_at": ts}
        t.update(extra)
        return t

    def test_first_run_creates_remote(self):
        _use_device(self.devA)
        storage.save_tasks({"a": self._task("A", "2024-01-01T00:00:00")})
        self.assertEqual(sync.sync_now(), "synced")
        self.assertTrue(os.path.exists(self.cloud))

    def test_two_device_convergence(self):
        _use_device(self.devA)
        storage.save_tasks({"a": self._task("from A", "2024-01-01T00:00:00")})
        self.assertEqual(sync.sync_now(), "synced")

        _use_device(self.devB)  # fresh device, same cloud
        self.assertEqual(sync.sync_now(), "synced")
        self.assertIn("a", storage.load_tasks())  # pulled A's task
        storage.save_tasks({**storage.load_tasks(),
                            "b": self._task("from B", "2024-02-01T00:00:00")})
        self.assertEqual(sync.sync_now(), "synced")

        _use_device(self.devA)  # back to A
        self.assertEqual(sync.sync_now(), "synced")
        self.assertEqual(set(storage.load_tasks()), {"a", "b"})  # A now has both

    def test_tombstone_propagates(self):
        _use_device(self.devA)
        storage.save_tasks({"x": self._task("alive", "2024-01-01T00:00:00")})
        sync.sync_now()
        _use_device(self.devB)
        sync.sync_now()
        self.assertIn("x", storage.load_tasks())
        # B deletes x (fresh tombstone, so it is not purged) and syncs.
        storage.save_tasks({"x": self._task("alive", storage.now_iso(), deleted=True)})
        sync.sync_now()
        # A syncs and should see x tombstoned.
        _use_device(self.devA)
        sync.sync_now()
        self.assertTrue(storage.load_tasks()["x"].get("deleted"))

    def test_offline_does_not_touch_local_or_remote(self):
        _use_device(self.devA)
        storage.save_tasks({"a": self._task("A", "2024-01-01T00:00:00")})
        sync.sync_now()  # seed the cloud
        with open(self.cloud) as f:
            cloud_before = f.read()

        os.environ["RCLONE_STUB_OFFLINE"] = "1"
        storage.save_tasks({"a": self._task("A", "2024-01-01T00:00:00"),
                            "local_only": self._task("L", "2024-03-01T00:00:00")})
        self.assertEqual(sync.sync_now(), "error")
        # Local kept its change; remote was NOT overwritten while we couldn't read it.
        self.assertIn("local_only", storage.load_tasks())
        with open(self.cloud) as f:
            self.assertEqual(f.read(), cloud_before)

    def test_parse_concatenated_duplicates(self):
        # rclone cat of two same-named Drive files -> two JSON objects back-to-back.
        a = json.dumps({"x": self._task("A", "2024-01-01T00:00:00")})
        b = json.dumps({"y": self._task("B", "2024-02-01T00:00:00")})
        merged, count = sync._parse_remote(a + b)
        self.assertEqual(count, 2)
        self.assertEqual(set(merged), {"x", "y"})

    def test_disabled_when_not_configured(self):
        _use_device(self.devA)
        sync.save_settings({"enabled": False, "remote": "", "remote_path": "tasks.json"})
        self.assertEqual(sync.sync_now(), "disabled")


if __name__ == "__main__":
    unittest.main()
