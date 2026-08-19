# ⚡ GitPulse — GitHub Activity Tracker & Desktop App

> **Keep your contribution graph alive with a modern, automated desktop application.**

[![GitHub Release](https://img.shields.io/github/v/release/Nithinkumaru777/gitpulse-desktop?color=39d353&style=flat-square)](https://github.com/Nithinkumaru777/gitpulse-desktop/releases/latest)
[![Platform](https://img.shields.io/badge/platform-Windows-blue?style=flat-square)](https://github.com/Nithinkumaru777/gitpulse-desktop)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=flat-square)](https://opensource.org/licenses/MIT)

GitPulse is a lightweight, background-running Windows desktop application built with Python and PyWebView. It automatically manages timestamped activity commits to your connected GitHub repositories on a customizable schedule (default: 10 minutes), keeping your GitHub graph active and green effortlessly.

---

## ✨ Features

- 🎨 **Ultra-Modern Glassmorphic UI**: Beautiful dark theme interface with live radar pulse animations and countdown progress bar.
- 📌 **System Tray & Background Runner**: Minimizes directly to your Windows **Hidden Icons** system tray menu and runs continuously in the background.
- 🔗 **1-Click GitHub Link Connector**: Simply paste any GitHub Repository URL to connect or automatically clone and link.
- 📋 **Clipboard Integration**: Instant "Paste from Clipboard" button for effortless link entry.
- ⚡ **Windows Boot Auto-Start**: Configure GitPulse to launch automatically whenever your laptop turns on.
- ⏱ **Customizable Pulse Intervals**: Flexible schedules including 1m, 5m, 10m, 15m, 30m, and 60m intervals.
- 📦 **Standalone Installer**: Comes with a sleek Setup Wizard (`GitPulse_Setup.exe`) supporting custom install locations, Desktop shortcuts, and Start Menu shortcuts.
- 💻 **Manual Test Pulse**: On-demand "Test Commit Now" button to verify GitHub authentication and git push operations instantly.

---

## 🚀 Download & Installation

### 📥 Download Installer (`GitPulse_Setup.exe`)
[**Click Here to Download Latest GitPulse_Setup.exe**](https://github.com/Nithinkumaru777/gitpulse-desktop/releases/latest)

1. Launch **`GitPulse_Setup.exe`**.
2. Choose your desired installation folder (e.g. `C:\Program Files\GitPulse` or `D:\GitPulse`).
3. Select shortcut options (Desktop & Start Menu) and click **Install Now**.
4. Launch GitPulse, paste your target GitHub Repository Link, and click **START PULSING**.

---

## 💻 How It Works

1. **Repository Connection**: GitPulse connects to any target Git repository or clones a GitHub URL.
2. **Automated Commit Loop**: At your configured interval (e.g., 10 minutes), GitPulse appends a timestamp log entry to `activity_log.txt`.
3. **Git Push Sequence**: Executes a safe `git pull → git add → git commit → git push` sequence in a background thread.
4. **Resilient & Silent**: Silently handles network dropouts and retries on the next scheduled cycle without interrupting your work.

---

## 🛠 Building from Source

### Setup Environment
```bash
# Clone this public repository
git clone https://github.com/Nithinkumaru777/gitpulse-desktop.git
cd gitpulse-desktop

# Install dependencies
pip install pywebview pystray pillow pyinstaller
```

### Run Application
```bash
python main.py
```

### Build Standalone Executable & Setup Installer
```bash
# Build main GitPulse app
pyinstaller --noconsole --onefile --add-data "gitpulse_icon.png;." --add-data "gitpulse_icon.ico;." --icon=gitpulse_icon.ico --name=GitPulse main.py

# Build Setup Installer
pyinstaller --noconsole --onefile --add-data "dist/GitPulse.exe;payload" --add-data "gitpulse_icon.ico;." --add-data "gitpulse_icon.png;." --icon=gitpulse_icon.ico --name=GitPulse_Setup installer.py
```

---

## 📄 Repository Structure

```
gitpulse-desktop/
├── main.py                # Main PyWebView Application & System Tray Logic
├── installer.py           # Setup Wizard & Installer Application
├── gitpulse_icon.ico      # Application Window & System Tray Icon
├── gitpulse_icon.png      # RGBA High-Res Icon Asset
├── BUILD.md               # Build Instructions & Technical Docs
├── README.md              # Project Documentation
└── .gitignore             # Git Ignore Configuration
```

---

## 📜 License

Distributed under the MIT License.
