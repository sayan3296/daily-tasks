Name:           daily-tasks
Version:        1.6
Release:        1
Summary:        A modern desktop task manager and reminder daemon

License:        MIT
Source0:        %{name}-%{version}.tar.gz
Source1:        dailytasks.desktop
Source2:        daily-tasks-daemon.service

BuildArch:      noarch
Requires:       python3
Requires:       python3-tkinter
Requires:       libnotify
Requires:       rclone

BuildRequires:  systemd-rpm-macros
%{?systemd_requires}

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
mkdir -p %{buildroot}%{_userunitdir}

# Copy Python scripts and Icon
cp app.py %{buildroot}/opt/daily-tasks/
cp daemon.py %{buildroot}/opt/daily-tasks/
cp storage.py %{buildroot}/opt/daily-tasks/
cp sync.py %{buildroot}/opt/daily-tasks/
cp icon.png %{buildroot}/opt/daily-tasks/

# App menu launcher and the systemd user service for the daemon
cp %{SOURCE1} %{buildroot}/usr/share/applications/
cp %{SOURCE2} %{buildroot}%{_userunitdir}/

%files
/opt/daily-tasks/app.py
/opt/daily-tasks/daemon.py
/opt/daily-tasks/storage.py
/opt/daily-tasks/sync.py
/opt/daily-tasks/icon.png
/usr/share/applications/dailytasks.desktop
%{_userunitdir}/daily-tasks-daemon.service

%post
%systemd_user_post daily-tasks-daemon.service

%preun
%systemd_user_preun daily-tasks-daemon.service
# On full removal (not upgrade), stop any running app/daemon processes.
if [ $1 -eq 0 ]; then
    pkill -f '/opt/daily-tasks/app.py' 2>/dev/null || :
    pkill -f '/opt/daily-tasks/daemon.py' 2>/dev/null || :
fi

%postun
%systemd_user_postun_with_restart daily-tasks-daemon.service

%changelog
* Thu Sep 10 2026 Sayan Das <connectwithsayan03@gmail.com> - 1.6-1
- Run the reminder daemon as a systemd user service (supervised, restarts on upgrade)
- Single-instance guard prevents duplicate daemons

* Thu Sep 10 2026 Sayan Das <connectwithsayan03@gmail.com> - 1.5-1
- Fix: tolerate and de-duplicate remote tasks.json (Google Drive duplicate files)

* Tue Sep 08 2026 Sayan Das <connectwithsayan03@gmail.com> - 1.4-1
- Optional Google Drive sync via rclone (record-level merge, tombstones)

* Fri Sep 04 2026 Sayan Das <connectwithsayan03@gmail.com> - 1.3-1
- Atomic writes and file locking to prevent task data loss
- Hardened daemon and UI against malformed task records

* Fri Mar 13 2026 Sayan Das <connectwithsayan03@gmail.com> - 1.0-1
- Initial RPM release