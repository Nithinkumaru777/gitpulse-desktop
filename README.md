# ⚡ GitPulse — GitHub Activity Tracker & Desktop App

> **Keep your contribution graph alive with a modern, automated desktop application.**

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

## 🚀 Quick Start & Installation

### Option 1: Using the Installer (`GitPulse_Setup.exe`)
1. Download **`GitPulse_Setup.exe`** from the project releases.
2. Launch the Setup Wizard and select your preferred installation directory.
3. Choose shortcut options (Desktop & Start Menu) and click **Install Now**.
4. Launch GitPulse, paste your GitHub Repository Link, and click **START PULSING**.

### Option 2: Running Standalone Executable (`GitPulse.exe`)
1. Download **`GitPulse.exe`** from the `dist/` directory.
2. Double-click `GitPulse.exe` to launch the application.

---

## 💻 How It Works

1. **Repository Connection**: GitPulse connects to any local Git repository or clones a GitHub URL.
2. **Automated Commit Loop**: At your configured interval (e.g., 10 minutes), GitPulse appends a timestamp log entry to `activity_log.txt`.
3. **Git Push Sequence**: Executes a safe `git pull → git add → git commit → git push` sequence in a background thread.
4. **Resilient & Silent**: Silently handles network dropouts and retries on the next scheduled cycle without interrupting your work.

---

## 🛠 Building from Source

### Prerequisites
- **Python 3.10+**
- **Git for Windows** / MinGit

### Setup Environment
```bash
# Clone this repository
git clone https://github.com/Nithinkumaru777/gitpulse-activity.git
cd gitpulse-activity

# Install dependencies
pip install pywebview pystray pillow pyinstaller
```

### Run Application
```bash
python main.py
```

### Build Standalone Executable
```bash
# Build main GitPulse app
pyinstaller --noconsole --onefile --add-data "gitpulse_icon.png;." --add-data "gitpulse_icon.ico;." --icon=gitpulse_icon.ico --name=GitPulse main.py

# Build Setup Installer
pyinstaller --noconsole --onefile --add-data "dist/GitPulse.exe;payload" --add-data "gitpulse_icon.ico;." --add-data "gitpulse_icon.png;." --icon=gitpulse_icon.ico --name=GitPulse_Setup installer.py
```

---

## 📄 Repository Structure

```
gitpulse-activity/
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

Distributed under the MIT License. See `LICENSE` for more information.
