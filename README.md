# ⚡ GitPulse — GitHub 4-Quadrant Activity Tracker & Desktop App

> **Keep your entire GitHub contribution graph and Activity Overview alive across all 4 quadrants.**

[![GitHub Release](https://img.shields.io/github/v/release/Nithinkumaru777/gitpulse-desktop?color=39d353&style=flat-square)](https://github.com/Nithinkumaru777/gitpulse-desktop/releases/latest)
[![Platform](https://img.shields.io/badge/platform-Windows-blue?style=flat-square)](https://github.com/Nithinkumaru777/gitpulse-desktop)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=flat-square)](https://opensource.org/licenses/MIT)

GitPulse is a lightweight, background-running Windows desktop application built with Python and PyWebView. Unlike basic commit bots that only populate the "Commits" axis (leaving your GitHub Activity Overview at 100% commits), GitPulse automates all **4 GitHub contribution quadrants**:

1. 📦 **Commits** (Timestamped git commits & squash merges on default branches)
2. 🐛 **Issues** (Automated task creation, tracking, and clean resolution)
3. 🔀 **Pull Requests** (Automated feature branching, change tracking, and PR lifecycles)
4. 🔍 **Code Reviews** (Automated PR peer reviews with verification comments)

---

## ✨ Features

- 📊 **Live GitHub Activity Overview**: Displays your real-time GitHub profile statistics (Commits, Issues, Pull Requests, Code Reviews) and graph percentage distribution directly inside the app.
- 🎯 **Selective Quadrant Toggles**: Check or uncheck any of the 4 quadrants (`Commits`, `Issues`, `Pull Requests`, `Code Reviews`) depending on which axes you want to boost.
- 🚀 **1-Click Quadrant Booster (10x)**: Catch up rapidly from commit-heavy histories with safe, rate-limited batch runs that immediately stretch all 4 axes of your GitHub radar graph outward.
- 🔑 **Zero-Config Token Detection**: Automatically detects your GitHub CLI authentication (`gh auth token`) or accepts standard Personal Access Tokens (PAT).
- 🎨 **Ultra-Modern Glassmorphic UI**: High-contrast dark theme interface with live radar pulse animations and countdown progress bar.
- 📌 **System Tray & Background Runner**: Minimizes directly to your Windows **Hidden Icons** system tray menu and runs continuously in the background.
- 🔗 **1-Click GitHub Link Connector**: Simply paste any GitHub Repository URL to connect or automatically clone and link.
- ⚡ **Windows Boot Auto-Start**: Configure GitPulse to launch automatically whenever your laptop turns on.
- ⏱ **Customizable Pulse Intervals**: Flexible schedules including 1m, 5m, 10m, 15m, 30m, and 60m intervals.

---

## 🚀 Download & Installation

### 📥 Download Installer (`GitPulse_Setup.exe`)
[**Click Here to Download Latest GitPulse_Setup.exe**](https://github.com/Nithinkumaru777/gitpulse-desktop/releases/latest)

1. Launch **`GitPulse_Setup.exe`**.
2. Choose your desired installation folder (e.g. `C:\Program Files\GitPulse` or `D:\GitPulse`).
3. Select shortcut options (Desktop & Start Menu) and click **Install Now**.
4. Launch GitPulse, connect your repository, and click **START PULSING**.

---

## 💻 How the 4-Quadrant Engine Works

GitHub's profile radar graph calculates percentages across 4 activity types:

```
                  🔍 Code Review
                        ▲
                        │
                        │
Commits ◄───────────────┼───────────────► Issues 🐛
  📦                    │
                        │
                        ▼
                 🔀 Pull Requests
```

When a pulse cycle triggers:
1. **🐛 Issue**: Opens a realistic development maintenance issue on GitHub.
2. **🌿 Branch**: Creates a lightweight temporary feature branch `pulse/YYYYMMDD-HHMMSS`.
3. **📦 Commit**: Commits updated telemetry metrics to the branch.
4. **🔀 Pull Request**: Opens a Pull Request linking and closing the issue.
5. **🔍 Code Review**: Submits an automated peer review (`COMMENT` review event) which registers on GitHub's Code Review metric.
6. **🚀 Squash Merge & Cleanup**: Merges the PR into the default branch (registering a commit contribution) and cleanly deletes the remote branch.
7. **✅ Issue Resolution**: Automatically closes the issue, leaving your repository pristine.

---

## 🛠 Building from Source

### Setup Environment
```bash
# Clone this repository
git clone https://github.com/Nithinkumaru777/gitpulse-desktop.git
cd gitpulse-desktop

# Install dependencies
pip install pywebview pystray pillow pyinstaller
```

### Run Application
```bash
python main.py
```

### Build Standalone Executable
```bash
pyinstaller --noconsole --onefile --add-data "gitpulse_icon.png;." --add-data "gitpulse_icon.ico;." --icon=gitpulse_icon.ico --name=GitPulse main.py
```

---

## 📜 License

Distributed under the MIT License.
