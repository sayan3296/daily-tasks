import os
import json
import tempfile
import unittest

# Redirect all storage I/O to a throwaway dir before importing the module.
os.environ["DAILY_TASKS_DIR"] = tempfile.mkdtemp(prefix="daily-tasks-test-")

import storage


def _task(updated_at, **extra):
    t = {"text": "t", "date": "2999-01-01", "updated_at": updated_at}
    t.update(extra)
    return t


class MergeTasksTest(unittest.TestCase):
    def test_newer_remote_wins(self):
        local = {"a": _task("2024-01-01T00:00:00", text="old")}
        remote = {"a": _task("2024-06-01T00:00:00", text="new")}
        self.assertEqual(storage.merge_tasks(local, remote)["a"]["text"], "new")

    def test_newer_local_wins(self):
        local = {"a": _task("2024-06-01T00:00:00", text="new")}
        remote = {"a": _task("2024-01-01T00:00:00", text="old")}
        self.assertEqual(storage.merge_tasks(local, remote)["a"]["text"], "new")

    def test_disjoint_union(self):
        local = {"a": _task("2024-01-01T00:00:00")}
        remote = {"b": _task("2024-01-01T00:00:00")}
        self.assertEqual(set(storage.merge_tasks(local, remote)), {"a", "b"})

    def test_newer_tombstone_wins(self):
        local = {"a": _task("2024-01-01T00:00:00", text="alive")}
        remote = {"a": _task("2024-06-01T00:00:00", deleted=True)}
        self.assertTrue(storage.merge_tasks(local, remote)["a"].get("deleted"))

    def test_missing_timestamp_sorts_oldest(self):
        local = {"a": {"text": "no-ts"}}  # no updated_at
        remote = {"a": _task("2024-01-01T00:00:00", text="stamped")}
        self.assertEqual(storage.merge_tasks(local, remote)["a"]["text"], "stamped")


class DiskStorageTest(unittest.TestCase):
    def setUp(self):
        for p in (storage.DATA_FILE, storage.DATA_FILE + ".bak", storage.CONFIG_FILE):
            if os.path.exists(p):
                os.remove(p)

    def test_atomic_write_and_bak_fallback(self):
        storage.save_tasks({"x": {"text": "v1", "updated_at": "2024-01-01T00:00:00"}})
        storage.save_tasks({"x": {"text": "v2", "updated_at": "2024-02-01T00:00:00"}})
        self.assertEqual(storage.load_tasks()["x"]["text"], "v2")
        self.assertTrue(os.path.exists(storage.DATA_FILE + ".bak"))
        # Corrupt the primary; load must fall back to the .bak (previous good).
        with open(storage.DATA_FILE, "w") as f:
            f.write("{ this is not valid json")
        self.assertEqual(storage.load_tasks()["x"]["text"], "v1")

    def test_purge_old_tombstones_on_write(self):
        storage.save_tasks({
            "recent": {"deleted": True, "updated_at": storage.now_iso()},
            "old": {"deleted": True, "updated_at": "2000-01-01T00:00:00"},
            "live": {"text": "keep", "updated_at": storage.now_iso()},
        })
        keys = set(storage.load_tasks())
        self.assertEqual(keys, {"recent", "live"})

    def test_mutate_preserves_concurrent_field(self):
        # Simulate the daemon writing reminder metadata...
        storage.mutate(lambda t: t.__setitem__(
            "b", {"text": "B", "date": "2999-01-01", "reminders_sent": 5,
                  "updated_at": "2024-01-01T00:00:00"}))

        # ...then the app editing an unrelated field via a stale in-memory copy.
        def _edit(tasks):
            tasks["b"]["date"] = "2999-02-02"
            tasks["b"]["updated_at"] = storage.now_iso()
        storage.mutate(_edit)

        t = storage.load_tasks()["b"]
        self.assertEqual(t["reminders_sent"], 5)   # not clobbered
        self.assertEqual(t["date"], "2999-02-02")  # edit applied

    def test_mutate_skips_write_on_false(self):
        storage.save_tasks({"x": {"text": "v1", "updated_at": "2024-01-01T00:00:00"}})
        mtime_before = os.path.getmtime(storage.DATA_FILE)
        storage.mutate(lambda t: False)  # no-op tick
        self.assertEqual(os.path.getmtime(storage.DATA_FILE), mtime_before)


if __name__ == "__main__":
    unittest.main()
