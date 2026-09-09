import os
import sys
import time
import fcntl
import subprocess
import threading
from datetime import datetime, timedelta

import storage
from storage import mutate
import sync

# Held for the process lifetime so the flock is not released (module global).
_singleton_fd = None


def acquire_singleton():
    # Ensure only one daemon runs (systemd already guarantees this for the managed
    # service, but this also covers manual launches and the autostart transition).
    global _singleton_fd
    _singleton_fd = open(os.path.join(storage.DATA_DIR, ".daemon.lock"), "w")
    try:
        fcntl.flock(_singleton_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        print("daemon: another instance is already running; exiting", file=sys.stderr)
        sys.exit(0)

def send_notification_and_handle_snooze(task_id, title, message):
    # -w waits for the notification to be closed/clicked
    # -A adds a custom action button to the Linux notification
    cmd = [
        "notify-send", 
        "-u", "critical", 
        "-w", 
        "-A", "snooze=Snooze (30m)", 
        title, 
        message
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    # If the user clicked the 'Snooze' button
    if result.stdout.strip() == "snooze":
        def _snooze(tasks):
            if task_id in tasks:
                # Add a 30-minute snooze timestamp
                tasks[task_id]['snoozed_until'] = (datetime.now() + timedelta(minutes=30)).isoformat()
            else:
                return False  # task gone; nothing to persist
        mutate(_snooze)

def _tick(tasks):
    # Fire due reminders. Returns False (skip write) when nothing changed so the
    # daemon doesn't rewrite tasks.json every minute while idle.
    now = datetime.now()
    today_str = now.strftime("%Y-%m-%d")
    changed = False

    for task_id, task in tasks.items():
        # Skip tombstoned or malformed records instead of crashing the loop.
        if task.get('deleted'):
            continue
        if not task.get('date'):
            continue
        if task['date'] == today_str and not task.get('completed', False) and task.get('reminders_sent', 0) < 3:

            # Check if the task is currently snoozed
            snoozed_until = task.get('snoozed_until')
            if snoozed_until and now < datetime.fromisoformat(snoozed_until):
                continue # Skip this task until snooze is over

            last_reminded = task.get('last_reminded')
            if not last_reminded:
                should_remind = True
            else:
                should_remind = now >= datetime.fromisoformat(last_reminded) + timedelta(hours=2)

            if should_remind:
                # Launch notification in a separate thread so it doesn't block other tasks
                threading.Thread(
                    target=send_notification_and_handle_snooze,
                    args=(task_id, "Daily-Tasks Reminder", task.get('text', '')),
                    daemon=True
                ).start()

                task['reminders_sent'] = task.get('reminders_sent', 0) + 1
                task['last_reminded'] = now.isoformat()
                task['snoozed_until'] = None # Reset snooze
                changed = True

    if not changed:
        return False

def run_daemon():
    while True:
        # Converge with Google Drive first (no-op if sync is off/unconfigured),
        # then fire due reminders on the up-to-date task set.
        sync.sync_now()
        # Locked read-modify-write each tick so we never clobber concurrent app edits.
        mutate(_tick)
        time.sleep(60)

if __name__ == "__main__":
    acquire_singleton()
    run_daemon()
