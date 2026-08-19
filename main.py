"""
GitPulse — Keep your graph alive.
Ultra-Modern Glassmorphic UI powered by PyWebView with Windows System Tray (Hidden Icons) & Background Runner.
"""

import ctypes
import json
import os
import random
import re
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from tkinter import Tk, filedialog

from PIL import Image, ImageDraw
import pystray
import webview

if sys.platform == "win32":
    import winreg
else:
    winreg = None

WINDOW_TITLE = "GitPulse — GitHub Activity Tracker"

# ── Paths ────────────────────────────────────────────────────────────
if getattr(sys, 'frozen', False):
    APP_DIR = Path(sys.executable).parent
    BUNDLE_DIR = Path(getattr(sys, '_MEIPASS', os.path.dirname(sys.executable)))
else:
    APP_DIR = Path(os.path.dirname(os.path.abspath(__file__)))
    BUNDLE_DIR = APP_DIR

CONFIG_FILE = APP_DIR / "config.json"
ICON_PNG = BUNDLE_DIR / "gitpulse_icon.png"
ICON_ICO = BUNDLE_DIR / "gitpulse_icon.ico"

# ── Windows Startup Registry Helper ─────────────────────────────────
REG_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_NAME = "GitPulse"


def is_autostart_enabled() -> bool:
    if sys.platform != "win32" or winreg is None:
        return False
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH, 0, winreg.KEY_READ) as key:
            val, _ = winreg.QueryValueEx(key, APP_NAME)
            return bool(val)
    except OSError:
        return False


def set_autostart(enable: bool) -> bool:
    if sys.platform != "win32" or winreg is None:
        return False
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH, 0, winreg.KEY_ALL_ACCESS) as key:
            if enable:
                if getattr(sys, 'frozen', False):
                    exe_path = f'"{sys.executable}"'
                else:
                    exe_path = f'"{sys.executable}" "{os.path.abspath(__file__)}"'
                winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, exe_path)
            else:
                try:
                    winreg.DeleteValue(key, APP_NAME)
                except OSError:
                    pass
        return True
    except Exception:
        return False


# ═══════════════════════════════════════════════════════════════════════
#  Config persistence
# ═══════════════════════════════════════════════════════════════════════
def load_config() -> dict | None:
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if "repo_path" in data:
                data.setdefault("interval_minutes", 10)
                data.setdefault("autostart", is_autostart_enabled())
                return data
        except (json.JSONDecodeError, OSError):
            pass
    return None


def save_config(repo_path: str, interval_minutes: int = 10, autostart: bool = False) -> None:
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump({
            "repo_path": repo_path,
            "interval_minutes": interval_minutes,
            "autostart": autostart,
        }, f, indent=2)


# ═══════════════════════════════════════════════════════════════════════
#  Git & Tray helpers
# ═══════════════════════════════════════════════════════════════════════
def create_tray_image():
    """Load or generate a high-res RGBA icon for pystray."""
    for path in [ICON_PNG, ICON_ICO, APP_DIR / "gitpulse_icon.png", APP_DIR / "gitpulse_icon.ico"]:
        if path.exists():
            try:
                img = Image.open(path).convert('RGBA')
                return img.resize((64, 64), Image.Resampling.LANCZOS)
            except Exception:
                pass

    # Generated RGBA icon fallback
    img = Image.new('RGBA', (128, 128), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse((4, 4, 124, 124), fill=(13, 17, 23, 255), outline=(48, 54, 61, 255), width=4)
    draw.ellipse((48, 48, 80, 80), fill=(57, 211, 83, 255))
    points = [(20, 64), (44, 64), (54, 38), (64, 90), (74, 50), (84, 64), (108, 64)]
    draw.line(points, fill=(255, 255, 255, 255), width=5)
    return img


def is_git_repo(path: str) -> bool:
    return (Path(path) / ".git").is_dir()


def repo_display_name(path: str) -> str:
    return Path(path).name


def parse_github_url(url: str) -> tuple[str, str] | None:
    url = url.strip()
    if not url:
        return None
    url = url.replace(".git", "").rstrip("/")
    if "github.com/" in url:
        parts = url.split("github.com/")[-1].split("/")
        if len(parts) >= 2:
            return parts[0], parts[1]
    elif "github.com:" in url:
        parts = url.split("github.com:")[-1].split("/")
        if len(parts) >= 2:
            return parts[0], parts[1]
    return None


def get_git_executable() -> str:
    import shutil
    git_path = shutil.which("git")
    if git_path:
        return git_path

    possible_paths = [
        Path(os.environ.get("LOCALAPPDATA", "")) / "MinGit" / "cmd" / "git.exe",
        Path(os.environ.get("LOCALAPPDATA", "")) / "MinGit" / "mingw64" / "bin" / "git.exe",
        Path(os.environ.get("USERPROFILE", "")) / ".cache" / "codex-runtimes" / "codex-primary-runtime" / "dependencies" / "native" / "git" / "cmd" / "git.exe",
        Path("C:/Program Files/Git/cmd/git.exe"),
        Path("C:/Program Files (x86)/Git/cmd/git.exe"),
        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Git" / "cmd" / "git.exe",
    ]
    for p in possible_paths:
        if p.exists():
            return str(p)
    return "git"


def run_git(args: list[str], cwd: str) -> tuple[bool, str]:
    git_cmd = get_git_executable()
    try:
        result = subprocess.run(
            [git_cmd] + args,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=60,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )
        output = (result.stdout + result.stderr).strip()
        return result.returncode == 0, output
    except FileNotFoundError:
        return False, "git is not installed or not in PATH."
    except subprocess.TimeoutExpired:
        return False, "git command timed out."
    except Exception as exc:
        return False, str(exc)


def get_repo_remote_url(repo_path: str) -> str | None:
    ok, output = run_git(["remote", "get-url", "origin"], repo_path)
    if ok and output:
        return output
    return None


def gitpulse_cycle(repo_path: str, log_callback) -> bool:
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    log_file = Path(repo_path) / "activity_log.txt"

    try:
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] routine maintenance\n")
        log_callback(f"📝  Appended timestamp: {timestamp}")
    except OSError as exc:
        log_callback(f"❌  Failed to write activity_log.txt: {exc}")
        return False

    steps = [
        (["pull"],                                      "pull"),
        (["add", "-f", "activity_log.txt"],             "add"),
        (["commit", "-m",
          f"update: routine maintenance {timestamp}"],  "commit"),
        (["push"],                                      "push"),
    ]

    for args, label in steps:
        ok, output = run_git(args, repo_path)
        if ok:
            log_callback(f"✅  git {label}")
        else:
            log_callback(f"⚠️  git {label} failed — {output}")
            if label == "commit" and "nothing to commit" in output.lower():
                log_callback("   (nothing new to commit, skipping push)")
                return True
            return False

    return True


