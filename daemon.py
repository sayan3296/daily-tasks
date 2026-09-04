import json
import os
import sys
import time
import subprocess
import threading
import fcntl
from contextlib import contextmanager
from datetime import datetime, timedelta

APP_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.expanduser("~/Daily-Tasks")
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)
DATA_FILE = os.path.join(DATA_DIR, "tasks.json")
LOCK_FILE = os.path.join(DATA_DIR, ".tasks.lock")

@contextmanager
def task_lock():
    # Exclusive flock on a dedicated lock file. A fresh open() per call gives
    # mutual exclusion across processes (app vs daemon) and threads, so the
    # app and daemon never write tasks.json at the same time.
    fd = open(LOCK_FILE, 'w')
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        fd.close()

def _atomic_write_json(path, data):
    # Write to a temp file in the same directory, fsync, then os.replace.
    # os.replace is atomic on POSIX, so a crash never leaves a truncated file.
    tmp = f"{path}.tmp"
    with open(tmp, 'w') as f:
        json.dump(data, f)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)

def load_tasks():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            print(f"Warning: could not read {DATA_FILE}: {e}", file=sys.stderr)
    return {}

def save_tasks(tasks):
    _atomic_write_json(DATA_FILE, tasks)

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
        with task_lock():
            tasks = load_tasks()
            if task_id in tasks:
                # Add a 30-minute snooze timestamp
                tasks[task_id]['snoozed_until'] = (datetime.now() + timedelta(minutes=30)).isoformat()
                save_tasks(tasks)

def run_daemon():
    while True:
        # Hold the lock across load -> modify -> save so the daemon can never
        # clobber a task the app added between our read and our write.
        with task_lock():
            tasks = load_tasks()
            now = datetime.now()
            today_str = now.strftime("%Y-%m-%d")
            updated = False

            for task_id, task in tasks.items():
                if task['date'] == today_str and not task['completed'] and task['reminders_sent'] < 3:

                    # Check if the task is currently snoozed
                    snoozed_until = task.get('snoozed_until')
                    if snoozed_until:
                        if now < datetime.fromisoformat(snoozed_until):
                            continue # Skip this task until snooze is over

                    last_reminded = task.get('last_reminded')
                    should_remind = False

                    if not last_reminded:
                        should_remind = True
                    else:
                        last_time = datetime.fromisoformat(last_reminded)
                        if now >= last_time + timedelta(hours=2):
                            should_remind = True

                    if should_remind:
                        # Launch notification in a separate thread so it doesn't block other tasks
                        threading.Thread(
                            target=send_notification_and_handle_snooze,
                            args=(task_id, "Daily-Tasks Reminder", task['text']),
                            daemon=True
                        ).start()

                        task['reminders_sent'] += 1
                        task['last_reminded'] = now.isoformat()
                        task['snoozed_until'] = None # Reset snooze
                        updated = True

            if updated:
                save_tasks(tasks)

        time.sleep(60)

if __name__ == "__main__":
    run_daemon()
