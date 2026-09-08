Name:           daily-tasks
Version:        1.4
Release:        1
Summary:        A modern desktop task manager and reminder daemon

License:        MIT
Source0:        %{name}-%{version}.tar.gz
Source1:        dailytasks.desktop
Source2:        dailytasks-daemon.desktop

BuildArch:      noarch
Requires:       python3
Requires:       python3-tkinter
Requires:       libnotify
Requires:       rclone

%description
Daily-Tasks is a lightweight, Python-based task manager. It features a modern 
UI for managing tasks and a background daemon that utilizes system notifications 
to remind you of due tasks automatically.

%prep
%setup -q

%install
# Create target directories
mkdir -p %{buildroot}/opt/daily-tasks
mkdir -p %{buildroot}/usr/share/applications
mkdir -p %{buildroot}/etc/xdg/autostart

# Copy Python scripts and Icon
cp app.py %{buildroot}/opt/daily-tasks/
cp daemon.py %{buildroot}/opt/daily-tasks/
cp storage.py %{buildroot}/opt/daily-tasks/
cp sync.py %{buildroot}/opt/daily-tasks/
cp icon.png %{buildroot}/opt/daily-tasks/

# Copy Desktop files
cp %{SOURCE1} %{buildroot}/usr/share/applications/
cp %{SOURCE2} %{buildroot}/etc/xdg/autostart/

%files
/opt/daily-tasks/app.py
/opt/daily-tasks/daemon.py
/opt/daily-tasks/storage.py
/opt/daily-tasks/sync.py
/opt/daily-tasks/icon.png
/usr/share/applications/dailytasks.desktop
/etc/xdg/autostart/dailytasks-daemon.desktop

%changelog
* Fri Sep 04 2026 Sayan Das <connectwithsayan03@gmail.com> - 1.3-1
- Atomic writes and file locking to prevent task data loss
- Hardened daemon and UI against malformed task records

* Fri Mar 13 2026 Sayan Das <connectwithsayan03@gmail.com> - 1.0-1
- Initial RPM release