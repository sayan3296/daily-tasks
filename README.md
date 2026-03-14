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
* **Persistent Daemon Integration:** A lightweight background process auto-starts with your computer to monitor deadlines and send system-level desktop notifications.
* **Frictionless Editing:** Double-click any task to quickly open a custom pop-up window and adjust its due date.
* **Foolproof Date Entry:** Native, dynamic dropdown menus prevent formatting errors and automatically calculate the day of the week (e.g., "Monday").
* **Safe Storage:** All data is safely stored locally in a simple `~/Daily-Tasks/` directory.

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
* **Background Reminders:** The app installs a daemon that will automatically start every time you log in. You don't need to keep the main window open to receive notifications!

---

## 🛠️ For Developers: Building from Source

This repository includes a fully automated build pipeline. Whether you are building locally or relying on GitHub Actions, packaging a new version takes seconds.

### Prerequisites
To build the `.rpm` locally, ensure you have the Fedora packaging tools installed:

```bash
sudo dnf install rpm-build rpmdevtools
```

### Local Build Workflow
The repository includes a smart `build.sh` script that automatically reads the current version from the `.spec` file, increments it (e.g., `1.0` -> `1.1`), updates the `.spec` file, and compiles the new RPM.

1. Make your code changes in `app.py` or `daemon.py`.
2. Run the automated build script:

```bash
./build.sh
```

3. Your new installer will be generated at `~/rpmbuild/RPMS/noarch/`.

### Cloud Build Workflow (GitHub Actions)
This repository is configured with a CI/CD pipeline using GitHub Actions. It spins up a pristine Fedora container to compile the RPM and automatically publishes it to the GitHub Releases page.

To trigger a cloud build and release, you **must** include the exact keyword `[build]` in your commit message:

```bash
git add .
git commit -m "Added a new feature [build]"
git push
```

If the commit message lacks `[build]`, GitHub Actions will safely ignore the push to save resources.

---

## 📂 File Structure

* `app.py`: The main GUI application.
* `daemon.py`: The background notification tracker.
* `icon.png`: The application icon.
* `tasks.json` & `config.json`: Local storage for user data and theme preferences (generated at runtime).
* `dailytasks.desktop`: System-wide application menu shortcut.
* `dailytasks-daemon.desktop`: System-wide autostart configuration.
* `daily-tasks.spec`: The RPM build recipe.
* `build.sh`: Local auto-incrementing build script.
* `.github/workflows/rpm-build.yml`: The GitHub Actions CI/CD pipeline.

## 📄 License
This project is licensed under the MIT License.