# ═══════════════════════════════════════════════════════════════════════
#  HTML UI Template
# ═══════════════════════════════════════════════════════════════════════
HTML_CONTENT = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>GitPulse</title>
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
      --font-mono: 'Consolas', 'JetBrains Mono', monospace;
    }

    * {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
      user-select: none;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }

    body {
      background: radial-gradient(circle at top right, #0d172e 0%, #080c14 100%);
      color: var(--text-main);
      height: 100vh;
      display: flex;
      flex-direction: column;
      overflow: hidden;
    }

    /* Top Navigation Bar */
    .topbar {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 12px 20px;
      background: rgba(13, 17, 23, 0.9);
      backdrop-filter: blur(12px);
      border-bottom: 1px solid var(--border);
    }

    .brand {
      display: flex;
      align-items: center;
      gap: 10px;
    }

    .pulse-dot-wrapper {
      position: relative;
      display: flex;
      align-items: center;
      justify-content: center;
    }

    .pulse-dot {
      width: 12px;
      height: 12px;
      border-radius: 50%;
      background: var(--text-dim);
      transition: background 0.3s;
    }

    .pulse-ring {
      position: absolute;
      width: 24px;
      height: 24px;
      border-radius: 50%;
      border: 2px solid var(--accent-green-bright);
      animation: radar-pulse 2s infinite ease-out;
      display: none;
    }

    @keyframes radar-pulse {
      0% { transform: scale(0.5); opacity: 1; }
      100% { transform: scale(1.7); opacity: 0; }
    }

    .brand-name {
      font-size: 18px;
      font-weight: 700;
      letter-spacing: -0.3px;
    }

    .badge-pro {
      font-size: 10px;
      font-weight: 700;
      background: rgba(57, 211, 83, 0.15);
      color: var(--accent-green-bright);
      padding: 2px 8px;
      border-radius: 12px;
      border: 1px solid rgba(57, 211, 83, 0.3);
    }

    /* Container */
    .container {
      flex: 1;
      padding: 16px 20px;
      display: flex;
      flex-direction: column;
      gap: 14px;
      overflow-y: auto;
    }

    /* Card */
    .card {
      background: var(--bg-surface);
      backdrop-filter: blur(12px);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 16px;
      transition: border-color 0.2s, box-shadow 0.2s;
    }

    .card:hover {
      border-color: rgba(255, 255, 255, 0.15);
    }

    /* Repo Connect Banner */
    .repo-banner {
      display: flex;
      flex-direction: column;
      gap: 12px;
      background: linear-gradient(135deg, rgba(22, 27, 34, 0.95) 0%, rgba(13, 29, 48, 0.7) 100%);
      border: 1px solid rgba(88, 166, 255, 0.3);
      box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
    }

    .repo-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
    }

    .repo-title {
      font-size: 14px;
      font-weight: 600;
      color: var(--text-main);
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .input-group {
      display: flex;
      gap: 8px;
    }

    .text-input {
      flex: 1;
      background: #0d1117;
      border: 1px solid var(--border);
      color: var(--text-main);
      padding: 10px 14px;
      border-radius: 8px;
      font-size: 13px;
      outline: none;
      transition: border-color 0.2s, box-shadow 0.2s;
      user-select: text;
    }

    .text-input:focus {
      border-color: var(--accent-blue);
      box-shadow: 0 0 0 3px rgba(88, 166, 255, 0.2);
    }

    /* Buttons */
    .btn {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      padding: 10px 16px;
      border-radius: 8px;
      font-size: 13px;
      font-weight: 600;
      border: none;
      cursor: pointer;
      transition: all 0.2s ease;
      outline: none;
    }

    .btn:active {
      transform: scale(0.97);
    }

    .btn-primary {
      background: linear-gradient(180deg, #2ea043 0%, #238636 100%);
      color: #ffffff;
      box-shadow: 0 4px 12px rgba(35, 134, 54, 0.3);
    }

    .btn-primary:hover {
      background: linear-gradient(180deg, #39d353 0%, #2ea043 100%);
      box-shadow: 0 4px 16px rgba(57, 211, 83, 0.4);
    }

    .btn-secondary {
      background: var(--bg-elevated);
      color: var(--text-main);
      border: 1px solid var(--border);
    }

    .btn-secondary:hover {
      background: #2d333b;
      border-color: rgba(255, 255, 255, 0.2);
    }

    .btn-danger {
      background: linear-gradient(180deg, #da3633 0%, #b62324 100%);
      color: #ffffff;
      box-shadow: 0 4px 12px rgba(218, 54, 51, 0.3);
    }

    .btn-danger:hover {
      background: linear-gradient(180deg, #f85149 0%, #da3633 100%);
    }

    .btn-blue {
      background: rgba(88, 166, 255, 0.15);
      color: var(--accent-blue);
      border: 1px solid rgba(88, 166, 255, 0.3);
    }

    .btn-blue:hover {
      background: rgba(88, 166, 255, 0.25);
    }

    /* Grid */
    .grid {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 12px;
    }

    .stat-label {
      font-size: 11px;
      font-weight: 700;
      color: var(--text-dim);
      text-transform: uppercase;
      letter-spacing: 0.5px;
      margin-bottom: 6px;
    }

    .stat-val {
      font-size: 18px;
      font-weight: 700;
      color: var(--text-main);
    }

    .stat-sub {
      font-size: 12px;
      color: var(--accent-yellow);
      margin-top: 4px;
    }

    /* Segmented interval selector */
    .segmented {
      display: flex;
      background: #0d1117;
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 2px;
    }

    .segmented-btn {
      flex: 1;
      padding: 6px 10px;
      font-size: 11px;
      font-weight: 600;
      background: transparent;
      color: var(--text-muted);
      border: none;
      border-radius: 6px;
      cursor: pointer;
      transition: all 0.2s;
    }

    .segmented-btn.active {
      background: var(--accent-green);
      color: #ffffff;
      box-shadow: 0 2px 6px rgba(35, 134, 54, 0.4);
    }

    /* Switch */
    .switch-label {
      display: flex;
      align-items: center;
      justify-content: space-between;
      cursor: pointer;
    }

    .switch {
      position: relative;
      width: 44px;
      height: 24px;
    }

    .switch input {
      opacity: 0;
      width: 0;
      height: 0;
    }

    .slider {
      position: absolute;
      cursor: pointer;
      top: 0; left: 0; right: 0; bottom: 0;
      background-color: var(--bg-elevated);
      border: 1px solid var(--border);
      transition: 0.3s;
      border-radius: 24px;
    }

    .slider:before {
      position: absolute;
      content: "";
      height: 16px;
      width: 16px;
      left: 3px;
      bottom: 3px;
      background-color: var(--text-muted);
      transition: 0.3s;
      border-radius: 50%;
    }

    input:checked + .slider {
      background-color: var(--accent-green);
      border-color: var(--accent-green-bright);
    }

    input:checked + .slider:before {
      transform: translateX(20px);
      background-color: #ffffff;
    }

    /* Terminal Console */
    .terminal {
      background: #05080e;
      border: 1px solid var(--border);
      border-radius: 10px;
      flex: 1;
      display: flex;
      flex-direction: column;
      overflow: hidden;
      min-height: 180px;
    }

    .terminal-head {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 8px 14px;
      background: #0d1117;
      border-bottom: 1px solid var(--border);
    }

    .dots {
      display: flex;
      gap: 6px;
    }

    .dot-ctrl {
      width: 10px;
      height: 10px;
      border-radius: 50%;
    }
    .dot-red { background: #ff5f56; }
    .dot-yellow { background: #ffbd2e; }
    .dot-green { background: #27c93f; }

    .terminal-body {
      padding: 12px 14px;
      font-family: var(--font-mono);
      font-size: 12px;
      line-height: 1.5;
      color: #c9d1d9;
      overflow-y: auto;
      flex: 1;
      user-select: text;
    }

    .log-line { margin-bottom: 4px; }
    .log-ts { color: var(--text-dim); }
    .log-ok { color: var(--accent-green-bright); }
    .log-warn { color: var(--accent-yellow); }
    .log-err { color: var(--accent-red); }

    /* Progress bar */
    .progress-bar {
      height: 4px;
      background: var(--bg-elevated);
      border-radius: 2px;
      overflow: hidden;
      margin-top: 6px;
    }

    .progress-fill {
      height: 100%;
      background: linear-gradient(90deg, var(--accent-green) 0%, var(--accent-green-bright) 100%);
      width: 0%;
      transition: width 1s linear;
    }
  </style>
</head>
<body>
  <!-- Top Navigation Bar -->
  <div class="topbar">
    <div class="brand">
      <div class="pulse-dot-wrapper">
        <div class="pulse-dot" id="mainDot"></div>
        <div class="pulse-ring" id="mainRing"></div>
      </div>
      <span class="brand-name">GitPulse</span>
      <span class="badge-pro">PRO</span>
    </div>
    <div style="display: flex; gap: 10px;">
      <button class="btn btn-secondary" onclick="hideToTray()" style="padding: 6px 12px; font-size: 12px;">
        📌 Hide to Tray
      </button>
      <button class="btn btn-secondary" onclick="testCommitNow()" style="padding: 6px 12px; font-size: 12px;">
        ⚡ Test Commit Now
      </button>
    </div>
  </div>

  <!-- Main Container -->
  <div class="container">

    <!-- GitHub Connection Banner -->
    <div class="card repo-banner">
      <div class="repo-header">
        <div class="repo-title">
          <span>🐙</span>
          <span id="repoNameDisplay">No GitHub Repository Connected</span>
        </div>
        <button class="btn btn-secondary" onclick="browseLocalFolder()" style="padding: 4px 10px; font-size: 12px;">
          📁 Browse Folder
        </button>
      </div>

      <div class="input-group">
        <input type="text" class="text-input" id="repoUrlInput" placeholder="Paste GitHub Repository Link (e.g. https://github.com/username/repository)" />
        <button class="btn btn-blue" onclick="pasteClipboard()">
          📋 Paste
        </button>
        <button class="btn btn-primary" onclick="connectRepoUrl()">
          ⚡ Connect Repo
        </button>
      </div>
      <div id="connectionStatus" style="font-size: 12px; color: var(--accent-green-bright); display: none;"></div>
    </div>

    <!-- Stats Grid -->
    <div class="grid">
      <!-- Status Card -->
      <div class="card">
        <div class="stat-label">STATUS</div>
        <div class="stat-val" id="statusText" style="color: var(--text-muted);">IDLE</div>
        <div class="stat-sub" id="timerCountdown">Stopped</div>
        <div class="progress-bar"><div class="progress-fill" id="timerProgress"></div></div>
      </div>

      <!-- Pulses Card -->
      <div class="card">
        <div class="stat-label">TOTAL PULSES</div>
        <div class="stat-val" id="pulseCountVal" style="color: var(--accent-green-bright);">0</div>
        <div class="stat-sub" id="lastPulseTime" style="color: var(--text-muted);">Last: Never</div>
      </div>

      <!-- Windows Boot Card -->
      <div class="card">
        <div class="stat-label">LAPTOP BOOT AUTOSTART</div>
        <div style="margin-top: 6px;">
          <label class="switch-label">
            <span style="font-size: 12px; color: var(--text-muted);" id="autostartText">Disabled</span>
            <div class="switch">
              <input type="checkbox" id="autostartToggle" onchange="toggleAutostart(this.checked)">
              <span class="slider"></span>
            </div>
          </label>
        </div>
      </div>
    </div>

    <!-- Control Strip -->
    <div class="card" style="display: flex; align-items: center; justify-content: space-between; padding: 12px 16px;">
      <div style="display: flex; align-items: center; gap: 12px;">
        <button class="btn btn-primary" id="btnTogglePulse" onclick="togglePulse()" style="padding: 10px 24px; font-size: 14px;">
          ▶ START PULSING
        </button>
      </div>

      <div style="display: flex; align-items: center; gap: 10px;">
        <span style="font-size: 12px; color: var(--text-dim); font-weight: 600;">INTERVAL:</span>
        <div class="segmented">
          <button class="segmented-btn" id="btnInt1" onclick="setIntervalMin(1)">1m</button>
          <button class="segmented-btn" id="btnInt5" onclick="setIntervalMin(5)">5m</button>
          <button class="segmented-btn active" id="btnInt10" onclick="setIntervalMin(10)">10m</button>
          <button class="segmented-btn" id="btnInt15" onclick="setIntervalMin(15)">15m</button>
          <button class="segmented-btn" id="btnInt30" onclick="setIntervalMin(30)">30m</button>
          <button class="segmented-btn" id="btnInt60" onclick="setIntervalMin(60)">60m</button>
        </div>
      </div>
    </div>

    <!-- Terminal Console -->
    <div class="terminal">
      <div class="terminal-head">
        <div class="dots">
          <div class="dot-ctrl dot-red"></div>
          <div class="dot-ctrl dot-yellow"></div>
          <div class="dot-ctrl dot-green"></div>
        </div>
        <span style="font-size: 11px; color: var(--text-dim); font-family: var(--font-mono);">ACTIVITY CONSOLE LOG</span>
        <button class="btn btn-secondary" onclick="clearLogs()" style="padding: 2px 8px; font-size: 11px;">Clear</button>
      </div>
      <div class="terminal-body" id="terminalBody"></div>
    </div>

  </div>

  <script>
    let isRunning = false;
    let currentInterval = 10;
    let pulseCount = 0;

    function addLog(msg) {
      const body = document.getElementById("terminalBody");
      const line = document.createElement("div");
      line.className = "log-line";
      
      let cls = "log-ts";
      if (msg.includes("✅")) cls = "log-ok";
      else if (msg.includes("⚠️") || msg.includes("⏱")) cls = "log-warn";
      else if (msg.includes("❌")) cls = "log-err";

      line.innerHTML = `<span class="${cls}">${msg}</span>`;
      body.appendChild(line);
      body.scrollTop = body.scrollHeight;
    }

    function clearLogs() {
      document.getElementById("terminalBody").innerHTML = "";
    }

    async function hideToTray() {
      if (window.pywebview && window.pywebview.api) {
        await window.pywebview.api.hide_to_tray();
      }
    }

    async function pasteClipboard() {
      if (window.pywebview && window.pywebview.api) {
        const text = await window.pywebview.api.get_clipboard();
        if (text) {
          document.getElementById("repoUrlInput").value = text.trim();
          showStatus("📋 Pasted from clipboard!", "var(--accent-blue)");
        }
      }
    }

    function showStatus(msg, color) {
      const s = document.getElementById("connectionStatus");
      s.innerText = msg;
      s.style.color = color || "var(--accent-green-bright)";
      s.style.display = "block";
    }

    async function connectRepoUrl() {
      const url = document.getElementById("repoUrlInput").value.trim();
      if (!url) {
        showStatus("❌ Please enter or paste a GitHub repository URL", "var(--accent-red)");
        return;
      }
      showStatus("🔍 Validating repository URL...", "var(--accent-yellow)");
      if (window.pywebview && window.pywebview.api) {
        const res = await window.pywebview.api.connect_url(url);
        if (res.status === "ok") {
          showStatus("✅ Connected to " + res.repo_name, "var(--accent-green-bright)");
          document.getElementById("repoNameDisplay").innerText = res.repo_name + " (" + res.path + ")";
          addLog("✅ Connected to GitHub repository: " + res.repo_name);
        } else if (res.status === "need_clone") {
          showStatus("⏳ Repository not found locally. Cloning...", "var(--accent-yellow)");
          const cloneRes = await window.pywebview.api.clone_and_connect(url, res.repo_name);
          if (cloneRes.status === "ok") {
            showStatus("✅ Cloned and connected successfully!", "var(--accent-green-bright)");
            document.getElementById("repoNameDisplay").innerText = res.repo_name + " (" + cloneRes.path + ")";
            addLog("✅ Cloned and connected: " + cloneRes.path);
          } else {
            showStatus("❌ Clone failed: " + cloneRes.error, "var(--accent-red)");
          }
        } else {
          showStatus("❌ " + res.error, "var(--accent-red)");
        }
      }
    }

    async function browseLocalFolder() {
      if (window.pywebview && window.pywebview.api) {
        const res = await window.pywebview.api.browse_folder();
        if (res && res.status === "ok") {
          showStatus("✅ Linked to " + res.repo_name, "var(--accent-green-bright)");
          document.getElementById("repoNameDisplay").innerText = res.repo_name + " (" + res.path + ")";
          addLog("🔗 Linked local repository: " + res.path);
        }
      }
    }

    async function togglePulse() {
      if (window.pywebview && window.pywebview.api) {
        const res = await window.pywebview.api.toggle_pulse();
        updateRunningState(res.running);
      }
    }

    function updateRunningState(running) {
      isRunning = running;
      const btn = document.getElementById("btnTogglePulse");
      const st = document.getElementById("statusText");
      const ring = document.getElementById("mainRing");
      const dot = document.getElementById("mainDot");

      if (running) {
        btn.innerText = "⏹ STOP PULSING";
        btn.className = "btn btn-danger";
        st.innerText = "PULSING ACTIVE";
        st.style.color = "var(--accent-green-bright)";
        ring.style.display = "block";
        dot.style.background = "var(--accent-green-bright)";
      } else {
        btn.innerText = "▶ START PULSING";
        btn.className = "btn btn-primary";
        st.innerText = "IDLE";
        st.style.color = "var(--text-muted)";
        ring.style.display = "none";
        dot.style.background = "var(--text-dim)";
        document.getElementById("timerCountdown").innerText = "Stopped";
        document.getElementById("timerProgress").style.width = "0%";
      }
    }

    async function setIntervalMin(min) {
      currentInterval = min;
      document.querySelectorAll(".segmented-btn").forEach(b => {
        b.classList.remove("active");
      });
      const targetBtn = document.getElementById("btnInt" + min);
      if (targetBtn) targetBtn.classList.add("active");

      if (window.pywebview && window.pywebview.api) {
        await window.pywebview.api.set_interval(min);
        addLog("⏱ Pulse interval set to " + min + " min.");
      }
    }

    async function toggleAutostart(enable) {
      document.getElementById("autostartText").innerText = enable ? "Enabled (Boot)" : "Disabled";
      if (window.pywebview && window.pywebview.api) {
        await window.pywebview.api.set_autostart(enable);
        addLog("⚡ Windows boot autostart " + (enable ? "enabled" : "disabled"));
      }
    }

    async function testCommitNow() {
      if (window.pywebview && window.pywebview.api) {
        addLog("⚡ Manual test commit initiated...");
        await window.pywebview.api.test_commit();
      }
    }

    function updateCountdownUI(remainingSecs, totalSecs) {
      if (!isRunning) return;
      const mins = Math.floor(remainingSecs / 60);
      const secs = remainingSecs % 60;
      const mStr = String(mins).padStart(2, '0');
      const sStr = String(secs).padStart(2, '0');
      document.getElementById("timerCountdown").innerText = `Next in ${mStr}:${sStr}`;

      const percent = Math.max(0, Math.min(100, ((totalSecs - remainingSecs) / totalSecs) * 100));
      document.getElementById("timerProgress").style.width = percent + "%";
    }

    function updatePulseCounterUI(count, lastTime) {
      pulseCount = count;
      document.getElementById("pulseCountVal").innerText = count;
      if (lastTime) {
        document.getElementById("lastPulseTime").innerText = "Last: " + lastTime;
      }
    }

    window.addEventListener("pywebviewready", async () => {
      if (window.pywebview && window.pywebview.api) {
        const init = await window.pywebview.api.get_initial_state();
        if (init) {
          if (init.repo_name) {
            document.getElementById("repoNameDisplay").innerText = init.repo_name + " (" + init.repo_path + ")";
            if (init.remote_url) document.getElementById("repoUrlInput").value = init.remote_url;
          }
          document.getElementById("autostartToggle").checked = init.autostart;
          document.getElementById("autostartText").innerText = init.autostart ? "Enabled (Boot)" : "Disabled";
          setIntervalMin(init.interval_minutes);
          updateRunningState(init.is_running);
          if (init.logs) {
            init.logs.forEach(addLog);
          }
        }
      }
    });
  </script>
</body>
</html>"""


# ═══════════════════════════════════════════════════════════════════════
#  Python JS API & App Logic
# ═══════════════════════════════════════════════════════════════════════
class JsApi:
    def __init__(self, app: "GitPulseApp"):
        self.app = app

    def get_initial_state(self):
        repo_name = repo_display_name(self.app.repo_path) if self.app.repo_path else None
        remote_url = get_repo_remote_url(self.app.repo_path) if self.app.repo_path else None
        return {
            "repo_path": self.app.repo_path,
            "repo_name": repo_name,
            "remote_url": remote_url,
            "interval_minutes": self.app.interval_minutes,
            "autostart": is_autostart_enabled(),
            "is_running": self.app.running,
            "pulse_count": self.app._pulse_count,
            "last_pulse": self.app._last_pulse_str,
            "logs": self.app.log_history,
        }

    def get_clipboard(self):
        try:
            r = Tk()
            r.withdraw()
            text = r.clipboard_get()
            r.destroy()
            return text
        except Exception:
            return ""

    def connect_url(self, raw_url: str):
        parsed = parse_github_url(raw_url)
        if not parsed:
            return {"status": "error", "error": "Invalid GitHub repository URL"}
        owner, repo_name = parsed

        candidates = [
            self.app.repo_path,
            str(APP_DIR / repo_name),
            f"D:\\antigravity\\{repo_name}",
        ]
        for p in candidates:
            if p and is_git_repo(p):
                remote = get_repo_remote_url(p)
                if remote and repo_name.lower() in remote.lower():
                    self.app.repo_path = p
                    save_config(p, self.app.interval_minutes, is_autostart_enabled())
                    self.app.log(f"✅ Connected to GitHub repo: {owner}/{repo_name}")
                    self.app.start()
                    return {"status": "ok", "repo_name": repo_name, "path": p}

        return {"status": "need_clone", "repo_name": repo_name, "owner": owner, "url": raw_url}

    def clone_and_connect(self, url: str, repo_name: str):
        dest_dir = str(APP_DIR / repo_name)
        ok, output = run_git(["clone", url, dest_dir], str(APP_DIR))
        if ok and is_git_repo(dest_dir):
            self.app.repo_path = dest_dir
            save_config(dest_dir, self.app.interval_minutes, is_autostart_enabled())
            self.app.log(f"✅ Cloned and connected repository: {dest_dir}")
            self.app.start()
            return {"status": "ok", "path": dest_dir}
        else:
            return {"status": "error", "error": output}

    def browse_folder(self):
        r = Tk()
        r.withdraw()
        folder = filedialog.askdirectory(title="Select Local Git Repository Folder")
        r.destroy()
        if folder and is_git_repo(folder):
            self.app.repo_path = folder
            save_config(folder, self.app.interval_minutes, is_autostart_enabled())
            self.app.log(f"🔗 Linked local repository: {folder}")
            self.app.start()
            return {"status": "ok", "repo_name": repo_display_name(folder), "path": folder}
        return {"status": "cancel"}

    def set_interval(self, minutes: int):
        self.app.interval_minutes = minutes
        if self.app.repo_path:
            save_config(self.app.repo_path, minutes, is_autostart_enabled())
        if self.app.running:
            self.app.restart_schedule()

    def set_autostart(self, enable: bool):
        set_autostart(enable)
        if self.app.repo_path:
            save_config(self.app.repo_path, self.app.interval_minutes, enable)

    def toggle_pulse(self):
        if self.app.running:
            self.app.stop()
        else:
            self.app.start()
        return {"running": self.app.running}

    def test_commit(self):
        self.app.run_test_pulse()

    def hide_to_tray(self):
        self.app.hide_to_tray()


class GitPulseApp:
    def __init__(self):
        self.repo_path: str | None = None
        self.running: bool = False
        self.interval_minutes: int = 10
        self.log_history: list[str] = []
        self._timer: threading.Timer | None = None
        self._next_run_epoch: float = 0
        self._pulse_count = 0
        self._last_pulse_str = "Never"
        self.window = None
        self.tray_icon = None
        self.is_exiting = False
        self.is_hidden = False

        # Load Saved Config
        cfg = load_config()
        if cfg and is_git_repo(cfg["repo_path"]):
            self.repo_path = cfg["repo_path"]
            self.interval_minutes = cfg.get("interval_minutes", 10)
            autostart_val = cfg.get("autostart", is_autostart_enabled())
            set_autostart(autostart_val)
            self.log(f"Loaded config. Repo: {Path(self.repo_path).name} | Default Interval: {self.interval_minutes} min")

            # Always auto-start pulse loop upon opening app (manual launch or startup)
            self.log("🚀 Auto-start active — launching 10-min pulse schedule.")
            threading.Thread(target=self._delayed_start, daemon=True).start()

        # Heartbeat Loop
        threading.Thread(target=self._heartbeat_loop, daemon=True).start()

    def setup_tray(self):
        image = create_tray_image()

        def _on_toggle_window(icon, item):
            self.toggle_window()

        def _on_show(icon, item):
            self.show_window()

        def _on_hide(icon, item):
            self.hide_to_tray()

        def _on_toggle_pulse(icon, item):
            if self.running:
                self.stop()
            else:
                self.start()

        def _on_test(icon, item):
            self.run_test_pulse()

        def _on_exit(icon, item):
            self.exit_app()

        menu = pystray.Menu(
            pystray.MenuItem("Show / Hide Window", _on_toggle_window, default=True),
            pystray.MenuItem("Open GitPulse", _on_show),
            pystray.MenuItem("Minimize to Tray", _on_hide),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Start / Pause Pulse", _on_toggle_pulse),
            pystray.MenuItem("⚡ Test Commit Now", _on_test),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Exit GitPulse", _on_exit)
        )

        self.tray_icon = pystray.Icon("GitPulse", image, "GitPulse — GitHub Activity Tracker", menu)
        threading.Thread(target=self.tray_icon.run, daemon=True).start()

    def get_hwnd(self):
        if sys.platform == "win32":
            user32 = ctypes.windll.user32
            return user32.FindWindowW(None, WINDOW_TITLE)
        return None

    def show_window(self):
        self.is_hidden = False
        hwnd = self.get_hwnd()
        if hwnd:
            ctypes.windll.user32.ShowWindow(hwnd, 9)  # SW_RESTORE
            ctypes.windll.user32.ShowWindow(hwnd, 5)  # SW_SHOW
            ctypes.windll.user32.SetForegroundWindow(hwnd)
        if self.window:
            try:
                self.window.show()
                self.window.restore()
            except Exception:
                pass

    def hide_to_tray(self):
        self.is_hidden = True
        hwnd = self.get_hwnd()
        if hwnd:
            ctypes.windll.user32.ShowWindow(hwnd, 0)  # SW_HIDE
        elif self.window:
            try:
                self.window.hide()
            except Exception:
                pass
        ts = datetime.now().strftime("%H:%M:%S")
        self.log_history.append(f"[{ts}]  📌 Minimized to System Tray (Hidden Icons). Running in background.")

    def toggle_window(self):
        if self.is_hidden:
            self.show_window()
        else:
            self.hide_to_tray()

    def exit_app(self):
        self.is_exiting = True
        self.stop()
        if self.tray_icon:
            try:
                self.tray_icon.stop()
            except Exception:
                pass
        if self.window:
            try:
                self.window.destroy()
            except Exception:
                pass
        os._exit(0)

    def log(self, msg: str):
        ts = datetime.now().strftime("%H:%M:%S")
        formatted = f"[{ts}]  {msg}"
        self.log_history.append(formatted)
        if self.window and not self.is_hidden:
            try:
                safe_msg = formatted.replace("'", "\\'").replace('"', '\\"')
                self.window.evaluate_js(f"addLog('{safe_msg}')")
            except Exception:
                pass

    def _delayed_start(self):
        time.sleep(1)
        self.start()

    def start(self):
        if self.repo_path is None or not is_git_repo(self.repo_path):
            self.log("⚠️ Cannot start: No valid repository connected.")
            return
        self.running = True
        if self.window:
            try:
                self.window.evaluate_js("updateRunningState(true)")
            except Exception:
                pass
        self.log("🚀 GitPulse active — background activity loop active.")
        self.restart_schedule()

    def stop(self):
        self.running = False
        if self._timer is not None:
            self._timer.cancel()
            self._timer = None
        self.log("⏸ GitPulse stopped.")

    def restart_schedule(self):
        if self._timer is not None:
            self._timer.cancel()
            self._timer = None
        if not self.running:
            return

        delay_seconds = self.interval_minutes * 60
        self._next_run_epoch = time.time() + delay_seconds
        self.log(f"⏱ Next pulse scheduled in {self.interval_minutes} min.")

        self._timer = threading.Timer(delay_seconds, self._run_cycle)
        self._timer.daemon = True
        self._timer.start()

    def run_test_pulse(self):
        if self.repo_path is None or not is_git_repo(self.repo_path):
            self.log("⚠️ Cannot test: No repository connected.")
            return

        def _bg_test():
            self.log("━━━ Manual Test Pulse Started ━━━")
            ok = gitpulse_cycle(self.repo_path, self.log)
            if ok:
                self._pulse_count += 1
                self._last_pulse_str = datetime.now().strftime("%H:%M:%S")
                if self.window:
                    self.window.evaluate_js(f"updatePulseCounterUI({self._pulse_count}, '{self._last_pulse_str}')")
                self.log("✅ Manual test pulse complete — pushed to GitHub.")
            else:
                self.log("⚠️ Test pulse finished with warnings.")
            self.log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

        threading.Thread(target=_bg_test, daemon=True).start()

    def _run_cycle(self):
        if not self.running:
            return
        self.log("━━━ Automated Pulse Cycle Started ━━━")
        success = gitpulse_cycle(self.repo_path, self.log)
        if success:
            self._pulse_count += 1
            self._last_pulse_str = datetime.now().strftime("%H:%M:%S")
            if self.window:
                self.window.evaluate_js(f"updatePulseCounterUI({self._pulse_count}, '{self._last_pulse_str}')")
            self.log("✅ Pulse complete — commit pushed to GitHub.")
        else:
            self.log("⚠️ Pulse cycle completed with issues (will retry next interval).")
        self.log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        if self.running:
            self.restart_schedule()

    def _heartbeat_loop(self):
        while True:
            time.sleep(1)
            if self.running and self._next_run_epoch > 0 and self.window:
                remaining = max(0, int(self._next_run_epoch - time.time()))
                total = self.interval_minutes * 60
                try:
                    self.window.evaluate_js(f"updateCountdownUI({remaining}, {total})")
                except Exception:
                    pass


# ═══════════════════════════════════════════════════════════════════════
#  Main Launch
# ═══════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    app_instance = GitPulseApp()
    api = JsApi(app_instance)

    # Initialize System Tray Icon
    app_instance.setup_tray()

    window = webview.create_window(
        title=WINDOW_TITLE,
        html=HTML_CONTENT,
        js_api=api,
        width=680,
        height=620,
        resizable=True,
        min_size=(620, 540),
        background_color="#090d16"
    )
    app_instance.window = window

    # Intercept window close button (X) to hide to system tray instead of quitting
    def on_closing():
        if app_instance.is_exiting:
            return True
        threading.Thread(target=app_instance.hide_to_tray, daemon=True).start()
        return False

    window.events.closing += on_closing

    webview.start(debug=False)
