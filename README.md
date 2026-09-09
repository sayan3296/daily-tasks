# 📋 Daily-Tasks

A modern, lightweight, native desktop task manager built for Fedora Linux. 

Daily-Tasks goes beyond a simple to-do list by offering a persistent background daemon that integrates directly with your system's native notifications, ensuring you never miss a deadline. It features a clean, responsive UI, smart color-coding, and an auto-sorting priority list.

*(Screenshot Placeholder: Add an updated image of your app here showing the search bar and dark mode!)*

## ✨ Features

* **Native Desktop Experience:** Built with a modern `clam` theme that blends perfectly with Fedora/GNOME.
* **🌙 Dark Mode Support:** Includes a toggle for Dark/Light mode, saving your preference automatically for the next launch.
* **🔍 Live Search Filtering:** Instantly filter your task list by description or date as you type.
* **📋 Quick Copy:** Right-click any task in your list to instantly copy it to your system clipboard.
* **Smart Sorting & Color-Coding:** Overdue tasks are automatically swept to the top in **Bold Red**, tasks due today are highlighted in **Bold Blue**, and upcoming tasks remain neatly ordered below. Colors dynamically adjust to be easy on the eyes in Dark Mode.
* **Persistent Daemon Integration:** A lightweight background process runs as a **systemd user service**, starting at login to monitor deadlines and send system-level desktop notifications (auto-restarts on failure and on package upgrades).
* **Frictionless Editing:** Double-click any task to quickly open a custom pop-up window and adjust its due date.
* **Foolproof Date Entry:** Native, dynamic dropdown menus prevent formatting errors and automatically calculate the day of the week (e.g., "Monday").
* **Safe Storage:** All data is stored locally in a simple `~/Daily-Tasks/` directory, using crash-safe atomic writes with automatic `.bak` recovery and concurrency-safe access shared between the app and the reminder daemon.
* **☁ Google Drive Sync (optional):** Keep your tasks in sync across every machine logged into the same Google account. Syncs on launch, after each edit, on a timer, and on demand — with per-task merging so concurrent edits on different devices never lose data.

---

## 🚀 For Users: Installation & Usage

You do **not** need to compile any code to use Daily-Tasks! 

### 1. Download
Go to the [Releases page](../../releases) on the right side of this repository and download the latest `.rpm` file (e.g., `daily-tasks-1.x-1.noarch.rpm`).

### 2. Install
Open your terminal, navigate to your downloads folder, and install the package using `dnf`. This will automatically install any required dependencies (like Python 3 and Tkinter):

```bash
sudo dnf install ./daily-tasks-1.*.noarch.rpm
```

### 3. Usage
* **Launch:** Open your system's application menu and search for "Daily-Tasks".
* **Add a Task:** Type your task, select the date, and press `Enter` (or click "Add Task").
* **Edit a Task:** Double-click any task in the list to change its due date.
* **Copy a Task:** Right-click a task to copy its text to your clipboard.
* **Search:** Use the search bar to instantly filter tasks by text or date.
* **Theme:** Click the Dark Mode / Light Mode button at the bottom right to switch themes.
* **Background Reminders:** The reminder daemon is installed as a systemd **user** service and starts automatically at every login — you don't need to keep the main window open to receive notifications. After the very first install, either log out and back in, or start it immediately with:

```bash
systemctl --user daemon-reload && systemctl --user enable --now daily-tasks-daemon
```

Check it any time with `systemctl --user status daily-tasks-daemon` or view logs with `journalctl --user -u daily-tasks-daemon`. Package upgrades restart it automatically.

> **One-time note when upgrading from an older (pre-systemd) version:** installing this version removes the old `/etc/xdg/autostart/dailytasks-daemon.desktop` and enables the systemd service, but a daemon already started by this login's autostart keeps running until you log out and back in. A built-in single-instance lock guarantees the two never run at once (the second exits cleanly). To complete the switch without re-logging in:
>
> ```bash
> pkill -f /opt/daily-tasks/daemon.py
> systemctl --user enable --now daily-tasks-daemon
> ```
>
> This is only needed once. Every upgrade after that restarts the daemon automatically.

---

## ☁ Cloud Sync (Google Drive)

