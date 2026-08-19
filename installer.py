"""
GitPulse Setup & Installer — Keep your graph alive.
Ultra-Modern Glassmorphic Setup Wizard with custom directory picker, shortcut creation, registry autostart, and safe installation.
"""

import base64
import ctypes
import json
import os
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path
from tkinter import Tk, filedialog

import webview

# ── Paths ────────────────────────────────────────────────────────────
if getattr(sys, 'frozen', False):
    INSTALLER_DIR = Path(sys.executable).parent
    BUNDLE_DIR = Path(getattr(sys, '_MEIPASS', os.path.dirname(sys.executable)))
else:
    INSTALLER_DIR = Path(os.path.dirname(os.path.abspath(__file__)))
    BUNDLE_DIR = INSTALLER_DIR

PAYLOAD_DIR = BUNDLE_DIR / "payload"
DEFAULT_EXE = PAYLOAD_DIR / "GitPulse.exe" if (PAYLOAD_DIR / "GitPulse.exe").exists() else INSTALLER_DIR / "dist" / "GitPulse.exe"
ICON_ICO = BUNDLE_DIR / "gitpulse_icon.ico"
ICON_PNG = BUNDLE_DIR / "gitpulse_icon.png"

# Windows User Shell Folders Helper
def get_user_shell_folder(folder_name: str) -> Path:
    if sys.platform == "win32":
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders")
            val, _ = winreg.QueryValueEx(key, folder_name)
            val = os.path.expandvars(val)
            if Path(val).exists():
                return Path(val)
        except Exception:
            pass
    if folder_name == "Desktop":
        return Path(os.path.expanduser("~/Desktop"))
    elif folder_name == "Programs":
        return Path(os.path.expanduser("~/AppData/Roaming/Microsoft/Windows/Start Menu/Programs"))
    return Path(os.path.expanduser("~"))


def get_default_install_dir() -> str:
    local_appdata = os.environ.get("LOCALAPPDATA", os.path.expanduser("~/AppData/Local"))
    return str(Path(local_appdata) / "Programs" / "GitPulse")


def create_desktop_shortcuts(target_exe: str):
    target_exe = os.path.abspath(target_exe)
    working_dir = os.path.dirname(target_exe)
    icon_path = os.path.join(working_dir, "gitpulse_icon.ico")
    if not os.path.exists(icon_path):
        icon_path = target_exe

    ps_code = f"""
$d1 = [Environment]::GetFolderPath([Environment+SpecialFolder]::Desktop)
$d2 = "$env:USERPROFILE\\Desktop"
$d3 = "$env:USERPROFILE\\OneDrive\\Desktop"
$d4 = "C:\\Users\\Public\\Desktop"
$desktops = @($d1, $d2, $d3, $d4) | Select-Object -Unique

foreach ($d in $desktops) {{
    if ($d -and (Test-Path $d)) {{
        $shortcutPath = Join-Path $d "GitPulse.lnk"
        $ws = New-Object -ComObject WScript.Shell
        $sc = $ws.CreateShortcut($shortcutPath)
        $sc.TargetPath = '{target_exe}'
        $sc.WorkingDirectory = '{working_dir}'
        $sc.IconLocation = '{icon_path}'
        $sc.Save()
    }}
}}
"""
    encoded = base64.b64encode(ps_code.encode('utf-16le')).decode('utf-8')
    subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-EncodedCommand", encoded],
        capture_output=True,
        text=True,
        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
    )


def create_start_menu_shortcut(target_exe: str):
    target_exe = os.path.abspath(target_exe)
    working_dir = os.path.dirname(target_exe)
    icon_path = os.path.join(working_dir, "gitpulse_icon.ico")
    if not os.path.exists(icon_path):
        icon_path = target_exe

    ps_code = f"""
$p1 = [Environment]::GetFolderPath([Environment+SpecialFolder]::Programs)
$p2 = "$env:APPDATA\\Microsoft\\Windows\\Start Menu\\Programs"
$programs = @($p1, $p2) | Select-Object -Unique

foreach ($p in $programs) {{
    if ($p -and (Test-Path $p)) {{
        $shortcutPath = Join-Path $p "GitPulse.lnk"
        $ws = New-Object -ComObject WScript.Shell
        $sc = $ws.CreateShortcut($shortcutPath)
        $sc.TargetPath = '{target_exe}'
        $sc.WorkingDirectory = '{working_dir}'
        $sc.IconLocation = '{icon_path}'
        $sc.Save()
    }}
}}
"""
    encoded = base64.b64encode(ps_code.encode('utf-16le')).decode('utf-8')
    subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-EncodedCommand", encoded],
        capture_output=True,
        text=True,
        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
    )


