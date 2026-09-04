import time
import subprocess
import threading
from datetime import datetime, timedelta

from storage import load_tasks, save_tasks, task_lock

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
                # Skip malformed records instead of crashing the whole loop.
                if not task.get('date'):
                    continue
                if task['date'] == today_str and not task.get('completed', False) and task.get('reminders_sent', 0) < 3:

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
                            args=(task_id, "Daily-Tasks Reminder", task.get('text', '')),
                            daemon=True
                        ).start()

                        task['reminders_sent'] = task.get('reminders_sent', 0) + 1
                        task['last_reminded'] = now.isoformat()
                        task['snoozed_until'] = None # Reset snooze
                        updated = True

            if updated:
                save_tasks(tasks)

        time.sleep(60)

if __name__ == "__main__":
    run_daemon()