Sync is **optional and off by default**. It uses [`rclone`](https://rclone.org/) as the transport, so Google authentication is handled once by rclone — the app never sees your password and stores no OAuth secrets.

### One-time setup (per machine)
1. Install rclone (bundled as a dependency of the RPM, or `sudo dnf install rclone`).
2. Create a Google Drive remote:

```bash
rclone config
```

Choose `n` (new remote), name it (e.g. `gdrive`), pick **Google Drive** as the storage type, and complete the browser sign-in. rclone saves the token in `~/.config/rclone/rclone.conf` (mode `0600`) — **outside** `~/Daily-Tasks`, so it is never itself synced.

3. In Daily-Tasks, click **⚙ Configure Sync** and enter the remote name you chose (e.g. `gdrive`).

### How it works
- Tasks are stored on Drive at `Daily-Tasks/tasks.json` in your account.
- The app syncs on launch, ~2 seconds after each edit (debounced), and whenever you click **☁ Sync Now**. The background daemon also syncs on its regular tick, so machines stay converged even with the window closed.
- Sync is **merge-based, not overwrite-based**: each task has a last-modified timestamp, deletions are recorded as tombstones, and every sync merges the two sides per task (newest wins). Concurrent edits on different devices converge without losing data, and a device that was offline catches up on its next sync.
- Only `tasks.json` is synced; your theme preference stays local to each machine.

### Disabling
Click **⚙ Configure Sync** and clear the remote name, or set `"enabled": false` in `~/Daily-Tasks/sync.json`.

---

## 🛠️ For Developers: Building from Source

This repository includes a fully automated build pipeline. Whether you are building locally or relying on GitHub Actions, packaging a new version takes seconds.

### Prerequisites
To build the `.rpm` locally, ensure you have the Fedora packaging tools installed:

```bash
sudo dnf install rpm-build rpmdevtools
```

### Local Build Workflow
The repository includes a `build.sh` script that reads the current version from the `.spec` file and compiles the RPM. By default it builds the version already in the `.spec` (a plain rebuild does **not** change the version).

1. Make your code changes in `app.py`, `daemon.py`, or `storage.py`.
2. Build the current version:

```bash
./build.sh
```

3. To release a new version, bump first. This increments the minor version (e.g., `1.3` -> `1.4`), resets the release number, and updates the `.spec`:

```bash
./build.sh --bump
```

4. Your new installer will be generated at `~/rpmbuild/RPMS/noarch/`.

### Automated Builds (GitHub Actions)
This repository is configured with a CI/CD pipeline using GitHub Actions. It spins up a pristine Fedora container to compile the RPM and automatically publishes it to the GitHub Releases page.

To trigger a build and release, you **must** include the exact keyword `[build]` in your commit message:

```bash
git add .
git commit -m "Added a new feature [build]"
git push
```

If the commit message lacks `[build]`, GitHub Actions will safely ignore the push to save resources.

The pipeline reads the version straight from the committed `daily-tasks.spec` — it does **not** bump it. To publish a *new* version, bump first (`./build.sh --bump`, or edit `Version:` in the `.spec` by hand), then commit and push with `[build]`. Pushing `[build]` without bumping re-releases the same version.

---

## 📂 File Structure

* `app.py`: The main GUI application.
* `daemon.py`: The background notification tracker.
* `storage.py`: Shared data layer (atomic writes, file locking, `.bak` recovery, tombstones, merge) used by both `app.py` and `daemon.py`.
* `sync.py`: Optional Google Drive sync via rclone (pull → merge → push).
* `test_storage.py` / `test_sync.py`: Unit tests (development only; not shipped in the RPM).
* `icon.png`: The application icon.
* `tasks.json` & `config.json`: Local storage for user data and theme preferences (generated at runtime).
* `sync.json`: Non-secret cloud-sync settings — rclone remote name and remote path (generated at runtime; no credentials).
* `dailytasks.desktop`: System-wide application menu shortcut.
* `daily-tasks-daemon.service`: systemd user service that runs the reminder daemon.
* `daily-tasks.spec`: The RPM build recipe.
* `build.sh`: Local auto-incrementing build script.
* `.github/workflows/rpm-build.yml`: The GitHub Actions CI/CD pipeline.

## 📄 License
This project is licensed under the MIT License.