def set_autostart_registry(exe_path: str, enable: bool):
    if sys.platform != "win32":
        return False
    try:
        import winreg
        REG_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
        APP_NAME = "GitPulse"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH, 0, winreg.KEY_ALL_ACCESS) as key:
            if enable:
                winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, f'"{exe_path}"')
            else:
                try:
                    winreg.DeleteValue(key, APP_NAME)
                except OSError:
                    pass
        return True
    except Exception:
        return False


# ═══════════════════════════════════════════════════════════════════════
#  Installer HTML UI
# ═══════════════════════════════════════════════════════════════════════
HTML_INSTALLER = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>GitPulse Setup Wizard</title>
  <style>
    :root {
      --bg-dark: #090d16;
      --bg-surface: rgba(22, 27, 34, 0.85);
      --bg-card: #161b22;
      --bg-elevated: #21262d;
      --border: #30363d;
      --text-main: #f0f6fc;
      --text-muted: #8b949e;
      --text-dim: #6e7681;
      --accent-green: #238636;
      --accent-green-bright: #39d353;
      --accent-green-hover: #2ea043;
      --accent-blue: #58a6ff;
      --accent-red: #da3633;
      --accent-yellow: #d29922;
    }

    * { box-sizing: border-box; margin: 0; padding: 0; user-select: none; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }

    body {
      background: radial-gradient(circle at top right, #0d172e 0%, #080c14 100%);
      color: var(--text-main);
      height: 100vh;
      display: flex;
      flex-direction: column;
      overflow: hidden;
    }

    .topbar {
      display: flex; align-items: center; justify-content: space-between;
      padding: 14px 20px; background: rgba(13, 17, 23, 0.9);
      backdrop-filter: blur(12px); border-bottom: 1px solid var(--border);
    }

    .brand { display: flex; align-items: center; gap: 10px; }
    .brand-name { font-size: 18px; font-weight: 700; }
    .badge { font-size: 10px; font-weight: 700; background: rgba(57, 211, 83, 0.15); color: var(--accent-green-bright); padding: 2px 8px; border-radius: 12px; border: 1px solid rgba(57, 211, 83, 0.3); }

    .container {
      flex: 1; padding: 20px; display: flex; flex-direction: column; gap: 16px; overflow-y: auto;
    }

    .card {
      background: var(--bg-surface); backdrop-filter: blur(12px);
      border: 1px solid var(--border); border-radius: 12px; padding: 18px;
    }

    .title { font-size: 15px; font-weight: 700; margin-bottom: 4px; }
    .subtitle { font-size: 12px; color: var(--text-muted); margin-bottom: 14px; }

    .input-group { display: flex; gap: 8px; }
    .text-input {
      flex: 1; background: #0d1117; border: 1px solid var(--border);
      color: var(--text-main); padding: 10px 14px; border-radius: 8px;
      font-size: 13px; outline: none; user-select: text;
    }

    .btn {
      display: inline-flex; align-items: center; justify-content: center; gap: 8px;
      padding: 10px 18px; border-radius: 8px; font-size: 13px; font-weight: 600;
      border: none; cursor: pointer; transition: all 0.2s ease; outline: none;
    }
    .btn:active { transform: scale(0.97); }

    .btn-primary {
      background: linear-gradient(180deg, #2ea043 0%, #238636 100%);
      color: #ffffff; box-shadow: 0 4px 12px rgba(35, 134, 54, 0.3);
    }
    .btn-primary:hover {
      background: linear-gradient(180deg, #39d353 0%, #2ea043 100%);
      box-shadow: 0 4px 16px rgba(57, 211, 83, 0.4);
    }

    .btn-secondary {
      background: var(--bg-elevated); color: var(--text-main); border: 1px solid var(--border);
    }
    .btn-secondary:hover { background: #2d333b; }

    .checkbox-group { display: flex; flex-direction: column; gap: 10px; margin-top: 6px; }
    .checkbox-label {
      display: flex; align-items: center; gap: 10px; font-size: 13px;
      color: var(--text-main); cursor: pointer;
    }
    .checkbox-label input { accent-color: var(--accent-green-bright); width: 16px; height: 16px; cursor: pointer; }

    /* Progress Bar */
    .progress-box { margin-top: 10px; }
    .progress-bar { height: 8px; background: var(--bg-elevated); border-radius: 4px; overflow: hidden; margin-top: 8px; }
    .progress-fill { height: 100%; background: linear-gradient(90deg, var(--accent-green) 0%, var(--accent-green-bright) 100%); width: 0%; transition: width 0.3s ease; }
    .progress-status { font-size: 12px; color: var(--accent-yellow); margin-top: 6px; }

    .bottom-bar {
      display: flex; justify-content: space-between; align-items: center;
      padding: 14px 20px; background: rgba(13, 17, 23, 0.9); border-top: 1px solid var(--border);
    }
  </style>
</head>
<body>
  <div class="topbar">
    <div class="brand">
      <span style="font-size: 20px;">⚡</span>
      <span class="brand-name">GitPulse Setup Wizard</span>
      <span class="badge">INSTALLER</span>
    </div>
  </div>

  <div class="container">
    <!-- Step 1: Install Folder -->
    <div class="card">
      <div class="title">1. Choose Installation Location</div>
      <div class="subtitle">Select the folder where GitPulse will be installed on your computer.</div>
      <div class="input-group">
        <input type="text" class="text-input" id="installDirInput" readonly />
        <button class="btn btn-secondary" onclick="browseInstallDir()">📁 Browse...</button>
      </div>
    </div>

    <!-- Step 2: Options -->
    <div class="card">
      <div class="title">2. Installation Options</div>
      <div class="subtitle">Select shortcut & startup preferences for GitPulse.</div>
      <div class="checkbox-group">
        <label class="checkbox-label">
          <input type="checkbox" id="chkDesktop" checked />
          <span>Create Desktop Shortcut</span>
        </label>
        <label class="checkbox-label">
          <input type="checkbox" id="chkStartMenu" checked />
          <span>Add to Start Menu Programs</span>
        </label>
        <label class="checkbox-label">
          <input type="checkbox" id="chkAutostart" checked />
          <span>Run automatically on Windows startup (Laptop turn-on)</span>
        </label>
      </div>
    </div>

    <!-- Step 3: Installation Progress -->
    <div class="card" id="progressCard" style="display: none;">
      <div class="title">Installing GitPulse...</div>
      <div class="progress-box">
        <div class="progress-bar"><div class="progress-fill" id="progressFill"></div></div>
        <div class="progress-status" id="progressStatus">Preparing installation...</div>
      </div>
    </div>
  </div>

  <div class="bottom-bar" id="bottomBar">
    <label class="checkbox-label" id="lblLaunch" style="display: none;">
      <input type="checkbox" id="chkLaunchNow" checked />
      <span>Launch GitPulse when setup finishes</span>
    </label>
    <div style="margin-left: auto; display: flex; gap: 10px;">
      <button class="btn btn-secondary" id="btnCancel" onclick="closeInstaller()">Cancel</button>
      <button class="btn btn-primary" id="btnInstall" onclick="startInstallation()">🚀 Install Now</button>
    </div>
  </div>

  <script>
    async function browseInstallDir() {
      if (window.pywebview && window.pywebview.api) {
        const res = await window.pywebview.api.browse_install_dir();
        if (res) document.getElementById("installDirInput").value = res;
      }
    }

    async function startInstallation() {
      const installDir = document.getElementById("installDirInput").value;
      const desktop = document.getElementById("chkDesktop").checked;
      const startMenu = document.getElementById("chkStartMenu").checked;
      const autostart = document.getElementById("chkAutostart").checked;

      document.getElementById("btnInstall").disabled = true;
      document.getElementById("btnCancel").disabled = true;
      document.getElementById("progressCard").style.display = "block";

      if (window.pywebview && window.pywebview.api) {
        await window.pywebview.api.install_app(installDir, desktop, startMenu, autostart);
      }
    }

    function updateProgressUI(percent, statusMsg) {
      document.getElementById("progressFill").style.width = percent + "%";
      document.getElementById("progressStatus").innerText = statusMsg;
    }

    function onInstallFinished(success, errorMsg) {
      if (success) {
        updateProgressUI(100, "🎉 Installation complete!");
        document.getElementById("btnInstall").style.display = "none";
        document.getElementById("btnCancel").style.display = "none";
        document.getElementById("lblLaunch").style.display = "flex";
        
        const btnFinish = document.createElement("button");
        btnFinish.className = "btn btn-primary";
        btnFinish.innerText = "🚀 Finish & Launch";
        btnFinish.onclick = async () => {
          const launch = document.getElementById("chkLaunchNow").checked;
          const installDir = document.getElementById("installDirInput").value;
          if (window.pywebview && window.pywebview.api) {
            await window.pywebview.api.finish_installer(installDir, launch);
          }
        };
        document.getElementById("bottomBar").appendChild(btnFinish);
      } else {
        updateProgressUI(0, "❌ Installation failed: " + errorMsg);
        document.getElementById("btnCancel").disabled = false;
      }
    }

    function closeInstaller() {
      if (window.pywebview && window.pywebview.api) {
        window.pywebview.api.close_installer();
      }
    }

    window.addEventListener("pywebviewready", async () => {
      if (window.pywebview && window.pywebview.api) {
        const defaultDir = await window.pywebview.api.get_default_dir();
        document.getElementById("installDirInput").value = defaultDir;
      }
    });
  </script>
</body>
</html>"""


# ═══════════════════════════════════════════════════════════════════════
#  Installer JS API & Logic
# ═══════════════════════════════════════════════════════════════════════
class InstallerApi:
    def __init__(self, window_ref):
        self.window = window_ref

    def get_default_dir(self):
        return get_default_install_dir()

    def browse_install_dir(self):
        r = Tk()
        r.withdraw()
        folder = filedialog.askdirectory(title="Select GitPulse Installation Folder")
        r.destroy()
        if folder:
            return str(Path(folder) / "GitPulse")
        return None

    def install_app(self, install_dir: str, create_desktop: bool, create_startmenu: bool, autostart: bool):
        def _bg_install():
            try:
                target_path = Path(install_dir)
                target_path.mkdir(parents=True, exist_ok=True)
                
                self.update_progress(20, "Copying application payload...")
                time.sleep(0.5)

                # Source executable
                source_exe = DEFAULT_EXE
                if not source_exe.exists():
                    raise FileNotFoundError(f"Source executable not found: {source_exe}")

                target_exe = target_path / "GitPulse.exe"
                shutil.copy2(source_exe, target_exe)

                # Copy icon files if present
                for icon in [ICON_ICO, ICON_PNG, BUNDLE_DIR / "gitpulse_icon.ico", BUNDLE_DIR / "gitpulse_icon.png"]:
                    if icon.exists():
                        try:
                            shutil.copy2(icon, target_path / icon.name)
                        except Exception:
                            pass

                self.update_progress(50, "Creating Windows shortcuts...")
                time.sleep(0.5)

                # Shortcuts
                if create_desktop:
                    create_desktop_shortcuts(str(target_exe))

                if create_startmenu:
                    create_start_menu_shortcut(str(target_exe))

                self.update_progress(80, "Configuring Windows startup registry...")
                time.sleep(0.4)

                if autostart:
                    set_autostart_registry(str(target_exe), True)

                # Save initial default config in target directory
                config_path = target_path / "config.json"
                if not config_path.exists():
                    with open(config_path, "w", encoding="utf-8") as f:
                        json.dump({"interval_minutes": 10, "autostart": autostart}, f, indent=2)

                self.update_progress(100, "Installation complete!")
                time.sleep(0.4)

                if self.window:
                    self.window.evaluate_js("onInstallFinished(true, '')")

            except Exception as exc:
                if self.window:
                    safe_err = str(exc).replace("'", "\\'").replace('"', '\\"')
                    self.window.evaluate_js(f"onInstallFinished(false, '{safe_err}')")

        threading.Thread(target=_bg_install, daemon=True).start()

    def update_progress(self, percent: int, msg: str):
        if self.window:
            safe_msg = msg.replace("'", "\\'").replace('"', '\\"')
            try:
                self.window.evaluate_js(f"updateProgressUI({percent}, '{safe_msg}')")
            except Exception:
                pass

    def finish_installer(self, install_dir: str, launch_now: bool):
        if launch_now:
            target_exe = Path(install_dir) / "GitPulse.exe"
            if target_exe.exists():
                subprocess.Popen([str(target_exe)], cwd=install_dir)
        self.close_installer()

    def close_installer(self):
        if self.window:
            self.window.destroy()
        os._exit(0)


if __name__ == "__main__":
    api = InstallerApi(None)
    window = webview.create_window(
        title="GitPulse Setup & Installer",
        html=HTML_INSTALLER,
        js_api=api,
        width=580,
        height=540,
        resizable=False,
        background_color="#090d16"
    )
    api.window = window
    webview.start(debug=False)
